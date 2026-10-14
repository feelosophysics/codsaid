"""오분류 이미지를 사람이 직접 보고 태그를 다는 오프라인 HTML 도구를 만든다 (Human-in-the-loop).

입력:  results/vision_errors.csv (주 모델의 Test 오분류), annotations/error_tags.csv (있으면 초안으로 채움)
출력:  annotations/tagging.html — 브라우저로 열어 태그를 고치고 [CSV 저장]을 누르면 error_tags.csv가 내려받아진다.
       그 파일로 annotations/error_tags.csv를 바꾼 뒤 scripts/vision_error_analysis.py를 다시 실행한다.

화면에는 오분류 사진 옆에 '실제 클래스'와 '예측 클래스'의 Train 사진 3장씩을 함께 보여 준다.
두 꽃을 나란히 봐야 클래스 유사성인지, 사진 품질 문제인지 판단할 수 있다.

실행: uv run python tools/build_tagging_page.py
"""
import base64
import html
import io
import json

import pandas as pd
from PIL import Image

from perfdiag.common import RESULTS, ROOT, utf8_console
from perfdiag.vision.data import CLASS_KO, FLOWERS, load_manifest

ANNOTATIONS = ROOT / "annotations"
TAGS_CSV = ANNOTATIONS / "error_tags.csv"
OUTPUT = ANNOTATIONS / "tagging.html"
COLUMNS = ["no", "file", "true", "pred", "confidence", "primary_tag", "secondary_tags", "detail", "note",
           "tagged_by", "reviewed_by"]
TAGS = {
    "데이터 품질": ["어두운 조명", "과노출·역광", "흐림·초점", "해상도 부족", "워터마크·글자", "중복 사진"],
    "배경/잡음": ["복잡한 배경", "배경 편향(흙·자갈·낙엽)", "객체 가림", "작은 객체·여러 송이", "일부만 보임"],
    "클래스 유사성": ["색·형태 유사", "피기 전·시든 상태", "측면·뒷면 각도"],
    "라벨 오류": ["라벨 오류 의심", "품종 변이"],
    "모델 한계": ["높은 신뢰도 오답", "근소한 차이 혼동"],
}


def data_uri(path, size):
    image = Image.open(path).convert("RGB")
    image.thumbnail((size, size))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def load_tags(errors):
    if TAGS_CSV.exists():
        tags = pd.read_csv(TAGS_CSV, dtype=str).fillna("")
        merged = errors.merge(tags[["file", "primary_tag", "secondary_tags", "detail", "note", "tagged_by",
                                    "reviewed_by"]], on="file", how="left")
    else:
        merged = errors.assign(primary_tag="", secondary_tags="", detail="", note="", tagged_by="", reviewed_by="")
    return merged.fillna("")


def main():
    utf8_console()
    errors = pd.read_csv(RESULTS / "vision_errors.csv")
    errors.insert(0, "no", range(1, len(errors) + 1))
    rows = load_tags(errors)
    manifest = load_manifest()
    refs = {}
    for name in sorted(set(rows["true"]) | set(rows["pred"])):
        files = manifest[(manifest["class"] == name) & (manifest["split"] == "train")].sort_values("order")["file"]
        refs[name] = [data_uri(FLOWERS / f, 150) for f in files[:3]]
    items = []
    for r in rows.to_dict("records"):
        r["image"] = data_uri(FLOWERS / r["file"], 360)
        r["confidence"] = float(r["confidence"])
        items.append(r)
    page = TEMPLATE.replace("__DATA__", json.dumps({"items": items, "refs": refs, "tags": TAGS, "ko": CLASS_KO,
                                                     "columns": COLUMNS}, ensure_ascii=False).replace("</", "<\\/"))
    ANNOTATIONS.mkdir(exist_ok=True)
    OUTPUT.write_text(page, encoding="utf-8", newline="\n")
    print(f"저장: {OUTPUT} ({OUTPUT.stat().st_size / 1e6:.1f}MB, 오분류 {len(items)}건)")


TEMPLATE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>오분류 태깅</title>
<style>
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1f;--muted:#666;--line:#ddd;--accent:#2b6cb0;--warn:#b7791f;--ok:#2f855a}
@media (prefers-color-scheme:dark){:root{--bg:#18181a;--card:#232326;--ink:#ececec;--muted:#a0a0a0;--line:#3a3a3e;--accent:#7fb0ea;--warn:#e0b050;--ok:#6cc58f}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,"Malgun Gothic",sans-serif}
header{position:sticky;top:0;z-index:2;background:var(--card);border-bottom:1px solid var(--line);padding:10px 16px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
header h1{font-size:17px;margin:0 12px 0 0}header .stat{color:var(--muted);font-size:13px}
button,select,input,textarea{font:inherit;color:inherit}button{background:var(--accent);color:#fff;border:0;border-radius:6px;padding:6px 12px;cursor:pointer}
button.ghost{background:transparent;color:var(--accent);border:1px solid var(--accent)}
main{max-width:1100px;margin:0 auto;padding:12px 16px 80px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px;margin:12px 0;display:grid;grid-template-columns:minmax(0,360px) minmax(0,1fr);gap:14px}
.card.done{border-left:5px solid var(--ok)}.card.draft{border-left:5px solid var(--warn)}
.card img.main{width:100%;border-radius:6px}.refs{display:grid;grid-template-columns:repeat(3,1fr);gap:4px}.refs img{width:100%;border-radius:4px}
.label{font-size:12px;color:var(--muted);margin:6px 0 2px}.meta{font-size:14px}.meta b{font-size:16px}
fieldset{border:1px solid var(--line);border-radius:8px;margin:6px 0;padding:6px 10px}legend{font-size:13px;color:var(--muted)}
.opts{display:flex;flex-wrap:wrap;gap:4px 12px}.opts label{font-size:14px;white-space:nowrap}
textarea,input[type=text]{width:100%;background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:4px 6px}
.badge{display:inline-block;font-size:12px;border-radius:10px;padding:0 8px;margin-left:6px;background:var(--line)}
@media (max-width:700px){.card{grid-template-columns:1fr}}
</style></head><body>
<header><h1>오분류 태깅</h1>
<label>검수자 <input type="text" id="reviewer" style="width:120px" placeholder="이름"></label>
<label>보기 <select id="filter"><option value="all">전체</option><option value="todo">미검수만</option><option value="done">검수 완료만</option></select></label>
<span class="stat" id="stat"></span>
<button id="save">CSV 저장</button><button class="ghost" id="reset">브라우저 임시 저장 지우기</button></header>
<main><p class="stat">각 사진을 직접 보고 주 원인 1개와 보조 원인을 고른다. 노란 줄은 Claude 초안, 초록 줄은 검수 완료다.
'검수 완료'에 체크하면 그 행의 reviewed_by에 검수자 이름이 들어간다. 편집 내용은 이 브라우저에 임시 저장된다.
다 끝나면 [CSV 저장]으로 받은 파일을 annotations/error_tags.csv로 바꾼다.</p><div id="list"></div></main>
<script>
const DATA = __DATA__;
const KEY = "a6-2-error-tags";
let saved = {};
try { saved = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { saved = {}; }
try { document.getElementById("reviewer").value = localStorage.getItem(KEY + "-reviewer") || ""; } catch (e) {}
const state = DATA.items.map(it => Object.assign({}, it, saved[it.file] || {}));
function persist() {
  const out = {};
  state.forEach(s => out[s.file] = {primary_tag: s.primary_tag, secondary_tags: s.secondary_tags, detail: s.detail,
    note: s.note, tagged_by: s.tagged_by, reviewed_by: s.reviewed_by});
  try { localStorage.setItem(KEY, JSON.stringify(out)); } catch (e) {}
}
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const ko = n => n + " (" + (DATA.ko[n] || "") + ")";
function card(s, i) {
  const sec = new Set((s.secondary_tags || "").split(";").filter(Boolean));
  const det = new Set((s.detail || "").split(";").filter(Boolean));
  const cats = Object.keys(DATA.tags);
  return `<div class="card ${s.reviewed_by ? "done" : (s.tagged_by ? "draft" : "")}" data-i="${i}">
  <div><img class="main" src="${s.image}" alt="오분류 ${s.no}">
   <div class="meta">#${s.no} <code>${esc(s.file)}</code><br><b>${esc(ko(s.true))} → ${esc(ko(s.pred))}</b>
   <br>신뢰도 ${s.confidence.toFixed(3)} · 정답 확률 ${Number(s.true_proba).toFixed(3)} · 2순위 ${esc(s.second)}
   <br>틀린 모델: ${esc(s.wrong_models)}</div></div>
  <div><div class="label">실제 클래스 ${esc(ko(s.true))}의 Train 사진</div><div class="refs">${DATA.refs[s.true].map(u => `<img src="${u}" alt="">`).join("")}</div>
   <div class="label">예측 클래스 ${esc(ko(s.pred))}의 Train 사진</div><div class="refs">${DATA.refs[s.pred].map(u => `<img src="${u}" alt="">`).join("")}</div>
   <fieldset><legend>주 원인 (1개)</legend><div class="opts">${cats.map(c => `<label><input type="radio" name="p${i}" value="${c}" ${s.primary_tag === c ? "checked" : ""}> ${c}</label>`).join("")}</div></fieldset>
   <fieldset><legend>보조 원인 (여러 개 가능)</legend><div class="opts">${cats.map(c => `<label><input type="checkbox" data-sec="${c}" ${sec.has(c) ? "checked" : ""}> ${c}</label>`).join("")}</div></fieldset>
   <fieldset><legend>세부 태그</legend><div class="opts">${cats.flatMap(c => DATA.tags[c]).map(d => `<label><input type="checkbox" data-det="${d}" ${det.has(d) ? "checked" : ""}> ${d}</label>`).join("")}</div></fieldset>
   <label class="label">메모 <textarea rows="2" data-note>${esc(s.note || "")}</textarea></label>
   <div>작성: <span class="badge">${esc(s.tagged_by || "없음")}</span>
   <label style="margin-left:12px"><input type="checkbox" data-review ${s.reviewed_by ? "checked" : ""}> 검수 완료</label>
   <span class="badge">${esc(s.reviewed_by || "")}</span></div></div></div>`;
}
function render() {
  const f = document.getElementById("filter").value;
  document.getElementById("list").innerHTML = state.map((s, i) =>
    (f === "all" || (f === "done") === Boolean(s.reviewed_by)) ? card(s, i) : "").join("");
  const done = state.filter(s => s.reviewed_by).length;
  document.getElementById("stat").textContent = `검수 ${done}/${state.length}`;
}
document.getElementById("list").addEventListener("change", e => {
  const el = e.target.closest(".card"); if (!el) return;
  const s = state[Number(el.dataset.i)];
  const reviewer = document.getElementById("reviewer").value.trim() || "user";
  s.primary_tag = (el.querySelector("input[type=radio]:checked") || {}).value || "";
  s.secondary_tags = [...el.querySelectorAll("[data-sec]:checked")].map(x => x.dataset.sec).join(";");
  s.detail = [...el.querySelectorAll("[data-det]:checked")].map(x => x.dataset.det).join(";");
  s.note = el.querySelector("[data-note]").value;
  if (!s.tagged_by) s.tagged_by = reviewer;
  const reviewed = el.querySelector("[data-review]").checked;
  s.reviewed_by = reviewed ? (s.reviewed_by || reviewer) : "";
  persist();
  if (e.target.matches("[data-review]")) render();
  else document.getElementById("stat").textContent = `검수 ${state.filter(x => x.reviewed_by).length}/${state.length}`;
});
document.getElementById("reviewer").addEventListener("change", e => { try { localStorage.setItem(KEY + "-reviewer", e.target.value); } catch (x) {} });
document.getElementById("filter").addEventListener("change", render);
document.getElementById("reset").addEventListener("click", () => {
  if (!confirm("이 브라우저에 임시 저장한 편집을 지우고 처음 초안으로 돌아갈까요?")) return;
  try { localStorage.removeItem(KEY); } catch (e) {} location.reload();
});
document.getElementById("save").addEventListener("click", () => {
  const q = v => { v = String(v ?? ""); return /[",\\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };
  const lines = [DATA.columns.join(",")].concat(state.map(s => DATA.columns.map(c => q(s[c])).join(",")));
  const blob = new Blob(["\\ufeff" + lines.join("\\n") + "\\n"], {type: "text/csv"});
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "error_tags.csv"; a.click();
});
render();
</script></body></html>
"""

if __name__ == "__main__":
    main()
