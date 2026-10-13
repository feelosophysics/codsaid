"""study/a6-1.template.html에 현재 소스·결과를 넣어 study/a6-1.html을 만든다.

넣는 것: 원본 Python 발췌(줄 번호 포함), 축소한 결과 그림, gradient check 로그 발췌,
MNIST 첫 바이트와 첫 이미지. 실행 전 `python scripts/run_all.py`로 결과를 최신으로 만든다.
"""
import ast
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path

from PIL import Image  # Matplotlib의 의존성으로 함께 설치된다

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "study"
TEMPLATE = STUDY / "a6-1.template.html"
OUTPUT = STUDY / "a6-1.html"
MANIFEST = STUDY / "source-manifest.json"
MNIST_IMAGES = ROOT / "data" / "mnist" / "train-images-idx3-ubyte.gz"
MNIST_LABELS = ROOT / "data" / "mnist" / "train-labels-idx1-ubyte.gz"

# 템플릿의 data-code 값 → (파일, 정규화된 이름)
EXCERPTS = {
    "autograd.topological_order": ("src/minigrad/core/autograd.py", "topological_order"),
    "autograd.backward": ("src/minigrad/core/autograd.py", "backward"),
    "tensor.unbroadcast": ("src/minigrad/core/tensor.py", "unbroadcast"),
    "tensor._accumulate": ("src/minigrad/core/tensor.py", "Tensor._accumulate"),
    "tensor.__add__": ("src/minigrad/core/tensor.py", "Tensor.__add__"),
    "tensor.__mul__": ("src/minigrad/core/tensor.py", "Tensor.__mul__"),
    "tensor.__matmul__": ("src/minigrad/core/tensor.py", "Tensor.__matmul__"),
    "tensor.softmax": ("src/minigrad/core/tensor.py", "Tensor.softmax"),
    "tensor.elu": ("src/minigrad/core/tensor.py", "Tensor.elu"),
    "gradcheck.numerical_gradient": ("src/minigrad/gradcheck.py", "numerical_gradient"),
    "gradcheck.check_gradients": ("src/minigrad/gradcheck.py", "check_gradients"),
    "layers.Linear": ("src/minigrad/nn/layers.py", "Linear"),
    "layers.Module.parameters": ("src/minigrad/nn/layers.py", "Module.parameters"),
    "layers.Dropout": ("src/minigrad/nn/layers.py", "Dropout"),
    "losses.binary_cross_entropy_with_logits": ("src/minigrad/nn/losses.py", "binary_cross_entropy_with_logits"),
    "optimizer.Optimizer.step": ("src/minigrad/optim/optimizer.py", "Optimizer.step"),
    "adam.Adam._update": ("src/minigrad/optim/adam.py", "Adam._update"),
    "mnist.parse_idx": ("src/minigrad/data/mnist.py", "parse_idx"),
    "loader.DataLoader": ("src/minigrad/data/loader.py", "DataLoader"),
}

FIGURES = {
    "init_comparison": ("figures/init_comparison.png", "XOR seed 20개의 loss 중앙값·사분위 범위(왼쪽)와 seed별 곡선(오른쪽)"),
    "init_deep_stats": ("figures/init_deep_stats.png", "10층 x 256 망의 층별 활성값 표준편차와 가중치 기울기 노름"),
    "init_mnist": ("figures/init_mnist.png", "MNIST 1 epoch 동안의 손실: 초기화별 시작점과 테스트 정확도"),
    "mnist_training": ("figures/mnist_training.png", "MNIST 학습 손실, 혼동 행렬, 틀린 예시"),
    "bonus_regularization": ("figures/bonus_regularization.png", "Dropout·L2: 정확도, 테스트 손실, 가중치 분포"),
    "bonus_activations": ("figures/bonus_activations.png", "활성화 함수와 도함수, 8층 망 기울기, Two Moons 결과"),
}

# 로그에서 이 문자열을 포함한 줄만 발췌한다
LOGS = {"gradcheck": ("reports/gradient_check.log", ("Gradient Check  ε", "Linear.input", "Linear.W", "Linear.b",
                                                     "Softmax.input", "Linear_1.", "Linear_2.", "All ", "FAILED"))}

TEXT_SOURCES = sorted({path for path, _ in EXCERPTS.values()} | {"study/a6-1.template.html"}
                      | {path for path, _ in LOGS.values()})


def read_text(path):
    return (ROOT / path).read_text(encoding="utf-8").replace("\r\n", "\n")


def text_hash(path):
    return hashlib.sha256(read_text(path).encode("utf-8")).hexdigest()


def binary_hash(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def find_node(tree, qualname):
    nodes = tree.body
    node = None
    for part in qualname.split("."):
        node = next(n for n in nodes if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == part)
        nodes = node.body
    return node


def excerpt(path, qualname):
    source = read_text(path)
    node = find_node(ast.parse(source), qualname)
    start = min([node.lineno] + [d.lineno for d in node.decorator_list])
    lines = source.split("\n")[start - 1:node.end_lineno]
    return {"file": path, "name": qualname, "start": start, "end": node.end_lineno, "text": "\n".join(lines)}


def shrink(path, width=1100):
    """그림을 폭 1100px 이하로 줄여 data URI로 만든다."""
    image = Image.open(ROOT / path).convert("RGB")
    if image.width > width:
        image = image.resize((width, round(image.height * width / image.width)), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def log_excerpt(path, patterns):
    return "\n".join(line for line in read_text(path).split("\n") if any(p in line for p in patterns))


def mnist_bytes():
    with gzip.open(MNIST_IMAGES, "rb") as f:
        head = f.read(16 + 784)
    with gzip.open(MNIST_LABELS, "rb") as f:
        labels = f.read(9)
    return {"header": list(head[:24]), "labelHeader": list(labels[:8]), "image": list(head[16:16 + 784]),
            "label": labels[8]}


def build():
    data = {
        "code": {key: excerpt(path, name) for key, (path, name) in EXCERPTS.items()},
        "fig": {key: {"src": shrink(path), "caption": caption, "file": path} for key, (path, caption) in FIGURES.items()},
        "log": {key: log_excerpt(path, prefixes) for key, (path, prefixes) in LOGS.items()},
        "idx": mnist_bytes(),
    }
    template = read_text("study/a6-1.template.html")
    marker = "/*__DATA__*/null"
    if template.count(marker) != 1:
        raise SystemExit("템플릿에 DATA 자리표시자가 정확히 하나 있어야 한다")
    html = template.replace(marker, json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
    OUTPUT.write_text(html, encoding="utf-8", newline="\n")
    manifest = {
        "hash_mode": "UTF-8 텍스트는 CRLF를 LF로 바꾼 뒤 SHA-256, 이미지와 MNIST 원본은 원래 바이트의 SHA-256",
        "text": {path: text_hash(path) for path in TEXT_SOURCES},
        "binary": {path: binary_hash(path) for path, _ in FIGURES.values()},
        "mnist": {p.relative_to(ROOT).as_posix(): binary_hash(p.relative_to(ROOT)) for p in (MNIST_IMAGES, MNIST_LABELS)},
        "excerpts": {key: {k: v for k, v in e.items() if k != "text"} for key, e in data["code"].items()},
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"생성: {OUTPUT.relative_to(ROOT).as_posix()} ({OUTPUT.stat().st_size / 1024:.0f} KB), "
          f"발췌 {len(data['code'])}개, 그림 {len(data['fig'])}개")


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    build()
