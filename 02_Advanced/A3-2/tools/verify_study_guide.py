"""study/a3-2.html이 현재 소스와 일치하고, 위젯 계산이 Python·OpenCV 구현과 같은지 검증한다.

1. source-manifest.json의 해시와 현재 파일 비교 (텍스트는 LF 정규화)
2. 내장 코드 발췌가 현재 원본 줄과 같은지 비교
3. 내부 링크(#id) 대상, 입력 요소 레이블, 외부 리소스 미사용 확인
4. HTML의 계산 함수(<script id="mathlib">)를 Node.js로 실행해 Python 결과와 비교
   - Hungarian·탐욕 할당 (무작위 행렬)
   - 추적기 재생: 시나리오 5개 × 추적기 설정 9개의 프레임별 ID·박스
   - 판정: 같은 조합의 이벤트별 ID Switch·추적 실패와 합계
   - 이동 평균 배경, 모폴로지(열림·닫힘)와 덩어리 박스, 비율 검정 개수

실행:  python tools/verify_study_guide.py [--mathlib 파일]   (Node.js 필요)
"""
import argparse
import base64
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_study_guide import byte_hash, code_excerpts, text_hash  # noqa: E402
from src import evaluate as E  # noqa: E402
from src import experiments as X  # noqa: E402
from src import synthetic as S  # noqa: E402
from src.features import TargetMatcher  # noqa: E402
from src.hungarian import greedy, hungarian  # noqa: E402
from src.image_io import imread  # noqa: E402
from src.motion import Detection, RunningAverageSubtractor  # noqa: E402
from src.tracker import Tracker  # noqa: E402

HTML = ROOT / "study" / "a3-2.html"
MANIFEST = ROOT / "study" / "source-manifest.json"
CONFIGS = [
    ("baseline", {}, {}),
    ("hungarian", {"matcher": "hungarian"}, {"matcher": "hungarian"}),
    ("iou", {"cost": "iou"}, {"cost": "iou"}),
    ("kalman", {"kalman": True}, {"kalman": True}),
    ("kalman_hungarian", {"kalman": True, "matcher": "hungarian"}, {"kalman": True, "matcher": "hungarian"}),
    ("dist30", {"max_distance": 30}, {"maxDistance": 30}),
    ("dist120", {"max_distance": 120}, {"maxDistance": 120}),
    ("missed5", {"max_missed": 5}, {"maxMissed": 5}),
    ("kalman_missed60", {"kalman": True, "max_missed": 60}, {"kalman": True, "maxMissed": 60}),
]
RAVG_MIN_AGREEMENT = 0.995   # float32(Python) vs float64(JS) 경계값 차이만 허용


def check_files(html):
    errors = []
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for rel, h in manifest["text"].items():
        if text_hash(ROOT / rel) != h:
            errors.append(f"텍스트 변경됨: {rel} — build_study_guide.py를 다시 실행")
    for rel, h in manifest["binary"].items():
        if byte_hash(ROOT / rel) != h:
            errors.append(f"결과 변경됨: {rel}")
    data = json.loads(re.search(r"const DATA = (\{.*?\});</script>", html, re.S).group(1).replace("<\\/", "</"))
    current = {(c["file"], c["name"]): c for c in code_excerpts()}
    for c in data["code"]:
        cur = current.get((c["file"], c["name"]))
        if cur is None or cur["text"] != c["text"] or cur["start"] != c["start"]:
            errors.append(f"코드 발췌 불일치: {c['file']}:{c['name']}")
    ids = set(re.findall(r'\sid="([^"]+)"', html))
    for target in set(re.findall(r'href="#([^"]+)"', html)):
        if target not in ids:
            errors.append(f"없는 링크 대상: #{target}")
    for target in set(re.findall(r"\$\('#([A-Za-z][\w-]*)'\)", html)):
        if target not in ids:
            errors.append(f"스크립트가 찾는 요소 없음: #{target}")
    static = re.sub(r"<script\b.*?</script>", "", html, flags=re.S)
    for m in re.finditer(r"<(input|select)\b[^>]*>", static):
        tag = m.group(0)
        if "aria-label" in tag:
            continue
        before = static[max(0, m.start() - 300):m.start()]
        if before.rfind("<label") <= before.rfind("</label>"):
            errors.append(f"레이블 없는 입력: {tag[:60]}")
    if re.search(r'<(script|link|img)[^>]+(src|href)="https?:', html):
        errors.append("외부 리소스를 불러옴 (오프라인 사용 불가)")
    return errors, data


def python_cases(data):
    """Node.js가 같은 입력으로 계산해 비교할 Python 기준값."""
    rng = np.random.default_rng(7)
    cases = {"assign": [], "track": [], "eval": [], "ravg": [], "morph": [], "ratio": []}
    for _ in range(150):
        n, m = (int(v) for v in rng.integers(1, 8, 2))
        c = rng.integers(0, 6, (n, m)).astype(float) if rng.random() < 0.4 else rng.uniform(0, 1, (n, m))
        rh, ch = hungarian(c)
        rg, cg = greedy(c)
        cases["assign"].append({"cost": c.tolist(), "h": [rh.tolist(), ch.tolist()], "g": [rg.tolist(), cg.tolist()]})
    for sc, raw in data["replay"].items():
        dets = [[Detection(tuple(b), (b[0] + b[2] / 2.0, b[1] + b[3] / 2.0), float(b[2] * b[3])) for b in fr]
                for fr in raw["dets"]]
        gt = S.load_gt(sc, "test")
        for name, pykw, jskw in CONFIGS:
            outs = E.track_detections(dets, Tracker(**pykw))
            cases["track"].append({"scenario": sc, "config": name, "opts": jskw,
                                   "ids": [[[t[0], *map(int, t[1])] for t in fr] for fr in outs]})
            r = E.evaluate_tracking(gt, outs)
            cases["eval"].append({"scenario": sc, "config": name, "opts": jskw,
                                  "summary": [r["switch_events"], r["switches"], r["fail_events"], r["fails"]],
                                  "events": [[e["switches"], e["fails"]] for e in r["events"]]})
    for name, p in data["pixels"].items():
        for alpha in (0.002, 0.01, 0.05, 0.2):
            for thr in (15, 25, 40):
                s = RunningAverageSubtractor(thr)
                fg = [int(s.apply(np.full((1, 1, 3), v, np.uint8), alpha)[0, 0] > 0) for v in p["values"]]
                cases["ravg"].append({"series": name, "alpha": alpha, "thr": thr, "fg": fg})
    mp = data["morph"]
    crop = np.frombuffer(base64.b64decode(mp["data"]), np.uint8).reshape(mp["h"], mp["w"])
    fg = np.where(crop > 200, 255, 0).astype(np.uint8)
    for ko in (1, 3, 5):
        for kc in (1, 5, 11, 21):
            out = fg
            if ko > 1:
                out = cv2.morphologyEx(out, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ko, ko)))
            if kc > 1:
                out = cv2.morphologyEx(out, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kc, kc)))
            contours, _ = cv2.findContours(out, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            boxes = sorted(list(cv2.boundingRect(c)) for c in contours)
            cases["morph"].append({"open": ko, "close": kc, "mask": base64.b64encode(out.tobytes()).decode("ascii"),
                                   "boxes": boxes})
    texture = imread(S.TARGET_DIR / "target.png")
    m = TargetMatcher(texture, "orb")
    conds = {"frontal": {}, "yaw60": {"yaw": 60}, "occ50": {"occlusion": 0.5}, "roll60": {"roll": 60}}
    for name in data["ratio"]["views"]:
        img, corners, H = next(X._views(texture, conds[name], 1, seed=5))
        for ratio in (0.6, 0.75, 0.9):
            m.ratio = ratio
            r = m.match(img)
            correct = 0
            if r.n_good:
                proj = cv2.perspectiveTransform(r.ref_pts[None], H)[0]
                correct = int((np.linalg.norm(proj - r.scene_pts, axis=1) < 5.0).sum())
            cases["ratio"].append({"view": name, "ratio": ratio, "kept": r.n_good, "correct": correct})
    return cases


NODE = r"""
const fs = require('fs');
const M = require(process.argv[2]);
const data = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const cases = JSON.parse(fs.readFileSync(process.argv[4], 'utf8'));
const report = {};
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
// 할당
let ok = 0, costOk = 0;
for (const c of cases.assign) {
  const h = M.hungarian(c.cost), g = M.greedy(c.cost);
  if (same(h, c.h) && same(g, c.g)) ok++;
  const sum = ([r, k]) => r.reduce((s, ri, i) => s + c.cost[ri][k[i]], 0);
  if (Math.abs(sum(h) - sum(c.h)) < 1e-9) costOk++;
}
report.assign = { n: cases.assign.length, exact: ok, cost: costOk };
// 추적 재생
const scen = {}; for (const [k, v] of Object.entries(data.replay)) scen[k] = M.prepScenario(v);
let tFrames = 0, tSame = 0; const tBad = [];
for (const c of cases.track) {
  const out = M.trackAll(scen[c.scenario].dets, c.opts);
  let bad = 0;
  out.forEach((fr, i) => { tFrames++; const js = fr.map(t => [t.id, ...t.bbox]); if (same(js, c.ids[i])) tSame++; else bad++; });
  if (bad) tBad.push(`${c.scenario}/${c.config}: ${bad} frames`);
}
report.track = { frames: tFrames, same: tSame, bad: tBad };
// 판정
let eSame = 0; const eBad = [];
for (const c of cases.eval) {
  const r = M.evaluate(scen[c.scenario], M.trackAll(scen[c.scenario].dets, c.opts));
  const js = [r.switchEvents, r.switches, r.failEvents, r.fails], ev = r.events.map(e => [e.switches, e.fails]);
  if (same(js, c.summary) && same(ev, c.events)) eSame++; else eBad.push(`${c.scenario}/${c.config}: js ${js} py ${c.summary}`);
}
report.eval = { n: cases.eval.length, same: eSame, bad: eBad };
// 이동 평균
let rN = 0, rSame = 0;
for (const c of cases.ravg) {
  const { fg } = M.runningAverage(data.pixels[c.series].values, c.alpha, c.thr);
  fg.forEach((v, i) => { rN++; if (v === c.fg[i]) rSame++; });
}
report.ravg = { n: rN, same: rSame };
// 모폴로지
const mp = data.morph, crop = Uint8Array.from(Buffer.from(mp.data, 'base64'));
const fg0 = crop.map(v => (v > 200 ? 255 : 0));
let mSame = 0, bSame = 0;
for (const c of cases.morph) {
  let out = fg0;
  if (c.open > 1) out = M.opening(out, mp.w, mp.h, mp.kernels[c.open]);
  if (c.close > 1) out = M.closing(out, mp.w, mp.h, mp.kernels[c.close]);
  const ref = Uint8Array.from(Buffer.from(c.mask, 'base64'));
  if (Buffer.compare(Buffer.from(out), Buffer.from(ref)) === 0) mSame++;
  const boxes = M.components(out, mp.w, mp.h).map(b => b.bbox).sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2] || a[3] - b[3]);
  if (same(boxes, c.boxes)) bSame++;
}
report.morph = { n: cases.morph.length, mask: mSame, boxes: bSame };
// 비율 검정
let qSame = 0;
for (const c of cases.ratio) { const r = M.ratioCounts(data.ratio.views[c.view], c.ratio); if (r.kept === c.kept && r.correct === c.correct) qSame++; }
report.ratio = { n: cases.ratio.length, same: qSame };
console.log(JSON.stringify(report));
"""


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--mathlib", help="HTML 대신 이 JS 파일의 계산 함수를 검증 (개발용)")
    args = ap.parse_args(argv)
    html = HTML.read_text(encoding="utf-8")
    errors, data = check_files(html)
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        lib = d / "mathlib.js"
        if args.mathlib:
            lib.write_text(Path(args.mathlib).read_text(encoding="utf-8"), encoding="utf-8")
        else:
            lib.write_text(re.search(r'<script id="mathlib">(.*?)</script>', html, re.S).group(1), encoding="utf-8")
        (d / "data.json").write_text(json.dumps(data), encoding="utf-8")
        cases = python_cases(data)
        (d / "cases.json").write_text(json.dumps(cases), encoding="utf-8")
        (d / "run.js").write_text(NODE, encoding="utf-8")
        out = subprocess.run(["node", str(d / "run.js"), str(lib), str(d / "data.json"), str(d / "cases.json")],
                             capture_output=True, text=True, encoding="utf-8")
    if out.returncode != 0:
        print(out.stderr)
        raise SystemExit("Node.js 실행 실패")
    r = json.loads(out.stdout)
    if r["assign"]["exact"] != r["assign"]["n"]:
        errors.append(f"할당 불일치: {r['assign']}")
    if r["track"]["same"] != r["track"]["frames"]:
        errors.append(f"추적 재생 불일치: {r['track']['bad'][:5]}")
    if r["eval"]["same"] != r["eval"]["n"]:
        errors.append(f"판정 불일치: {r['eval']['bad'][:5]}")
    if r["ravg"]["same"] < RAVG_MIN_AGREEMENT * r["ravg"]["n"]:
        errors.append(f"이동 평균 일치율 낮음: {r['ravg']}")
    if r["morph"]["mask"] != r["morph"]["n"] or r["morph"]["boxes"] != r["morph"]["n"]:
        errors.append(f"모폴로지 불일치: {r['morph']}")
    if r["ratio"]["same"] != r["ratio"]["n"]:
        errors.append(f"비율 검정 불일치: {r['ratio']}")
    total = (r["assign"]["n"] + r["track"]["frames"] + r["eval"]["n"] + r["ravg"]["n"] + r["morph"]["n"] * 2
             + r["ratio"]["n"])
    print(f"할당 {r['assign']['exact']}/{r['assign']['n']}, 추적 프레임 {r['track']['same']}/{r['track']['frames']}, "
          f"판정 {r['eval']['same']}/{r['eval']['n']}, 이동 평균 {r['ravg']['same']}/{r['ravg']['n']}, "
          f"모폴로지 {r['morph']['mask']}+{r['morph']['boxes']}/{2 * r['morph']['n']}, 비율 검정 {r['ratio']['same']}/{r['ratio']['n']}"
          f" — 비교 {total}회")
    if errors:
        print("\n".join("✗ " + e for e in errors))
        raise SystemExit(1)
    print("✓ 모든 검증 통과")


if __name__ == "__main__":
    main()
