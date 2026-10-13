"""웹캠 보드 (선택 과제): 실시간 프레임에서 문서를 찾아 윤곽선을 표시한다.

키: s = 현재 프레임을 변환해 저장, q 또는 Esc = 종료
카메라 대신 동영상 파일로도 실행할 수 있다 (--source video.mp4).

실행 예:
  python -m src.webcam              # 0번 카메라
  python -m src.webcam --source 1   # 1번 카메라
"""
import argparse
import sys
import time
from pathlib import Path

import cv2

from .image_io import imwrite
from .scanner import ScanParams, draw_contours, scan

WINDOW = "Webcam Scanner (s: save, q: quit)"


def process_frame(frame, params):
    """프레임 하나를 처리해 (화면 표시용 이미지, ScanResult)를 돌려준다.

    실시간 처리를 위해 검출만 하고 투시 변환은 저장할 때 한다.
    """
    result = scan(frame, params, warp=False)
    view = draw_contours(result, show_candidates=False)
    status = "DOCUMENT" if result.found else "searching..."
    color = (0, 200, 0) if result.found else (0, 160, 255)
    cv2.putText(view, status, (12, view.shape[0] - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)
    return view, result


def open_source(source):
    """숫자면 카메라 번호, 아니면 파일 경로로 연다."""
    src = int(source) if str(source).isdigit() else str(source)
    cap = cv2.VideoCapture(src, cv2.CAP_DSHOW) if isinstance(src, int) and sys.platform == "win32" else cv2.VideoCapture(src)
    if not cap.isOpened():
        cap = cv2.VideoCapture(src)
    return cap


def main(argv=None):
    parser = argparse.ArgumentParser(description="웹캠 실시간 문서 검출")
    parser.add_argument("--source", default="0", help="카메라 번호 또는 동영상 경로")
    parser.add_argument("--out", default="outputs/webcam", help="저장 폴더")
    parser.add_argument("--work-size", type=int, default=640, help="검출용 축소 크기 (작을수록 빠름)")
    args = parser.parse_args(argv)

    cap = open_source(args.source)
    if not cap.isOpened():
        print(f"카메라/영상을 열 수 없다: {args.source}. OS의 카메라 권한을 확인하세요.", file=sys.stderr)
        return 1
    params = ScanParams(work_size=args.work_size).normalized()
    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    saved = 0
    fps, t_prev = 0.0, time.perf_counter()
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("프레임을 더 읽을 수 없다. 종료한다.")
                break
            view, result = process_frame(frame, params)
            now = time.perf_counter()
            fps = 0.9 * fps + 0.1 / max(now - t_prev, 1e-6)
            t_prev = now
            cv2.putText(view, f"{fps:4.1f} fps", (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2, cv2.LINE_AA)
            cv2.imshow(WINDOW, view)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("s"):
                full = scan(frame, params)  # 원본 해상도로 변환
                stamp = time.strftime("%Y%m%d-%H%M%S")
                if full.found:
                    imwrite(Path(args.out) / f"scanned_{stamp}.png", full.scanned)
                    imwrite(Path(args.out) / f"warped_{stamp}.jpg", full.warped)
                    saved += 1
                    print(f"저장: {args.out}/scanned_{stamp}.png")
                else:
                    imwrite(Path(args.out) / f"frame_{stamp}.jpg", frame)
                    print(f"문서를 찾지 못해 원본 프레임만 저장: {args.out}/frame_{stamp}.jpg ({full.reason})")
            if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    print(f"종료. 저장한 스캔 {saved}장")
    return 0


if __name__ == "__main__":
    sys.exit(main())
