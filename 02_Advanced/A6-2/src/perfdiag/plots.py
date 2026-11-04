"""그림 공통 설정: 한글 글꼴, 색, 저장."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

from .common import FIGURES  # noqa: E402

# 라틴 문자·기호는 DejaVu Sans로, 한글은 설치된 한글 글꼴로 대체 출력한다.
_installed = {f.name for f in font_manager.fontManager.ttflist}
_korean = [f for f in ("Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR") if f in _installed][:1]
plt.rcParams.update({
    "font.family": ["DejaVu Sans", *_korean],
    "axes.unicode_minus": False,
    "figure.dpi": 110,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

TRAIN_COLOR = "#1f77b4"
VALIDATION_COLOR = "#d62728"
ACTUAL_COLOR = "#1f77b4"      # 미션 가이드: 실제값 파란선
PREDICTION_COLOR = "#d62728"  # 예측값 빨간선
BASELINE_COLOR = "#9aa5b1"
DEEP_COLOR = "#2b6cb0"


def save(fig, name):
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / name
    fig.savefig(path, bbox_inches="tight", dpi=110)
    plt.close(fig)
    return path
