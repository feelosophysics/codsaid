"""study/a3-1.html이 현재 소스와 일치하고, 위젯 계산이 Python·OpenCV 구현과 같은지 검증한다.

1. source-manifest.json의 해시와 현재 파일 비교 (텍스트는 LF 정규화)
2. 내장 코드 발췌가 현재 원본 줄과 같은지 비교
3. 내부 링크(#id) 대상, 입력 요소 레이블, 외부 리소스 미사용 확인
4. HTML의 계산 함수(<script id="mathlib">)를 Node.js로 실행해 Python·OpenCV 결과와 비교

실행:  python tools/verify_study_guide.py   (Node.js 필요)
"""
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
from src import geometry  # noqa: E402
from src.synthetic import project, rotation  # noqa: E402

HTML = ROOT / "study" / "a3-1.html"
MANIFEST = ROOT / "study" / "source-manifest.json"

# Canny는 OpenCV 내부(정수 기울기, 경계 처리)와 완전히 같게 만들지 않았다. 픽셀 일치율 기준으로 비교한다.
CANNY_MIN_AGREEMENT = 0.995
ADAPTIVE_MIN_AGREEMENT = 0.995


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


def decode_gray(item):
    return np.frombuffer(base64.b64decode(item["data"]), np.uint8).reshape(item["h"], item["w"])


def python_cases(data):
    """Node.js가 같은 입력으로 계산해 비교할 Python 기준값."""
    rng = np.random.default_rng(42)
    cases = {"kernel": [], "blur": [], "canny": [], "dp": [], "order": [], "convex": [], "homography": [],
             "aspect": [], "adaptive": [], "otsu": [], "project": []}
    for k in range(1, 22, 2):
        cases["kernel"].append({"k": k, "expect": cv2.getGaussianKernel(k, 0).ravel().tolist()})
    for name, item in data["gray"].items():
        g = decode_gray(item)
        for k in (3, 5, 9, 13):
            cases["blur"].append({"img": name, "k": k, "expect": cv2.GaussianBlur(g, (k, k), 0).ravel().tolist()})
        blurred = cv2.GaussianBlur(g, (5, 5), 0)
        for lo, hi in ((50, 150), (10, 60), (100, 250)):
            cases["canny"].append({"img": name, "lo": lo, "hi": hi,
                                   "expect": cv2.Canny(blurred, lo, hi).ravel().tolist()})
    for name, c in data["contours"].items():
        pts = np.array(c["points"], np.int32).reshape(-1, 1, 2)
        per = cv2.arcLength(pts, True)
        for e in (0.01, 0.02, 0.04, 0.08):
            cases["dp"].append({"c": name, "e": e, "eps": e * per, "expect": len(cv2.approxPolyDP(pts, e * per, True))})
    for deg in (-60, -45, -30, 0, 15, 44, 45, 46, 80):
        t = np.radians(deg)
        base = np.array([[-90, -70], [90, -70], [100, 70], [-100, 70]], float)
        quad = base @ np.array([[np.cos(t), np.sin(t)], [-np.sin(t), np.cos(t)]]) + 150
        shuffled = quad[[2, 0, 3, 1]]
        cases["order"].append({"pts": shuffled.tolist(), "angle": geometry.order_points(shuffled).tolist(),
                               "sumdiff": geometry.order_points_sum_diff(shuffled).tolist()})
    for _ in range(20):
        pts = rng.uniform(0, 100, (4, 2))
        cases["convex"].append({"pts": pts.tolist(), "convex": geometry.is_convex(pts),
                                "area": geometry.polygon_area(pts)})
    for _ in range(8):
        src = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], float) * rng.uniform(100, 300) + rng.uniform(-20, 20, (4, 2))
        dst = rng.uniform(0, 400, (4, 2))
        H = cv2.getPerspectiveTransform(src.astype(np.float32), dst.astype(np.float32))
        probe = np.vstack([src, rng.uniform(0, 300, (6, 2))]).astype(np.float64)
        mapped = cv2.perspectiveTransform(probe.reshape(-1, 1, 2), H).reshape(-1, 2)
        # OpenCV는 float32 입력으로 풀어 네 꼭짓점도 1e-4px 수준 오차가 있다. JS(float64)는 꼭짓점을 정확히 보내는지,
        # 그리고 다른 점들을 OpenCV와 1e-3px 안에서 같은 곳으로 보내는지 비교한다.
        cases["homography"].append({"src": src.astype(np.float32).astype(float).tolist(),
                                    "dst": dst.astype(np.float32).astype(float).tolist(),
                                    "probe": probe.tolist(), "expect": mapped.tolist()})
    for wmm, hmm, p, y, r in ((210, 297, 50, 0, 5), (210, 297, 5, 2, 3), (80, 210, 58, -8, 30), (90, 50, 30, 20, -10),
                              (210, 297, 0, 0, 0), (216, 279, 65, -6, -12)):
        corners = np.array([[-wmm / 2, -hmm / 2], [wmm / 2, -hmm / 2], [wmm / 2, hmm / 2], [-wmm / 2, hmm / 2]])
        rot = rotation(p, y, r)
        cam = np.column_stack([corners, np.zeros(4)]) @ rot.T + [0, 0, 650]
        quad = cam[:, :2] / cam[:, 2:] * 1000 + [480, 640]
        o = geometry.order_points(quad + rng.normal(0, 1.0, (4, 2)))
        aspect, focal, method = geometry.estimate_aspect_ratio(o, (1280, 960))
        cases["aspect"].append({"q": o.tolist(), "aspect": aspect, "method": method,
                                "size": list(geometry.output_size_by_distance(o))})
        cases["project"].append({"args": [wmm, hmm, p, y, r], "expect": quad.tolist()})
    page = decode_gray(data["shadowPage"])
    for block in (3, 7, 15, 31, 61):
        for c in (5, 10):
            cases["adaptive"].append({"block": block, "c": c, "expect": cv2.adaptiveThreshold(
                page, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block, c).ravel().tolist()})
    for name, item in list(data["gray"].items()) + [("page", data["shadowPage"])]:
        t, _ = cv2.threshold(decode_gray(item), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cases["otsu"].append({"img": name, "expect": t})
    _ = project  # synthetic.project와 같은 식을 JS projectPaper가 쓴다 (위 aspect 사례에서 직접 계산)
    return cases


NODE_RUNNER = r"""
const fs = require('fs');
const [htmlPath, casesPath] = process.argv.slice(2);
const html = fs.readFileSync(htmlPath, 'utf8');
const lib = html.match(/<script id="mathlib">([\s\S]*?)<\/script>/)[1];
const M = new Function(lib + '\nreturn M;')();
const DATA = JSON.parse(html.match(/const DATA = (\{[\s\S]*?\});<\/script>/)[1].replace(/<\\\//g, '</'));
const C = JSON.parse(fs.readFileSync(casesPath, 'utf8'));
const dec = b64 => Uint8Array.from(Buffer.from(b64, 'base64'));
const G = {}; for (const [k, v] of Object.entries(DATA.gray)) G[k] = { w: v.w, h: v.h, px: dec(v.data) };
const PAGE = { w: DATA.shadowPage.w, h: DATA.shadowPage.h, px: dec(DATA.shadowPage.data) };
let n = 0; const fails = [], notes = [];
const close = (a, b, tol, label) => {
  if (Array.isArray(b)) { if (!Array.isArray(a) || a.length !== b.length) { n++; fails.push(label + ' 길이'); return; } b.forEach((v, i) => close(a[i], v, tol, label + '[' + i + ']')); return; }
  n++; if (!(a === b || Math.abs(a - b) <= tol * Math.max(1, Math.abs(b)))) fails.push(`${label}: js=${a} py=${b}`);
};
C.kernel.forEach(c => close(M.gaussianKernel1d(c.k), c.expect, 1e-12, `kernel${c.k}`));
C.blur.forEach(c => { const g = G[c.img], r = M.gaussianBlur(g.px, g.w, g.h, c.k); let d = 0; r.forEach((v, i) => d = Math.max(d, Math.abs(v - c.expect[i]))); n++; if (d > 1) fails.push(`blur ${c.img} k${c.k}: 최대 차이 ${d}`); });
C.canny.forEach(c => {
  const g = G[c.img], blurred = Uint8Array.from(require('./blur_' + c.img + '.json'));
  const e = M.canny(blurred, g.w, g.h, c.lo, c.hi); let same = 0, tp = 0, fp = 0, fn = 0;
  e.forEach((v, i) => { const o = c.expect[i]; if (v === o) same++; if (v && o) tp++; else if (v) fp++; else if (o) fn++; });
  const agree = same / e.length, f1 = tp ? 2 * tp / (2 * tp + fp + fn) : 1; n++;
  notes.push(`canny ${c.img} (${c.lo},${c.hi}) 일치 ${(agree * 100).toFixed(2)}% F1 ${f1.toFixed(3)}`);
  if (agree < C.cannyMin) fails.push(`canny ${c.img} (${c.lo},${c.hi}) 일치율 ${agree}`);
});
C.dp.forEach(c => { const pts = DATA.contours[c.c].points, r = M.approxClosed(pts, c.eps); n++; notes.push(`dp ${c.c} e=${c.e}: js ${r.length} cv ${c.expect}`); if (c.e === 0.02 && r.length !== c.expect) fails.push(`approxPolyDP ${c.c} ε=2%: js ${r.length} vs cv ${c.expect}`); });
C.order.forEach((c, i) => { close(M.orderPoints(c.pts), c.angle, 1e-12, `order${i}`); close(M.orderSumDiff(c.pts), c.sumdiff, 1e-12, `sumdiff${i}`); });
C.convex.forEach((c, i) => { n++; if (M.isConvex(c.pts) !== c.convex) fails.push(`convex${i}`); close(M.polygonArea(c.pts), c.area, 1e-12, `area${i}`); });
C.homography.forEach((c, i) => { const H = M.homography(c.src, c.dst);
  c.src.forEach((p, j) => close(M.applyH(H, p[0], p[1]), c.dst[j], 1e-9, `H${i} 꼭짓점${j}`));
  c.probe.forEach((p, j) => { const q = M.applyH(H, p[0], p[1]); [0, 1].forEach(k => { n++; if (Math.abs(q[k] - c.expect[j][k]) > 1e-3) fails.push(`H${i} 점${j}: js=${q[k]} cv=${c.expect[j][k]}`); }); }); });
C.aspect.forEach((c, i) => { const z = M.zhangAspect(c.q, 960, 1280); close(z.aspect, c.aspect, 1e-9, `aspect${i}`); n++; if (z.method !== c.method) fails.push(`aspect${i} method ${z.method} vs ${c.method}`); close(M.distanceSize(c.q), c.size, 0, `size${i}`); });
C.project.forEach((c, i) => close(M.projectPaper(...c.args, 960, 1280, 1000, 650), c.expect, 1e-9, `project${i}`));
C.adaptive.forEach(c => { const r = M.adaptiveThreshold(PAGE.px, PAGE.w, PAGE.h, c.block, c.c); let same = 0; r.forEach((v, i) => { if (v === c.expect[i]) same++; }); const a = same / r.length; n++; notes.push(`adaptive b${c.block} C${c.c} 일치 ${(a * 100).toFixed(3)}%`); if (a < C.adaptiveMin) fails.push(`adaptive b${c.block} C${c.c} 일치율 ${a}`); });
C.otsu.forEach(c => { const g = c.img === 'page' ? PAGE : G[c.img]; close(M.otsu(g.px), c.expect, 0, `otsu ${c.img}`); });
console.log(JSON.stringify({ compared: n, fails, notes }));
"""


def main():
    html = HTML.read_text(encoding="utf-8")
    errors, data = check_files(html)
    cases = python_cases(data)
    cases["cannyMin"], cases["adaptiveMin"] = CANNY_MIN_AGREEMENT, ADAPTIVE_MIN_AGREEMENT
    with tempfile.TemporaryDirectory(dir=ROOT / "study") as tmp:
        tmp = Path(tmp)
        for name, item in data["gray"].items():  # Canny 비교는 같은 블러 입력(OpenCV)에서 시작한다
            blurred = cv2.GaussianBlur(decode_gray(item), (5, 5), 0)
            (tmp / f"blur_{name}.json").write_text(json.dumps(blurred.ravel().tolist()), encoding="utf-8")
        (tmp / "runner.cjs").write_text(NODE_RUNNER, encoding="utf-8")
        (tmp / "cases.json").write_text(json.dumps(cases), encoding="utf-8")
        proc = subprocess.run(["node", str(tmp / "runner.cjs"), str(HTML), str(tmp / "cases.json")],
                              capture_output=True, text=True, encoding="utf-8", cwd=tmp)
    if proc.returncode != 0:
        errors.append("Node 실행 실패: " + proc.stderr.strip()[:800])
        result = {"compared": 0, "fails": [], "notes": []}
    else:
        result = json.loads(proc.stdout)
        errors.extend("계산 불일치 " + f for f in result["fails"])
    counts = {k: len(v) for k, v in cases.items() if isinstance(v, list)}
    print(f"파일·발췌·링크 검사 완료, 코드 발췌 {len(data['code'])}개, 그림 {len(data['images'])}개")
    print(f"JS ↔ Python/OpenCV 대조: 사례 {counts}, 비교 {result['compared']}회")
    for note in result["notes"]:
        print("  ", note)
    if errors:
        print("실패:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print("통과")


if __name__ == "__main__":
    main()
