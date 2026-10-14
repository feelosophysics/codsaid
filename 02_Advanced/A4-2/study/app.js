/* A4-2 학습 화면. 계산은 모두 engine.js(A42)가 하고, 여기서는 그리기만 한다. */
(function () {
  "use strict";
  const D = JSON.parse(document.getElementById("study-data").textContent);
  const E = globalThis.A42.makeEngine(D.engine);
  const $ = (s, r = document) => r.querySelector(s);
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pct = (x, d = 1) => (x * 100).toFixed(d) + "%";
  const f3 = (x) => (x === null || x === undefined ? "—" : Number(x).toFixed(3));
  const sgn = (x) => (x > 0 ? "+" : "") + (Math.round(x * 1000) / 1000);
  const LABELS = D.engine.labels;
  const STEPS = D.engine.steps;
  const FINAL = D.engine.final_config;
  const REQUIRED = STEPS[4].config;

  // ───────── 테마 ─────────
  const themeBtn = $("#theme-btn");
  const themes = ["system", "light", "dark"], themeName = { system: "시스템", light: "라이트", dark: "다크" };
  let theme = "system";
  try { theme = localStorage.getItem("a42-theme") || "system"; } catch (e) { /* 저장소를 못 쓰면 시스템 설정 */ }
  const applyTheme = () => {
    if (theme === "system") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", theme);
    themeBtn.textContent = "테마: " + themeName[theme];
  };
  themeBtn.addEventListener("click", () => {
    theme = themes[(themes.indexOf(theme) + 1) % 3];
    try { localStorage.setItem("a42-theme", theme); } catch (e) { /* 무시 */ }
    applyTheme(); redrawCharts();
  });
  applyTheme();

  // ───────── 목차 강조 ─────────
  const links = [...document.querySelectorAll("#toc a")];
  const io = new IntersectionObserver((entries) => {
    for (const en of entries) if (en.isIntersecting) {
      links.forEach((a) => a.classList.toggle("on", a.getAttribute("href") === "#" + en.target.id));
    }
  }, { rootMargin: "-40% 0px -55% 0px" });
  document.querySelectorAll("main section").forEach((s) => io.observe(s));

  // ───────── 공용: 규칙 스위치 ─────────
  const RULES = [["negation", "부정어"], ["intensifier", "강조어"], ["double_negation", "이중부정"], ["emoticon", "이모티콘"],
    ["contrast", "대조 접속"], ["orphan", "고립 부정어"], ["rating", "평점 언급"]];
  function ruleToggles(box, initial, onChange) {
    const state = Object.assign({}, initial);
    const presets = [["사전만", STEPS[0].config], ["필수", REQUIRED], ["최종", FINAL]];
    box.innerHTML = presets.map(([n], i) => `<button type="button" class="preset" data-p="${i}">${n}</button>`).join("") +
      RULES.map(([k, n]) => `<label><input type="checkbox" data-k="${k}">${n}</label>`).join("");
    const sync = () => {
      box.querySelectorAll("input").forEach((i) => { i.checked = !!state[i.dataset.k]; });
      box.querySelectorAll(".preset").forEach((b) => {
        const p = presets[+b.dataset.p][1];
        b.setAttribute("aria-pressed", RULES.every(([k]) => !!p[k] === !!state[k]) ? "true" : "false");
      });
    };
    box.addEventListener("change", (e) => { if (e.target.dataset.k) { state[e.target.dataset.k] = e.target.checked; sync(); onChange(state); } });
    box.addEventListener("click", (e) => {
      const b = e.target.closest(".preset"); if (!b) return;
      Object.assign(state, presets[+b.dataset.p][1]); sync(); onChange(state);
    });
    sync();
    return state;
  }
  function segmented(box, options, value, onChange) {
    box.innerHTML = options.map(([v, n]) => `<button type="button" data-v="${v}">${n}</button>`).join("");
    const sync = () => box.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.v === value ? "true" : "false"));
    box.addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; value = b.dataset.v; sync(); onChange(value); });
    sync();
  }

  // ───────── 공용: 감성 결과 그리기 ─────────
  function piecesHTML(res) {
    let qi = 0, acc = "";
    return res.pieces.map(([t, role]) => {
      let cls = role;
      if (role === "senti" || role === "emo") {
        const it = res.items[qi];
        if (it) {
          cls += it.base > 0 ? " p" : " n";
          acc += t;
          if (acc === it.surface.replace(/ /g, "")) { qi += 1; acc = ""; }
        }
      }
      return `<span class="${cls}">${esc(t)}</span>`;
    }).join("");
  }
  function explainText(res) {
    const L = [];
    const senti = res.items.map((i) => `${i.surface}(${sgn(i.base)})`);
    L.push("감성 단어: " + (senti.join(", ") || "(없음)"));
    const negs = res.items.flatMap((i) => i.negators.map((n) => `'${n}'`));
    L.push("부정어: " + (negs.length ? negs.join(", ") + " → 반전" : "(없음)"));
    const mods = res.items.flatMap((i) => i.modifiers.map(([s, f]) => `'${s}' ×${f}`));
    L.push("강조·약화어: " + (mods.join(", ") || "(없음)"));
    const extra = [];
    if (res.items.some((i) => i.contrast !== 1)) extra.push("대조 접속: 앞 절 ×0.5, 뒤 절 ×1.5");
    res.orphans.forEach((o) => extra.push(`고립 부정어 '${o.surface}' ${sgn(o.value)}`));
    if (res.rating) extra.push(`평점 '${res.rating.text}' ${sgn(res.rating.value)}`);
    if (extra.length) L.push("확장 규칙: " + extra.join("; "));
    const terms = res.items.map((i) => {
      const p = [`(${sgn(i.base)})`];
      i.negators.forEach(() => p.push("(-1)"));
      i.modifiers.forEach(([, f]) => p.push(String(f)));
      if (i.contrast !== 1) p.push(String(i.contrast));
      return p.join(" × ");
    }).concat(res.orphans.map((o) => `(${sgn(o.value)})`), res.rating ? [`(${sgn(res.rating.value)})`] : []);
    L.push("", `계산: ${terms.join(" + ") || "0"} = ${sgn(res.score)}`);
    return L.join("\n");
  }
  function verdictHTML(res) {
    const p = res.label === 1;
    return `<div class="verdict ${p ? "p" : "n"}"><span class="dot"></span>${p ? "긍정" : "부정"} <small>${res.decided_by_tie ? "점수 0 — 단서가 없어 기본값(부정)" : "점수 " + sgn(res.score)}</small></div>`;
  }
  function sentimentBlock(text, cfg) {
    const r = E.analyze(text, cfg);
    return `<div class="pieces">${piecesHTML(r)}</div><div class="calc">${esc(explainText(r))}</div>${verdictHTML(r)}`;
  }

  // ───────── 00 통합 파이프라인 ─────────
  const LAB_EXAMPLES = [
    ["미션 예시", "문의: support@company.co.kr, 전화 02-1234-5678 일시: 2024년 3월 15일, 참가비: 50,000원"],
    ["부정+강조", "이 식당은 정말 맛있지 않았어요"],
    ["고객 불만", "주문일 2024.04.02, 금액 $59.90 결제했는데 배송이 너무 느려서 정말 실망했어요. 환불 요청합니다. 연락처 010-9876-5432"],
    ["속성 감성", "음식은 맛있는데 가격이 비싸요"],
    ["이중부정", "재미있지 않을 수 없다"],
    ["개인정보", "주민번호 900101-1234567, 카드 4518-4212-3456-7890, 배송지 서울특별시 강남구 테헤란로 123, 101동 202호"],
    ["규칙이 틀리는 문장", "최고라니요ㅋㅋㅋㅋ 최악입니다"],
  ];
  const labInput = $("#lab-input");
  $("#lab-chips").innerHTML = LAB_EXAMPLES.map(([n], i) => `<button type="button" data-i="${i}">${n}</button>`).join("");
  $("#lab-chips").addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; labInput.value = LAB_EXAMPLES[+b.dataset.i][1]; renderLab(); });
  labInput.value = LAB_EXAMPLES[2][1];
  const labCfg = ruleToggles($("#lab-toggles"), FINAL, () => renderLab());
  function entValue(e) {
    if (e.type === "money") return e.info.currency === "KRW" ? `${e.value.toLocaleString("ko-KR")}원 → ${e.value}` : `${e.value} 센트 (USD)`;
    return String(e.value);
  }
  function hideEntities(text, ents) {
    let out = "", last = 0;
    for (const e of ents) { out += text.slice(last, e.start) + "□"; last = e.end; }
    return out + text.slice(last);
  }
  function highlight(text, ents) {
    let out = "", last = 0;
    for (const e of ents) {
      out += esc(text.slice(last, e.start)) + `<mark class="ent" style="--ec:var(--t-${e.type})">${esc(e.text)}<sub>${LABELS[e.type]}</sub></mark>`;
      last = e.end;
    }
    return out + esc(text.slice(last));
  }
  function aspectHTML(r) {
    const cl = r.clauses.filter((c) => c.aspects.length || c.assigned.length).map((c) => `<li><span class="mono small">${esc(c.text)}</span> ${c.aspects.map((a) => `<span class="pill">${esc(a)}</span>`).join("")}${c.assigned.length ? " ← " + c.assigned.map(([s, t]) => `${esc(s)}→${esc(t)}`).join(", ") : ""}</li>`).join("");
    const res = Object.entries(r.aspects).map(([a, v]) => `<span class="verdict ${v.polarity === "pos" ? "p" : "n"}" style="font-size:var(--step-0);margin-right:14px"><span class="dot"></span>${esc(a)} ${v.polarity === "pos" ? "긍정" : v.polarity === "neg" ? "부정" : "중립"} <small>${sgn(v.score)}</small></span>`).join("");
    return `<ul class="small" style="margin:0 0 8px;padding-left:18px">${cl}</ul>${res || '<span class="empty">감성 단서 없음</span>'}`;
  }
  function renderLab() {
    const text = labInput.value;
    const ents = E.extract(text);
    $("#lab-ents").innerHTML = highlight(text, ents) || '<span class="empty">(입력 없음)</span>';
    $("#lab-entlist").innerHTML = ents.length ? ents.map((e) => `<dt><span class="swatch" style="--ec:var(--t-${e.type})"></span>${LABELS[e.type]}</dt><dd>${esc(entValue(e))}</dd>`).join("") : '<dt class="empty">추출된 정보 없음</dt><dd></dd>';
    const [masked, pii] = E.mask(text);
    $("#lab-mask").innerHTML = pii.length ? esc(masked) : '<span class="empty">가릴 개인정보 없음</span>';
    const hidden = hideEntities(text, ents);
    const r = E.analyze(hidden, labCfg);
    $("#lab-pieces").innerHTML = piecesHTML(r);
    $("#lab-calc").textContent = explainText(r);
    $("#lab-verdict").innerHTML = verdictHTML(r);
    $("#lab-aspect").innerHTML = aspectHTML(E.aspects(hidden, "preceding"));
  }
  labInput.addEventListener("input", renderLab);
  renderLab();

  // ───────── 01 요약 수치 ─────────
  const R = D.results;
  const testAb = R.sentiment.test.ablation;
  const tfCross = R.tfidf.crossover_n;
  $("#facts").innerHTML = [
    [f3(R.extraction.micro.f1), "정보 추출 micro F1 (정밀도 " + f3(R.extraction.micro.precision) + ")"],
    [pct(testAb[4].accuracy), "감성 test 정확도 — 필수 규칙"],
    [pct(testAb[8].accuracy), "감성 test 정확도 — 확장 규칙 포함"],
    [`${R.masking.leaks.length}/${R.masking.n_gold}`, "마스킹 유출 (보너스 1)"],
    [tfCross ? tfCross.toLocaleString() + "건" : "—", "TF-IDF가 규칙을 넘는 학습량 (보너스 2)"],
    [f3(R.aspect.preceding.pair.f1), "속성·극성 쌍 F1 (보너스 3)"],
  ].map(([b, s]) => `<div class="fact"><b>${b}</b><span>${s}</span></div>`).join("");

  // ───────── 02 정규식 문법 ─────────
  const CARDS = [
    ["문자 클래스와 범위", "[A-Za-z0-9._%+-]", "이메일 로컬 파트. \\w 대신 허용할 문자를 직접 적는다", "[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\\.[A-Za-z]{2,}", "문의: user.name+cs@shop.com, 실패: user@@x.com"],
    ["수량자 ? {m,n}", "[ .-]?  [0-9]{3,4}", "전화번호 구분자는 있어도 없어도 되고, 국번은 3~4자리", "01[016789][ .-]?[0-9]{3,4}[ .-]?[0-9]{4}", "010-1234-5678, 010.123.4567, 01012345678"],
    ["선택 | 와 묶음 (?:…)", "(?:02|0[3-6][1-5])", "지역번호 목록. (?:…)는 묶기만 하고 값을 저장하지 않는다", "(?:02|0[3-6][1-5])-[0-9]{3,4}-[0-9]{4}", "02-123-4567, 031-1234-5678, 071-123-4567"],
    ["캡처와 이름 있는 그룹", "(?<y>…)", "날짜의 연·월·일을 이름으로 꺼내 정규화에 쓴다", "(?<y>[0-9]{4})-(?<m>[0-9]{2})-(?<d>[0-9]{2})", "작성 2024-03-15 / 수정 2024-12-01"],
    ["역참조 \\k<이름>", "(?<sep>[./-])…\\k<sep>", "첫 구분자와 같은 구분자만 허용한다. 2024-01/15 같은 혼합은 거부", "[0-9]{4}(?<sep>[./-])[0-9]{1,2}\\k<sep>[0-9]{1,2}", "2024-01-15, 2024.01.15, 2024-01/15"],
    ["전방·후방 탐색", "(?<![0-9]) … (?![0-9])", "글자를 소비하지 않고 앞뒤만 확인한다. 더 긴 숫자열의 일부를 자르지 않게 막는다", "(?<![0-9])01[016789]-[0-9]{4}-[0-9]{4}(?![0-9])", "010-1234-5678 / 9010-1234-56789"],
    ["\\b를 쓰지 않는 이유", "(?![A-Za-z0-9-])", "Python의 \\b는 한글도 단어 문자로 본다. 'x.com입니다'에서 com과 입 사이가 경계가 아니라서 실패한다(JS의 \\b는 ASCII 기준이라 여기서는 통과한다). 범위를 직접 쓰면 두 언어가 같게 동작한다", "[a-z]+@[a-z]+\\.com(?![A-Za-z0-9-])", "메일은 test@x.com입니다"],
    ["반복되는 묶음", "(?:…[만억조][ ]?)*", "금액의 '1억 2천만'처럼 큰 단위 묶음이 여러 번 온다", "(?:[0-9]+[천]?[만억조][ ]?)*[0-9,]*[ ]?원", "총액 1억 2천만원, 월세 50만 원, 10,000원"],
  ];
  $("#rx-cards").innerHTML = CARDS.map(([t, s, d], i) => `<div class="card"><h4>${esc(t)}</h4><p class="mono" style="margin:0 0 6px">${esc(s)}</p><p class="small" style="margin:0 0 8px">${esc(d)}</p><button type="button" data-i="${i}">시험대에 올리기</button></div>`).join("");
  $("#rx-try-chips").innerHTML = "";
  const tryRe = $("#rx-try-re"), tryText = $("#rx-try-text");
  $("#rx-cards").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    const c = CARDS[+b.dataset.i]; tryRe.value = c[3]; tryText.value = c[4]; renderTry();
    tryRe.scrollIntoView({ block: "center", behavior: "smooth" });
  });
  function renderTry() {
    let re;
    try { re = new RegExp(tryRe.value, "g"); } catch (err) { $("#rx-try-out").innerHTML = `<p class="no">${esc(err.message)}</p>`; return; }
    const text = tryText.value;
    const ms = [...text.matchAll(re)].filter((m) => m[0].length);
    let html = "", last = 0;
    for (const m of ms) { html += esc(text.slice(last, m.index)) + `<span class="rxhit">${esc(m[0])}</span>`; last = m.index + m[0].length; }
    html += esc(text.slice(last));
    const rows = ms.map((m) => `<tr><td class="mono">${esc(m[0])}</td><td class="mono small">${m.groups ? Object.entries(m.groups).map(([k, v]) => `${esc(k)}=${esc(v ?? "∅")}`).join("  ") : m.slice(1).map((v, i) => `$${i + 1}=${esc(v ?? "∅")}`).join("  ")}</td></tr>`).join("");
    $("#rx-try-out").innerHTML = `<p class="textview">${html}</p><p class="small">일치 ${ms.length}개</p>${ms.length ? `<div class="scroll"><table><tr><th>일치</th><th>그룹</th></tr>${rows}</table></div>` : ""}`;
  }
  tryRe.value = CARDS[4][3]; tryText.value = CARDS[4][4];
  tryRe.addEventListener("input", renderTry); tryText.addEventListener("input", renderTry);
  renderTry();

  // ───────── 03 패턴 실험실 ─────────
  const TYPES = ["email", "phone", "date", "money", "url"];
  const HINTS = {
    email: "도전: e10 'user at domain dot com'을 잡아 보자. '@'를 '(?:@| at )'로 바꾸면 무엇이 같이 들어오나?",
    phone: "도전: p12 '공일공-일이삼사-오육칠팔'을 잡으려면 [0-9] 자리에 한글 숫자를 넣어야 한다. 그러면 '일이삼' 같은 일반 단어는 안전할까?",
    date: "도전: d12 '3/15/2024'(월/일/연)를 넣어 보자. '15/3/2024'(일/월/연)와 어떻게 구별할 것인가?",
    money: "도전: m13 '만원 버스'를 막아 보자. 원 뒤에 '버스'가 오면 거부하는 lookahead는 '만원 지하철'에도 통할까? 규칙이 끝없이 늘어나는 이유다.",
    url: "도전: u11 한글 경로를 허용하려면 [^\\s<>\"'가-힣]에서 가-힣을 빼면 된다. 그러면 u04처럼 URL 바로 뒤에 붙은 조사도 URL에 들어온다.",
  };
  const extCases = D.cases.extraction;
  let rxType = "phone";
  const rxEdit = $("#rx-edit");
  function verboseHTML(src) {
    return src.replace(/^\n/, "").split("\n").map((line) => {
      let i = -1;
      for (let k = 0; k < line.length; k++) if (line[k] === "#" && line[k - 1] !== "\\") { i = k; break; }
      return i < 0 ? esc(line) : esc(line.slice(0, i)) + `<span class="cm">${esc(line.slice(i))}</span>`;
    }).join("\n");
  }
  function scoreRegex(src, type) {
    const re = new RegExp(src, "g");
    let tp = 0, fp = 0, fn = 0;
    const fps = [], fns = [];
    for (const c of extCases) {
      let pred = [...c.text.matchAll(re)].map((m) => m[0]).filter(Boolean);
      if (type === "url") pred = pred.map(E.trimUrl).filter(Boolean);
      const gold = c.gold.filter((g) => g.type === type).map((g) => g.text);
      const pool = gold.slice();
      for (const p of pred) { const i = pool.indexOf(p); if (i >= 0) { pool.splice(i, 1); tp++; } else { fp++; fps.push([c, p]); } }
      fn += pool.length; pool.forEach((g) => fns.push([c, g]));
    }
    const P = tp + fp ? tp / (tp + fp) : 1, Rr = tp + fn ? tp / (tp + fn) : 1, F = P + Rr ? (2 * P * Rr) / (P + Rr) : 0;
    return { tp, fp, fn, P, R: Rr, F, fps, fns };
  }
  function caseLine(c, s) {
    const i = c.text.indexOf(s);
    const shown = i >= 0 ? esc(c.text.slice(0, i)) + `<span class="rxhit">${esc(s)}</span>` + esc(c.text.slice(i + s.length)) : esc(c.text) + ` <span class="mono">[${esc(s)}]</span>`;
    return `<p class="small" style="margin:0 0 6px"><span class="mono">${c.id}</span> ${shown}${c.fail ? ` <span class="pill">${esc(c.fail)}</span>` : ""}</p>`;
  }
  function renderRx() {
    $("#rx-verbose").innerHTML = verboseHTML(D.engine.pattern_sources[rxType]);
    $("#rx-hint").textContent = HINTS[rxType];
    let s;
    try { s = scoreRegex(rxEdit.value, rxType); $("#rx-err").textContent = ""; }
    catch (err) { $("#rx-err").textContent = "정규식 오류: " + err.message; return; }
    const b = scoreRegex(D.engine.patterns[rxType], rxType);
    const d = (x, y) => { const v = x - y; return Math.abs(v) < 1e-9 ? "" : ` <span class="${v > 0 ? "delta-up" : "delta-down"}">(${v > 0 ? "+" : ""}${v.toFixed(3)})</span>`; };
    $("#rx-score").innerHTML = `<span>정규식만 · ${LABELS[rxType]}</span><span>TP <b>${s.tp}</b></span><span>FP <b>${s.fp}</b></span><span>FN <b>${s.fn}</b></span>` +
      `<span>정밀도 <b>${f3(s.P)}</b>${d(s.P, b.P)}</span><span>재현율 <b>${f3(s.R)}</b>${d(s.R, b.R)}</span><span>F1 <b>${f3(s.F)}</b>${d(s.F, b.F)}</span>`;
    $("#rx-fn").innerHTML = s.fns.map(([c, g]) => caseLine(c, g)).join("") || '<p class="empty">없음</p>';
    $("#rx-fp").innerHTML = s.fps.map(([c, p]) => caseLine(c, p)).join("") || '<p class="empty">없음</p>';
  }
  segmented($("#rx-types"), TYPES.map((t) => [t, LABELS[t]]), rxType, (v) => { rxType = v; rxEdit.value = D.engine.patterns[v]; renderRx(); });
  rxEdit.value = D.engine.patterns[rxType];
  $("#rx-run").addEventListener("click", renderRx);
  rxEdit.addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) renderRx(); });
  $("#rx-reset").addEventListener("click", () => { rxEdit.value = D.engine.patterns[rxType]; renderRx(); });
  renderRx();
  const pt = R.extraction.per_type;
  $("#ext-table").innerHTML = `<tr><th>패턴</th><th class="num">TP</th><th class="num">FP</th><th class="num">FN</th><th class="num">정밀도</th><th class="num">재현율</th><th class="num">F1</th><th class="num">정규화</th></tr>` +
    TYPES.map((t) => `<tr><td><span class="swatch" style="--ec:var(--t-${t})"></span>${LABELS[t]}</td><td class="num">${pt[t].tp}</td><td class="num">${pt[t].fp}</td><td class="num">${pt[t].fn}</td><td class="num">${f3(pt[t].precision)}</td><td class="num">${f3(pt[t].recall)}</td><td class="num">${f3(pt[t].f1)}</td><td class="num">${pct(pt[t].normalization_accuracy, 0)}</td></tr>`).join("") +
    `<tr><td><b>전체(micro)</b></td><td class="num">${R.extraction.micro.tp}</td><td class="num">${R.extraction.micro.fp}</td><td class="num">${R.extraction.micro.fn}</td><td class="num"><b>${f3(R.extraction.micro.precision)}</b></td><td class="num"><b>${f3(R.extraction.micro.recall)}</b></td><td class="num"><b>${f3(R.extraction.micro.f1)}</b></td><td></td></tr>`;

  // ───────── 04 검증과 정규화 ─────────
  const AMTS = ["1억 2천만", "1,500만", "2.5억", "삼만오천", "오천", "만", "사"];
  $("#amt-chips").innerHTML = AMTS.map((a) => `<button type="button">${a}</button>`).join("");
  $("#amt-chips").addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; $("#amt-input").value = b.textContent; renderAmt(); });
  function renderAmt() {
    const trace = [];
    const v = E.parseKoreanAmount($("#amt-input").value, trace);
    $("#amt-trace").innerHTML = `<tr><th>토큰</th><th class="num">대기 숫자</th><th class="num">만 아래 자리(section)</th><th class="num">누적(total)</th></tr>` +
      trace.map((t) => `<tr><td class="mono">${esc(t.tok)}</td><td class="num">${t.num ?? "—"}</td><td class="num">${t.section.toLocaleString()}</td><td class="num">${t.total.toLocaleString()}</td></tr>`).join("");
    $("#amt-out").innerHTML = v === null ? '<span class="no">해석 불가 → 금액 후보에서 버린다 (예: "회사원"의 "사")</span>' : `결과: <b>${v.toLocaleString()}</b>원`;
  }
  $("#amt-input").addEventListener("input", renderAmt);
  renderAmt();
  function renderDates() {
    const parts = $("#date-input").value.split(",").map((s) => s.trim()).filter(Boolean);
    $("#date-out").innerHTML = `<tr><th>입력</th><th>정규식</th><th>검증 후</th></tr>` + parts.map((p) => {
      const raw = [...p.matchAll(E.extractor.compiled.date)].map((m) => m[0]);
      const ok = E.extract(p, ["date"]);
      return `<tr><td class="mono">${esc(p)}</td><td>${raw.length ? '<span class="ok">일치</span>' : '<span class="small">불일치</span>'}</td><td class="mono">${ok.length ? esc(ok[0].value) : raw.length ? '<span class="no">거부 (없는 날짜)</span>' : "—"}</td></tr>`;
    }).join("");
  }
  $("#date-input").addEventListener("input", renderDates);
  renderDates();
  $("#float-demo").textContent = String(0.1 + 0.2);

  // ───────── 05 감성 사전 ─────────
  function renderVariants() {
    const stem = $("#var-input").value.trim();
    if (!stem) { $("#var-out").innerHTML = ""; return; }
    const forms = E.predicateVariants(stem);
    const last = stem[stem.length - 1];
    const jm = E.jamo(last).join(" + ");
    const open = E.isSyl(last) && E.splitSyl(last)[2] === 0;
    const ext = (f) => {
      const l = f[f.length - 1];
      if (!E.isSyl(l) || E.splitSyl(l)[2] !== 0) return [];
      const [c, j] = E.splitSyl(l);
      return [4, 8, 16, 17, 20].map((t) => f.slice(0, -1) + String.fromCharCode(0xac00 + c * 588 + j * 28 + t));
    };
    $("#var-out").innerHTML = `<p class="small">마지막 음절 '${esc(last)}' = ${esc(jm)} ${open ? "(받침 없음 → 받침 확장 대상)" : "(받침 있음)"}</p>` +
      `<table><tr><th>표면형</th><th>받침 확장으로 함께 맞는 음절(ㄴ·ㄹ·ㅁ·ㅂ·ㅆ)</th></tr>` +
      forms.map((f, i) => `<tr><td class="mono">${esc(f)}${i === 0 ? ' <span class="pill">원형</span>' : ""}</td><td class="mono small">${ext(f).map(esc).join(" ") || "—"}</td></tr>`).join("") + "</table>";
  }
  $("#var-input").addEventListener("input", renderVariants);
  renderVariants();
  const KIND = { SENTI: "감성어", EMO: "이모티콘", INT: "강조어", DIM: "약화어", NEG_PRE: "앞 부정어", NEG_POST: "뒤 부정어", BLOCK: "차단어" };
  function renderMatch() {
    const t = E.normalizeText($("#match-input").value);
    const hits = E.matcher.find(t);
    $("#match-out").innerHTML = hits.length ? `<table><tr><th>문장 속</th><th>표제어</th><th>종류</th><th class="num">점수·배율</th><th>일치</th></tr>` +
      hits.map((h) => `<tr><td class="mono">${esc(h.surface)}</td><td class="mono">${esc(h.entry.term)}</td><td>${KIND[h.kind]}</td><td class="num">${h.entry.score}</td><td class="small">${h.exact ? "정확히" : "받침 확장"}</td></tr>`).join("") + "</table>"
      : '<p class="empty">사전에 걸리는 말이 없다</p>';
  }
  $("#match-input").addEventListener("input", renderMatch);
  renderMatch();
  const LEXF = [["all", "전체"], ["general", "일반"], ["movie", "영화"], ["service", "고객"], ["mod", "수식어"], ["block", "차단어"]];
  let lexF = "all";
  const DOMAIN_NAME = { general: "일반", movie: "영화", service: "고객" };
  function renderLex() {
    const q = $("#lex-q").value.trim().toLowerCase();
    const rows = D.engine.entries.filter((e) => {
      const isMod = !["SENTI", "EMO", "BLOCK"].includes(e.kind);
      if (lexF === "mod" && !isMod) return false;
      if (lexF === "block" && e.kind !== "BLOCK") return false;
      if (["general", "movie", "service"].includes(lexF) && (isMod || e.kind === "BLOCK" || e.domain !== lexF)) return false;
      return !q || e.term.includes(q) || (e.note || "").toLowerCase().includes(q) || (KIND[e.kind] || "").includes(q) || (DOMAIN_NAME[e.domain] || "").includes(q);
    });
    $("#lex-table").innerHTML = `<tr><th>표제어</th><th class="num">점수·배율</th><th>종류</th><th>분야</th><th>제한</th><th>설명</th></tr>` +
      rows.slice(0, 300).map((e) => `<tr><td class="mono">${esc(e.term)}${e.forms.length > 1 ? `<br><span class="small">${e.forms.slice(1).map(esc).join(" ")}</span>` : ""}</td><td class="num">${e.score}</td><td>${KIND[e.kind]}${e.pos === "P" ? " (용언)" : ""}</td><td>${DOMAIN_NAME[e.domain] || ""}</td><td class="mono small">${e.flags.join(" ")}</td><td class="small">${esc(e.note)}</td></tr>`).join("");
    const senti = D.engine.entries.filter((e) => e.kind === "SENTI");
    $("#lex-stat").innerHTML = `<span>표시 <b>${Math.min(rows.length, 300)}</b> / ${rows.length}</span><span>감성어 <b>${senti.length}</b></span><span>도메인 특화 <b>${senti.filter((e) => e.domain !== "general").length}</b></span><span>이모티콘·영어 <b>${D.engine.entries.filter((e) => e.kind === "EMO").length}</b></span><span>수식어 <b>${D.engine.entries.filter((e) => !["SENTI", "EMO", "BLOCK"].includes(e.kind)).length}</b></span>`;
  }
  segmented($("#lex-filter"), LEXF, lexF, (v) => { lexF = v; renderLex(); });
  $("#lex-q").addEventListener("input", renderLex);
  renderLex();

  // ───────── 06 규칙 표적 문장 ─────────
  const TAGN = { negation: "부정", double_negation: "이중부정", contrast: "대조", plain: "기본" };
  const ruleRows = D.cases.rules;
  const ruleRes = ruleRows.map((r) => STEPS.map((s) => E.analyze(r.text, s.config)));
  let ruleSel = [0, 8];
  function renderRules() {
    const accs = STEPS.map((_, j) => ruleRows.filter((r, i) => ruleRes[i][j].label === r.label).length);
    $("#rules-table").innerHTML = `<tr><th>문장</th><th>유형</th><th>정답</th>${STEPS.map((s, j) => `<th class="num" title="${esc(s.name)}">${s.name.split(" ")[0]}<br><span class="small">${accs[j]}/${ruleRows.length}</span></th>`).join("")}</tr>` +
      ruleRows.map((r, i) => `<tr${ruleSel[0] === i ? ' class="sel"' : ""}><td>${esc(r.text)}</td><td class="small">${TAGN[r.tag]}</td><td>${r.label ? "긍정" : "부정"}</td>${STEPS.map((s, j) => {
        const ok = ruleRes[i][j].label === r.label;
        return `<td class="num"><button type="button" data-i="${i}" data-j="${j}" style="min-height:30px;padding:0 8px" aria-pressed="${ruleSel[0] === i && ruleSel[1] === j}" aria-label="${s.name} ${ok ? "맞음" : "틀림"}"><span class="${ok ? "ok" : "no"}">${ok ? "✓" : "✗"}</span></button></td>`;
      }).join("")}</tr>`).join("");
    const [i, j] = ruleSel;
    $("#rules-detail").innerHTML = `<h4>${esc(STEPS[j].name)} · "${esc(ruleRows[i].text)}"${ruleRows[i].note ? ` <span class="small">— ${esc(ruleRows[i].note)}</span>` : ""}</h4>` + sentimentBlock(ruleRows[i].text, STEPS[j].config);
    $("#rules-acc").textContent = `A ${accs[0]}/40 → E ${accs[4]}/40 → I ${accs[8]}/40`;
  }
  $("#rules-table").addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; ruleSel = [+b.dataset.i, +b.dataset.j]; renderRules(); });
  renderRules();
  const pairsOn = Object.assign({}, REQUIRED), pairsOff = Object.assign({}, REQUIRED, { intensifier: false });
  $("#pairs-table").innerHTML = `<tr><th>기본</th><th class="num">점수</th><th>바꾼 문장</th><th class="num">규칙 끔</th><th class="num">규칙 켬</th><th>크기 변화</th></tr>` +
    D.cases.pairs.map((p) => {
      const b = E.analyze(p.base, pairsOn).score, off = E.analyze(p.modified, pairsOff).score, on = E.analyze(p.modified, pairsOn).score;
      const good = (p.kind === "intensifier" ? Math.abs(on) > Math.abs(b) : Math.abs(on) < Math.abs(b)) && (on > 0) === (b > 0);
      return `<tr><td>${esc(p.base)}</td><td class="num">${sgn(b)}</td><td>${esc(p.modified)} <span class="pill">${p.kind === "intensifier" ? "강조" : "약화"}</span></td><td class="num">${sgn(off)}</td><td class="num">${sgn(on)}</td><td class="${good ? "ok" : "no"}">${good ? "✓" : "✗ 어순(강조어가 뒤)"}</td></tr>`;
    }).join("");

  // ───────── 07 NSMC 평가 ─────────
  let evSplit = "test", evFilter = "wrong", evSel = null;
  const evCfg = ruleToggles($("#ev-toggles"), FINAL, () => renderEval());
  segmented($("#ev-split"), [["dev", "dev 1,000"], ["test", "test 1,000"]], evSplit, (v) => { evSplit = v; evSel = null; renderEval(); });
  segmented($("#ev-filter"), [["wrong", "오분류"], ["tie", "단서 없음"], ["neg", "부정어 작동"], ["all", "전체"]], evFilter, (v) => { evFilter = v; renderEvalList(); });
  let evRes = [];
  function macroF1(y, p) {
    const f = (c) => { const tp = y.filter((t, i) => t === c && p[i] === c).length, fp = y.filter((t, i) => t !== c && p[i] === c).length, fn = y.filter((t, i) => t === c && p[i] !== c).length;
      const P = tp + fp ? tp / (tp + fp) : 1, Rr = tp + fn ? tp / (tp + fn) : 1; return P + Rr ? (2 * P * Rr) / (P + Rr) : 0; };
    return (f(0) + f(1)) / 2;
  }
  function renderEval() {
    const rows = D.reviews[evSplit];
    evRes = rows.map(([, t]) => E.analyze(t, evCfg));
    const y = rows.map((r) => r[2]), p = evRes.map((r) => r.label);
    const acc = y.filter((t, i) => t === p[i]).length / y.length;
    const ties = evRes.filter((r) => r.decided_by_tie).length;
    const cov = evRes.map((r, i) => [r, i]).filter(([r]) => !r.decided_by_tie);
    const covAcc = cov.filter(([r, i]) => r.label === y[i]).length / Math.max(1, cov.length);
    $("#ev-facts").innerHTML = [[pct(acc), "정확도"], [f3(macroF1(y, p)), "macro F1"], [ties, "단서 없음(점수 0)"], [pct(covAcc), "단서 있는 리뷰 정확도"]]
      .map(([b, s]) => `<div class="fact"><b>${b}</b><span>${s}</span></div>`).join("");
    const cm = [[0, 0], [0, 0]];
    y.forEach((t, i) => { cm[t][p[i]] += 1; });
    const mx = Math.max(...cm.flat());
    $("#ev-cm").innerHTML = `<div></div><div class="h">예측 부정</div><div class="h">예측 긍정</div>` +
      [0, 1].map((t) => `<div class="h">정답 ${t ? "긍정" : "부정"}</div>` + [0, 1].map((q) => `<div class="c" style="--v:${cm[t][q] / mx}">${cm[t][q]}</div>`).join("")).join("");
    renderEvalList();
  }
  function renderEvalList() {
    const rows = D.reviews[evSplit];
    const idx = rows.map((r, i) => i).filter((i) => {
      const r = evRes[i];
      if (evFilter === "wrong") return r.label !== rows[i][2];
      if (evFilter === "tie") return r.decided_by_tie;
      if (evFilter === "neg") return r.items.some((it) => it.negators.length);
      return true;
    });
    $("#ev-list").innerHTML = `<p class="small" style="margin:0">${idx.length}건 중 앞 40건. 누르면 계산 과정이 나온다.</p>` + idx.slice(0, 40).map((i) => {
      const r = evRes[i], gold = rows[i][2];
      return `<button type="button" data-i="${i}" aria-pressed="${evSel === i}"><span class="s ${r.label === gold ? "ok" : "no"}">${sgn(r.score)}</span><span>${esc(rows[i][1])} <span class="pill">정답 ${gold ? "긍정" : "부정"}</span></span></button>`;
    }).join("");
    if (evSel !== null) $("#ev-detail").innerHTML = sentimentBlock(rows[evSel][1], evCfg);
    else $("#ev-detail").innerHTML = '<p class="empty">리뷰를 고르면 계산 과정이 여기 나온다</p>';
  }
  $("#ev-list").addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; evSel = +b.dataset.i; renderEvalList(); });
  renderEval();

  // ───────── 차트 (SVG) ─────────
  const tip = $("#tip");
  function lineChart(box, o) {
    const W = 760, H = o.height || 300, m = { l: 48, r: 64, t: 14, b: o.xlabelLines === 2 ? 52 : 38 };
    const n = o.xs.length;
    const xpos = (i) => m.l + (o.log ? (Math.log10(o.xs[i]) - Math.log10(o.xs[0])) / (Math.log10(o.xs[n - 1]) - Math.log10(o.xs[0])) : i / (n - 1)) * (W - m.l - m.r);
    const ypos = (v) => m.t + (1 - (v - o.ymin) / (o.ymax - o.ymin)) * (H - m.t - m.b);
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(o.title)}">`;
    if (o.band) {
      const bx = Math.max(m.l + 1, xpos(o.band[0]) - 12);
      s += `<rect x="${bx}" y="${m.t}" width="${xpos(o.band[1]) + 24 - bx}" height="${H - m.t - m.b}" style="fill:var(--sunk)"/>` +
        `<text x="${(xpos(o.band[0]) + xpos(o.band[1])) / 2}" y="${m.t + 12}" text-anchor="middle">${esc(o.bandLabel)}</text>`;
    }
    for (let v = o.ymin; v <= o.ymax + 1e-9; v += o.ystep) {
      s += `<line class="grid" x1="${m.l}" x2="${W - m.r}" y1="${ypos(v)}" y2="${ypos(v)}"/><text x="${m.l - 8}" y="${ypos(v) + 4}" text-anchor="end">${v.toFixed(2)}</text>`;
    }
    s += `<line class="axis" x1="${m.l}" x2="${W - m.r}" y1="${H - m.b}" y2="${H - m.b}"/>`;
    o.xlabels.forEach((lab, i) => {
      const parts = String(lab).split("\n");
      parts.forEach((p, k) => { s += `<text x="${xpos(i)}" y="${H - m.b + 16 + k * 13}" text-anchor="middle">${esc(p)}</text>`; });
    });
    for (const h of o.hlines || []) {
      s += `<line x1="${m.l}" x2="${W - m.r}" y1="${ypos(h.y)}" y2="${ypos(h.y)}" style="stroke:var(${h.color})" stroke-width="2" ${h.dash ? 'stroke-dasharray="6 4"' : ""}/>` +
        `<text x="${W - m.r + 4}" y="${ypos(h.y) + 4}">${esc(h.short)}</text>`;
    }
    for (const se of o.series) {
      const c = `var(${se.color})`;
      if (se.points[0].lo !== undefined) {
        const up = se.points.map((p, i) => `${xpos(i)},${ypos(p.hi)}`).join(" "), dn = se.points.map((p, i) => `${xpos(i)},${ypos(p.lo)}`).reverse().join(" ");
        s += `<polygon points="${up} ${dn}" style="fill:${c}" opacity=".14"/>`;
      }
      s += `<polyline fill="none" style="stroke:${c}" stroke-width="2" points="${se.points.map((p, i) => `${xpos(i)},${ypos(p.y)}`).join(" ")}"/>`;
      se.points.forEach((p, i) => { s += `<circle cx="${xpos(i)}" cy="${ypos(p.y)}" r="4" style="fill:${c};stroke:var(--surface)" stroke-width="2"/>`; });
      const lp = se.points[n - 1];
      s += `<text x="${xpos(n - 1) + 8}" y="${ypos(lp.y) + 4}">${lp.y.toFixed(3)}</text>`;
    }
    for (let i = 0; i < n; i++) {
      const x0 = i === 0 ? m.l : (xpos(i - 1) + xpos(i)) / 2, x1 = i === n - 1 ? W - m.r : (xpos(i) + xpos(i + 1)) / 2;
      s += `<rect class="hit" data-i="${i}" x="${x0}" y="${m.t}" width="${x1 - x0}" height="${H - m.t - m.b}" fill="transparent"/>`;
    }
    s += `<line class="cross" x1="0" x2="0" y1="${m.t}" y2="${H - m.b}" style="stroke:var(--axis)" visibility="hidden"/></svg>`;
    box.innerHTML = s;
    const svg = box.querySelector("svg"), cross = box.querySelector(".cross");
    svg.addEventListener("pointermove", (e) => {
      const r = e.target.closest(".hit"); if (!r) return;
      const i = +r.dataset.i, rect = svg.getBoundingClientRect(), sc = rect.width / W;
      cross.setAttribute("x1", xpos(i)); cross.setAttribute("x2", xpos(i)); cross.setAttribute("visibility", "visible");
      tip.innerHTML = o.tip(i);
      tip.style.display = "block";
      const bx = box.getBoundingClientRect();
      tip.style.left = Math.min(window.scrollX + bx.left + xpos(i) * sc + 12, window.scrollX + bx.right - tip.offsetWidth) + "px";
      tip.style.top = window.scrollY + rect.top + 10 + "px";
    });
    svg.addEventListener("pointerleave", () => { tip.style.display = "none"; cross.setAttribute("visibility", "hidden"); });
  }
  const swatch = (v, dash) => `<i style="background:${dash ? "transparent" : `var(${v})`};border:${dash ? `2px dashed var(${v})` : "0"};height:${dash ? 0 : 10}px;vertical-align:${dash ? 3 : -1}px"></i>`;
  function drawAblation() {
    const dev = R.sentiment.dev.ablation, test = R.sentiment.test.ablation;
    const short = ["사전", "+강조", "+부정", "+부정·강조", "+이중부정", "+이모티콘", "+대조", "+고립부정", "+평점"];
    lineChart($("#ab-chart"), {
      title: "규칙 단계별 정확도", xs: dev.map((_, i) => i), xlabels: dev.map((r, i) => `${r.step[0]}\n${short[i]}`), xlabelLines: 2,
      ymin: 0.68, ymax: 0.84, ystep: 0.04, band: [0, 4], bandLabel: "필수 범위",
      series: [{ name: "dev", color: "--s1", points: dev.map((r) => ({ y: r.accuracy })) }, { name: "test", color: "--s2", points: test.map((r) => ({ y: r.accuracy })) }],
      tip: (i) => `<b>${esc(dev[i].step)}</b><br>dev ${f3(dev[i].accuracy)} · test ${f3(test[i].accuracy)}<br>test 단서 없음 ${test[i].ties}건`,
    });
    $("#ab-chart").insertAdjacentHTML("beforeend", `<div class="legend">${"<span>" + swatch("--s1") + "dev (사전을 만든 집합)</span><span>" + swatch("--s2") + "test (규칙 고정 후 1회)</span>"}</div>`);
  }
  function drawTfidf() {
    const T = R.tfidf, sizes = T.sizes;
    const ser = (name) => sizes.map((n) => T.curve.find((r) => r.model === name && r.n === n));
    const a = ser("TF-IDF"), b = ser("TF-IDF+규칙 점수");
    const rf = T.rules["규칙(최종 I)"].accuracy, rr = T.rules["규칙(필수 E)"].accuracy;
    lineChart($("#tf-chart"), {
      title: "규칙 vs TF-IDF 학습 곡선", xs: sizes, log: true, xlabels: sizes.map((n) => n.toLocaleString()), ymin: 0.5, ymax: 0.85, ystep: 0.05,
      series: [{ name: "TF-IDF", color: "--s1", points: a.map((r) => ({ y: r.acc_mean, lo: r.acc_mean - r.acc_std, hi: r.acc_mean + r.acc_std })) },
        { name: "혼합", color: "--s2", points: b.map((r) => ({ y: r.acc_mean, lo: r.acc_mean - r.acc_std, hi: r.acc_mean + r.acc_std })) }],
      hlines: [{ y: rf, color: "--s3", short: "규칙 최종" }, { y: rr, color: "--s0", short: "규칙 필수", dash: true }],
      tip: (i) => `<b>학습 ${sizes[i].toLocaleString()}건</b> (seed ${a[i].seeds}회)<br>TF-IDF ${f3(a[i].acc_mean)} ± ${f3(a[i].acc_std)}<br>TF-IDF+규칙 ${f3(b[i].acc_mean)} ± ${f3(b[i].acc_std)}<br>규칙 최종 ${f3(rf)}`,
    });
    $("#tf-legend").innerHTML = `<span>${swatch("--s1")}TF-IDF (글자 1~3-gram + 로지스틱 회귀)</span><span>${swatch("--s2")}TF-IDF + 규칙 점수</span><span>${swatch("--s3")}규칙 최종 ${f3(rf)}</span><span>${swatch("--s0", true)}규칙 필수 ${f3(rr)}</span>`;
  }
  function redrawCharts() { drawAblation(); drawTfidf(); }
  redrawCharts();
  $("#ab-table").innerHTML = `<tr><th>단계</th><th class="num">dev</th><th class="num">test</th><th class="num">test macro F1</th><th class="num">test 단서 없음</th></tr>` +
    testAb.map((r, i) => `<tr><td>${esc(r.step)}</td><td class="num">${f3(R.sentiment.dev.ablation[i].accuracy)}</td><td class="num"><b>${f3(r.accuracy)}</b></td><td class="num">${f3(r.macro_f1)}</td><td class="num">${r.ties}</td></tr>`).join("");
  const sig = R.significance;
  $("#sig").innerHTML = `<p class="small">test 1,000건 정확도의 bootstrap 95% 구간</p><table>${Object.entries(sig.ci95).map(([k, v]) => `<tr><td>${esc(k)}</td><td class="num mono">${f3(v.accuracy[0])} – ${f3(v.accuracy[1])}</td></tr>`).join("")}</table>` +
    `<p class="small" style="margin-top:10px">McNemar 검정: 같은 리뷰에서 한쪽만 맞힌 수</p><table>${Object.entries(sig.mcnemar).map(([k, v]) => `<tr><td class="small">${esc(k.replace(/ D \+ 이중부정 \(필수 범위\)| H \+ 평점 언급| 사전 합산만/g, ""))}</td><td class="num">${v.a_only} 대 ${v.b_only}</td><td class="num">p=${v.p_value < 0.001 ? v.p_value.toExponential(1) : v.p_value.toFixed(3)}</td></tr>`).join("")}</table>`;
  const ns = (s) => R.sentiment[s].negation_subset;
  $("#negsub").innerHTML = `<p class="small">전체 정확도에서는 부정어 효과가 1.4%p뿐이다. 부정 표현이 든 리뷰가 적어 효과가 희석되기 때문이다. 부정어 규칙이 실제로 감성어를 뒤집은 리뷰만 모으면:</p><table><tr><th></th><th class="num">건수</th><th class="num">규칙 없음(A)</th><th class="num">필수(E)</th><th class="num">p</th></tr>` +
    ["dev", "test"].map((s) => `<tr><td>${s}</td><td class="num">${ns(s).n}</td><td class="num">${pct(ns(s).acc_A)}</td><td class="num"><b>${pct(ns(s).acc_E)}</b></td><td class="num">${ns(s).mcnemar_A_vs_E.p_value < 0.001 ? ns(s).mcnemar_A_vs_E.p_value.toExponential(1) : ns(s).mcnemar_A_vs_E.p_value.toFixed(3)}</td></tr>`).join("") + "</table>";
  const LN = { custom: "직접 구축 (394)", knu: "KNU (14,854)", "knu+domain": "KNU + 도메인어 92", union: "직접 구축 + KNU" };
  const lc = R.lexicon_comparison;
  $("#lexcmp").innerHTML = `<tr><th>사전</th><th class="num">dev 필수</th><th class="num">dev 최종</th><th class="num">test 필수</th><th class="num">test 최종</th><th class="num">test 단서 없음(최종)</th></tr>` +
    Object.keys(LN).map((k) => { const g = (s, c) => lc[s].find((x) => x.lexicon === k && x.config.startsWith(c)); return `<tr><td>${LN[k]}</td><td class="num">${f3(g("dev", "필수").accuracy)}</td><td class="num">${f3(g("dev", "최종").accuracy)}</td><td class="num">${f3(g("test", "필수").accuracy)}</td><td class="num"><b>${f3(g("test", "최종").accuracy)}</b></td><td class="num">${g("test", "최종").ties}</td></tr>`; }).join("");

  // ───────── 08 실패 사례 ─────────
  const fmtPairs = (a) => a.map((x) => `${LABELS[x[0]]} <span class="mono">${esc(x[1])}</span>`).join("<br>") || "—";
  $("#ext-fail").innerHTML = `<tr><th>ID</th><th>문장</th><th>유형</th><th>놓친 것</th><th>잘못 잡은 것</th><th>원인</th></tr>` +
    R.extraction.errors.map((e) => `<tr><td class="mono">${e.id}</td><td>${esc(e.text)}</td><td><span class="pill">${esc(e.fail)}</span></td><td class="small">${fmtPairs(e.missed)}</td><td class="small">${fmtPairs(e.false_positive)}</td><td class="small">${esc(e.note)}</td></tr>`).join("");
  $("#err-intro").innerHTML = `최종 규칙의 test 오분류는 ${R.n_test_errors}건이다. 그중 ${R.n_tie_errors}건은 사전 단서가 하나도 없어 기본값(부정)으로 판정된 긍정 리뷰다. 아래는 원인을 직접 분류한 ${R.error_annotations.length}건이다. 누르면 엔진의 계산 과정이 나온다. 이 사례들은 test를 본 뒤에 알게 되었으므로 규칙에 반영하지 않았다.`;
  const cats = [...new Set(R.error_annotations.map((a) => a.category))];
  let errCat = "전체", errSel = 0;
  segmented($("#err-filter"), [["전체", "전체"]].concat(cats.map((c) => [c, c])), errCat, (v) => { errCat = v; renderErr(); });
  function renderErr() {
    const list = R.error_annotations.map((a, i) => [a, i]).filter(([a]) => errCat === "전체" || a.category === errCat);
    $("#err-list").innerHTML = list.map(([a, i]) => `<button type="button" data-i="${i}" aria-pressed="${errSel === i}"><span class="s small">${a.label ? "긍정" : "부정"}</span><span>${esc(a.text)} <span class="pill">${esc(a.category)}</span></span></button>`).join("");
    const a = R.error_annotations[errSel];
    $("#err-detail").innerHTML = `<h4>${esc(a.category)} — 정답 ${a.label ? "긍정" : "부정"}</h4><p class="small">${esc(a.cause)}</p>` + sentimentBlock(a.text, FINAL);
  }
  $("#err-list").addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; errSel = +b.dataset.i; renderErr(); });
  renderErr();

  // ───────── 09 보너스 ─────────
  $("#mask-table").innerHTML = `<tr><th>ID</th><th>원문</th><th>마스킹 결과</th><th>상태</th></tr>` + D.cases.masking.map((c) => {
    const [m] = E.mask(c.text);
    const leak = c.gold.filter((g) => m.includes(g.text));
    const st = c.gold.length === 0 ? (m === c.text ? '<span class="ok">✓ 건드리지 않음</span>' : '<span class="no">✗ 오탐</span>') : leak.length ? `<span class="no">✗ 유출: ${leak.map((g) => LABELS[g.type]).join(", ")}</span>` : '<span class="ok">✓ 모두 가림</span>';
    return `<tr${leak.length ? ' style="box-shadow:inset 3px 0 var(--bad)"' : ""}><td class="mono">${c.id}</td><td>${esc(c.text)}</td><td class="mono small">${esc(m)}</td><td class="small">${st}${c.note ? `<br>${esc(c.note)}` : ""}</td></tr>`;
  }).join("");
  $("#tf-table").innerHTML = `<tr><th class="num">학습 리뷰</th><th class="num">TF-IDF</th><th class="num">TF-IDF + 규칙</th><th class="num">특성 수</th><th class="num">반복</th></tr>` +
    R.tfidf.sizes.map((n) => { const a = R.tfidf.curve.find((r) => r.model === "TF-IDF" && r.n === n), b = R.tfidf.curve.find((r) => r.model !== "TF-IDF" && r.n === n);
      return `<tr><td class="num">${n.toLocaleString()}</td><td class="num">${f3(a.acc_mean)} ± ${f3(a.acc_std)}</td><td class="num">${f3(b.acc_mean)} ± ${f3(b.acc_std)}</td><td class="num">${Math.round(a.features_mean).toLocaleString()}</td><td class="num">${a.seeds}</td></tr>`; }).join("");
  const ASP_EX = ["음식은 맛있는데 가격이 비싸요", "가격 대비 품질은 괜찮은데 배송이 너무 느려요", "직원분들이 정말 친절하고 분위기도 좋았어요", "배송이 빠르지 않았어요", "연기는 좋았지만 스토리가 최악이다"];
  let aspMode = "preceding";
  const aspInput = $("#asp-input");
  aspInput.value = ASP_EX[0];
  $("#asp-chips").innerHTML = ASP_EX.map((t, i) => `<button type="button" data-i="${i}">${esc(t.slice(0, 12))}…</button>`).join("");
  $("#asp-chips").addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; aspInput.value = ASP_EX[+b.dataset.i]; renderAsp(); });
  segmented($("#asp-mode"), [["preceding", "앞 속성 우선"], ["nearest", "가장 가까운 속성"]], aspMode, (v) => { aspMode = v; renderAsp(); renderAspTable(); });
  function renderAsp() { $("#asp-out").innerHTML = aspectHTML(E.aspects(aspInput.value, aspMode)); }
  aspInput.addEventListener("input", renderAsp);
  function renderAspTable() {
    let tp = 0, fp = 0, fn = 0, exact = 0;
    const rows = D.cases.aspect.map((c) => {
      const pred = E.aspectPairs(c.text, aspMode).map((x) => x.join(":")), gold = c.gold.map((x) => x.join(":"));
      const t = pred.filter((x) => gold.includes(x)).length;
      tp += t; fp += pred.length - t; fn += gold.length - t;
      const ok = t === gold.length && pred.length === gold.length; exact += ok;
      const show = (a) => a.map((x) => { const [k, v] = x.split(":"); return `${esc(k)}${v === "pos" ? "+" : "−"}`; }).join(" ") || "—";
      return `<tr><td class="mono">${c.id}</td><td>${esc(c.text)}</td><td class="mono">${show(gold)}</td><td class="mono">${show(pred)}</td><td class="${ok ? "ok" : "no"}">${ok ? "✓" : "✗"}${c.fail ? ` <span class="pill">${esc(c.fail)}</span>` : ""}</td></tr>`;
    });
    $("#asp-table").innerHTML = `<tr><th>ID</th><th>문장</th><th>정답</th><th>예측</th><th></th></tr>` + rows.join("");
    const P = tp / (tp + fp), Rr = tp / (tp + fn);
    $("#asp-score").innerHTML = `<span>48문장 · 정답 쌍 ${tp + fn}개</span><span>정밀도 <b>${f3(P)}</b></span><span>재현율 <b>${f3(Rr)}</b></span><span>F1 <b>${f3((2 * P * Rr) / (P + Rr))}</b></span><span>완전히 맞힌 문장 <b>${exact}</b></span><span>문장 단위 기준선 F1 ${f3(R.aspect.preceding.sentence_baseline.f1)}</span>`;
  }
  renderAsp(); renderAspTable();

  // ───────── 10 · 11 결론과 자기 점검 ─────────
  const tf = R.tfidf.curve, at = (m, n) => tf.find((r) => r.model === m && r.n === n).acc_mean;
  $("#verdict-text").innerHTML = `<p><b>형식의 언어는 대부분 정의할 수 있었다.</b> 이메일·전화·날짜·금액·URL 추출은 정밀도 ${f3(R.extraction.micro.precision)}, 재현율 ${f3(R.extraction.micro.recall)}였다. 놓친 것은 한글 숫자, 미국식 날짜, 띄어쓰기 모호성처럼 규칙을 만들 때 상상하지 못한 표기다.</p>` +
    `<p><b>태도의 언어는 규칙으로 ${pct(testAb[8].accuracy)}까지 갔다.</b> 나머지는 사전 단서가 없는 묘사형 칭찬, 반어, 인용, 감성의 대상(영화인가 다른 관객인가) 문제다. 단어 수준 규칙의 바깥이라서 규칙을 더 늘려도 잡기 어렵다.</p>` +
    `<p><b>그래도 규칙이 담은 지식은 값이 있다.</b> 학습 리뷰가 10건뿐일 때 TF-IDF는 ${pct(at("TF-IDF", 10))}, 규칙 점수를 더한 혼합형은 ${pct(at("TF-IDF+규칙 점수", 10))}다. TF-IDF가 규칙을 넘는 데는 약 ${tfCross ? tfCross.toLocaleString() : "?"}건이 필요했다. 1만 건에서도 혼합형(${pct(at("TF-IDF+규칙 점수", 10000))})이 TF-IDF(${pct(at("TF-IDF", 10000))})보다 높았다.</p>`;
  $("#when-table").innerHTML = `<tr><th>상황</th><th>적합한 쪽</th><th>이번 근거</th></tr>` + [
    ["형식이 정해진 값(연락처, 날짜, 금액, 개인정보)", "규칙", `추출 정밀도 ${f3(R.extraction.micro.precision)}, 정규화 100%, 검증식(달력·Luhn) 사용 가능`],
    ["레이블이 거의 없거나 판정 근거를 설명해야 할 때", "규칙 또는 혼합", `학습 10건: TF-IDF ${pct(at("TF-IDF", 10))} vs 혼합 ${pct(at("TF-IDF+규칙 점수", 10))}`],
    ["레이블이 수천 건 이상, 표현이 다양할 때", "통계", `TF-IDF가 약 ${tfCross ? tfCross.toLocaleString() : "?"}건부터 규칙을 넘음`],
    ["순위를 매기는 검색(A4-1)", "통계", "TF-IDF·BM25는 점수로 순위를 낸다. 규칙은 일치 여부만 낸다"],
  ].map((r) => `<tr><td>${r[0]}</td><td><b>${r[1]}</b></td><td class="small">${r[2]}</td></tr>`).join("");
  $("#qa2").innerHTML = `장점은 정밀도와 해석 가능성이다. 추출 정밀도 ${f3(R.extraction.micro.precision)}, 마스킹 오탐 0건이다. 틀린 경우에도 어느 패턴의 어느 부분 때문인지 바로 짚을 수 있다. 단점은 재현율과 유지보수다. 재현율은 ${f3(R.extraction.micro.recall)}에 그쳤다. 놓친 것은 모두 '상상하지 못한 표기'였다. 그리고 하나를 고치면 다른 것이 깨진다. URL을 한글에서 멈추게 하면 조사는 떨어지지만 한글 경로가 잘린다. '만원'을 금액으로 받으면 '만원 버스'도 들어온다.`;
  $("#qa5").innerHTML = `형식이 정해져 있고 틀리면 안 되는 일(연락처·금액 추출, 개인정보 마스킹)은 규칙이 맞다. 데이터가 적거나 판정 근거를 설명해야 할 때도 규칙이 낫다. 레이블 데이터가 충분하고 표현이 다양한 일(리뷰 감성, 주제 분류, 검색 순위)은 통계가 맞다. 이번 실험에서 TF-IDF는 약 ${tfCross ? tfCross.toLocaleString() : "?"}건부터 규칙을 넘었다. 둘을 합치는 것이 가장 좋았다. 규칙 점수를 TF-IDF 특성에 더하면 모든 데이터 크기에서 둘 다보다 높았다. 데이터가 적을 때의 안정성(표준편차)도 가장 좋았다.`;

  // ───────── 12 코드 지도 ─────────
  $("#code-list").innerHTML = D.code.map((c) => {
    const body = c.code.split("\n").map((l, i) => {
      const k = l.indexOf("#");
      const line = k >= 0 && !/["']/.test(l.slice(0, k).replace(/"[^"]*"|'[^']*'/g, "")) ? esc(l.slice(0, k)) + `<span class="cm">${esc(l.slice(k))}</span>` : esc(l);
      return `<span class="ln">${c.start + i}</span>${line}`;
    }).join("\n");
    return `<details class="code"><summary>${esc(c.file)}:${c.start} — ${esc(c.name)}</summary><pre class="src">${body}</pre></details>`;
  }).join("");
})();
