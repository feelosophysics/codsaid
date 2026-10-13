"""study/a6-1.html이 현재 저장소와 일치하고, 위젯 계산이 Python 구현과 같은지 검사한다.

1. 파일 대조: source-manifest.json의 해시와 현재 파일
2. 코드 발췌: HTML 속 발췌가 현재 원본 줄과 같은지
3. 페이지 구조: 내부 링크 대상, 입력 요소 레이블, 외부 리소스 없음
4. 계산 대조: <script id="mathlib">를 Node.js로 실행해 minigrad 결과와 비교

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
sys.path.insert(0, str(ROOT / "scripts"))

import build_study_guide as build  # noqa: E402
from minigrad import Tensor, nn  # noqa: E402
from minigrad.gradcheck import relative_difference  # noqa: E402
from train_xor import build_model, train_xor  # noqa: E402

HTML = build.OUTPUT
failures = []


def check(condition, message):
    if not condition:
        failures.append(message)
    return condition


# ---------------------------------------------------------------------------- 1. 파일
def verify_files():
    manifest = json.loads(build.MANIFEST.read_text(encoding="utf-8"))
    for path, digest in manifest["text"].items():
        check(build.text_hash(path) == digest, f"텍스트 해시 불일치: {path} (다시 빌드 필요)")
    for path, digest in {**manifest["binary"], **manifest["mnist"]}.items():
        check(build.binary_hash(path) == digest, f"바이너리 해시 불일치: {path}")
    return len(manifest["text"]) + len(manifest["binary"]) + len(manifest["mnist"])


def load_data(html):
    match = re.search(r"const DATA = (.*?);</script>", html, re.S)
    return json.loads(match.group(1).replace("<\\/", "</"))


# ---------------------------------------------------------------------------- 2. 발췌
def verify_excerpts(data, html):
    for key, (path, name) in build.EXCERPTS.items():
        current = build.excerpt(path, name)
        shown = data["code"].get(key)
        check(shown == current, f"코드 발췌가 원본과 다르다: {key}")
        check(f'data-code="{key}"' in html, f"템플릿에서 쓰지 않는 발췌: {key}")
    used = set(re.findall(r'data-code="([^"]+)"', html))
    check(used <= set(build.EXCERPTS), f"정의되지 않은 발췌: {used - set(build.EXCERPTS)}")
    figs = set(re.findall(r'data-fig="([^"]+)"', html))
    check(figs == set(build.FIGURES), f"그림 목록 불일치: {figs ^ set(build.FIGURES)}")
    return len(build.EXCERPTS)


# ---------------------------------------------------------------------------- 3. 구조
class Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.hrefs, self.srcs, self.labels_for, self.controls = set(), [], [], set(), []
        self.label_depth, self.wrapped = 0, set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and "href" in a:
            self.hrefs.append(a["href"])
        if "src" in a:
            self.srcs.append(a["src"])
        if tag == "link" and "href" in a:
            self.srcs.append(a["href"])
        if tag == "label":
            self.label_depth += 1
            if "for" in a:
                self.labels_for.add(a["for"])
        if tag in ("input", "select", "textarea"):
            self.controls.append(a.get("id"))
            if self.label_depth:
                self.wrapped.add(a.get("id"))

    def handle_endtag(self, tag):
        if tag == "label":
            self.label_depth -= 1


def verify_structure(template):
    c = Collector()
    c.feed(template)
    internal = [h[1:] for h in c.hrefs if h.startswith("#")]
    for target in internal:
        check(target in c.ids, f"내부 링크 대상 없음: #{target}")
    for control in c.controls:
        check(control and (control in c.labels_for or control in c.wrapped), f"레이블 없는 입력 요소: {control}")
    for src in c.srcs:
        check(not re.match(r"(https?:)?//", src), f"외부 리소스: {src}")
    check(not re.search(r"url\(\s*['\"]?https?:", template), "CSS에 외부 url()")
    check("@import" not in template, "CSS @import 사용")
    for target in sorted(set(re.findall(r'[$]\("#([\w-]+)"\)', template))):
        check(target in c.ids, f"스크립트가 찾는 id가 없다: #{target}")
    return len(internal), len(c.controls)


# ---------------------------------------------------------------------------- 4. 계산 대조
def python_cases():
    rng = np.random.default_rng(0)
    cases = {"xor": [], "hand": [], "graph": [], "init": [], "act": [], "softmax": [], "bce": [], "reldiff": []}
    for init, seed, loss in (("he", 0, "bce"), ("random", 0, "bce"), ("random", 4, "bce"), ("random", 4, "logits"),
                             ("xavier", 3, "bce"), ("zero", 0, "bce")):
        model = build_model(init, seed, sigmoid_output=(loss == "bce"))
        params = [{"W": layer.W.data.tolist(), "b": layer.b.data.tolist()} for layer in model.layers if hasattr(layer, "W")]
        losses = train_xor(init, seed, 100, loss=loss)[0]
        cases["xor"].append({"params": params, "loss": loss, "expected": losses.tolist(), "name": f"{init}/{seed}/{loss}"})

    problems = [{"x": [1, 2], "y": 1, "W1": [[0.5, -0.6], [0.2, 0.1]], "b1": [0.1, 0.2], "W2": [0.8, -0.5], "b2": -0.3}]
    for _ in range(6):
        problems.append({"x": rng.choice([-2, -1, -0.5, 0.5, 1, 2], 2).tolist(), "y": int(rng.integers(0, 2)),
                         "W1": np.round(rng.uniform(-1, 1, (2, 2)), 1).tolist(), "b1": np.round(rng.uniform(-.5, .5, 2), 1).tolist(),
                         "W2": np.round(rng.uniform(-1, 1, 2), 1).tolist(), "b2": round(float(rng.uniform(-.5, .5)), 1)})
    for p in problems:
        x = Tensor(np.array([p["x"]], dtype=float))
        W1, b1 = Tensor(p["W1"], requires_grad=True), Tensor(p["b1"], requires_grad=True)
        W2, b2 = Tensor(np.array(p["W2"])[:, None], requires_grad=True), Tensor([p["b2"]], requires_grad=True)
        z1 = x @ W1 + b1
        h = z1.relu()
        z2 = h @ W2 + b2
        prob = z2.sigmoid()
        loss = nn.binary_cross_entropy(prob, [[p["y"]]])
        loss.backward()
        cases["hand"].append({"problem": p, "expected": {
            "z1": z1.data[0].tolist(), "h": h.data[0].tolist(), "z2": float(z2.data[0, 0]), "prob": float(prob.data[0, 0]),
            "loss": loss.item(), "dW2": W2.grad[:, 0].tolist(), "db2": float(b2.grad[0]),
            "dW1": W1.grad.tolist(), "db1": b1.grad.tolist()}})

    for x, y in ((2.0, 3.0), (-1.5, 0.5), (0.0, -2.0)):
        tx, ty = Tensor(x, requires_grad=True), Tensor(y, requires_grad=True)
        L = (tx * ty + ty) ** 2
        L.backward()
        cases["graph"].append({"x": x, "y": y, "expected": {"L": L.item(), "dx": tx.grad.item(), "dy": ty.grad.item()}})

    for method in nn.init.METHODS:
        for n_in, n_out in ((2, 32), (784, 128), (256, 256)):
            cases["init"].append({"method": method, "nIn": n_in, "nOut": n_out,
                                  "expected": float(nn.init.init_std(method, n_in, n_out))})

    xs = np.linspace(-4, 4, 161)
    xs = xs[np.abs(xs) > 1e-9]
    ops = {"relu": lambda t: t.relu(), "leaky": lambda t: t.leaky_relu(0.1), "elu": lambda t: t.elu(1.0),
           "tanh": lambda t: t.tanh(), "sigmoid": lambda t: t.sigmoid()}
    for name, op in ops.items():
        t = Tensor(xs.copy(), requires_grad=True)
        out = op(t)
        out.sum().backward()
        cases["act"].append({"name": name, "x": xs.tolist(), "f": out.data.tolist(), "d": t.grad.tolist()})

    for z in ([2.0, 1.0, 0.1], [1000.0, 999.0, -5.0], [0.0, 0.0, 0.0]):
        jac = []
        for i in range(3):
            t = Tensor(z, requires_grad=True)
            t.softmax().backward(np.eye(3)[i])
            jac.append(t.grad.tolist())
        cases["softmax"].append({"z": z, "s": Tensor(z).softmax().data.tolist(), "J": jac})

    for z, y in ((0.7, 1.0), (-3.0, 0.0), (-50.0, 1.0), (45.0, 0.0), (12.0, 1.0)):
        tz = Tensor([[z]], requires_grad=True)
        clipped = nn.binary_cross_entropy(tz.sigmoid(), [[y]])
        clipped.backward()
        grad_clipped = tz.grad.item()
        tz.grad = None
        stable = nn.binary_cross_entropy_with_logits(tz, [[y]])
        stable.backward()
        cases["bce"].append({"z": z, "y": y, "clipped": [clipped.item(), grad_clipped], "logits": [stable.item(), tz.grad.item()]})

    for _ in range(5):
        a, n = rng.standard_normal(7), rng.standard_normal(7)
        cases["reldiff"].append({"a": a.tolist(), "n": n.tolist(), "expected": float(relative_difference(a, n))})
    return cases


HARNESS = r"""
const M = require(process.argv[2]);
const C = JSON.parse(require("fs").readFileSync(0, "utf8"));
const out = {};
out.xor = C.xor.map(c => M.trainXor({ params: c.params, loss: c.loss, epochs: 100 }).losses);
out.hand = C.hand.map(c => M.handNet(c.problem));
out.graph = C.graph.map(c => M.graphExample(c.x, c.y));
out.init = C.init.map(c => M.initStd(c.method, c.nIn, c.nOut));
out.act = C.act.map(c => ({ f: c.x.map(x => M.ACT[c.name].f(x)), d: c.x.map(x => M.ACT[c.name].d(x)) }));
out.softmax = C.softmax.map(c => ({ s: M.softmax(c.z), J: M.softmaxJacobian(c.z) }));
out.bce = C.bce.map(c => { const p = M.sigmoid(c.z), [l, g] = M.bceClipped(p, c.y);
  return { clipped: [l, g * p * (1 - p)], logits: M.bceLogits(c.z, c.y) }; });
out.reldiff = C.reldiff.map(c => M.relDiff(c.a, c.n));
console.log(JSON.stringify(out));
"""


def close(a, b, rel=1e-9, abs_=1e-12):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return a.shape == b.shape and np.all(np.abs(a - b) <= abs_ + rel * np.abs(b))


def verify_math(html):
    lib = re.search(r'<script id="mathlib">(.*?)</script>', html, re.S).group(1)
    cases = python_cases()
    with tempfile.TemporaryDirectory() as tmp:
        lib_path, harness_path = Path(tmp) / "mathlib.js", Path(tmp) / "harness.js"
        lib_path.write_text(lib, encoding="utf-8")
        harness_path.write_text(HARNESS, encoding="utf-8")
        proc = subprocess.run(["node", str(harness_path), str(lib_path)], input=json.dumps(cases),
                              capture_output=True, text=True, encoding="utf-8")
    if not check(proc.returncode == 0, f"Node 실행 실패: {proc.stderr[:500]}"):
        return {}
    js = json.loads(proc.stdout)
    counts = {}
    for c, got in zip(cases["xor"], js["xor"]):
        check(close(got, c["expected"], rel=1e-9), f"XOR 학습 곡선 불일치: {c['name']}")
    counts["XOR 학습 곡선 (101점)"] = len(cases["xor"])
    for c, got in zip(cases["hand"], js["hand"]):
        for key, value in c["expected"].items():
            check(close(got[key], value), f"손계산 망 {key} 불일치: {c['problem']}")
    counts["손계산 망 (9개 값)"] = len(cases["hand"])
    for c, got in zip(cases["graph"], js["graph"]):
        check(close([got["L"], got["dx"], got["dy"]], [c["expected"][k] for k in ("L", "dx", "dy")]), f"계산 그래프 불일치: {c}")
    counts["계산 그래프"] = len(cases["graph"])
    for c, got in zip(cases["init"], js["init"]):
        check(close(got, c["expected"], rel=1e-15), f"초기화 표준편차 불일치: {c}")
    counts["초기화 표준편차"] = len(cases["init"])
    for c, got in zip(cases["act"], js["act"]):
        check(close(got["f"], c["f"], rel=1e-14), f"활성화 값 불일치: {c['name']}")
        check(close(got["d"], c["d"], rel=1e-12), f"활성화 도함수 불일치: {c['name']}")
    counts["활성화 함수 (160점 x f, f')"] = len(cases["act"])
    for c, got in zip(cases["softmax"], js["softmax"]):
        check(close(got["s"], c["s"], rel=1e-14), f"softmax 불일치: {c['z']}")
        check(close(got["J"], c["J"], rel=1e-12, abs_=1e-15), f"softmax 야코비안 불일치: {c['z']}")
    counts["Softmax·야코비안"] = len(cases["softmax"])
    for c, got in zip(cases["bce"], js["bce"]):
        check(close(got["clipped"], c["clipped"], rel=1e-12), f"분리형 BCE 불일치: {c}")
        check(close(got["logits"], c["logits"], rel=1e-12), f"안정형 BCE 불일치: {c}")
    counts["BCE 두 방식 (포화 포함)"] = len(cases["bce"])
    for c, got in zip(cases["reldiff"], js["reldiff"]):
        check(close(got, c["expected"], rel=1e-14), "relDiff 불일치")
    counts["상대 오차"] = len(cases["reldiff"])
    return counts


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    html = HTML.read_text(encoding="utf-8")
    template = build.read_text("study/a6-1.template.html")
    n_files = verify_files()
    n_excerpts = verify_excerpts(load_data(html), html)
    n_links, n_controls = verify_structure(template)
    counts = verify_math(html)
    print(f"파일 대조 {n_files}개, 코드 발췌 {n_excerpts}개, 내부 링크 {n_links}개, 입력 요소 {n_controls}개")
    for name, n in counts.items():
        print(f"계산 대조  {name}: {n}건")
    if failures:
        print(f"\n실패 {len(failures)}건:")
        for f in failures:
            print("  -", f)
        return 1
    print("\n모든 검사 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
