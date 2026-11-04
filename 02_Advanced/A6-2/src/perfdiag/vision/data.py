"""Oxford Flowers 102에서 비슷한 꽃 몇 종만 골라 Few-shot 데이터셋을 만든다.

내려받기: 공식 서버(robots.ox.ac.uk)는 이 환경에서 초당 약 20KB여서 345MB를 받는 데 몇 시간이 걸렸다.
그래서 같은 이미지·라벨을 Parquet으로 옮긴 Hugging Face 미러를 커밋 해시로 고정해 받고, SHA-256으로 검증한다.
라벨 번호는 torchvision Flowers102와 같은 0~101이다.

선별: 미션의 '필요한 클래스 폴더만 복사하고 나머지는 삭제' 전략을 따른다. 고른 클래스의 이미지만
data/flowers_subset/<클래스>/에 JPEG로 풀고, 원본 Parquet은 지운다(--keep-raw로 남길 수 있다).
"""
import hashlib
import io
import shutil
from dataclasses import dataclass

import numpy as np
import pandas as pd
from PIL import Image

from ..common import FLOWERS, RAW

MIRROR = "https://huggingface.co/datasets/Donghyun99/Oxford-Flower-102/resolve/7e43fe37eeb9278138ab0bd2d0abb10d0f703d09/data/"
PARQUET_DIR = RAW / "flowers102_parquet"
PARQUET = {
    "train": ("train-00000-of-00001-95813d8dab877ff5.parquet",
              "37612eb6ade6dcbdeafde4d204a92949cbc5216fa2f84975b5fb481471f8d448"),
    "validation": ("validation-00000-of-00001-a2ccf8138610462c.parquet",
                   "f06a149f7f6ba2c72b09283953bdb60590b8f74f3baba9794b7a4b494689da1c"),
    "test": ("test-00000-of-00001-1cc6f065cd5391ec.parquet",
             "1cf2e854c1d870bffcca9326b82dc2dca23ce2aca73d6ad943f43af9a3954035"),
}


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_parquet():
    import requests

    PARQUET_DIR.mkdir(parents=True, exist_ok=True)
    for split, (name, expected) in PARQUET.items():
        path = PARQUET_DIR / name
        if path.exists() and sha256(path) == expected:
            continue
        part = path.with_suffix(".part")
        with requests.get(MIRROR + name, stream=True, timeout=60) as response:
            response.raise_for_status()
            with open(part, "wb") as f:
                for chunk in response.iter_content(1 << 20):
                    f.write(chunk)
        if sha256(part) != expected:
            part.unlink()
            raise ValueError(f"SHA-256 불일치: {name}")
        part.replace(path)
        print(f"받음: {name} ({path.stat().st_size / 1e6:.0f}MB)")


def read_labels():
    """(공식 split, 행 번호, 라벨) 표. 이미지는 읽지 않아 빠르다."""
    frames = []
    for split, (name, _) in PARQUET.items():
        labels = pd.read_parquet(PARQUET_DIR / name, columns=["label"])["label"].to_numpy()
        frames.append(pd.DataFrame({"source_split": split, "row": np.arange(len(labels)), "label": labels}))
    return pd.concat(frames, ignore_index=True)


# ----------------------------------------------------------------------------- 선별
# 노랑·주황 계열의 '데이지형(국화과)' 꽃만 고른다. 꽃잎이 방사형으로 퍼지고 가운데 꽃판이 있어
# 서로 헷갈리기 쉽다 → 클래스 유사성 오류를 관찰하기 좋다. (라벨 번호: 이름, 전체 장수)
CLASSES = {
    4: "english marigold",     # 65
    11: "colt's foot",         # 87
    46: "marigold",            # 67
    49: "common dandelion",    # 92
    53: "sunflower",           # 61
    62: "black-eyed susan",    # 54
    65: "osteospermum",        # 61
    70: "gazania",             # 78
}
CLASS_KO = {
    "english marigold": "금잔화", "colt's foot": "머위(관동)", "marigold": "메리골드",
    "common dandelion": "서양민들레", "sunflower": "해바라기", "black-eyed susan": "루드베키아",
    "osteospermum": "오스테오스페르뭄", "gazania": "가자니아",
}
TRAIN_PER_CLASS = 20        # 미션 조건: 클래스당 50장 미만. Shots 실험은 이 20장의 앞부분을 쓴다.
VALIDATION_PER_CLASS = 10
SPLIT_SEED = 42
MANIFEST = FLOWERS / "manifest.csv"


def slug(name):
    return name.replace("'", "").replace(" ", "_")


def build_subset(keep_raw=False):
    """고른 클래스 이미지만 JPEG로 풀고, 클래스마다 무작위로 Train 20 / Validation 10 / Test 나머지로 나눈다.

    공식 split(train 10·validation 10·test 나머지)은 무시하고 다시 나눈다. 공식 train은 클래스당 10장뿐이라
    Shots 실험(5·10·20장)을 하려면 더 필요하고, Test도 클래스마다 크기가 달라 그대로 쓰면 편하지 않다.
    """
    rng = np.random.default_rng(SPLIT_SEED)
    if FLOWERS.exists():
        shutil.rmtree(FLOWERS)
    rows = []
    for source_split, (name, _) in PARQUET.items():
        table = pd.read_parquet(PARQUET_DIR / name)
        for row, (image, label) in enumerate(zip(table["image"], table["label"])):
            if label not in CLASSES:
                continue
            folder = FLOWERS / slug(CLASSES[label])
            folder.mkdir(parents=True, exist_ok=True)
            file = folder / f"{source_split}_{row:04d}.jpg"
            data = image["bytes"]
            Image.open(io.BytesIO(data)).verify()  # 깨진 파일이면 여기서 멈춘다
            file.write_bytes(data)
            rows.append({"file": file.relative_to(FLOWERS).as_posix(), "label": int(label),
                         "class": CLASSES[label], "source_split": source_split, "source_row": row})
    df = pd.DataFrame(rows).sort_values("file").reset_index(drop=True)
    df["split"], df["order"] = "", 0
    for label in sorted(CLASSES):
        idx = df.index[df["label"] == label].to_numpy()
        idx = idx[rng.permutation(len(idx))]
        n_train, n_validation = TRAIN_PER_CLASS, VALIDATION_PER_CLASS
        df.loc[idx[:n_train], "split"] = "train"
        df.loc[idx[n_train:n_train + n_validation], "split"] = "validation"
        df.loc[idx[n_train + n_validation:], "split"] = "test"
        df.loc[idx, "order"] = np.arange(len(idx))   # Train 안의 순서: shots=k이면 앞 k장
    df["target"] = df["label"].map({label: i for i, label in enumerate(sorted(CLASSES))})
    df.to_csv(MANIFEST, index=False, lineterminator="\n")
    if not keep_raw:
        shutil.rmtree(PARQUET_DIR)
    return df


def load_manifest():
    return pd.read_csv(MANIFEST)


def class_names():
    return [CLASSES[label] for label in sorted(CLASSES)]


# ----------------------------------------------------------------------------- 메모리 캐시
CACHE_SIZE = 256   # 짧은 변을 256으로 줄이고 가운데 256×256을 잘라 uint8로 메모리에 둔다 (약 200KB/장)


def load_image(path, size=CACHE_SIZE):
    image = Image.open(path).convert("RGB")
    w, h = image.size
    scale = size / min(w, h)
    image = image.resize((max(size, round(w * scale)), max(size, round(h * scale))), Image.BICUBIC)
    w, h = image.size
    left, top = (w - size) // 2, (h - size) // 2
    return np.asarray(image.crop((left, top, left + size, top + size)), dtype=np.uint8)


@dataclass
class ImageSet:
    images: np.ndarray      # (n, 256, 256, 3) uint8
    targets: np.ndarray     # (n,) 0..7
    files: list


def load_split(df, split, shots=None):
    part = df[df["split"] == split]
    if shots is not None:
        part = part[part["order"] < shots]
    part = part.sort_values(["target", "order"])
    images = np.stack([load_image(FLOWERS / f) for f in part["file"]])
    return ImageSet(images, part["target"].to_numpy(), part["file"].tolist())
