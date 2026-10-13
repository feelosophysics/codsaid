"""MNIST 원본 4개 파일(약 11MB)을 data/mnist/에 내려받고 SHA-256을 검증한다.

다른 스크립트도 파일이 없으면 자동으로 내려받으므로, 미리 받아 두고 싶을 때만 실행한다.
실행: uv run python scripts/download_mnist.py
"""
from _common import MNIST_DIR, ROOT
from minigrad.data import download, parse_idx

if __name__ == "__main__":
    for key, path in download(MNIST_DIR).items():
        array = parse_idx(path)
        print(f"{key:<13} {path.relative_to(ROOT).as_posix():<45} shape={array.shape} dtype={array.dtype}")
