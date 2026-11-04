"""SVD 실험용 128x128 흑백 이미지를 만든다.

원본: Matplotlib 배포본에 포함된 sample_data/grace_hopper.jpg (512x600 RGB,
Grace Hopper 제독의 미 해군 공식 초상 사진, 퍼블릭 도메인).
처리: 위쪽 512x512 정사각형 → ITU-R BT.601 휘도 → 4x4 블록 평균 → 128x128.
"""
from pathlib import Path

import numpy as np
import matplotlib.cbook as cbook
import matplotlib.image as mpimg
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "grace_hopper_128.png"


def main():
    """원본을 읽어 128x128 흑백 PNG로 저장한다."""
    with cbook.get_sample_data("grace_hopper.jpg") as fh:
        rgb = mpimg.imread(fh, format="jpg").astype(float) / 255.0
    square = rgb[:512, :512]
    gray = square @ np.array([0.299, 0.587, 0.114])
    small = gray.reshape(128, 4, 128, 4).mean(axis=(1, 3))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    plt.imsave(OUT, small, cmap="gray", vmin=0, vmax=1)
    print(f"saved {OUT} shape={small.shape}")


if __name__ == "__main__":
    main()
