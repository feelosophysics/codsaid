"""노트북 화면 표시용 도우미. 사진 처리 계산은 없고, 결과를 표와 그림으로 띄우는 일만 한다.

노트북에서 `from src.nbview import table, show_images, show_grid`로 가져와 쓴다.
그림 제목은 matplotlib 기본 글꼴이 한글을 그리지 못하므로 영어로 쓴다.
"""

import cv2
import matplotlib.pyplot as plt
import numpy as np
from IPython.display import Markdown, display


def table(headers, rows):
    """마크다운 표를 띄운다.

    Args:
        headers: 열 이름 목록. 예: ['이름', '값'].
        rows: 줄 목록. 줄 하나는 값 목록이다. 예: [['가로', 960], ['세로', 1280]].
    """
    lines = [" | ".join(headers), " | ".join(["---"] * len(headers))]
    for row in rows:
        lines.append(" | ".join(str(value) for value in row))
    display(Markdown("\n".join(lines)))


def show_images(items, columns=3, height=3.8):
    """사진 여러 장을 나란히 띄운다.

    Args:
        items: (제목, 사진) 쌍의 목록. 컬러 사진은 OpenCV의 BGR 순서, 흑백 사진은 0–255 값이다.
        columns: 한 줄에 놓을 사진 수.
        height: 사진 한 줄의 높이(인치).
    """
    rows = (len(items) + columns - 1) // columns
    fig, axes = plt.subplots(rows, columns, figsize=(4 * columns, height * rows), squeeze=False)
    for axis in axes.flat:
        axis.axis("off")
    for axis, (name, picture) in zip(axes.flat, items):
        if picture.ndim == 3:
            # OpenCV는 파랑·초록·빨강(BGR) 순서로, matplotlib은 빨강·초록·파랑(RGB) 순서로 색을 읽는다.
            picture = cv2.cvtColor(picture, cv2.COLOR_BGR2RGB)
        axis.imshow(picture, cmap="gray", vmin=0, vmax=255)
        axis.set_title(name)
    fig.tight_layout()
    display(fig)
    plt.close(fig)


def show_grid(title, grid, low=0, high=255, cell=0.55):
    """작은 숫자 표를 "칸마다 숫자가 적힌 그림"으로 띄운다.

    Args:
        title: 그림 제목.
        grid: 2차원 배열. 값이 클수록 밝게 칠한다.
        low: 검정으로 칠할 값.
        high: 흰색으로 칠할 값.
        cell: 한 칸의 크기(인치).
    """
    grid = np.atleast_2d(grid).astype(float)
    fig, axis = plt.subplots(figsize=(grid.shape[1] * cell + 1.2, grid.shape[0] * cell + 1.0))
    axis.imshow(grid, cmap="gray", vmin=low, vmax=high)
    for r in range(grid.shape[0]):
        for c in range(grid.shape[1]):
            color = "black" if grid[r, c] > (low + high) / 2 else "white"
            axis.text(c, r, f"{grid[r, c]:.0f}", ha="center", va="center", color=color, fontsize=9)
    axis.set_xticks([])
    axis.set_yticks([])
    axis.set_title(title, fontsize=10)
    fig.tight_layout()
    display(fig)
    plt.close(fig)
