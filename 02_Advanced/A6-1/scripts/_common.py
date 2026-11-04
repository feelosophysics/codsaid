"""스크립트 공통: 경로, 로그 저장, 그림 저장."""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
REPORTS = ROOT / "reports"
MNIST_DIR = ROOT / "data" / "mnist"

# Windows 콘솔(cp949)에서도 ✓·ε 같은 문자를 출력할 수 있게 한다.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

from matplotlib import font_manager  # noqa: E402

# 라틴 문자·수식 기호(−, ε)는 DejaVu Sans로, 한글은 설치된 한글 글꼴로 대체 출력한다.
# 없는 글꼴을 나열하면 findfont 경고가 쏟아지므로 설치된 것 하나만 고른다.
_installed = {f.name for f in font_manager.fontManager.ttflist}
_korean = [f for f in ("Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR") if f in _installed][:1]

plt.rcParams.update({
    "font.family": ["DejaVu Sans", *_korean],
    "figure.dpi": 110,
    "axes.grid": True,
    "grid.alpha": 0.3,
})

INIT_COLORS = {"zero": "#7f7f7f", "random": "#d62728", "he": "#1f77b4", "xavier": "#2ca02c"}
INIT_LABELS = {"zero": "Zero", "random": "Random N(0,1)", "he": "He", "xavier": "Xavier"}


class Tee:
    """print 출력을 화면과 로그 파일에 함께 쓴다."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = open(self.path, "w", encoding="utf-8", newline="\n")
        self.stdout = sys.stdout

    def __enter__(self):
        sys.stdout = self
        return self

    def __exit__(self, *exc):
        sys.stdout = self.stdout
        self.file.close()

    def write(self, text):
        self.stdout.write(text)
        self.file.write(text)

    def flush(self):
        self.stdout.flush()
        self.file.flush()


def save_figure(fig, name):
    FIGURES.mkdir(exist_ok=True)
    path = FIGURES / name
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"그림 저장: {path.relative_to(ROOT).as_posix()}")
    return path


def _to_builtin(value):
    """NumPy 스칼라·배열을 JSON에 쓸 수 있는 파이썬 값으로 바꾼다."""
    if hasattr(value, "tolist"):
        return value.tolist()
    raise TypeError(f"JSON으로 저장할 수 없는 값: {type(value).__name__}")


def save_json(data, name):
    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / name
    text = json.dumps(data, ensure_ascii=False, indent=2, default=_to_builtin)
    path.write_text(text + "\n", encoding="utf-8")
    print(f"결과 저장: {path.relative_to(ROOT).as_posix()}")
    return path
