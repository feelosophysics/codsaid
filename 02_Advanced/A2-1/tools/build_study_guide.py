"""study/a2-1.template.html에 현재 소스·결과를 넣어 study/a2-1.html을 만든다.

넣는 것: 원본 Python 함수 발췌(줄 번호 포함), 축소한 결과 그림, SVD 위젯용 U·Σ·Vᵀ와 원본 이미지.
실행 전 `python -m src.run_all`로 outputs/를 최신으로 만든다.
"""
import ast
import base64
import hashlib
import io
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "study"
TEMPLATE = STUDY / "a2-1.template.html"
OUTPUT = STUDY / "a2-1.html"
MANIFEST = STUDY / "source-manifest.json"
IMAGE = ROOT / "data" / "grace_hopper_128.png"

EXCERPTS = [
    ("src/linear_algebra.py", ["rotation_matrix", "scaling_matrix", "shear_matrix", "determinant_2x2",
                               "polygon_area", "area_ratio_check", "power_iteration", "svd_compress"]),
    ("src/calculus.py", ["numerical_derivative", "numerical_gradient", "gradient_contour_orthogonality"]),
    ("src/neural_net.py", ["TwoLayerNet.forward", "TwoLayerNet.backward"]),
    ("src/optimizer.py", ["VanillaGD", "Momentum", "Adam", "NewtonMethod", "optimize"]),
    ("src/probability.py", ["softmax", "gaussian_nll", "bernoulli_nll"]),
    ("src/information.py", ["entropy", "cross_entropy", "kl_divergence"]),
]

FIGURES = [
    ("04_transforms_overview.png", "회전·스케일링·전단: 변환 전(파랑)과 후(빨강), det와 면적비"),
    ("05_power_iteration.png", "Power Iteration 오차가 (λ₂/λ₁)^(2t)로 감소, 찾은 고유벡터가 타원의 긴 축"),
    ("06_svd_compression.png", "SVD k=10, 50, 100 복원과 저장 비율·에너지·PSNR"),
    ("07_singular_values.png", "특이값 크기(로그)와 누적 에너지"),
    ("08_gradient_field.png", "등고선 위 Gradient 화살표와 접선, 최대 |cos| 9.6e-12"),
    ("09_derivative_error.png", "x=3 접선 기울기, h에 따른 전진·중심차분 오차"),
    ("11_lr_divergence.png", "학습률별 수렴·진동·발산과 타원의 lr=0.5 발산"),
    ("12_gd_vs_momentum_quadratic.png", "x²+y², lr=0.1: GD와 Momentum 경로와 거리"),
    ("13_gd_vs_momentum_elliptic.png", "x²+10y²: lr=0.01·0.09 경로와 학습률별 1e-3 도달 반복 수"),
    ("14_adam_comparison.png", "보너스 Adam: 같은 lr=0.1에서 세 옵티마이저 비교"),
    ("15_newton_method.png", "보너스 Newton: 이차 함수 1회, Rosenbrock, 안장점"),
    ("16_normal_pdf.png", "N(0,1)과 N(2,0.5) PDF"),
    ("17_bernoulli_pmf.png", "B(0.3)과 B(0.7) PMF"),
    ("18_loss_mle.png", "MSE↔가우시안 NLL, BCE↔베르누이 우도의 같은 최적점"),
    ("19_information_theory.png", "보너스 정보 이론: 이진 엔트로피, H(p,q)=H(p)+KL"),
]


def text_hash(path):
    """줄바꿈을 LF로 통일한 UTF-8 텍스트의 SHA-256 (Git 체크아웃 차이에 무관)."""
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def byte_hash(path):
    """바이너리 파일의 SHA-256."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find_node(tree, qualname):
    """'Class.method' 또는 'function' 이름의 AST 노드를 찾는다."""
    parts = qualname.split(".")
    body = tree.body
    node = None
    for part in parts:
        node = next(n for n in body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == part)
        body = node.body
    return node


def code_excerpts():
    """지정한 함수·클래스의 원본 텍스트와 줄 번호를 모은다."""
    items = []
    for rel, names in EXCERPTS:
        source = (ROOT / rel).read_text(encoding="utf-8")
        lines = source.splitlines()
        tree = ast.parse(source)
        for name in names:
            node = find_node(tree, name)
            start, end = node.lineno, node.end_lineno
            items.append({"file": rel, "name": name, "start": start, "end": end,
                          "text": "\n".join(lines[start - 1:end])})
    return items


def figure_data_uri(path, max_width=1000):
    """그림을 블록 평균으로 축소해 JPEG data URI로 만든다."""
    img = plt.imread(path)[..., :3]
    h, w = img.shape[:2]
    factor = max(1, math.ceil(w / max_width))
    if factor > 1:
        h2, w2 = h // factor * factor, w // factor * factor
        img = img[:h2, :w2].reshape(h2 // factor, factor, w2 // factor, factor, 3).mean(axis=(1, 3))
    buf = io.BytesIO()
    plt.imsave(buf, np.clip(img, 0, 1), format="jpg", pil_kwargs={"quality": 82})
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def svd_payload():
    """SVD 위젯용 데이터. 원본은 8비트 그대로, 분해 결과는 float32로 넣는다."""
    img = plt.imread(IMAGE)
    gray = img[..., 0] if img.ndim == 3 else img
    pixels = np.rint(gray * 255).astype(np.uint8)
    A = pixels.astype(float) / 255
    U, S, Vt = np.linalg.svd(A, full_matrices=False)
    enc = lambda arr: base64.b64encode(np.ascontiguousarray(arr).tobytes()).decode("ascii")  # noqa: E731
    return {"m": int(A.shape[0]), "n": int(A.shape[1]), "image": enc(pixels),
            "U": enc(U.astype("<f4")), "S": enc(S.astype("<f4")), "Vt": enc(Vt.astype("<f4"))}


def main():
    """HTML과 source-manifest.json을 생성한다."""
    template = TEMPLATE.read_text(encoding="utf-8")
    marker = "/*__DATA__*/null"
    if template.count(marker) != 1:
        raise SystemExit("템플릿에 데이터 자리표시자가 정확히 하나 있어야 한다")
    data = {
        "code": code_excerpts(),
        "images": [{"file": f, "caption": c, "src": figure_data_uri(ROOT / "outputs" / f)} for f, c in FIGURES],
        "svd": svd_payload(),
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    OUTPUT.write_text(template.replace(marker, payload), encoding="utf-8", newline="\n")

    sources = sorted({rel for rel, _ in EXCERPTS}) + ["src/run_all.py", "study/a2-1.template.html"]
    manifest = {
        "hash_mode": "UTF-8 텍스트는 CRLF를 LF로 바꾼 뒤 SHA-256, 이미지·JSON 결과는 원래 바이트의 SHA-256",
        "text": {rel: text_hash(ROOT / rel) for rel in sources},
        "binary": {**{f"outputs/{f}": byte_hash(ROOT / "outputs" / f) for f, _ in FIGURES},
                   "data/grace_hopper_128.png": byte_hash(IMAGE)},
        "excerpts": [{k: v for k, v in item.items() if k != "text"} for item in data["code"]],
        "html_bytes": OUTPUT.stat().st_size,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size / 1024:.0f} KB), "
          f"{len(data['code'])} excerpts, {len(data['images'])} figures")


if __name__ == "__main__":
    main()
