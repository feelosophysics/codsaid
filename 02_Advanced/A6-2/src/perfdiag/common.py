"""경로, 재현성(seed), CPU 스레드 제한, 결과 저장을 모은다."""
import json
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"                     # 내려받은 원본 (git 제외)
TIMESERIES = DATA / "timeseries"       # 시계열 스냅샷 CSV (git 포함, 재현용)
FLOWERS = DATA / "flowers_subset"      # 선별한 꽃 이미지 (git 제외)
FIGURES = ROOT / "figures"
RESULTS = ROOT / "results"
REPORTS = ROOT / "reports"

# i5-13420H(8코어 12스레드) 노트북에서 다른 작업을 막지 않도록 절반만 쓴다.
DEFAULT_THREADS = 6


def lower_priority():
    """프로세스 우선순위를 한 단계 낮춘다 (PERFDIAG_LOW_PRIORITY=1일 때만).

    기본으로 끈 이유: Windows 11은 낮은 우선순위 프로세스를 백그라운드 작업으로 보고 효율 코어·낮은 클럭으로
    돌린다(EcoQoS). i5-13420H에서 학습 속도가 약 4분의 1로 떨어졌다. 부하는 스레드 수로 조절한다.
    """
    if os.environ.get("PERFDIAG_LOW_PRIORITY") != "1":
        return
    try:
        if sys.platform == "win32":
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.GetCurrentProcess.restype = ctypes.c_void_p      # HANDLE은 64비트 포인터다
            kernel32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
            kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), 0x4000)   # BELOW_NORMAL_PRIORITY_CLASS
        else:
            os.nice(5)
    except (OSError, AttributeError):
        pass


def configure_cpu(threads=None):
    """PyTorch 연산 스레드 수를 제한하고 우선순위를 낮춘다. PERFDIAG_THREADS 환경 변수로 스레드 수를 바꾼다."""
    lower_priority()
    threads = int(threads or os.environ.get("PERFDIAG_THREADS", DEFAULT_THREADS))
    torch.set_num_threads(threads)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:  # 이미 병렬 작업이 시작된 뒤에는 바꿀 수 없다
        pass
    return threads


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def utf8_console():
    """Windows 콘솔(cp949)에서도 한글·기호를 출력한다."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _default(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, Path):
        return obj.relative_to(ROOT).as_posix()
    raise TypeError(f"JSON으로 바꿀 수 없다: {type(obj)}")


def save_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=_default) + "\n",
                    encoding="utf-8", newline="\n")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class Tee:
    """print 출력을 화면과 로그 파일에 함께 쓴다."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def __enter__(self):
        self.file = open(self.path, "w", encoding="utf-8", newline="\n")
        self.stdout = sys.stdout
        sys.stdout = self
        return self

    def __exit__(self, *exc):
        sys.stdout = self.stdout
        self.file.close()

    def write(self, text):
        self.stdout.write(text)
        self.file.write(text)
        self.file.flush()   # 오래 걸리는 학습 중에도 로그 파일로 진행 상황을 볼 수 있게

    def flush(self):
        self.stdout.flush()
        self.file.flush()
