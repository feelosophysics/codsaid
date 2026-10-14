"""study/a6-2.html이 현재 저장소와 일치하고, 위젯 계산이 Python 구현과 같은지 검사한다.

1. 파일 대조: source-manifest.json의 해시와 현재 파일 (결과 JSON·CSV·그림·템플릿·소스)
2. 코드 발췌: HTML 속 발췌가 현재 원본 줄과 같은지
3. 페이지 구조: 내부 링크 대상, 입력 요소 레이블, 스크립트가 찾는 id, 외부 리소스 없음, 용어(Val·Dev) 없음
4. 계산 대조: <script id="mathlib">를 Node.js로 실행해 Python 결과와 비교
   - 베이스라인 9개 × 2개 시계열 × Train/Validation/Test × MAE·RMSE·MAPE (results/ts_baselines_*.json)
   - 진단 규칙: 분류·시계열 각각 격자 441점 (diagnosis.py)
   - 개선율, MinMax(Train fit)의 Test 최댓값

실행: uv run python tools/verify_study_guide.py   (Node.js 필요)
"""
import json
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_study_guide as build  # noqa: E402
from perfdiag.common import RESULTS, load_json, utf8_console  # noqa: E402
from perfdiag.diagnosis import diagnose_classification, diagnose_forecast  # noqa: E402
from perfdiag.metrics import improvement  # noqa: E402
from perfdiag.timeseries.data import SERIES, prepare  # noqa: E402

HTML = build.OUTPUT
failures = []


def check(condition, message):
    if not condition:
        failures.append(message)
    return condition


def verify_files():
    manifest = json.loads(build.MANIFEST.read_text(encoding="utf-8"))
    for path, digest in manifest["text"].items():
        check(build.text_hash(path) == digest, f"텍스트 해시 불일치: {path} (다시 빌드 필요)")
    for path, digest in manifest["binary"].items():
        check(build.binary_hash(path) == digest, f"그림 해시 불일치: {path}")
    return len(manifest["text"]) + len(manifest["binary"])


def load_data(html):
    match = re.search(r"const DATA = (.*?);</script>", html, re.S)
    return json.loads(match.group(1).replace("<\\/", "</"))


def verify_excerpts(data, html):
    for key, (path, name) in build.EXCERPTS.items():
        check(data["code"].get(key) == build.excerpt(path, name), f"코드 발췌가 원본과 다르다: {key}")
        check(f'data-code="{key}"' in html, f"템플릿에서 쓰지 않는 발췌: {key}")
    used = set(re.findall(r'data-code="([^"]+)"', html))
    check(used <= set(build.EXCERPTS), f"정의되지 않은 발췌: {used - set(build.EXCERPTS)}")
    figs = set(re.findall(r'data-fig="([^"]+)"', html))
    check(figs <= set(build.FIGURE_FILES), f"정의되지 않은 그림: {figs - set(build.FIGURE_FILES)}")
    missing = set(build.FIGURE_FILES) - set(data["fig"])
    check(not missing, f"빌드에 빠진 그림: {missing}")
    return len(build.EXCERPTS)


class Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.hrefs, self.srcs, self.labels_for, self.controls = set(), [], [], set(), []
        self.label_depth, self.wrapped, self.skip, self.text = 0, set(), 0, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and "href" in a:
            self.hrefs.append(a["href"])
        if tag in ("script", "img", "link") and (a.get("src") or a.get("href")):
            self.srcs.append(a.get("src") or a.get("href"))
        if tag == "label":
            self.label_depth += 1
            if "for" in a:
                self.labels_for.add(a["for"])
        if tag in ("input", "select", "textarea"):
            self.controls.append(a.get("id"))
            if self.label_depth:
                self.wrapped.add(a.get("id"))
        if tag in ("script", "style", "pre", "code"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag == "label":
            self.label_depth -= 1
        if tag in ("script", "style", "pre", "code"):
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.text.append(data)


def verify_structure(html):
    template = build.read_text("study/a6-2.template.html")
    c = Collector()
    c.feed(template)
    for href in c.hrefs:
        if href.startswith("#"):
            check(href[1:] in c.ids, f"내부 링크 대상 없음: {href}")
        else:
            check(href.startswith("https://"), f"외부 링크 형식: {href}")
    check(not [s for s in c.srcs if not s.startswith("data:")], f"외부 리소스: {c.srcs}")
    for cid in c.controls:
        check(cid in c.labels_for or cid in c.wrapped, f"레이블 없는 입력 요소: {cid}")
    for sid in set(re.findall(r'\$\("#([A-Za-z0-9_-]+)"\)', template)):
        check(sid in c.ids, f"스크립트가 찾는 id가 없다: #{sid}")
    prose = "".join(c.text)
    hits = re.findall(r"\b(Val|val|Dev|dev)\b", prose)
    check(not hits, f"용어 규칙 위반(Val·Dev): {hits[:5]}")
    plain = re.sub(r"data:[a-z/]+;base64,[A-Za-z0-9+/=]+", "", html)   # 그림·사진의 base64는 제외하고 본다
    check("http://" not in plain and "cdn." not in plain.lower(), "외부 주소가 들어 있다")
    return len(c.ids)


def python_expected():
    expected = {}
    for name in SERIES:
        expected[name] = load_json(RESULTS / f"ts_baselines_{name}.json")["metrics"]
    grid = [round(x, 2) for x in np.linspace(0, 1.6, 21)]
    diag_f = [[t, v, diagnose_forecast(t, v, 1.0, 1.0).state] for t in grid for v in grid]
    grid_c = [round(x, 2) for x in np.linspace(0, 1, 21)]
    diag_c = [[t, v, diagnose_classification(t, v).state] for t in grid_c for v in grid_c]
    prep = prepare("aapl")
    rows = np.arange(prep.first_target - 90, prep.splits["train"][-1] + 1)
    lo, hi = prep.y[rows].min(), prep.y[rows].max()
    test_max = float(((prep.y[prep.splits["test"]] - lo) / (hi - lo)).max())
    return expected, diag_f, diag_c, test_max


def verify_math(data, html):
    lib = re.search(r'<script id="mathlib">(.*?)</script>', html, re.S).group(1)
    expected, diag_f, diag_c, test_max = python_expected()
    series = {k: {"y": v["y"], "splits": v["splits"], "with_mape": v["with_mape"]} for k, v in data["ts"].items()}
    first = data["ts"]["aapl"]["first_target"]
    script = lib + f"""
const S = {json.dumps(series)};
const out = {{ baselines: {{}}, diagF: [], diagC: [], improve: MathLib.improvement(2.0, 1.5) }};
for (const k in S) out.baselines[k] = MathLib.baselineTable(S[k]);
for (const [t, v] of {json.dumps([d[:2] for d in diag_f])}) out.diagF.push(MathLib.diagnoseForecast(t, v, 1, 1).state);
for (const [t, v] of {json.dumps([d[:2] for d in diag_c])}) out.diagC.push(MathLib.diagnoseClassification(t, v).state);
const a = S.aapl, fit = MathLib.range({first} - 90, a.splits.train[1]);
const scaled = MathLib.minmax(a.y, fit);
out.testMax = Math.max(...MathLib.range(a.splits.test[0], a.splits.test[1]).map(k => scaled[k]));
console.log(JSON.stringify(out));
"""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(script)
    result = subprocess.run(["node", f.name], capture_output=True, text=True, encoding="utf-8")
    Path(f.name).unlink()
    if not check(result.returncode == 0, f"Node.js 실행 실패: {result.stderr[:300]}"):
        return 0
    js = json.loads(result.stdout)
    count, worst = 0, 0.0
    for name, table in expected.items():
        for model, splits in table.items():
            for split, metrics in splits.items():
                for key, value in metrics.items():
                    got = js["baselines"][name][model][split][key]
                    if value is None:
                        check(got is None, f"{name} {model} {split} {key}: MAPE가 없어야 한다")
                        continue
                    rel = abs(got - value) / max(abs(value), 1e-12)
                    worst = max(worst, rel)
                    count += check(rel < 1e-6, f"{name} {model} {split} {key}: JS {got} vs Python {value}")
    for (t, v, state), got in zip(diag_f, js["diagF"]):
        count += check(state == got, f"시계열 진단 불일치: Train {t}, Validation {v}: {got} vs {state}")
    for (t, v, state), got in zip(diag_c, js["diagC"]):
        count += check(state == got, f"분류 진단 불일치: Train {t}, Validation {v}: {got} vs {state}")
    count += check(abs(js["improve"] - improvement(2.0, 1.5)) < 1e-12, "개선율 계산 불일치")
    count += check(abs(js["testMax"] - test_max) < 1e-6, f"MinMax Test 최댓값 불일치: {js['testMax']} vs {test_max}")
    print(f"  베이스라인 지표 최대 상대 오차 {worst:.2e}")
    return count


def main():
    utf8_console()
    html = HTML.read_text(encoding="utf-8")
    data = load_data(html)
    n_files = verify_files()
    n_excerpts = verify_excerpts(data, html)
    n_ids = verify_structure(html)
    n_math = verify_math(data, html)
    print(f"파일 {n_files}개, 발췌 {n_excerpts}개, id {n_ids}개, 계산 대조 {n_math}건")
    if failures:
        print(f"\n실패 {len(failures)}건:")
        for msg in failures[:40]:
            print("  -", msg)
        sys.exit(1)
    print("모든 검사를 통과했다.")


if __name__ == "__main__":
    main()
