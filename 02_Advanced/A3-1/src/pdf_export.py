"""보너스 3: 처리된 스캔 이미지를 PDF로 저장한다 (보너스 3에 한해 허용된 Pillow 사용).

페이지 크기는 이미지 픽셀 수와 해상도(dpi)로 정해진다. 기본 150dpi에서 가로 1240px이면 약 210mm(A4 폭)이다.
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def to_pil(image):
    """OpenCV 배열(BGR 또는 흑백)을 Pillow 이미지로 바꾼다. 이진 이미지는 1비트로 저장해 용량을 줄인다."""
    arr = np.asarray(image)
    if arr.ndim == 2:
        if set(np.unique(arr).tolist()) <= {0, 255}:
            return Image.fromarray(arr).convert("1")
        return Image.fromarray(arr, mode="L")
    return Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))


def save_pdf(images, path, dpi=150):
    """이미지 여러 장을 한 PDF의 여러 페이지로 저장한다."""
    pages = [to_pil(im) for im in images]
    if not pages:
        raise ValueError("PDF로 저장할 이미지가 없다")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(path, "PDF", resolution=float(dpi), save_all=True, append_images=pages[1:])
    return path
