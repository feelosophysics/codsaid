"""공개 데이터 내려받기와 표본 분할.

- NSMC(네이버 영화 리뷰, CC0): ratings_train.txt 150,000건, ratings_test.txt 50,000건.
  평점 1~4는 부정(0), 9~10은 긍정(1)으로 이미 레이블돼 있다.
- KNU 한국어 감성사전(군산대 Data Intelligence Lab, 2018): SentiWord_info.json 14,843개 표제어.
  저장소에 라이선스가 명시돼 있지 않아 커밋하지 않고 실행할 때 내려받는다.

분할 원칙(A5-1의 누수 방지와 같은 생각)
- dev 1,000건: ratings_train에서 뽑는다. 사전·규칙을 만들고 임계값을 정할 때만 본다.
- test 1,000건: ratings_test에서 뽑는다. 규칙을 고정한 뒤 성능을 잴 때만 쓴다.
- pool: ratings_train에서 dev를 뺀 나머지. 보너스 2(TF-IDF 학습)의 학습 데이터를 여기서 뽑는다.
"""
from __future__ import annotations

import csv
import json
import random
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / "data" / "downloads"

SOURCES = {
    "ratings_train.txt": "https://raw.githubusercontent.com/e9t/nsmc/master/ratings_train.txt",
    "ratings_test.txt": "https://raw.githubusercontent.com/e9t/nsmc/master/ratings_test.txt",
    "SentiWord_info.json": "https://raw.githubusercontent.com/park1200656/KnuSentiLex/master/data/SentiWord_info.json",
}

SEED = 42
DEV_SIZE = 1000
TEST_SIZE = 1000


def fetch(name: str) -> Path:
    """data/downloads/<name>이 없으면 내려받는다."""
    path = DOWNLOADS / name
    if not path.exists():
        DOWNLOADS.mkdir(parents=True, exist_ok=True)
        print(f"내려받는 중: {SOURCES[name]}")
        tmp = path.with_suffix(path.suffix + ".part")
        urllib.request.urlretrieve(SOURCES[name], tmp)
        tmp.replace(path)
    return path


def read_nsmc(name: str) -> list[dict]:
    """id, document, label. 본문이 비어 있는 행은 뺀다."""
    rows = []
    with open(fetch(name), encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        for r in reader:
            text = (r["document"] or "").strip()
            if text:
                rows.append({"id": int(r["id"]), "text": text, "label": int(r["label"])})
    return rows


def stratified_sample(rows: list[dict], n: int, seed: int) -> list[dict]:
    """긍정·부정을 같은 수로 뽑는다(NSMC는 원래 거의 50:50이다)."""
    rng = random.Random(seed)
    out = []
    for label in (0, 1):
        group = [r for r in rows if r["label"] == label]
        out += rng.sample(group, n // 2)
    rng.shuffle(out)
    return out


def load_splits() -> dict[str, list[dict]]:
    train = read_nsmc("ratings_train.txt")
    test_all = read_nsmc("ratings_test.txt")
    dev = stratified_sample(train, DEV_SIZE, SEED)
    dev_ids = {r["id"] for r in dev}
    pool = [r for r in train if r["id"] not in dev_ids]
    test = stratified_sample(test_all, TEST_SIZE, SEED)
    return {"dev": dev, "test": test, "pool": pool}


def load_knu() -> list[dict]:
    """[{word, word_root, polarity}] 형식. polarity는 -2~2 문자열이다."""
    return json.loads(fetch("SentiWord_info.json").read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    s = load_splits()
    print({k: len(v) for k, v in s.items()})
    print(len(load_knu()), "KNU entries")
