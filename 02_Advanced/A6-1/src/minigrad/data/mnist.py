"""MNIST 내려받기와 IDX(UBYTE) 바이너리 직접 파싱.

IDX 형식: [0x00, 0x00, 자료형 코드, 차원 수] 4바이트 매직 넘버, 차원별 크기(빅엔디안 uint32),
그 뒤에 값이 행 우선 순서로 이어진다. MNIST는 자료형 코드 0x08(unsigned byte)이다.
"""
import gzip
import hashlib
import os
import struct
import urllib.request
from pathlib import Path

import numpy as np

MIRRORS = (
    "https://storage.googleapis.com/cvdf-datasets/mnist/",
    "https://ossci-datasets.s3.amazonaws.com/mnist/",
)

# 파일명과 SHA-256. 원 배포처(yann.lecun.com)가 공개한 MD5와 일치하는 파일에서 계산했다.
FILES = {
    "train_images": ("train-images-idx3-ubyte.gz", "440fcabf73cc546fa21475e81ea370265605f56be210a4024d2ca8f203523609"),
    "train_labels": ("train-labels-idx1-ubyte.gz", "3552534a0a558bbed6aed32b30c495cca23d567ec52cac8be1a0730e8010255c"),
    "test_images": ("t10k-images-idx3-ubyte.gz", "8d422c7b0a1c1c79245a5bcf07fe86e33eeafee792b84584aec276f5a2dbc4e6"),
    "test_labels": ("t10k-labels-idx1-ubyte.gz", "f7ae60f92e00ec6debd23a6088c31dbd2371eca3ffa0defaefb259924204aec6"),
}

_DTYPES = {0x08: np.uint8, 0x09: np.int8, 0x0B: ">i2", 0x0C: ">i4", 0x0D: ">f4", 0x0E: ">f8"}


def default_root():
    """MINIGRAD_DATA 환경 변수가 있으면 그 아래, 없으면 현재 폴더의 data/mnist."""
    return Path(os.environ.get("MINIGRAD_DATA", "data")) / "mnist"


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(root=None, quiet=False):
    """네 파일을 내려받아 검증한다. 이미 있고 해시가 맞으면 건너뛴다."""
    root = Path(root) if root else default_root()
    root.mkdir(parents=True, exist_ok=True)
    paths = {}
    for key, (filename, expected) in FILES.items():
        path = root / filename
        if path.exists() and sha256(path) == expected:
            paths[key] = path
            continue
        errors = []
        for mirror in MIRRORS:
            try:
                if not quiet:
                    print(f"내려받는 중: {mirror}{filename}")
                tmp = path.with_suffix(".part")
                urllib.request.urlretrieve(mirror + filename, tmp)
                if sha256(tmp) != expected:
                    tmp.unlink()
                    raise ValueError("SHA-256 불일치")
                tmp.replace(path)
                break
            except Exception as error:  # 다음 미러로 넘어간다
                errors.append(f"{mirror}: {error}")
        else:
            raise RuntimeError(f"{filename}을 내려받지 못했다:\n" + "\n".join(errors))
        paths[key] = path
    return paths


def parse_idx(path):
    """IDX 파일(.gz 또는 원본)을 읽어 NumPy 배열로 만든다."""
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rb") as f:
        raw = f.read()
    zero, dtype_code, ndim = struct.unpack(">HBB", raw[:4])
    if zero != 0 or dtype_code not in _DTYPES:
        raise ValueError(f"IDX 형식이 아니다: {path}")
    shape = struct.unpack(f">{ndim}I", raw[4:4 + 4 * ndim])
    data = np.frombuffer(raw, dtype=_DTYPES[dtype_code], offset=4 + 4 * ndim)
    if data.size != int(np.prod(shape)):
        raise ValueError(f"값 개수 {data.size}가 shape {shape}와 맞지 않는다")
    return data.reshape(shape)


def load_mnist(root=None, download_if_missing=True, normalize=True, flatten=True):
    """(X_train, y_train, X_test, y_test)를 반환한다.

    normalize=True이면 픽셀을 [0, 1] float64로, flatten=True이면 이미지를 784차원 벡터로 바꾼다.
    """
    root = Path(root) if root else default_root()
    if download_if_missing:
        paths = download(root)
    else:
        paths = {key: root / filename for key, (filename, _) in FILES.items()}
    X_train, y_train = parse_idx(paths["train_images"]), parse_idx(paths["train_labels"])
    X_test, y_test = parse_idx(paths["test_images"]), parse_idx(paths["test_labels"])
    if flatten:
        X_train, X_test = X_train.reshape(len(X_train), -1), X_test.reshape(len(X_test), -1)
    if normalize:
        X_train, X_test = X_train / 255.0, X_test / 255.0
    return X_train, y_train.astype(np.int64), X_test, y_test.astype(np.int64)
