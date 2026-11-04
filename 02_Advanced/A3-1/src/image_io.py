"""한글 경로에서도 동작하는 이미지 읽기·쓰기.

Windows의 cv2.imread/imwrite는 경로에 한글이 있으면 실패하고 None을 돌려준다.
파일은 NumPy로 바이트를 읽고 OpenCV로 디코딩한다.

읽기: 파일 → 바이트 1차원 배열 (n,) uint8 → imdecode → BGR 이미지 (H, W, 3) uint8
쓰기: 이미지 → imencode → 바이트 배열 → tofile
"""
# pathlib.Path는 경로를 문자열 대신 객체로 다룬다. path.suffix(확장자), path.parent(상위 폴더)처럼 쓴다.
from pathlib import Path

import cv2
import numpy as np

# {값, ...}는 집합(set). "in"으로 포함 여부를 빠르게 확인한다. 중복이 없고 순서도 없다.
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def imread(path, flags=cv2.IMREAD_COLOR):
    """이미지를 BGR uint8 배열로 읽는다. 읽을 수 없으면 FileNotFoundError.

    OpenCV는 색을 RGB가 아니라 B, G, R 순서로 저장한다. matplotlib으로 보여 줄 때는 RGB로 바꿔야 한다
    (figures.rgb).

    Args:
        path: 이미지 파일 경로. 문자열이나 Path.
        flags: 읽기 방식. 기본 IMREAD_COLOR는 항상 3채널 BGR로 읽는다.

    Returns:
        numpy.ndarray: (H, W, 3) uint8 이미지. 합성 데이터는 (1280, 960, 3)이다.

    Raises:
        FileNotFoundError: 파일이 없거나 이미지로 해석할 수 없는 경우.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"이미지 파일이 없다: {path}")
    # fromfile은 파일의 모든 바이트를 (n,) uint8 배열로 읽는다. 경로를 Python이 열기 때문에 한글 경로도 된다.
    # imdecode는 그 바이트가 JPEG·PNG인지 보고 압축을 풀어 (H, W, 3) 배열을 만든다.
    image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), flags)
    if image is None:  # OpenCV는 실패해도 예외 대신 None을 돌려주므로 직접 확인한다
        raise FileNotFoundError(f"이미지로 읽을 수 없다: {path}")
    return image


def imwrite(path, image, jpeg_quality=92):
    """확장자에 맞춰 인코딩해 저장한다. 상위 폴더가 없으면 만든다.

    Args:
        path: 저장할 경로. 확장자(.jpg, .png 등)로 형식을 정한다.
        image: (H, W, 3) BGR 또는 (H, W) 회색 uint8 이미지.
        jpeg_quality: JPEG 품질 0~100. 클수록 화질이 좋고 파일이 크다. PNG에는 쓰지 않는다.

    Returns:
        pathlib.Path: 저장한 경로.

    Raises:
        ValueError: 지원하지 않는 확장자 등으로 인코딩에 실패한 경우.
    """
    path = Path(path)
    # parents=True는 중간 폴더까지 만들고, exist_ok=True는 이미 있어도 오류를 내지 않는다.
    path.parent.mkdir(parents=True, exist_ok=True)
    # lower()로 ".JPG"도 ".jpg"로 비교한다. JPEG일 때만 품질 옵션 [이름, 값]을 넘기고 나머지는 빈 리스트.
    params = [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality] if path.suffix.lower() in (".jpg", ".jpeg") else []
    ok, buf = cv2.imencode(path.suffix, image, params)  # (성공 여부, 바이트 배열) 두 값을 돌려준다
    if not ok:
        raise ValueError(f"인코딩 실패: {path}")
    buf.tofile(str(path))
    return path


def list_images(folder):
    """폴더 안의 이미지 파일을 이름순으로 돌려준다.

    Args:
        folder: 찾을 폴더 경로.

    Returns:
        list: 이미지 확장자를 가진 Path 목록. 하위 폴더는 보지 않는다.
    """
    # iterdir는 폴더 안의 항목을 하나씩 준다. (식 for p in ... if 조건)으로 이미지만 골라 sorted로 정렬한다.
    return sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
