"""study/a2-1.html이 현재 소스와 일치하고, 위젯 계산이 Python 구현과 같은지 검증한다.

1. source-manifest.json의 해시와 현재 파일 비교 (텍스트는 LF 정규화)
2. 내장 코드 발췌가 현재 원본 줄과 같은지 비교
3. 내부 링크(#id) 대상, 입력 요소 레이블, 외부 리소스 미사용 확인
4. HTML의 계산 함수(<script id="mathlib">)를 Node.js로 실행해 Python 결과와 비교

실행:  python tools/verify_study_guide.py   (Node.js 필요)
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_study_guide import byte_hash, code_excerpts, text_hash  # noqa: E402
from src import information as info  # noqa: E402
from src import linear_algebra as la  # noqa: E402
from src import optimizer as opt  # noqa: E402
from src import probability as prob  # noqa: E402
from src.neural_net import TwoLayerNet  # noqa: E402

HTML = ROOT / "study" / "a2-1.html"
MANIFEST = ROOT / "study" / "source-manifest.json"


def check_files(html):
    """해시·발췌·링크·레이블·외부 리소스 검사. 실패 목록을 반환한다."""
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
    for target in set(re.findall(r'href="#([^"]+)"', html)) | set(re.findall(r'data-go="#([^"]+)"', html)):
        if target not in ids:
            errors.append(f"없는 링크 대상: #{target}")
    for target in set(re.findall(r"\$\('#([A-Za-z][\w-]*)'\)", html)):
        if target not in ids and not target.startswith(("sm-", "ws-")):  # 동적으로 만드는 요소
            errors.append(f"스크립트가 찾는 요소 없음: #{target}")
    static = re.sub(r"<script\b.*?</script>", "", html, flags=re.S)  # 스크립트가 만드는 요소 제외
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
    """Node.js가 같은 입력으로 계산해 비교할 Python 기준값을 만든다."""
    cases = {"network": [], "area": [], "power": [], "softmax": [], "normal": [], "bernoulli": [],
             "info": [], "optim": [], "svd": []}
    rng = np.random.default_rng(42)
    nets = [dict(x=[1.0, 0.0], W1=[[0.1, 0.2], [0.3, 0.4]], b1=[0.0, 0.0], W2=[0.5, 0.6], b2=0.0, y=1.0)]
    for i in range(6):
        nets.append(dict(x=rng.normal(size=2).tolist(), W1=rng.normal(size=(2, 2)).tolist(),
                         b1=rng.normal(size=2).tolist(), W2=rng.normal(size=2).tolist(),
                         b2=float(rng.normal()), y=float(i % 2)))
    for p in nets:
        net = TwoLayerNet(p["W1"], p["b1"], p["W2"], p["b2"])
        c = net.forward(p["x"], p["y"])
        g = net.backward(c, p["y"])
        cases["network"].append({"input": p, "expect": {
            "z1": c["z1"].tolist(), "a1": c["a1"].tolist(), "z2": c["z2"], "yp": c["y_pred"], "loss": c["loss"],
            "dyp": g["dL_dy_pred"], "dz2": g["dL_dz2"], "dW2": g["dL_dW2"].tolist(), "da1": g["dL_da1"].tolist(),
            "dz1": g["dL_dz1"].tolist(), "dW1": g["dL_dW1"].tolist()}})
    for A in (la.rotation_matrix(np.pi / 4), la.scaling_matrix(2, 0.5), la.shear_matrix(1.0),
              np.array([[2.0, 1.0], [1.0, 3.0]]), np.array([[0.0, 2.0], [1.0, 0.0]])):
        r = la.area_ratio_check(A)
        cases["area"].append({"A": A.tolist(), "det": r["det"], "before": r["area_before"], "ratio": r["area_ratio"]})
    for A in ([[4.0, 1.0], [1.0, 3.0]], [[1.0, 2.0], [2.0, 1.0]], [[3.0, 0.2], [0.2, 2.9]]):
        x0 = np.random.default_rng(42).standard_normal(2)
        r = la.power_iteration(np.array(A), x0=x0)
        cases["power"].append({"A": A, "x0": x0.tolist(), "eigenvalue": r["eigenvalue"],
                               "eigenvector": r["eigenvector"].tolist(), "iterations": r["iterations"]})
    for z in (rng.normal(size=5).tolist(), [1000.0, 1001.0, 1002.0], [-3.0, 0.0, 2.5, 7.0]):
        cases["softmax"].append({"z": z, "expect": prob.softmax(z).tolist()})
    for x, mu, var in ((0.3, 0.0, 1.0), (2.4, 2.0, 0.5), (-1.0, 1.0, 0.1)):
        cases["normal"].append({"x": x, "mu": mu, "var": var, "expect": float(prob.normal_pdf(x, mu, var))})
    for p in (0.3, 0.7):
        cases["bernoulli"].append({"p": p, "expect": prob.bernoulli_pmf([0, 1], p).tolist()})
    for p, q in (([0.7, 0.2, 0.1], [0.4, 0.4, 0.2]), ([0.7, 0.3], [0.4, 0.6]), ([0.0, 1.0, 0.0], [0.4, 0.4, 0.2])):
        cases["info"].append({"p": p, "q": q, "H": info.entropy(p), "CE": info.cross_entropy(p, q),
                              "KL": info.kl_divergence(p, q)})
    funcs = {"bowl": opt.quadratic_grad, "ellipse": opt.elliptic_grad,
             "rosenbrock": opt.rosenbrock_grad, "saddle": opt.saddle_grad}
    hess = {"bowl": lambda p: np.diag([2.0, 2.0]), "ellipse": lambda p: np.diag([2.0, 20.0]),
            "saddle": lambda p: np.diag([2.0, -2.0]),
            "rosenbrock": lambda p: np.array([[2 - 400 * (p[1] - p[0] ** 2) + 800 * p[0] ** 2, -400 * p[0]],
                                              [-400 * p[0], 200.0]])}
    runs = [("bowl", "GD", 0.1, 100, [5, 5]), ("bowl", "Momentum", 0.1, 100, [5, 5]), ("bowl", "GD", 1.1, 30, [5, 5]),
            ("ellipse", "GD", 0.01, 100, [5, 5]), ("ellipse", "Momentum", 0.01, 100, [5, 5]),
            ("ellipse", "Adam", 0.1, 200, [5, 5]), ("bowl", "Adam", 0.3, 150, [5, 5]),
            ("rosenbrock", "GD", 0.001, 500, [-1.5, 2]), ("rosenbrock", "Newton", 1.0, 50, [-1.5, 2]),
            ("saddle", "Newton", 1.0, 5, [1, 0.5]), ("ellipse", "Newton", 1.0, 5, [5, 5])]
    for fname, name, lr, n, x0 in runs:
        o = {"GD": lambda: opt.VanillaGD(lr), "Momentum": lambda: opt.Momentum(lr, 0.9), "Adam": lambda: opt.Adam(lr),
             "Newton": lambda: opt.NewtonMethod(hess_fn=hess[fname], lr=lr)}[name]()
        stop = 1e-10 if name == "Newton" else None
        path = opt.optimize(o, funcs[fname], np.array(x0, dtype=float), n, stop_tol=stop)
        cases["optim"].append({"f": fname, "opt": name, "lr": lr, "n": n, "x0": x0, "stop": stop,
                               "final": path[-1].tolist(), "length": len(path)})
    gray = plt.imread(ROOT / "data" / "grace_hopper_128.png")[..., 0]
    for k in (10, 50, 100):
        r = la.svd_compress(np.rint(gray * 255) / 255, k)
        cases["svd"].append({"k": k, "relErr": r["relative_error"], "energy": r["energy_retained"],
                             "psnr": r["psnr_db"], "storage": r["storage_ratio"]})
    return cases


NODE_RUNNER = r"""
const fs = require('fs');
const [htmlPath, casesPath] = process.argv.slice(2);
const html = fs.readFileSync(htmlPath, 'utf8');
const lib = html.match(/<script id="mathlib">([\s\S]*?)<\/script>/)[1];
const M = new Function(lib + '\nreturn M;')();
const DATA = JSON.parse(html.match(/const DATA = (\{[\s\S]*?\});<\/script>/)[1].replace(/<\\\//g, '</'));
const C = JSON.parse(fs.readFileSync(casesPath, 'utf8'));
let n = 0; const fails = [];
const close = (a, b, tol, label) => {
  n++;
  if (Array.isArray(b)) { if (!Array.isArray(a) || a.length !== b.length) { fails.push(label + ' 길이'); return; } b.forEach((v, i) => { n--; close(a[i], v, tol, label + '[' + i + ']'); }); return; }
  const ok = (a === b) || Math.abs(a - b) <= tol * Math.max(1, Math.abs(b));
  if (!ok) fails.push(`${label}: js=${a} py=${b}`);
};
C.network.forEach((c, i) => { const r = M.network(c.input); for (const k in c.expect) close(r[k], c.expect[k], 1e-12, `network${i}.${k}`); });
C.area.forEach((c, i) => { const r = M.areaRatio(c.A); close(r.det, c.det, 1e-12, `area${i}.det`); close(r.before, c.before, 1e-12, `area${i}.before`); close(r.ratio, c.ratio, 1e-12, `area${i}.ratio`); });
C.power.forEach((c, i) => { const r = M.powerIteration(c.A, c.x0); close(r.eigenvalue, c.eigenvalue, 1e-12, `power${i}.lambda`); close(r.eigenvector, c.eigenvector, 1e-10, `power${i}.v`); close(r.iterations, c.iterations, 0, `power${i}.iters`); });
C.softmax.forEach((c, i) => close(M.softmax(c.z), c.expect, 1e-14, `softmax${i}`));
C.normal.forEach((c, i) => close(M.normalPdf(c.x, c.mu, c.var), c.expect, 1e-14, `normal${i}`));
C.bernoulli.forEach((c, i) => close([M.bernoulliPmf(0, c.p), M.bernoulliPmf(1, c.p)], c.expect, 1e-14, `bernoulli${i}`));
C.info.forEach((c, i) => { close(M.entropy(c.p), c.H, 1e-12, `entropy${i}`); close(M.crossEntropy(c.p, c.q), c.CE, 1e-12, `ce${i}`); close(M.kl(c.p, c.q), c.KL, 1e-12, `kl${i}`); });
C.optim.forEach((c, i) => { const path = M.runOptimizer(c.f, c.opt, { lr: c.lr, beta: 0.9 }, c.x0, c.n, c.stop);
  close(path.length, c.length, 0, `optim${i}(${c.f},${c.opt}).length`); close(path[path.length - 1], c.final, 1e-9, `optim${i}(${c.f},${c.opt}).final`); });
const dec = (b64, T) => new T(Uint8Array.from(Buffer.from(b64, 'base64')).buffer);
const { m, n: nn } = DATA.svd, U = dec(DATA.svd.U, Float32Array), S = dec(DATA.svd.S, Float32Array), Vt = dec(DATA.svd.Vt, Float32Array);
const orig = Float64Array.from(dec(DATA.svd.image, Uint8Array), v => v / 255);
C.svd.forEach(c => { const st = M.svdStats(orig, M.svdReconstruct(U, S, Vt, m, nn, c.k), S, m, nn, c.k);
  close(st.relErr, c.relErr, 2e-4, `svd${c.k}.relErr`); close(st.energy, c.energy, 1e-6, `svd${c.k}.energy`);
  close(st.psnr, c.psnr, 2e-3, `svd${c.k}.psnr`); close(st.storage, c.storage, 1e-12, `svd${c.k}.storage`); });
console.log(JSON.stringify({ compared: n, fails }));
"""


def main():
    """모든 검사를 실행하고 실패가 있으면 종료 코드 1을 반환한다."""
    html = HTML.read_text(encoding="utf-8")
    errors, data = check_files(html)
    cases = python_cases(data)
    with tempfile.TemporaryDirectory(dir=ROOT / "study") as tmp:
        runner, case_file = Path(tmp) / "runner.cjs", Path(tmp) / "cases.json"
        runner.write_text(NODE_RUNNER, encoding="utf-8")
        case_file.write_text(json.dumps(cases), encoding="utf-8")
        proc = subprocess.run(["node", str(runner), str(HTML), str(case_file)],
                              capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        errors.append("Node 실행 실패: " + proc.stderr.strip()[:500])
        result = {"compared": 0, "fails": []}
    else:
        result = json.loads(proc.stdout)
        errors.extend("계산 불일치 " + f for f in result["fails"])
    counts = {k: len(v) for k, v in cases.items()}
    print(f"파일·발췌·링크 검사 완료, 코드 발췌 {len(data['code'])}개, 그림 {len(data['images'])}개")
    print(f"JS ↔ Python 대조: 사례 {counts}, 비교 값 {result['compared']}개")
    if errors:
        print("실패:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print("통과")


if __name__ == "__main__":
    main()
