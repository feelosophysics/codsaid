"""한글 경로에서도 동작하는 이미지 읽기·쓰기.

Windows의 cv2.imread/imwrite는 경로에 한글이 있으면 실패하고 None을 돌려준다.
파일은 NumPy로 바이트를 읽고 OpenCV로 디코딩한다.
"""
from pathlib import Path

import cv2
import numpy as np

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def imread(path, flags=cv2.IMREAD_COLOR):
    """이미지를 BGR uint8 배열로 읽는다. 읽을 수 없으면 FileNotFoundError."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"이미지 파일이 없다: {path}")
    image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), flags)
    if image is None:
        raise FileNotFoundError(f"이미지로 읽을 수 없다: {path}")
    return image


def imwrite(path, image, jpeg_quality=92):
    """확장자에 맞춰 인코딩해 저장한다. 상위 폴더가 없으면 만든다."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    params = [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality] if path.suffix.lower() in (".jpg", ".jpeg") else []
    ok, buf = cv2.imencode(path.suffix, image, params)
    if not ok:
        raise ValueError(f"인코딩 실패: {path}")
    buf.tofile(str(path))
    return path


def list_images(folder):
    """폴더 안의 이미지 파일을 이름순으로 돌려준다."""
    return sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
