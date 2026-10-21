/* A4-2 규칙 엔진의 JavaScript 이식판.
   src/patterns.py · normalize.py · extract.py · lexicon.py(Matcher) · sentiment.py · aspect.py 를 한 줄씩 옮겼다.
   사전 표면형(활용 변이)과 정규식 소스는 작성 당시 Python이 만든 것을 빌드 때 그대로 받았다.
   작성 당시 Node에서 이 파일을 실행해 Python 결과와 대조했다. */
(function () {
  "use strict";

  // ───────────────────────── 한글 음절 ─────────────────────────
  const SBASE = 0xac00, SEND = 0xd7a3;
  const isSyl = (ch) => typeof ch === "string" && ch.length === 1 && ch.charCodeAt(0) >= SBASE && ch.charCodeAt(0) <= SEND;
  const splitSyl = (ch) => { const c = ch.charCodeAt(0) - SBASE; return [Math.floor(c / 588), Math.floor((c % 588) / 28), c % 28]; };
  const joinSyl = (c, j, t = 0) => String.fromCharCode(SBASE + c * 588 + j * 28 + t);
  const base = (ch) => { if (!isSyl(ch)) return ch; const [c, j] = splitSyl(ch); return joinSyl(c, j); };
  const isOpen = (ch) => isSyl(ch) && splitSyl(ch)[2] === 0;
  const CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ";
  const JUNG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ";
  const JONG = ["", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ", "ㄻ", "ㄼ", "ㄽ", "ㄾ", "ㄿ", "ㅀ", "ㅁ", "ㅂ", "ㅄ", "ㅅ", "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"];
  const jamo = (ch) => { if (!isSyl(ch)) return [ch]; const [c, j, t] = splitSyl(ch); return [CHO[c], JUNG[j], JONG[t]].filter(Boolean); };

  // 활용 변이(설명용 화면에서만 쓴다. 매칭에 쓰는 표면형은 Python이 만든 것을 받는다)
  const BRIGHT = new Set(["ㅏ", "ㅑ", "ㅗ"].map((v) => JUNG.indexOf(v)));
  const CONTRACT = { "ㅣ": "ㅕ", "ㅜ": "ㅝ", "ㅗ": "ㅘ", "ㅚ": "ㅙ" };
  function predicateVariants(stem) {
    const out = [stem];
    const last = stem[stem.length - 1];
    if (!isSyl(last)) return out;
    const [c, j, t] = splitSyl(last);
    const head = stem.slice(0, -1);
    const vowel = JUNG[j];
    if (t === 0) {
      if (last === "하") out.push(head + "해");
      else if (last === "르" && head && isOpen(head[head.length - 1])) {
        const [pc, pj] = splitSyl(head[head.length - 1]);
        const nv = BRIGHT.has(pj) ? "ㅏ" : "ㅓ";
        out.push(head.slice(0, -1) + joinSyl(pc, pj, JONG.indexOf("ㄹ")) + joinSyl(CHO.indexOf("ㄹ"), JUNG.indexOf(nv)));
      } else if (vowel === "ㅡ") {
        const prev = head[head.length - 1];
        const bright = Boolean(head) && isSyl(prev) && BRIGHT.has(splitSyl(prev)[1]);
        out.push(head + joinSyl(c, JUNG.indexOf(bright ? "ㅏ" : "ㅓ")));
      } else if (CONTRACT[vowel]) out.push(head + joinSyl(c, JUNG.indexOf(CONTRACT[vowel])));
    } else if (JONG[t] === "ㅂ" && stem.length >= 2) {
      out.push(head + joinSyl(c, j) + "우", head + joinSyl(c, j) + "워");
    } else if (JONG[t] === "ㅅ" && stem === "낫") out.push("나으", "나아");
    return out;
  }

  // ───────────────────────── 매칭기 ─────────────────────────
  class Matcher {
    constructor(entries) {
      this.index = new Map();
      this.emoticons = new Map();
      const seen = new Set();
      for (const e of entries) {
        if (e.kind === "EMO") { if (!this.emoticons.has(e.term)) this.emoticons.set(e.term, e); continue; }
        for (const s of e.forms) {
          if (seen.has(s)) continue;
          seen.add(s);
          const f = { surface: s, entry: e, ext: !e.flags.includes("noext") && isOpen(s[s.length - 1]) };
          const k = base(s[0]);
          if (!this.index.has(k)) this.index.set(k, []);
          this.index.get(k).push(f);
        }
      }
      for (const list of this.index.values()) list.sort((a, b) => b.surface.length - a.surface.length);
    }
    matchAt(text, i) {
      const list = this.index.get(base(text[i]));
      if (!list) return null;
      let best = null;
      for (const f of list) {
        const s = f.surface, n = s.length;
        if (i + n > text.length || (best && n < best[0].surface.length)) continue;
        if (text.slice(i, i + n - 1) !== s.slice(0, -1)) continue;
        const last = text[i + n - 1];
        let exact;
        if (last === s[n - 1]) exact = true;
        else if (f.ext && isSyl(last) && base(last) === s[n - 1]) exact = false;
        else continue;
        const fl = f.entry.flags;
        const atStart = i === 0 || !isSyl(text[i - 1]);
        const atEnd = i + n === text.length || !isSyl(text[i + n]);
        if ((fl.includes("start") || fl.includes("glue")) && !atStart) continue;
        if (fl.includes("exact") && !(atStart && atEnd)) continue;
        if (fl.includes("end") && !atEnd) continue;
        if (best === null || n > best[0].surface.length || (exact && !best[1])) best = [f, exact];
      }
      return best;
    }
    find(text) {
      const hits = [];
      let i = 0;
      while (i < text.length) {
        const m = this.matchAt(text, i);
        if (m) {
          const [f, exact] = m;
          const n = f.surface.length;
          hits.push({ kind: f.entry.kind, entry: f.entry, start: i, end: i + n, surface: text.slice(i, i + n), exact });
          i += n;
        } else i += 1;
      }
      const kept = [];
      hits.forEach((h, k) => {
        if (h.entry.flags.includes("glue")) {
          const whole = h.end === text.length || !isSyl(text[h.end]);
          const nxt = hits[k + 1];
          const glued = nxt !== undefined && nxt.start === h.end && nxt.kind === "SENTI";
          if (!(whole || glued)) return;
        }
        if (h.kind === "BLOCK") return;
        kept.push(h);
      });
      return kept;
    }
  }

  // ───────────────────────── 감성 분석 ─────────────────────────
  const TOKEN_RE = /(?<hangul>[가-힣]+)|(?<emo>\^[_\-.ㅡ~o]?\^|[-ㅡ][_.][-ㅡ]|;{2,}|[♥♡❤]+)|(?<jamo>[ㄱ-ㅎㅏ-ㅣ]+)|(?<latin>[a-z]+)|(?<num>[0-9]+(?:[.,][0-9]+)*)|(?<punct>[.!?…~,]+)|(?<other>\S)/gu;
  const CLAUSE_PUNCT = new Set([".", "!", "?", "…", "~", ","]);
  const STRONG_CONJ = new Set(["하지만", "그러나", "그런데", "근데", "그래도", "반면", "반면에", "그치만", "그렇지만", "허나", "다만"]);
  const RATING_RE = /(?<![0-9.])(-?[0-9]{1,2}(?:\.[0-9])?)[ ]?점(?![ ]?만점)(?!수)/g;
  const STAR_RE = /별[ ]?(?:0|1|한|하나|반)[ ]?개/g;
  const AFTER_JI = /(?<!까)지(?:는|도|를|가|들)?[ ]?$/;

  const normalizeText = (t) => t.normalize("NFC").toLowerCase().replace(/\s+/g, " ").trim();

  function canonicalEmo(kind, s) {
    if (kind === "emo") {
      if (s.startsWith("^")) return "^^";
      if ("-ㅡ".includes(s[0])) return "-_-";
      if (s.startsWith(";")) return ";;";
      return s[0];
    }
    s = s.replace(/ㅜ/g, "ㅠ");
    return s.replace(/(.)\1+/g, "$1$1");
  }

  function tokenize(text) {
    const out = [];
    let eojeol = 0;
    for (const m of text.matchAll(TOKEN_RE)) {
      if (m.index > 0 && text[m.index - 1] === " ") eojeol += 1;
      const kind = Object.keys(m.groups).find((k) => m.groups[k] !== undefined);
      out.push({ text: m[0], kind, start: m.index, end: m.index + m[0].length, eojeol });
    }
    return out;
  }

  function endsWithContrast(word) {
    if (word.endsWith("지만") || word.endsWith("으나")) return "strong";
    if (word.endsWith("데") && word.length >= 2) {
      const prev = word[word.length - 2];
      if ("는던".includes(prev) || (isSyl(prev) && splitSyl(prev)[2] === 4)) return "weak";
    }
    return null;
  }

  function clauseMap(text, tokens) {
    const clause = new Array(text.length + 1).fill(0);
    let cid = 0, lastStrong = null;
    const after = new Set(), before = new Set();
    for (const m of text.matchAll(/\S+/g)) {
      const w = m[0], s = m.index;
      const core = w.replace(/[^가-힣]+$/, "");
      if (STRONG_CONJ.has(core)) { before.add(s); lastStrong = s; }
      else if (core) {
        const c = endsWithContrast(core);
        if (c) { after.add(s + core.length); if (c === "strong") lastStrong = s + core.length; }
      }
    }
    const punctAt = new Set(tokens.filter((t) => t.kind === "punct" && [...t.text].some((ch) => CLAUSE_PUNCT.has(ch))).map((t) => t.start));
    for (let i = 0; i <= text.length; i++) {
      if (before.has(i) || after.has(i)) cid += 1;
      clause[i] = cid;
      if (punctAt.has(i)) cid += 1;
    }
    return [clause, lastStrong];
  }

  function eojeolIndex(text) {
    const out = [];
    let k = 0;
    for (const ch of text) { out.push(k); if (ch === " ") k += 1; }
    // 위 for…of는 코드포인트 단위라 서로게이트 쌍이 있으면 길이가 달라진다. 인덱스 단위로 다시 맞춘다
    if (out.length !== text.length) {
      out.length = 0; k = 0;
      for (let i = 0; i < text.length; i++) { out.push(k); if (text[i] === " ") k += 1; }
    }
    out.push(k);
    return out;
  }

  const DEFAULT_CONFIG = { negation: true, intensifier: true, double_negation: true, contrast: false, orphan: false,
    rating: false, emoticon: false, tie_label: 0, neg_window: 3, int_window: 2, orphan_score: -1, rating_score: 2 };

  const contrastFactor = (cfg, lastStrong, pos) => (!cfg.contrast || lastStrong === null ? 1 : pos < lastStrong ? 0.5 : 1.5);
  const afterJi = (text, pos) => AFTER_JI.test(text.slice(Math.max(0, pos - 4), pos));

  function modifiesNext(hits, j, eo) {
    const m = hits[j];
    for (const n of hits.slice(j + 1)) {
      if (n.kind === "SENTI") return eo[n.start] - eo[m.start] <= 1;
      if (eo[n.start] - eo[m.start] > 1) break;
    }
    return false;
  }

  const round6 = (x) => { const r = Math.round(x * 1e6) / 1e6; return r === 0 ? 0 : r; };

  function makeAnalyzer(matcher, josa) {
    function analyze(raw, cfgIn) {
      const cfg = Object.assign({}, DEFAULT_CONFIG, cfgIn || {});
      const text = normalizeText(raw);
      const tokens = tokenize(text);
      let hits = matcher.find(text);
      if (cfg.emoticon) {
        for (const t of tokens) {
          if (t.kind === "emo" || t.kind === "jamo" || t.kind === "latin") {
            const e = matcher.emoticons.get(canonicalEmo(t.kind, t.text));
            if (e) hits.push({ kind: "EMO", entry: e, start: t.start, end: t.end, surface: t.text, exact: true });
          }
        }
        hits = hits.map((h, i) => [h, i]).sort((a, b) => a[0].start - b[0].start || a[1] - b[1]).map((x) => x[0]);
      }
      const eo = eojeolIndex(text);
      const [clause, lastStrong] = clauseMap(text, tokens);
      const used = new Set();
      const items = [];
      hits.forEach((h, k) => {
        if (h.kind === "EMO") {
          const c = contrastFactor(cfg, lastStrong, h.start);
          items.push({ surface: h.surface, term: h.entry.term, base: h.entry.score, start: h.start, modifiers: [], negators: [], contrast: c, value: h.entry.score * c, kind: "EMO", negation_factor: 1 });
          return;
        }
        if (h.kind !== "SENTI") return;
        const item = { surface: h.surface, term: h.entry.term, base: h.entry.score, start: h.start, modifiers: [], negators: [], contrast: 1, value: 0, kind: "SENTI", negation_factor: 1 };
        let factor = 1, flips = 0;
        const fixed = h.entry.flags.includes("keep");
        for (let j = k - 1; j >= 0; j--) {
          const m = hits[j];
          if (clause[m.start] !== clause[h.start] || m.kind === "SENTI") break;
          const dist = eo[h.start] - eo[m.start];
          if ((m.kind === "INT" || m.kind === "DIM") && cfg.intensifier && dist <= cfg.int_window) {
            factor *= m.entry.score;
            item.modifiers.push([m.surface, m.entry.score]);
          } else if (m.kind === "NEG_PRE" && cfg.negation && !fixed && dist <= 1 && !used.has(j)) {
            used.add(j); flips += 1; item.negators.push(m.surface);
          }
        }
        if (cfg.negation && !fixed) {
          for (let j = k + 1; j < hits.length; j++) {
            const m = hits[j];
            if (clause[m.start] !== clause[h.start] || m.kind === "SENTI") break;
            if (eo[m.start] - eo[h.end - 1] > cfg.neg_window) break;
            if (used.has(j)) continue;
            let isPost;
            if (m.kind === "NEG_POST") isPost = !m.entry.flags.includes("afterji") || afterJi(text, m.start);
            else isPost = m.kind === "NEG_PRE" && !modifiesNext(hits, j, eo);
            if (isPost) { used.add(j); flips += 1; item.negators.push(m.surface); }
          }
          if (!cfg.double_negation) flips = Math.min(flips, 1);
        }
        const sign = flips % 2 ? -1 : 1;
        item.negation_factor = sign;
        item.contrast = contrastFactor(cfg, lastStrong, h.start);
        item.value = item.base * factor * sign * item.contrast;
        items.push(item);
      });
      const orphans = [];
      if (cfg.orphan) hits.forEach((m, j) => {
        if ((m.kind === "NEG_PRE" || m.kind === "NEG_POST") && !used.has(j)) orphans.push({ surface: m.surface, start: m.start, value: cfg.orphan_score });
      });
      let rating = null;
      if (cfg.rating) {
        const found = [];
        for (const rm of text.matchAll(RATING_RE)) {
          const v = parseFloat(rm[1]);
          if (v <= 4) found.push([rm.index, { text: rm[0], points: v, value: -cfg.rating_score }]);
          else if (v >= 8 && v <= 10) found.push([rm.index, { text: rm[0], points: v, value: cfg.rating_score }]);
        }
        for (const rm of text.matchAll(STAR_RE)) found.push([rm.index, { text: rm[0], points: null, value: -cfg.rating_score }]);
        if (found.length) rating = found.reduce((a, b) => (b[0] > a[0] ? b : a))[1];
      }
      let s = 0;
      for (const it of items) s += it.value;
      let so = 0;
      for (const o of orphans) so += o.value;
      const score = round6(s + so + (rating ? rating.value : 0));
      const tie = score === 0;
      const label = tie ? cfg.tie_label : score > 0 ? 1 : 0;
      return { text: raw, normalized: text, score, label, decided_by_tie: tie, items, tokens: tokens.map((t) => t.text), pieces: pieces(text, tokens, hits, josa), rating, orphans, hits };
    }
    return analyze;
  }

  function pieces(text, tokens, hits, josa) {
    const role = { SENTI: "senti", EMO: "emo", INT: "int", DIM: "int", NEG_PRE: "neg", NEG_POST: "neg" };
    const byStart = new Map(hits.map((h) => [h.start, h]));
    const cover = new Map();
    hits.forEach((h, idx) => { for (let i = h.start; i < h.end; i++) cover.set(i, [h, idx]); });
    const out = [];
    for (const t of tokens) {
      if (t.kind !== "hangul") {
        const h = byStart.get(t.start);
        out.push([t.text, h ? role[h.kind] : t.kind]);
        continue;
      }
      let segs = [];
      for (let i = t.start; i < t.end; i++) {
        const c = cover.get(i);
        const key = c ? c[1] : null;
        const r = c ? role[c[0].kind] : "rest";
        const last = segs[segs.length - 1];
        if (last && last[2] === key && last[1] === r) last[0] += text[i];
        else segs.push([text[i], r, key]);
      }
      segs = segs.map((x) => [x[0], x[1]]);
      const lastSeg = segs[segs.length - 1];
      if (lastSeg && lastSeg[1] === "rest" && !lastSeg[0].endsWith("지만")) {
        const gap = lastSeg[0];
        for (const j of josa) {
          if (gap.endsWith(j) && gap.length - j.length >= 2) { segs.splice(segs.length - 1, 1, [gap.slice(0, -j.length), "rest"], [j, "josa"]); break; }
        }
      }
      const merged = [];
      for (const sg of segs) {
        const m = merged[merged.length - 1];
        if (m && m[1] === "neg" && sg[1] === "rest") merged[merged.length - 1] = [m[0] + sg[0], "neg"];
        else merged.push(sg);
      }
      out.push(...merged);
    }
    return out;
  }

  // ───────────────────────── 정보 추출 ─────────────────────────
  const MONTHS = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6, jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12 };
  const HANGUL_DIGITS = { "일": 1, "이": 2, "삼": 3, "사": 4, "오": 5, "육": 6, "칠": 7, "팔": 8, "구": 9 };
  const SMALL = { "십": 10, "백": 100, "천": 1000 };
  const BIG = { "만": 1e4, "억": 1e8, "조": 1e12 };
  const twoDigitYear = (yy) => (yy >= 69 ? 1900 + yy : 2000 + yy);
  const pad = (n, w = 2) => String(n).padStart(w, "0");
  const daysIn = (y, m) => [31, (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0 ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1];
  function isoDate(y, m, d) {
    const yy = y === null ? 2000 : y;
    if (yy < 1 || yy > 9999 || m < 1 || m > 12 || d < 1 || d > daysIn(yy, m)) return null;
    return y === null ? `--${pad(m)}-${pad(d)}` : `${pad(y, 4)}-${pad(m)}-${pad(d)}`;
  }

  /* 한글 수사 금액: 만 아래 자리(section)를 모으다가 큰 단위를 만나면 곱해서 total에 더한다.
     trace에 단계별 상태를 남긴다(학습 화면의 표). */
  function parseKoreanAmount(text, trace) {
    const s = text.replace(/ /g, "");
    if (!/[0-9십백천만억조]/.test(s)) return null;
    const tokens = s.match(/[0-9][0-9,]*(?:\.[0-9]+)?|[일이삼사오육칠팔구]|[십백천]|[만억조]/g) || [];
    if (tokens.join("") !== s) return null;
    let total = 0, section = 0, num = null;
    for (const tok of tokens) {
      if (/^[0-9]/.test(tok)) { if (num !== null) return null; num = parseFloat(tok.replace(/,/g, "")); }
      else if (tok in HANGUL_DIGITS) { if (num !== null) return null; num = HANGUL_DIGITS[tok]; }
      else if (tok in SMALL) { section += (num !== null ? num : 1) * SMALL[tok]; num = null; }
      else { section += num !== null ? num : 0; total += (section ? section : 1) * BIG[tok]; section = 0; num = null; }
      if (trace) trace.push({ tok, num, section, total });
    }
    total += section + (num !== null ? num : 0);
    return Math.round(total);
  }

  function luhnOk(digits) {
    let total = 0;
    [...digits].reverse().forEach((ch, i) => { let d = +ch; if (i % 2 === 1) d = d * 2 > 9 ? d * 2 - 9 : d * 2; total += d; });
    return total % 10 === 0;
  }
  function rrnChecksumOk(d13) {
    const w = [2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5];
    let s = 0;
    for (let i = 0; i < 12; i++) s += +d13[i] * w[i];
    return (11 - (s % 11)) % 10 === +d13[12];
  }
  const TRAILING = ".,;:!?'\"";
  const CLOSERS = { ")": "(", "]": "[", "}": "{" };
  const countCh = (s, c) => s.split(c).length - 1;
  function trimUrl(raw) {
    while (raw) {
      const last = raw[raw.length - 1];
      if (TRAILING.includes(last)) raw = raw.slice(0, -1);
      else if (CLOSERS[last] && countCh(raw, last) > countCh(raw, CLOSERS[last])) raw = raw.slice(0, -1);
      else break;
    }
    return raw;
  }
  const dollarsToCents = (s) => Math.round(parseFloat(s.replace(/,/g, "")) * 100);

  function normalize(kind, g, raw) {
    if (kind === "email") return [`${g.local}@${g.domain.toLowerCase()}`, {}];
    if (kind === "phone") {
      if (g.rep) return [`${g.rep}-${g.rep_last}`, { kind: "대표번호" }];
      const area = g.area_i ? "0" + g.area_i : g.area;
      return [`${area}-${g.mid}-${g.last}`, { kind: area.startsWith("01") ? "휴대전화" : "일반" }];
    }
    if (kind === "date") {
      let iso;
      if (g.m) {
        const y = g.y;
        const year = y === undefined ? null : y.length === 4 ? +y : twoDigitYear(+y);
        iso = isoDate(year, +g.m, +g.d);
      } else if (g.m2) {
        const y = g.y2;
        iso = isoDate(y.length === 4 ? +y : twoDigitYear(+y), +g.m2, +g.d2);
      } else iso = isoDate(+g.y3, MONTHS[g.mon.slice(0, 3).toLowerCase()], +g.d3);
      return iso ? [iso, {}] : null;
    }
    if (kind === "money") {
      if (g.krw !== undefined) { const v = parseKoreanAmount(g.krw); return v !== null ? [v, { currency: "KRW" }] : null; }
      if (g.won_sym) return [Math.trunc(parseFloat(g.won_sym.replace(/,/g, ""))), { currency: "KRW" }];
      return [dollarsToCents(g.usd || g.usd2), { currency: "USD", unit: "cent" }];
    }
    if (kind === "url") {
      const scheme = (g.scheme || "http").toLowerCase();
      const host = g.host.toLowerCase();
      let port = g.port;
      if (port && ((scheme === "http" && port === "80") || (scheme === "https" && port === "443"))) port = undefined;
      return [`${scheme}://${host}${port ? ":" + port : ""}${g.rest || ""}`, {}];
    }
    if (kind === "rrn") {
      const digits = g.birth + g.back;
      const yy = +digits.slice(0, 2), mm = +digits.slice(2, 4), dd = +digits.slice(4, 6);
      const century = { 1: 1900, 2: 1900, 3: 2000, 4: 2000, 5: 1900, 6: 1900, 7: 2000, 8: 2000 }[digits[6]];
      if (isoDate(century + yy, mm, dd) === null) return null;
      return [`${g.birth}-${g.back}`, { checksum: rrnChecksumOk(digits) }];
    }
    if (kind === "card") {
      const digits = raw.replace(/[ -]/g, "");
      const groups = digits.length === 16 ? [0, 4, 8, 12].map((i) => digits.slice(i, i + 4)) : [digits.slice(0, 4), digits.slice(4, 10), digits.slice(10)];
      return [groups.join("-"), { luhn: luhnOk(digits) }];
    }
    if (kind === "address") return [raw.trim().replace(/\s+/g, " "), { sido: g.sido, sigungu: g.sigungu.trim() }];
    throw new Error(kind);
  }

  function makeExtractor(patterns, priority) {
    const compiled = {};
    for (const [k, src] of Object.entries(patterns)) compiled[k] = new RegExp(src, "g");
    function candidates(text, types) {
      const found = [];
      for (const kind of types) {
        for (const m of text.matchAll(compiled[kind])) {
          let raw = m[0], start = m.index, end = m.index + raw.length;
          const g = Object.assign({}, m.groups);
          if (kind === "url") {
            const trimmed = trimUrl(raw);
            const removed = raw.length - trimmed.length;
            end -= removed;
            if (g.rest) g.rest = g.rest.slice(0, g.rest.length - removed);
            raw = trimmed;
          }
          const r = normalize(kind, g, raw);
          if (r === null) continue;
          found.push({ type: kind, text: raw, start, end, value: r[0], info: r[1] });
        }
      }
      return found;
    }
    function resolve(found) {
      const order = found.map((e, i) => [e, i]).sort((a, b) => (b[0].end - b[0].start) - (a[0].end - a[0].start)
        || priority.indexOf(a[0].type) - priority.indexOf(b[0].type) || a[0].start - b[0].start || a[1] - b[1]).map((x) => x[0]);
      const kept = [];
      for (const e of order) if (kept.every((k) => e.end <= k.start || e.start >= k.end)) kept.push(e);
      return kept.sort((a, b) => a.start - b.start);
    }
    const extract = (text, types) => resolve(candidates(text, types));
    return { extract, candidates, compiled };
  }

  function maskValue(e) {
    const v = String(e.value);
    if (e.type === "phone") { const p = v.split("-"); return p.length === 3 ? `${p[0]}-${"*".repeat(p[1].length)}-${p[2]}` : `${p[0]}-****`; }
    if (e.type === "email") { const i = v.indexOf("@"); const local = v.slice(0, i); return `${local.slice(0, 2)}${"*".repeat(Math.max(3, local.length - 2))}@${v.slice(i + 1)}`; }
    if (e.type === "rrn") return v.slice(0, 8) + "*".repeat(6);
    if (e.type === "card") {
      const digits = v.replace(/-/g, "");
      const masked = digits.slice(0, 6) + "*".repeat(digits.length - 10) + digits.slice(-4);
      let i = 0;
      return v.split("-").map((p) => { const s = masked.slice(i, i + p.length); i += p.length; return s; }).join("-");
    }
    if (e.type === "address") return `${e.info.sido} ${e.info.sigungu} ****`;
    return "*".repeat(e.text.length);
  }

  // ───────────────────────── 엔진 조립 ─────────────────────────
  function makeEngine(data) {
    const entries = data.entries; // modifiers + 직접 구축 사전(Python build_entries("custom") 순서)
    const matcher = new Matcher(entries);
    const analyze = makeAnalyzer(matcher, data.josa);
    const ex = makeExtractor(data.patterns, data.priority);
    const extract = (text, types) => ex.extract(text, types || data.core_types);
    function mask(text, types) {
      const ents = ex.extract(text, types || data.pii_types);
      let out = "", last = 0;
      for (const e of ents) { out += text.slice(last, e.start) + maskValue(e); last = e.end; }
      return [out + text.slice(last), ents];
    }

    // 속성 분석(보너스 3)
    const aspectMention = new Matcher(data.aspects.mentions);
    const termToAspect = data.aspects.term_to_aspect;
    const contextByAspect = data.aspects.context; // {속성: [entry…]}
    const mods = entries.filter((e) => !["SENTI", "EMO", "BLOCK"].includes(e.kind));
    const rest = entries.filter((e) => ["SENTI", "EMO", "BLOCK"].includes(e.kind));
    const aspectCfg = { emoticon: true, orphan: true };
    const cache = new Map();
    function contextAnalyzer(present) {
      const key = present.join("|");
      if (!cache.has(key)) {
        const extra = present.flatMap((a) => contextByAspect[a] || []);
        cache.set(key, makeAnalyzer(new Matcher(mods.concat(extra, rest)), data.josa));
      }
      return cache.get(key);
    }
    function link(mentions, pos, mode) {
      if (mode !== "nearest") {
        const before = mentions.filter((m) => m[2] <= pos);
        if (before.length) return before.reduce((a, b) => (b[2] > a[2] ? b : a))[0];
      }
      return mentions.reduce((a, b) => {
        const ka = [Math.abs(a[2] - pos), a[2] > pos ? 1 : 0], kb = [Math.abs(b[2] - pos), b[2] > pos ? 1 : 0];
        return kb[0] < ka[0] || (kb[0] === ka[0] && kb[1] < ka[1]) ? b : a;
      })[0];
    }
    function aspects(raw, mode) {
      const text = normalizeText(raw);
      const [clause] = clauseMap(text, tokenize(text));
      const spans = [];
      let start = 0;
      for (let i = 1; i <= text.length; i++) if (i === text.length || clause[i] !== clause[start]) { spans.push([start, i]); start = i; }
      const result = { text: raw, aspects: {}, mentions: [], clauses: [] };
      for (const [a, b] of spans) {
        const seg = text.slice(a, b);
        if (!seg.trim()) continue;
        const mentions = aspectMention.find(seg).map((h) => [termToAspect[h.entry.term], h.surface, h.start]);
        result.mentions.push(...mentions.map((m) => [m[0], m[1], m[2] + a]));
        const present = [...new Set(mentions.map((m) => m[0]))].sort();
        const res = contextAnalyzer(present)(seg, aspectCfg);
        const evid = res.items.map((it) => [it.surface, it.value, it.start, it.term]).concat(res.orphans.map((o) => [o.surface, o.value, o.start, null]));
        const assigned = [];
        for (const [surface, value, pos, term] of evid) {
          if (value === 0) continue;
          let target = null;
          for (const asp of present) if (term && (contextByAspect[asp] || []).some((e) => e.term === term)) target = asp;
          if (target === null && mentions.length) target = link(mentions, pos, mode);
          target = target || "전체";
          const slot = result.aspects[target] || (result.aspects[target] = { score: 0, evidence: [] });
          slot.score += value;
          slot.evidence.push([surface, Math.round(value * 100) / 100]);
          assigned.push([surface, target]);
        }
        result.clauses.push({ text: seg.trim(), aspects: present, assigned });
      }
      for (const v of Object.values(result.aspects)) v.polarity = v.score > 0 ? "pos" : v.score < 0 ? "neg" : "neutral";
      return result;
    }
    function aspectPairs(raw, mode) {
      const r = aspects(raw, mode);
      return Object.entries(r.aspects).filter(([a, v]) => v.polarity !== "neutral" && a !== "전체").map(([a, v]) => [a, v.polarity]).sort();
    }

    return { analyze, extract, mask, aspects, aspectPairs, matcher, extractor: ex, normalizeText, tokenize, canonicalEmo, clauseMap, trimUrl,
      parseKoreanAmount, predicateVariants, jamo, base, isSyl, splitSyl, DEFAULT_CONFIG };
  }

  globalThis.A42 = { makeEngine, predicateVariants, parseKoreanAmount, jamo, base, isSyl, isOpen };
})();
