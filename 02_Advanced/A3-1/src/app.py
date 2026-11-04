"""문서 스캐너 애플리케이션.

GUI 모드 (기본): 단계별 윈도우 5개와 트랙바 패널을 띄운다. 트랙바를 움직이면 즉시 다시 처리한다.
  키: s = 결과 저장 (scanned_이름.png, warped_이름.jpg, --pdf면 PDF도), q 또는 Esc = 종료
GUI 없는 모드 (--no-gui): Colab처럼 창을 띄울 수 없는 환경용. 파라미터는 명령줄로 받고 단계별 이미지를 파일로 저장한다.

실행 예:
  python -m src.app data/synthetic/E01.jpg
  python -m src.app                      # 경로를 묻는다
  python -m src.app photo.jpg --no-gui --blur 7 --low 30 --high 120 --out outputs/cli

흐름: 명령줄 → ScanParams → scan() → stage_images() → 창 5개 표시 → 트랙바 변경 시 다시 scan().
이벤트 루프(while True)의 동작은 study/code-walkthrough.md 7장에 있다.
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
    """명령줄 인자를 읽는다.

    argparse는 터미널에서 적은 "--blur 7" 같은 글자를 파이썬 값으로 바꾼다. type=int면 정수로 바꾸고,
    default는 생략했을 때의 값이다. 기본값을 ScanParams.blur처럼 클래스에서 가져와 두 곳의 기본값이 어긋나지 않게 한다.

    Args:
        argv: 인자 문자열 목록. None이면 실제 명령줄(sys.argv)을 읽는다. 테스트에서 직접 넘길 수 있다.

    Returns:
        argparse.Namespace: args.image, args.blur처럼 점으로 꺼내는 객체. "--no-gui"는 args.no_gui가 된다.
    """
    parser = argparse.ArgumentParser(description="비스듬히 찍은 문서를 반듯하게 펴는 스캐너")
    # nargs="?"는 "0개 또는 1개". 경로를 생략할 수 있게 해서, 생략하면 main에서 input()으로 묻는다.
    parser.add_argument("image", nargs="?", help="입력 이미지 경로 (생략하면 실행 후 묻는다)")
    parser.add_argument("--blur", type=int, default=ScanParams.blur, help="가우시안 커널 크기 (홀수)")
    parser.add_argument("--low", type=int, default=ScanParams.canny_low, help="Canny 낮은 임계값")
    parser.add_argument("--high", type=int, default=ScanParams.canny_high, help="Canny 높은 임계값")
    parser.add_argument("--block", type=int, default=ScanParams.block_size, help="적응형 이진화 블록 (0=자동)")
    parser.add_argument("--c", type=int, default=ScanParams.thresh_c, help="적응형 이진화 상수 C")
    parser.add_argument("--aspect", choices=("zhang", "distance"), default=ScanParams.aspect,
                        help="결과 종횡비 결정 방법")
    parser.add_argument("--out", default="outputs/app", help="저장 폴더")
    # store_true: 옵션을 적으면 True, 생략하면 False가 되는 스위치.
    parser.add_argument("--pdf", action="store_true", help="저장할 때 PDF도 만든다 (보너스 3)")
    parser.add_argument("--no-gui", action="store_true", help="창 없이 단계별 이미지를 파일로 저장")
    return parser.parse_args(argv)


def fit_height(image, height=DISPLAY_HEIGHT):
    """화면 표시용으로 높이를 맞춰 줄인다. 가로세로 비율은 유지한다.

    Args:
        image: (H, W, 3) 이미지.
        height: 표시할 높이(픽셀). 기본 480.

    Returns:
        numpy.ndarray: (height, 새 너비, 3) 새 이미지. 예: (960, 720, 3) → (480, 360, 3).
    """
    h, w = image.shape[:2]
    scale = height / h
    return cv2.resize(image, (max(1, round(w * scale)), height), interpolation=cv2.INTER_AREA)  # (가로, 세로)


def save_outputs(result, stem, out_dir, pdf=False):
    """결과 저장. 문서를 못 찾았으면 단계별 이미지 5장만 저장한다(5번은 NOT FOUND 화면).

    파일 이름 예(stem="E01"): E01_1_original.jpg … E01_5_result.jpg, scanned_E01.png, warped_E01.jpg.
    이진 결과는 PNG(무손실)로 저장한다. JPEG로 저장하면 0/255 경계에 압축 잡음이 생긴다.

    Args:
        result: scan()의 ScanResult.
        stem: 파일 이름 앞부분(입력 파일 이름에서 확장자를 뺀 것).
        out_dir: 저장 폴더.
        pdf: True면 scanned 이미지를 PDF로도 저장한다.

    Returns:
        list: 저장한 파일 경로 목록.
    """
    out_dir = Path(out_dir)
    saved = []
    # .items()는 dict의 (키, 값) 쌍을 하나씩 준다. Path / "이름"은 경로를 이어 붙인다.
    for name, img in stage_images(result).items():
        # name.split()은 공백으로 나눈다: "1 Original" → ["1", "Original"]. [0]은 "1", [1].lower()는 "original".
        saved.append(imwrite(out_dir / f"{stem}_{name.split()[0]}_{name.split()[1].lower()}.jpg", img))
    if result.found:
        saved.append(imwrite(out_dir / f"scanned_{stem}.png", result.scanned))
        saved.append(imwrite(out_dir / f"warped_{stem}.jpg", result.warped))
        if pdf:
            saved.append(save_pdf([result.scanned], out_dir / f"scanned_{stem}.pdf"))
    return saved


def describe(result):
    """콘솔에 출력할 한 줄 요약을 만든다.

    Args:
        result: scan()의 ScanResult.

    Returns:
        str: 파라미터·윤곽선 수·결과 크기 요약. 실패하면 이유를 붙인다.
    """
    p = result.params
    head = f"blur={p.blur} canny=({p.canny_low},{p.canny_high}) 윤곽선 {len(result.contours)}개, 후보 {len(result.candidates)}개"
    if not result.found:
        return f"{head} → 문서 사각형 못 찾음: {result.reason}"
    a = result.aspect
    h, w = result.scanned.shape[:2]
    # {값:.3f}는 소수점 아래 3자리로 표시한다. 저장된 값 자체는 바뀌지 않는다.
    return f"{head} → 사각형 검출: 결과 {w}x{h}, 종횡비 {a['estimated']:.3f} ({a['method']}). 올바른지는 4 Contours 창에서 확인"


# ───────────────────────── GUI ─────────────────────────

def create_trackbars(params):
    """트랙바 패널 창을 만들고 슬라이더 5개를 단다.

    트랙바는 0부터 최댓값까지의 정수만 준다. 짝수 블러 같은 값은 read_trackbars → normalized()에서 고친다.

    Args:
        params: 슬라이더의 처음 위치로 쓸 ScanParams.
    """
    cv2.namedWindow(PANEL, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(PANEL, 520, 260)
    # 트랙바를 움직일 때 부를 함수(콜백)가 필요하지만, 여기서는 루프에서 직접 값을 읽으므로 아무 일도 하지 않는다.
    noop = lambda _v: None  # noqa: E731
    # createTrackbar(이름, 창, 처음 값, 최댓값, 콜백)
    cv2.createTrackbar("Blur Kernel", PANEL, params.blur, 31, noop)
    cv2.createTrackbar("Canny Low", PANEL, params.canny_low, 500, noop)
    cv2.createTrackbar("Canny High", PANEL, params.canny_high, 500, noop)
    cv2.createTrackbar("Thresh Block", PANEL, params.block_size, 151, noop)
    cv2.createTrackbar("Thresh C", PANEL, params.thresh_c, 40, noop)


def read_trackbars(params):
    """현재 슬라이더 값으로 새 ScanParams를 만든다.

    Args:
        params: 트랙바에 없는 값(면적 비율 등)을 가져올 기준 ScanParams.

    Returns:
        ScanParams: 슬라이더 값을 반영하고 normalized()로 홀수·순서를 맞춘 새 객체.
    """
    # 여러 줄에 걸친 호출은 괄호 안이라 줄을 바꿔도 된다. replace(...).normalized()처럼 메서드를 이어 부른다.
    return replace(params,
                   blur=cv2.getTrackbarPos("Blur Kernel", PANEL),
                   canny_low=cv2.getTrackbarPos("Canny Low", PANEL),
                   canny_high=cv2.getTrackbarPos("Canny High", PANEL),
                   block_size=cv2.getTrackbarPos("Thresh Block", PANEL),
                   thresh_c=cv2.getTrackbarPos("Thresh C", PANEL)).normalized()


def run_gui(image, stem, params, out_dir, pdf=False, max_iterations=None):
    """트랙바 값이 바뀔 때만 다시 처리하고, 키 입력을 기다린다.

    매 바퀴(약 50ms): 트랙바 읽기 → 값이 바뀌었으면 scan()과 창 5개 갱신 → 키 확인.
    값이 같을 때 다시 처리하지 않으므로, 가만히 있을 때 CPU를 거의 쓰지 않는다.

    Args:
        image: 원본 BGR 이미지.
        stem: 저장 파일 이름 앞부분.
        params: 처음 파라미터.
        out_dir: 저장 폴더.
        pdf: s로 저장할 때 PDF도 만들지 여부.
        max_iterations: 테스트용. 이 횟수만큼 돌면 스스로 끝난다. None이면 키를 누를 때까지.

    Returns:
        ScanParams: 마지막으로 처리한 파라미터.
    """
    create_trackbars(params)
    # enumerate는 (번호, 원소)를 함께 준다: (0, "1 Original"), (1, "2 Preprocessed"), ...
    for i, name in enumerate(("1 Original", "2 Preprocessed", "3 Edges", "4 Contours", "5 Result")):
        cv2.namedWindow(name, cv2.WINDOW_NORMAL)
        # //는 몫, %는 나머지. 창 3개씩 한 줄로: i=0,1,2는 첫 줄, i=3,4는 둘째 줄.
        cv2.moveWindow(name, 40 + (i % 3) * 420, 40 + (i // 3) * 540)
    last, result = None, None
    iterations = 0
    while True:  # break를 만날 때까지 계속 도는 반복문
        current = read_trackbars(params)
        if current != last:  # frozen dataclass라 ==, != 로 모든 값을 한 번에 비교할 수 있다
            result = scan(image, current)
            for name, img in stage_images(result).items():
                cv2.imshow(name, fit_height(img))
            print(describe(result))
            last = current
        # waitKey(50): 최대 50ms 키를 기다리고, 그동안 창을 다시 그린다. 이 호출이 없으면 창이 멈춘 것처럼 보인다.
        # & 0xFF는 아래 8비트만 남겨 운영체제별로 다른 상위 비트를 지운다. 27은 Esc 키 코드, ord("q")는 "q"의 코드.
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
    """명령줄을 읽고 GUI 또는 --no-gui 모드를 실행한다.

    Args:
        argv: 인자 문자열 목록. None이면 실제 명령줄을 읽는다.

    Returns:
        int: 종료 코드. 0 정상, 1 이미지 읽기 실패, 2 문서를 찾지 못함(--no-gui).
    """
    args = parse_args(argv)
    # input()은 사용자가 엔터를 칠 때까지 기다린다. strip()은 앞뒤 공백, strip('"')는 탐색기에서 복사한 따옴표를 지운다.
    path = args.image or input("이미지 경로를 입력하세요: ").strip().strip('"')
    # try 블록에서 오류가 나면 except로 넘어간다. 프로그램이 긴 오류 메시지로 죽지 않고 이유만 보여 준다.
    try:
        image = imread(path)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)  # stderr는 오류 메시지용 출력 통로
        return 1
    params = ScanParams(blur=args.blur, canny_low=args.low, canny_high=args.high, block_size=args.block,
                        thresh_c=args.c, aspect=args.aspect).normalized()
    stem = Path(path).stem  # "data/synthetic/E01.jpg" → "E01"
    if args.no_gui:
        result = scan(image, params)
        print(describe(result))
        for p in save_outputs(result, stem, args.out, args.pdf):
            print("저장:", p)
        return 0 if result.found else 2
    print("트랙바로 파라미터를 조절하세요. s = 저장, q/Esc = 종료")
    run_gui(image, stem, params, args.out, args.pdf)
    return 0


# 이 파일을 직접 실행할 때만(python -m src.app) 참이다. 다른 파일에서 import하면 main이 실행되지 않는다.
# sys.exit(코드)는 main의 반환값을 종료 코드로 운영체제에 알린다.
if __name__ == "__main__":
    sys.exit(main())
