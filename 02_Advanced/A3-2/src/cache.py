"""실험 중간 결과의 디스크 캐시 (선택).

검출 결과와 정답 마스크 통계는 계산이 오래 걸리지만(전체 실행의 절반 이상), 영상·파라미터·관련 소스가 같으면
결과도 같다. 키에 영상 파일 해시, 파라미터, 계산에 쓰인 소스 파일 해시를 모두 넣어서 하나라도 바뀌면 다시 계산한다.
run_all --cache DIR 로 켠다. 끄면(기본) 항상 새로 계산한다.
"""
import hashlib
import pickle
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_DIR = None
_HASHES = {}


def configure(directory):
    global _DIR
    _DIR = Path(directory) if directory else None
    if _DIR:
        _DIR.mkdir(parents=True, exist_ok=True)


def file_hash(path):
    path = Path(path)
    key = (str(path), path.stat().st_mtime_ns, path.stat().st_size)
    if key not in _HASHES:
        _HASHES[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    return _HASHES[key]


def cached(name, inputs, sources, compute):
    """inputs: 키에 넣을 값(repr 가능), sources: 결과에 영향을 주는 파일 목록. 캐시가 꺼져 있으면 compute()만 한다."""
    if _DIR is None:
        return compute()
    h = hashlib.sha256(repr(inputs).encode("utf-8"))
    for s in sources:
        h.update(file_hash(s).encode())
    path = _DIR / f"{name}-{h.hexdigest()[:20]}.pkl"
    if path.exists():
        with path.open("rb") as fh:
            return pickle.load(fh)
    value = compute()
    tmp = path.with_suffix(".tmp")
    with tmp.open("wb") as fh:
        pickle.dump(value, fh, protocol=pickle.HIGHEST_PROTOCOL)
    tmp.replace(path)
    return value
