"""웹캠 보드 (선택 과제): 실시간 프레임에서 문서를 찾아 윤곽선을 표시한다.

키: s = 현재 프레임을 변환해 저장, q 또는 Esc = 종료
카메라 대신 동영상 파일로도 실행할 수 있다 (--source video.mp4).

실행 예:
  python -m src.webcam              # 0번 카메라
  python -m src.webcam --source 1   # 1번 카메라

app.py와 같은 scan()을 쓴다. 다른 점은 매 프레임 warp=False로 검출만 하고(빠르게),
s를 누른 순간에만 같은 프레임을 다시 warp=True로 처리한다는 것이다.
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

    Args:
        frame: 카메라가 준 BGR 프레임 (H, W, 3).
        params: ScanParams. 웹캠은 work_size 640으로 더 작게 줄여 속도를 높인다.

    Returns:
        tuple: (view, result). view는 축소본에 사각형과 상태 글자를 그린 새 이미지다.
    """
    result = scan(frame, params, warp=False)
    view = draw_contours(result, show_candidates=False)
    status = "DOCUMENT" if result.found else "searching..."
    color = (0, 200, 0) if result.found else (0, 160, 255)  # BGR: 초록 / 주황
    # view.shape[0]은 높이. 아래쪽에서 16px 위에 글자를 쓴다.
    cv2.putText(view, status, (12, view.shape[0] - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)
    return view, result


def open_source(source):
    """숫자면 카메라 번호, 아니면 파일 경로로 연다.

    Windows에서는 DirectShow(CAP_DSHOW)로 먼저 열어 본다. 기본 방식보다 카메라가 빨리 열리는 경우가 많다.
    실패하면 기본 방식으로 다시 연다.

    Args:
        source: "0" 같은 카메라 번호 문자열 또는 동영상 경로.

    Returns:
        cv2.VideoCapture: 열린(또는 열기에 실패한) 캡처 객체. isOpened()로 확인한다.
    """
    # isdigit()은 문자열이 숫자로만 되어 있는지. "0" → 정수 0(카메라), "a.mp4" → 문자열 그대로(파일).
    src = int(source) if str(source).isdigit() else str(source)
    # isinstance(값, int)는 "정수인가". sys.platform == "win32"는 Windows인지 확인한다.
    cap = cv2.VideoCapture(src, cv2.CAP_DSHOW) if isinstance(src, int) and sys.platform == "win32" else cv2.VideoCapture(src)
    if not cap.isOpened():
        cap = cv2.VideoCapture(src)
    return cap


def main(argv=None):
    """카메라를 열고 프레임마다 검출해 보여 준다. s로 저장, q/Esc로 끝낸다.

    Args:
        argv: 인자 문자열 목록. None이면 실제 명령줄을 읽는다.

    Returns:
        int: 종료 코드. 0 정상, 1 카메라·영상을 열 수 없음.
    """
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
    # try ... finally: 중간에 오류가 나거나 break로 나가도 finally 블록은 반드시 실행된다. 카메라를 꼭 닫기 위해서다.
    try:
        while True:
            ok, frame = cap.read()  # (성공 여부, 프레임). 영상 파일이 끝나면 ok가 False다.
            if not ok:
                print("프레임을 더 읽을 수 없다. 종료한다.")
                break
            view, result = process_frame(frame, params)
            now = time.perf_counter()
            # 지수 이동 평균: 새 fps(1 / 이번 프레임 시간)를 10%만 반영해 숫자가 덜 흔들린다.
            # max(…, 1e-6)은 시간이 0이라 0으로 나누는 일을 막는다.
            fps = 0.9 * fps + 0.1 / max(now - t_prev, 1e-6)
            t_prev = now
            cv2.putText(view, f"{fps:4.1f} fps", (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2, cv2.LINE_AA)
            cv2.imshow(WINDOW, view)
            key = cv2.waitKey(1) & 0xFF  # 1ms만 기다려 다음 프레임으로 빨리 넘어간다
            if key in (ord("q"), 27):
                break
            if key == ord("s"):
                full = scan(frame, params)  # 원본 해상도로 변환
                stamp = time.strftime("%Y%m%d-%H%M%S")  # 현재 시각 "20261015-193000" 형식. 파일 이름이 겹치지 않게 한다
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
