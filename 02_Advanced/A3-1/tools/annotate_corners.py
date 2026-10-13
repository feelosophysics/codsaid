"""직접 찍은 사진에 정답 꼭짓점과 촬영 조건을 기록해 labels.json을 만든다.

사용법:
  python tools/annotate_corners.py data/real

창에서 문서 모서리 4개를 클릭한다 (순서 상관없음, 저장할 때 TL·TR·BR·BL로 정렬).
  1~4  조건 선택: 1 단순 배경+정면, 2 그림자, 3 45도 이상, 4 복잡한 배경
  r    다시 찍기      Enter/Space  저장 후 다음      n  건너뛰기      q/Esc  종료
조명·각도·배경 메모는 저장 후 labels.json에서 직접 고친다. 이미 라벨이 있는 이미지는 건너뛴다(--redo로 다시).
그 뒤 `python -m src.run_all --data data/real --out outputs/real`로 합성 데이터와 같은 기준으로 평가한다.
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.geometry import order_points  # noqa: E402
from src.image_io import imread, list_images  # noqa: E402

CONDITIONS = {ord("1"): "easy", ord("2"): "shadow", ord("3"): "tilt", ord("4"): "complex"}
CONDITION_NAMES = {"easy": "단순 배경 + 정면", "shadow": "그림자 있음", "tilt": "45도 이상 기울어짐",
                   "complex": "복잡한 배경"}
WINDOW = "annotate (click 4 corners, 1-4 condition, Enter save, r reset, n skip, q quit)"
MAX_SIDE = 1000


def annotate(image, condition):
    """클릭한 네 점(원본 좌표)과 조건을 돌려준다. 건너뛰면 None, 종료면 'quit'."""
    scale = min(1.0, MAX_SIDE / max(image.shape[:2]))
    view = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    points = []

    def on_mouse(event, x, y, _flags, _param):
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
            points.append((x / scale, y / scale))

    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(WINDOW, on_mouse)
    while True:
        canvas = view.copy()
        for x, y in points:
            cv2.circle(canvas, (int(x * scale), int(y * scale)), 6, (0, 0, 255), -1)
        if len(points) == 4:
            q = (order_points(points) * scale).round().astype(np.int32)
            cv2.polylines(canvas, [q], True, (0, 0, 255), 2)
        cv2.putText(canvas, f"condition: {condition}  points: {len(points)}/4", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.imshow(WINDOW, canvas)
        key = cv2.waitKey(30) & 0xFF
        if key in CONDITIONS:
            condition = CONDITIONS[key]
        elif key == ord("r"):
            points.clear()
        elif key == ord("n"):
            return None
        elif key in (ord("q"), 27):
            return "quit"
        elif key in (13, 32) and len(points) == 4:
            return order_points(points), condition


def main(argv=None):
    parser = argparse.ArgumentParser(description="실제 사진 정답 꼭짓점 라벨링")
    parser.add_argument("folder")
    parser.add_argument("--condition", default="easy", choices=list(CONDITION_NAMES))
    parser.add_argument("--redo", action="store_true")
    args = parser.parse_args(argv)
    folder = Path(args.folder)
    label_file = folder / "labels.json"
    doc = json.loads(label_file.read_text(encoding="utf-8")) if label_file.is_file() else {
        "description": "직접 촬영한 문서 사진. corners는 좌상·우상·우하·좌하 픽셀 좌표다.", "images": []}
    done = {lab["file"]: lab for lab in doc["images"]}
    condition = args.condition
    for path in list_images(folder):
        if path.name in done and not args.redo:
            continue
        image = imread(path)
        answer = annotate(image, condition)
        if answer == "quit":
            break
        if answer is None:
            continue
        quad, condition = answer
        done[path.name] = {
            "id": path.stem, "file": path.name, "condition": condition, "condition_name": CONDITION_NAMES[condition],
            "lighting": done.get(path.name, {}).get("lighting", "기록 필요"),
            "angle": done.get(path.name, {}).get("angle", {"note": "기록 필요"}),
            "background_complexity": done.get(path.name, {}).get("background_complexity", "기록 필요"),
            "corners": quad.round(1).tolist(),
        }
        doc["images"] = [done[k] for k in sorted(done)]
        label_file.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"저장: {path.name} ({condition})")
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
