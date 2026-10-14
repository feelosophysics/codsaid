"""직접 찍은 영상의 수동 측정 도구 (미션 기능 6의 측정 프로토콜).

추적 결과를 보면서 이벤트 구간을 열고 닫고, 그 사이에 본 ID Switch·추적 실패·가림을 키로 센다.
닫을 때마다 기록 템플릿 한 줄(영상명 - 조건 - 프레임 범위 - ID Switch 수 - 실패 수 - 관찰 메모)이 CSV에 추가된다.

실행:  python tools/annotate_events.py data/real/두사람교차.mp4 --condition 겹침
       python tools/annotate_events.py data/real/조명.mp4 --condition 조명 --out outputs/real/measurement_log.csv

키:
  space  재생/일시정지        . (일시정지 중) 한 프레임 앞으로
  b      이벤트 시작           e  이벤트 끝 (CSV에 한 줄 저장)
  i      ID Switch +1          f  추적 실패 +1          o  50% 이상 가림 +1 (실패에서 빼고 메모에 남김)
  1~4    조건: 1 단일 이동, 2 겹침, 3 일시 정지, 4 조명 변화
  u      마지막 표시 취소      q  종료
판정 기준: ID Switch는 겹침 뒤 다른 ID가 5프레임 이상 유지될 때, 추적 실패는 보이는데 10프레임 이상 박스가 없을 때.
"""
import argparse
import csv
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.motion import MotionParams  # noqa: E402
from src.pipeline import VideoAnalyzer  # noqa: E402
from src.tracker import Tracker  # noqa: E402

CONDITIONS = {ord("1"): "단일 객체 이동", ord("2"): "두 객체 겹침", ord("3"): "객체 일시 정지", ord("4"): "조명 변화"}
ALIASES = {"단일": "단일 객체 이동", "겹침": "두 객체 겹침", "정지": "객체 일시 정지", "조명": "조명 변화"}


def append_row(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["영상명", "조건", "프레임 범위", "ID Switch 수", "실패 수", "관찰 메모"])
        w.writerow(row)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("video")
    ap.add_argument("--condition", default="겹침", help="단일 | 겹침 | 정지 | 조명 (또는 직접 쓴 이름)")
    ap.add_argument("--out", default=str(ROOT / "outputs" / "real" / "measurement_log.csv"))
    ap.add_argument("--lr", type=float, default=MotionParams.learning_rate)
    ap.add_argument("--width", type=int, default=640)
    args = ap.parse_args(argv)
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        raise SystemExit(f"영상을 열 수 없다: {args.video}")
    out = Path(args.out)
    an = VideoAnalyzer(MotionParams(learning_rate=args.lr), Tracker())
    cond = ALIASES.get(args.condition, args.condition)
    paused, event, history = False, None, []
    frame = res = None
    idx = -1
    name = Path(args.video).name
    while True:
        if not paused or frame is None:
            ok, raw = cap.read()
            if not ok:
                break
            h, w = raw.shape[:2]
            frame = cv2.resize(raw, (args.width, round(h * args.width / w))) if w != args.width else raw
            res = an.process(frame)
            idx += 1
            if event is not None:
                event["ids"].update(t.id for t in res.tracks)
        view = an.draw(frame, res, None, None, paused)
        status = f"f{idx}  [{cond}]  " + (f"EVENT from f{event['start']}: switch {event['switch']} fail {event['fail']} "
                                          f"occl {event['occl']}" if event else "b: begin event")
        cv2.putText(view, status, (10, view.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(view, status, (10, view.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
        cv2.imshow("annotate", view)
        key = cv2.waitKey(1 if not paused else 30) & 0xFF
        if key == ord("q"):
            break
        if key == ord(" "):
            paused = not paused
        elif key == ord(".") and paused:
            frame = None
            paused = False
            continue
        elif key in CONDITIONS:
            cond = CONDITIONS[key]
        elif key == ord("b"):
            event = {"start": idx, "switch": 0, "fail": 0, "occl": 0, "ids": set()}
        elif event is not None and key in (ord("i"), ord("f"), ord("o")):
            field = {ord("i"): "switch", ord("f"): "fail", ord("o"): "occl"}[key]
            event[field] += 1
            history.append(field)
        elif key == ord("u") and event is not None and history:
            event[history.pop()] -= 1
        elif key == ord("e") and event is not None:
            memo = f"사용 ID {sorted(event['ids'])}"
            if event["occl"]:
                memo += f"; 50% 이상 가림 {event['occl']}회 (실패에서 제외)"
            append_row(out, [name, cond, f"{event['start']}–{idx}", event["switch"], event["fail"], memo])
            print(f"기록: {name} {cond} {event['start']}–{idx} switch {event['switch']} fail {event['fail']} → {out}")
            event, history = None, []
        if paused and frame is not None and key == 255:
            continue
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
