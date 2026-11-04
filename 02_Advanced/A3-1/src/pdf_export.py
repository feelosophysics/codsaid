"""보너스 3: 처리된 스캔 이미지를 PDF로 저장한다 (보너스 3에 한해 허용된 Pillow 사용).

페이지 크기는 이미지 픽셀 수와 해상도(dpi)로 정해진다. 기본 150dpi에서 가로 1240px이면 약 210mm(A4 폭)이다.
계산: 1240px ÷ 150 dpi = 8.27인치 × 25.4mm = 210mm.
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image  # Pillow 라이브러리. 패키지 이름은 PIL이다.


def to_pil(image):
    """OpenCV 배열(BGR 또는 흑백)을 Pillow 이미지로 바꾼다. 이진 이미지는 1비트로 저장해 용량을 줄인다.

    Args:
        image: (H, W) 회색·이진 또는 (H, W, 3) BGR uint8 배열.

    Returns:
        PIL.Image.Image: 0/255만 있으면 1비트("1"), 그 밖의 회색은 8비트("L"), 컬러는 RGB 이미지.
    """
    arr = np.asarray(image)
    if arr.ndim == 2:
        # np.unique는 서로 다른 값만 정렬해 준다. tolist()로 파이썬 리스트, set()으로 집합을 만든다.
        # 집합의 <=는 "부분집합인가". {0, 255} 또는 {255}처럼 0과 255만 있으면 픽셀당 1비트로 충분하다.
        if set(np.unique(arr).tolist()) <= {0, 255}:
            return Image.fromarray(arr).convert("1")
        return Image.fromarray(arr, mode="L")
    # Pillow는 RGB 순서를 기대한다. BGR 그대로 넘기면 파란색과 빨간색이 바뀐다.
    return Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))


def save_pdf(images, path, dpi=150):
    """이미지 여러 장을 한 PDF의 여러 페이지로 저장한다.

    Args:
        images: 페이지로 넣을 이미지 목록. 순서대로 1쪽, 2쪽, …이 된다.
        path: 저장할 .pdf 경로.
        dpi: 인치당 픽셀 수. 클수록 같은 이미지가 작은 종이로 인쇄된다.

    Returns:
        pathlib.Path: 저장한 경로.

    Raises:
        ValueError: 이미지가 하나도 없는 경우.
    """
    pages = [to_pil(im) for im in images]  # 리스트 컴프리헨션: 각 이미지에 to_pil을 적용한 새 리스트
    if not pages:
        raise ValueError("PDF로 저장할 이미지가 없다")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # 첫 페이지 객체의 save에 나머지 페이지(pages[1:], 두 번째부터 끝까지)를 붙여 한 파일로 저장한다.
    pages[0].save(path, "PDF", resolution=float(dpi), save_all=True, append_images=pages[1:])
    return path
