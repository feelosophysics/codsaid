"""문서 스캐너 애플리케이션.

GUI 모드 (기본): 단계별 윈도우 5개와 트랙바 패널을 띄운다. 트랙바를 움직이면 즉시 다시 처리한다.
  키: s = 결과 저장 (scanned_이름.png, warped_이름.jpg, --pdf면 PDF도), q 또는 Esc = 종료
GUI 없는 모드 (--no-gui): Colab처럼 창을 띄울 수 없는 환경용. 파라미터는 명령줄로 받고 단계별 이미지를 파일로 저장한다.

실행 예:
  python -m src.app data/synthetic/E01.jpg
  python -m src.app                      # 경로를 묻는다
  python -m src.app photo.jpg --no-gui --blur 7 --low 30 --high 120 --out outputs/cli
"""
import argparse
import sys
from dataclasses import replace
from pathlib import Path

import cv2

from .image_io import imread, imwrite
from .pdf_export import save_pdf
from .scanner import ScanParams, scan, stage_images

PANEL = "Trackbars"
DISPLAY_HEIGHT = 480  # 윈도우 하나의 표시 높이


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="비스듬히 찍은 문서를 반듯하게 펴는 스캐너")
    parser.add_argument("image", nargs="?", help="입력 이미지 경로 (생략하면 실행 후 묻는다)")
    parser.add_argument("--blur", type=int, default=ScanParams.blur, help="가우시안 커널 크기 (홀수)")
    parser.add_argument("--low", type=int, default=ScanParams.canny_low, help="Canny 낮은 임계값")
    parser.add_argument("--high", type=int, default=ScanParams.canny_high, help="Canny 높은 임계값")
    parser.add_argument("--block", type=int, default=ScanParams.block_size, help="적응형 이진화 블록 (0=자동)")
    parser.add_argument("--c", type=int, default=ScanParams.thresh_c, help="적응형 이진화 상수 C")
    parser.add_argument("--aspect", choices=("zhang", "distance"), default=ScanParams.aspect,
                        help="결과 종횡비 결정 방법")
    parser.add_argument("--out", default="outputs/app", help="저장 폴더")
    parser.add_argument("--pdf", action="store_true", help="저장할 때 PDF도 만든다 (보너스 3)")
    parser.add_argument("--no-gui", action="store_true", help="창 없이 단계별 이미지를 파일로 저장")
    return parser.parse_args(argv)


def fit_height(image, height=DISPLAY_HEIGHT):
    h, w = image.shape[:2]
    scale = height / h
    return cv2.resize(image, (max(1, round(w * scale)), height), interpolation=cv2.INTER_AREA)


def save_outputs(result, stem, out_dir, pdf=False):
    """결과 저장. 문서를 못 찾았으면 윤곽선 단계까지만 저장한다."""
    out_dir = Path(out_dir)
    saved = []
    for name, img in stage_images(result).items():
        saved.append(imwrite(out_dir / f"{stem}_{name.split()[0]}_{name.split()[1].lower()}.jpg", img))
    if result.found:
        saved.append(imwrite(out_dir / f"scanned_{stem}.png", result.scanned))
        saved.append(imwrite(out_dir / f"warped_{stem}.jpg", result.warped))
        if pdf:
            saved.append(save_pdf([result.scanned], out_dir / f"scanned_{stem}.pdf"))
    return saved


def describe(result):
    p = result.params
    head = f"blur={p.blur} canny=({p.canny_low},{p.canny_high}) 윤곽선 {len(result.contours)}개, 후보 {len(result.candidates)}개"
    if not result.found:
        return f"{head} → 문서 사각형 못 찾음: {result.reason}"
    a = result.aspect
    h, w = result.scanned.shape[:2]
    return f"{head} → 사각형 검출: 결과 {w}x{h}, 종횡비 {a['estimated']:.3f} ({a['method']}). 올바른지는 4 Contours 창에서 확인"


# ───────────────────────── GUI ─────────────────────────

def create_trackbars(params):
    cv2.namedWindow(PANEL, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(PANEL, 520, 260)
    noop = lambda _v: None  # noqa: E731
    cv2.createTrackbar("Blur Kernel", PANEL, params.blur, 31, noop)
    cv2.createTrackbar("Canny Low", PANEL, params.canny_low, 500, noop)
    cv2.createTrackbar("Canny High", PANEL, params.canny_high, 500, noop)
    cv2.createTrackbar("Thresh Block", PANEL, params.block_size, 151, noop)
    cv2.createTrackbar("Thresh C", PANEL, params.thresh_c, 40, noop)


def read_trackbars(params):
    return replace(params,
                   blur=cv2.getTrackbarPos("Blur Kernel", PANEL),
                   canny_low=cv2.getTrackbarPos("Canny Low", PANEL),
                   canny_high=cv2.getTrackbarPos("Canny High", PANEL),
                   block_size=cv2.getTrackbarPos("Thresh Block", PANEL),
                   thresh_c=cv2.getTrackbarPos("Thresh C", PANEL)).normalized()


def run_gui(image, stem, params, out_dir, pdf=False, max_iterations=None):
    """트랙바 값이 바뀔 때만 다시 처리하고, 키 입력을 기다린다."""
    create_trackbars(params)
    for i, name in enumerate(("1 Original", "2 Preprocessed", "3 Edges", "4 Contours", "5 Result")):
        cv2.namedWindow(name, cv2.WINDOW_NORMAL)
        cv2.moveWindow(name, 40 + (i % 3) * 420, 40 + (i // 3) * 540)
    last, result = None, None
    iterations = 0
    while True:
        current = read_trackbars(params)
        if current != last:
            result = scan(image, current)
            for name, img in stage_images(result).items():
                cv2.imshow(name, fit_height(img))
            print(describe(result))
            last = current
        key = cv2.waitKey(50) & 0xFF
        iterations += 1
        if key in (ord("q"), 27) or (max_iterations and iterations >= max_iterations):
            break
        if key == ord("s"):
            for path in save_outputs(result, stem, out_dir, pdf):
                print("저장:", path)
        # 사용자가 창의 X 버튼으로 닫으면 종료
        if cv2.getWindowProperty("5 Result", cv2.WND_PROP_VISIBLE) < 1:
            break
    cv2.destroyAllWindows()
    return last


def main(argv=None):
    args = parse_args(argv)
    path = args.image or input("이미지 경로를 입력하세요: ").strip().strip('"')
    try:
        image = imread(path)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    params = ScanParams(blur=args.blur, canny_low=args.low, canny_high=args.high, block_size=args.block,
                        thresh_c=args.c, aspect=args.aspect).normalized()
    stem = Path(path).stem
    if args.no_gui:
        result = scan(image, params)
        print(describe(result))
        for p in save_outputs(result, stem, args.out, args.pdf):
            print("저장:", p)
        return 0 if result.found else 2
    print("트랙바로 파라미터를 조절하세요. s = 저장, q/Esc = 종료")
    run_gui(image, stem, params, args.out, args.pdf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
