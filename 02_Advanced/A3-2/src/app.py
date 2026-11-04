"""실시간 영상 분석 앱.

실행:
  python -m src.app                                    # 데모: 합성 교차 영상 + 등록 물체
  python -m src.app --source 0                         # 웹캠 0번
  python -m src.app --source 영상.mp4 --target 물체.png
  python -m src.app --source data/synthetic/target_test.mp4 --feature sift
  python -m src.app --kalman --matcher hungarian       # 보너스 추적기
  python -m src.app --no-gui --out outputs/cli         # 창 없이 주석 영상·스냅샷 저장

키:
  q / Esc  종료          s  스냅샷 저장 (outputs/app/)      p  일시정지/재개
  n        (일시정지 중) 한 프레임 진행
  [ / ]    배경 학습률 ÷2 / ×2                              m  전경 마스크 창 켜기/끄기
  c        침입 구역 지우기      마우스 왼쪽 버튼 끌기: 침입 구역 지정 (보너스 2)
"""
import argparse
import sys
import time
from pathlib import Path

import cv2

from .features import TargetMatcher
from .image_io import imread, imwrite
from .motion import MotionParams
from .pipeline import VideoAnalyzer
from .tracker import Tracker
from .zone import IntrusionZone, ZoneSelector

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "synthetic" / "crossing_test.mp4"
DEFAULT_TARGET = ROOT / "data" / "target" / "target.png"
WINDOW = "A3-2 Tracker"
HELP = "q quit  s snapshot  p pause  [ ] learning rate  m mask  drag: zone  c clear"


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="배경 차분 + 거리 기반 추적 + 특징점 매칭 영상 분석기")
    ap.add_argument("--source", default=str(DEFAULT_SOURCE), help="웹캠 번호(0) 또는 영상 경로")
    ap.add_argument("--target", default=str(DEFAULT_TARGET), help="등록 물체 이미지 ('' 이면 끔)")
    ap.add_argument("--feature", choices=["orb", "sift"], default="orb")
    ap.add_argument("--target-every", type=int, default=2, help="특징점 매칭을 N프레임마다 (CPU 절약)")
    ap.add_argument("--method", choices=["mog2", "running_avg", "frame_diff"], default="mog2")
    ap.add_argument("--lr", type=float, default=MotionParams.learning_rate, help="배경 학습률 (−1: MOG2 자동)")
    ap.add_argument("--min-area", type=int, default=MotionParams.min_area)
    ap.add_argument("--max-distance", type=float, default=60.0)
    ap.add_argument("--max-missed", type=int, default=20)
    ap.add_argument("--matcher", choices=["greedy", "hungarian"], default="greedy")
    ap.add_argument("--cost", choices=["centroid", "iou"], default="centroid")
    ap.add_argument("--kalman", action="store_true")
    ap.add_argument("--zone", default="", help="침입 구역 x,y,w,h (처리 해상도 기준)")
    ap.add_argument("--width", type=int, default=640, help="처리 해상도 가로 (파라미터가 640 기준)")
    ap.add_argument("--out", default=str(ROOT / "outputs" / "app"))
    ap.add_argument("--no-gui", action="store_true", help="창 없이 처리하고 주석 영상을 저장")
    ap.add_argument("--snap-every", type=int, default=0, help="--no-gui에서 N프레임마다 스냅샷")
    ap.add_argument("--max-frames", type=int, default=0)
    ap.add_argument("--no-realtime", action="store_true", help="영상 파일을 원래 속도에 맞추지 않고 최대 속도로")
    ap.add_argument("--threads", type=int, default=2, help="OpenCV 스레드 수 (노트북 발열·소음 제한)")
    return ap.parse_args(argv)


def open_source(source):
    src = int(source) if str(source).isdigit() else source
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        hint = " (Windows: 설정 → 개인 정보 → 카메라에서 데스크톱 앱 접근 허용)" if isinstance(src, int) else ""
        raise SystemExit(f"입력을 열 수 없다: {source}{hint}")
    return cap, isinstance(src, int)


def build_analyzer(args):
    motion = MotionParams(method=args.method, learning_rate=args.lr, min_area=args.min_area)
    tracker = Tracker(max_distance=args.max_distance, max_missed=args.max_missed, matcher=args.matcher,
                      cost=args.cost, kalman=args.kalman)
    matcher = None
    if args.target:
        matcher = TargetMatcher(imread(args.target), args.feature)
        print(f"등록 물체: {args.target} ({args.feature.upper()} 특징점 {matcher.n_ref}개)")
    out = Path(args.out)
    zone = IntrusionZone(tuple(int(v) for v in args.zone.split(",")) if args.zone else None,
                         log_path=out / "intrusion_log.csv")
    return VideoAnalyzer(motion, tracker, matcher, zone, args.target_every)


def resize(frame, width):
    h, w = frame.shape[:2]
    if width and w != width:
        frame = cv2.resize(frame, (width, round(h * width / w)), interpolation=cv2.INTER_AREA)
    return frame


class FpsMeter:
    """지수 이동 평균 FPS."""

    def __init__(self, alpha=0.1):
        self.alpha = alpha
        self.value = None
        self.last = None

    def tick(self, now=None):
        now = time.perf_counter() if now is None else now
        if self.last is not None and now > self.last:
            inst = 1.0 / (now - self.last)
            self.value = inst if self.value is None else (1 - self.alpha) * self.value + self.alpha * inst
        self.last = now
        return self.value or 0.0


def save_snapshot(out_dir, index, frame, annotated, mask=None):
    out_dir = Path(out_dir)
    paths = [imwrite(out_dir / f"snapshot_{index:05d}.png", annotated), imwrite(out_dir / f"raw_{index:05d}.jpg", frame)]
    if mask is not None:
        paths.append(imwrite(out_dir / f"mask_{index:05d}.png", mask))
    return paths


def handle_key(key, state, analyzer):
    """키 하나를 처리해 상태를 바꾼다. 'quit', 'snapshot', 'step' 또는 None을 돌려준다 (테스트 가능하게 분리)."""
    key &= 0xFF
    if key in (ord("q"), 27):
        return "quit"
    if key == ord("s"):
        return "snapshot"
    if key == ord("p"):
        state["paused"] = not state["paused"]
    elif key == ord("n") and state["paused"]:
        return "step"
    elif key == ord("m"):
        state["show_mask"] = not state["show_mask"]
    elif key == ord("c") and analyzer.zone is not None:
        analyzer.zone.clear()
    elif key in (ord("["), ord("]")):
        lr = analyzer.motion_params.learning_rate
        if lr <= 0:
            lr = 1.0 / analyzer.motion_params.history
        lr = lr / 2 if key == ord("[") else lr * 2
        analyzer.set_learning_rate(round(min(1.0, max(1e-5, lr)), 6))
        print(f"배경 학습률 = {analyzer.motion_params.learning_rate:g}")
    return None


def run_gui(args):
    cap, live = open_source(args.source)
    analyzer = build_analyzer(args)
    selector = ZoneSelector(analyzer.zone)
    cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(WINDOW, selector)
    fps_src = cap.get(cv2.CAP_PROP_FPS) or 30.0
    delay = 0 if (live or args.no_realtime) else 1.0 / fps_src
    state = {"paused": False, "show_mask": False}
    meter = FpsMeter()
    proc_fps = None
    frame = res = None
    print(HELP)

    def advance():
        nonlocal frame, res, proc_fps
        ok, raw = cap.read()
        if not ok:
            return False
        frame = resize(raw, args.width)
        t = time.perf_counter()
        res = analyzer.process(frame)
        inst = 1.0 / max(time.perf_counter() - t, 1e-6)   # 분석만의 속도 (표시·대기 제외)
        proc_fps = inst if proc_fps is None else 0.9 * proc_fps + 0.1 * inst
        meter.tick()                                       # 화면 갱신 속도 = 표시 FPS
        return True

    while True:
        t0 = time.perf_counter()
        if (not state["paused"] or frame is None) and not advance():
            break
        annotated = analyzer.draw(frame, res, meter.value or 0.0, proc_fps, state["paused"])
        selector.draw(annotated)
        cv2.putText(annotated, HELP, (10, annotated.shape[0] - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1,
                    cv2.LINE_AA)
        cv2.imshow(WINDOW, annotated)
        if state["show_mask"]:
            cv2.imshow("Foreground mask", res.mask)
        else:
            try:
                if cv2.getWindowProperty("Foreground mask", cv2.WND_PROP_VISIBLE) >= 1:
                    cv2.destroyWindow("Foreground mask")
            except cv2.error:
                pass
        wait = max(1, int((delay - (time.perf_counter() - t0)) * 1000)) if delay and not state["paused"] else 1
        action = handle_key(cv2.waitKey(wait), state, analyzer)
        if action == "quit":
            break
        if action == "snapshot":
            paths = save_snapshot(args.out, res.index, frame, annotated, res.mask)
            print("저장:", ", ".join(str(p) for p in paths))
        if action == "step" and not advance():
            break
        if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
            break
    cap.release()
    cv2.destroyAllWindows()
    if analyzer.zone:
        analyzer.zone.close()


def run_headless(args):
    """창 없이 처리. 주석 영상(annotated.mp4)과 스냅샷, 침입 로그를 out에 저장한다."""
    cap, _ = open_source(args.source)
    analyzer = build_analyzer(args)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    writer = None
    meter = FpsMeter()
    n, found, t_start = 0, 0, time.perf_counter()
    while True:
        ok, raw = cap.read()
        if not ok or (args.max_frames and n >= args.max_frames):
            break
        frame = resize(raw, args.width)
        res = analyzer.process(frame)
        fps = meter.tick()
        annotated = analyzer.draw(frame, res, fps)
        if writer is None:
            writer = cv2.VideoWriter(str(out / "annotated.mp4"), cv2.VideoWriter_fourcc(*"mp4v"),
                                     cap.get(cv2.CAP_PROP_FPS) or 30.0, annotated.shape[1::-1])
        writer.write(annotated)
        found += bool(res.target is not None and res.target.found)
        if args.snap_every and n % args.snap_every == 0:
            save_snapshot(out, res.index, frame, annotated)
        n += 1
    cap.release()
    if writer:
        writer.release()
    if analyzer.zone:
        analyzer.zone.close()
    dt = time.perf_counter() - t_start
    print(f"{n} frames, {n / max(dt, 1e-9):.1f} fps, IDs used {analyzer.tracker.next_id - 1}, "
          f"target frames {found}, zone events {len(analyzer.zone.events) if analyzer.zone else 0} → {out}")
    return {"frames": n, "fps": n / max(dt, 1e-9), "ids": analyzer.tracker.next_id - 1, "target_frames": found}


def main(argv=None):
    args = parse_args(argv)
    cv2.setNumThreads(max(1, args.threads))
    if args.no_gui:
        return run_headless(args)
    try:
        return run_gui(args)
    except cv2.error as e:
        if "display" in str(e).lower() or "gui" in str(e).lower() or "not implemented" in str(e).lower():
            print("창을 띄울 수 없는 환경이다. --no-gui로 실행한다.", file=sys.stderr)
            return run_headless(args)
        raise


if __name__ == "__main__":
    main()
