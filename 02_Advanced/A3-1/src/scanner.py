"""문서 스캐너 파이프라인: 전처리 → 엣지 → 윤곽선 → 꼭짓점 정렬 → 투시 변환 → 적응형 이진화.

검출은 긴 변이 `work_size`인 축소본에서 한다. 사진 해상도가 달라도 블러 커널·면적 기준이 같은 의미를 갖게 하려는 것이다.
찾은 꼭짓점은 원본 좌표로 되돌려 원본 해상도에서 변환한다.

이 파일에서 배열이 바뀌는 모습 (E01 실행 결과, 원본 1280×960 사진):
    original  (1280, 960, 3) uint8   BGR 컬러. 축 순서는 (세로 H, 가로 W, 채널)
    work      (960, 720, 3)  uint8   긴 변을 960으로 줄인 축소본 (scale 0.75)
    gray      (960, 720)     uint8   채널 축이 사라진 밝기 한 장
    edges     (960, 720)     uint8   값은 0 또는 255. 255가 엣지 픽셀
    contours  374개 목록, 각 (N, 1, 2) int32   윤곽선 하나 = 점 N개의 (x, y)
    quad      (4, 2)         float64  문서 네 꼭짓점 TL·TR·BR·BL의 (x, y)
    warped    (883, 623, 3)  uint8   반듯하게 편 문서
    scanned   (883, 623)     uint8   흑백(0/255) 스캔본

함수 단위 데이터 흐름과 숫자 추적은 study/code-walkthrough.md 1~6장에 있다.
"""
# import 모듈: 다른 파일의 기능을 "모듈.이름"으로 쓸 수 있게 불러온다.
# from 모듈 import 이름: 이름만 꺼내 와서 앞에 모듈 이름 없이 쓴다.
import time
from dataclasses import asdict, dataclass, field, replace

import cv2  # OpenCV. 이미지 처리 함수 모음. 이미지는 NumPy 배열로 주고받는다.
import numpy as np  # "as np"는 짧은 별명. 이후 np.zeros처럼 쓴다.

# 앞의 점(.)은 "같은 src 폴더(패키지) 안"이라는 뜻이다(상대 import). python -m src.app처럼 실행해야 동작한다.
from . import geometry


# @dataclass는 아래 클래스에 적은 "이름: 자료형 = 기본값" 목록으로 __init__ 같은 기본 메서드를 자동으로 만든다.
# frozen=True면 만든 뒤 값을 바꿀 수 없다(params.blur = 7은 오류). 바꿀 때는 replace()로 새 객체를 만든다.
# 바뀌지 않으므로 두 객체를 ==로 비교해 "파라미터가 바뀌었는가"를 안전하게 판단할 수 있다(app.run_gui).
@dataclass(frozen=True)
class ScanParams:
    """트랙바·명령줄로 바꾸는 값과 고정 규칙의 기준값.

    ``ScanParams()``는 모든 기본값, ``ScanParams(blur=7)``은 blur만 바꾼 객체다.
    아래 각 줄의 ``이름: int = 5``에서 ``int``는 자료형 표시(타입 힌트)이고 실행 시 검사하지는 않는다.

    Attributes:
        blur: 가우시안 블러 커널 크기. 홀수여야 하며 1이면 블러를 하지 않는다.
        canny_low: Canny 낮은 임계값. 이 값보다 약한 기울기는 엣지가 아니다.
        canny_high: Canny 높은 임계값. 이 값보다 강한 기울기는 확실한 엣지다.
        close_kernel: 끊긴 엣지를 잇는 닫힘 연산 커널 크기. 0이면 끈다.
        min_area_ratio: 문서 후보의 최소 면적(축소본 면적 대비 비율).
        max_area_ratio: 문서 후보의 최대 면적. 화면 테두리 전체를 잡는 것을 막는다.
        approx_epsilon: approxPolyDP 허용 오차(윤곽선 둘레 대비 비율).
        work_size: 검출용 축소본의 긴 변 길이(픽셀).
        aspect: 결과 크기 결정 방법. "zhang" 또는 "distance".
        block_size: 적응형 이진화 블록 크기. 0이면 결과 크기에 맞춰 자동으로 정한다.
        thresh_c: 적응형 이진화에서 지역 평균에서 빼는 값.
        color_edges: 규칙 추가 실험용. B·G·R 채널마다 Canny를 돌려 합친다.
        auto_canny: 규칙 추가 실험용. 밝기 중앙값으로 Canny 임계값을 정한다.
        clahe: 규칙 추가 실험용. 블러 전에 지역 대비를 키운다.
    """
    blur: int = 5  # 가우시안 커널 크기 (홀수, 1이면 블러 없음)
    canny_low: int = 50
    canny_high: int = 150
    close_kernel: int = 3  # 끊긴 엣지를 잇는 닫힘 연산 커널 (0이면 끔)
    min_area_ratio: float = 0.05  # 문서 후보의 최소 면적 (축소본 면적 대비)
    max_area_ratio: float = 0.98  # 화면 테두리 전체를 잡는 것을 막는 최대 면적
    approx_epsilon: float = 0.02  # approxPolyDP 허용 오차 (둘레 대비)
    work_size: int = 960
    aspect: str = "zhang"  # 결과 크기 결정: "zhang"(보너스 2 확장) | "distance"(보너스 2 기본)
    block_size: int = 0  # 적응형 이진화 블록 크기 (0이면 결과 크기에 맞춰 자동)
    thresh_c: int = 10  # 적응형 이진화에서 지역 평균에서 빼는 값
    # 아래는 "규칙을 더하면 해결되는가" 실험용 추가 규칙. 기본 파이프라인에서는 모두 끈다.
    color_edges: bool = False  # B·G·R 채널마다 Canny를 돌려 합친다 (회색 변환에서 사라지는 색 경계 보존)
    auto_canny: bool = False  # 블러 이미지 밝기 중앙값의 0.66배·1.33배를 임계값으로 쓴다
    clahe: bool = False  # 블러 전에 지역 히스토그램 평활화로 대비를 키운다

    def normalized(self):
        """커널 크기는 홀수로, 임계값은 low ≤ high로 맞춘다.

        트랙바는 짝수나 0도 줄 수 있고, low를 high보다 크게 올릴 수도 있다. OpenCV의 GaussianBlur는
        짝수 커널에서 오류를 내므로 여기서 미리 고친다. 예: blur=4, low=200, high=80 → blur=5, low=80, high=200.

        Returns:
            ScanParams: 고친 값을 담은 새 객체. 원래 객체(self)는 바뀌지 않는다.
        """
        # self는 이 메서드를 부른 객체 자신이다. params.normalized()라면 self가 params다.
        # max(1, ...)로 0이나 음수를 1로 올린다. int()는 트랙바가 준 값을 정수로 바꾼다.
        blur = max(1, int(self.blur))
        # %는 나머지. 짝수면 blur % 2 == 0이라 1을 더하고, 홀수면 0을 더한다. 4 → 5, 5 → 5.
        blur += 1 - blur % 2
        # sorted는 작은 값부터 정렬한 리스트를 돌려준다. 두 값을 low, high에 나눠 담는다(언패킹).
        low, high = sorted((int(self.canny_low), int(self.canny_high)))
        close = max(0, int(self.close_kernel))
        # replace(객체, 이름=값)은 지정한 값만 바꾼 새 dataclass 객체를 만든다(frozen이라 직접 못 바꾼다).
        return replace(self, blur=blur, canny_low=low, canny_high=high, close_kernel=close)

    def to_dict(self):
        """results.json에 저장할 수 있게 모든 값을 dict로 바꾼다.

        Returns:
            dict: {"blur": 5, "canny_low": 50, ...} 형태의 사전.
        """
        return asdict(self)


# frozen이 없으므로 scan()이 객체를 만든 뒤 quad·warped 같은 칸을 나중에 채울 수 있다.
@dataclass
class ScanResult:
    """각 단계의 중간 결과. 시각화·평가·보고서가 모두 이 객체를 쓴다.

    문서를 못 찾으면 quad 이후 칸은 None으로 남고 reason에 이유가 적힌다.
    shape는 E01 실행 결과 기준 예시다.

    Attributes:
        params: 실제로 쓴 파라미터(normalized를 거친 값).
        original: 입력 원본 BGR 이미지. 예: (1280, 960, 3).
        scale: 원본 → 축소본 배율. 예: 0.75.
        work: 축소본 BGR. 예: (960, 720, 3).
        gray: 축소본의 회색 이미지 (960, 720).
        blurred: 블러한 회색 이미지 (960, 720).
        edges: Canny 결과. 0 또는 255인 (960, 720).
        closed: edges에 닫힘 연산을 한 결과. 윤곽선은 이 이미지에서 찾는다.
        contours: 모든 윤곽선의 목록. 각 원소는 (N, 1, 2) int32.
        candidates: 면적 조건을 통과한 윤곽선의 근사 다각형 목록. 각 원소는 (k, 1, 2).
        quad_work: 축소본 좌표의 꼭짓점 (4, 2), TL·TR·BR·BL 순서.
        quad: 원본 좌표의 꼭짓점 (4, 2), TL·TR·BR·BL 순서.
        reason: 실패 이유. 성공하면 빈 문자열.
        warped: 투시 변환 결과 BGR (높이, 너비, 3).
        scanned: 적응형 이진화 결과 (높이, 너비). 값은 0 또는 255.
        aspect: 종횡비 추정 결과 {"estimated", "focal_px", "method"}.
        timings: 단계별 걸린 시간(초).
    """
    params: ScanParams
    original: np.ndarray
    scale: float  # 원본 → 축소본 배율
    work: np.ndarray
    gray: np.ndarray
    blurred: np.ndarray
    edges: np.ndarray
    closed: np.ndarray
    contours: list
    # 리스트 기본값은 field(default_factory=list)로 준다. "= []"로 쓰면 모든 객체가 리스트 하나를 함께 쓰게
    # 되므로 dataclass가 금지한다. default_factory는 객체를 만들 때마다 list()를 새로 호출한다.
    candidates: list = field(default_factory=list)  # 면적 조건을 통과한 윤곽선의 근사 다각형
    quad_work: np.ndarray = None  # 축소본 좌표, TL·TR·BR·BL
    quad: np.ndarray = None  # 원본 좌표, TL·TR·BR·BL
    reason: str = ""  # 실패 이유
    warped: np.ndarray = None
    scanned: np.ndarray = None
    aspect: dict = None
    timings: dict = field(default_factory=dict)

    # @property를 붙이면 메서드를 괄호 없이 값처럼 읽는다: result.found (result.found()가 아니다).
    @property
    def found(self):
        """문서 사각형을 찾았는지 여부.

        Returns:
            bool: quad가 있으면 True.
        """
        # "is not None"은 "값이 비어 있지 않은가"를 묻는다. 배열은 ==로 비교하면 원소별 비교가 되므로 is를 쓴다.
        return self.quad is not None


def resize_for_work(image, work_size):
    """긴 변이 work_size가 되도록 줄인다. 이미 작으면 그대로 둔다.

    축소하면 계산이 빨라지고, 블러 커널 5px·최소 면적 5% 같은 기준이 사진 해상도와 무관하게 같은 의미를 갖는다.
    확대는 하지 않는다(정보가 늘지 않고 계산만 커진다).

    Args:
        image: BGR 이미지 (H, W, 3) 또는 회색 (H, W).
        work_size: 축소본의 긴 변 길이. 기본 파이프라인은 960.

    Returns:
        tuple: (축소본, 배율). 예: (1280, 960, 3)과 960 → ((960, 720, 3), 0.75).
        축소하지 않으면 원본의 복사본과 1.0을 돌려준다.
    """
    # image.shape는 (H, W, 3) 같은 튜플이다. [:2]는 앞의 두 값만 자른다(슬라이싱). 회색 (H, W)에도 동작한다.
    h, w = image.shape[:2]
    scale = min(1.0, work_size / max(h, w))  # 960 / max(1280, 960) = 0.75
    if scale == 1.0:
        # .copy()로 새 배열을 만든다. 이후 단계가 축소본에 그림을 그려도 원본이 바뀌지 않게 한다.
        return image.copy(), 1.0
    # OpenCV의 크기 인자는 (가로, 세로) 순서다. NumPy shape (세로, 가로)와 반대라 자주 틀린다.
    # INTER_AREA는 줄일 때 여러 픽셀을 평균해 계단 현상과 잡음을 줄이는 보간법이다.
    return cv2.resize(image, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA), scale


def preprocess(work, blur, clahe=False):
    """BGR → Grayscale → 가우시안 블러. 블러는 Canny가 잡음을 엣지로 착각하지 않게 한다.

    Args:
        work: 축소본 BGR (H, W, 3). 이미 회색 (H, W)이면 변환을 건너뛴다.
        blur: 홀수 커널 크기. 1이면 블러하지 않는다.
        clahe: True면 블러 전에 CLAHE로 지역 대비를 키운다(규칙 추가 실험 V4).

    Returns:
        tuple: (gray, blurred). 둘 다 (H, W) uint8 새 배열이다.
    """
    # "A if 조건 else B"는 조건에 따라 A나 B를 고르는 한 줄 조건식이다. ndim은 축의 개수(컬러 3, 회색 2).
    # (H, W, 3) → (H, W). 회색 = 0.299·R + 0.587·G + 0.114·B. 문서 경계는 대부분 밝기 차이라 색이 없어도 된다.
    gray = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY) if work.ndim == 3 else work
    if clahe:
        # 이미지를 8×8 칸으로 나눠 칸마다 히스토그램을 펴서 어두운 곳의 대비를 키운다. clipLimit은 과증폭 제한.
        gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    # (blur, blur)는 커널의 (가로, 세로) 크기. 마지막 0은 "sigma를 커널 크기에서 자동으로 정하라"는 뜻이다.
    # 블러를 하지 않을 때도 .copy()로 별도 배열을 만들어 gray와 blurred가 같은 메모리를 공유하지 않게 한다.
    blurred = cv2.GaussianBlur(gray, (blur, blur), 0) if blur > 1 else gray.copy()
    return gray, blurred


def auto_canny_thresholds(blurred, sigma=0.33):
    """밝기 중앙값 기준 임계값. 어두운 사진에서는 임계값도 함께 낮아진다.

    E01은 중앙값 73 → (48, 97). 기본값 (50, 150)과 달리 사진마다 값이 바뀐다.
    규칙 추가 실험(V3)에서만 쓴다.

    Args:
        blurred: 블러한 회색 이미지 (H, W).
        sigma: 중앙값에서 아래·위로 벌릴 비율.

    Returns:
        tuple: (low, high) 정수 임계값. 0~255 범위로 자른다.
    """
    median = float(np.median(blurred))  # 모든 픽셀을 한 줄로 세웠을 때 가운데 값
    return int(max(0, (1 - sigma) * median)), int(min(255, (1 + sigma) * median))


def detect_edges(blurred, low, high, close_kernel, color_source=None, blur=1):
    """Canny 엣지와, 작은 틈을 메운 닫힘 연산 결과.

    color_source를 주면 B·G·R 각 채널의 Canny 결과를 OR로 합친다.

    Canny는 밝기 기울기가 high 이상인 픽셀을 엣지로 확정하고, low~high 사이는 확정 엣지와 이어질 때만 남긴다.
    문서 경계가 몇 픽셀 끊기면 윤곽선이 닫히지 않으므로, 닫힘 연산(팽창 → 침식)으로 작은 틈을 메운다.
    E01에서 엣지 픽셀은 20,191개, 닫힘 연산 뒤에는 30,800개다(선이 조금 두꺼워진다).

    Args:
        blurred: 블러한 회색 이미지 (H, W).
        low: Canny 낮은 임계값.
        high: Canny 높은 임계값.
        close_kernel: 닫힘 연산 커널 크기. 0이면 하지 않는다.
        color_source: 채널별 엣지를 쓸 때의 BGR 축소본 (H, W, 3). 기본은 None.
        blur: color_source의 각 채널에 적용할 블러 크기.

    Returns:
        tuple: (edges, closed). 둘 다 (H, W) uint8, 값은 0 또는 255인 새 배열이다.
    """
    if color_source is not None:
        # np.zeros(shape, 자료형)은 0으로 채운 새 배열이다. 여기에 채널별 엣지를 OR로 쌓는다.
        edges = np.zeros(blurred.shape, np.uint8)
        # cv2.split은 (H, W, 3)을 (H, W) 세 장(B, G, R)으로 나눈다. for는 그 세 장을 하나씩 꺼낸다.
        for channel in cv2.split(color_source):
            ch = cv2.GaussianBlur(channel, (blur, blur), 0) if blur > 1 else channel
            # |=는 비트 OR 후 다시 저장. 0|255 = 255라서 어느 채널에서든 엣지면 엣지로 남는다. edges를 제자리에서 바꾼다.
            edges |= cv2.Canny(ch, low, high)
    else:
        edges = cv2.Canny(blurred, low, high)
    if close_kernel > 0:
        # 3×3 사각형 모양 커널. 닫힘 = 팽창(선을 두껍게)한 뒤 침식(다시 얇게). 폭 2px 정도의 틈이 메워진 채 남는다.
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (close_kernel, close_kernel))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    else:
        closed = edges.copy()
    return edges, closed


def find_document_quad(closed, params):
    """닫힌 윤곽선 중 조건을 만족하는 가장 큰 사각형을 찾는다.

    규칙:
      R4 면적: 화면의 min_area_ratio 이상, max_area_ratio 이하
      R5 꼭짓점: approxPolyDP로 근사한 다각형의 꼭짓점이 정확히 4개
      R6 볼록: 네 점이 볼록 사각형
      R7 크기: 위 조건을 만족하는 후보 중 면적이 가장 큰 것

    E01 실행 결과: 윤곽선 374개 중 최소 면적 34,560(= 0.05 × 720 × 960)을 넘는 것은 3개다.
    가장 큰 두 개(289,978과 289,974)는 종이 경계선의 바깥쪽과 안쪽 테두리라 거의 같다.

    Args:
        closed: 닫힘 연산까지 마친 엣지 이미지 (H, W).
        params: ScanParams. min_area_ratio·max_area_ratio·approx_epsilon을 쓴다.

    Returns:
        tuple: (모든 윤곽선, 면적 통과 후보 목록, 선택된 사각형 또는 None, 실패 이유).
        선택된 사각형은 (4, 2) float64이고, 아직 꼭짓점 순서가 정해지지 않았다.
    """
    # findContours는 흰 픽셀 덩어리의 테두리를 점 목록으로 돌려준다. 두 번째 값(계층 정보)은 쓰지 않아 _에 버린다.
    # RETR_LIST: 안쪽·바깥쪽 구분 없이 모든 윤곽선. CHAIN_APPROX_SIMPLE: 직선 구간의 중간 점을 생략해 점 수를 줄인다.
    contours, _ = cv2.findContours(closed, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    image_area = closed.shape[0] * closed.shape[1]  # 960 × 720 = 691,200
    candidates = []
    best, best_area = None, 0.0  # 두 변수에 한 번에 값을 넣는다
    # sorted(목록, key=함수, reverse=True): 각 원소에 함수를 적용한 값(면적)이 큰 순서로 정렬한 새 리스트.
    # key에는 함수 자체를 넘긴다(cv2.contourArea(...)처럼 호출하지 않는다).
    for contour in sorted(contours, key=cv2.contourArea, reverse=True):
        area = cv2.contourArea(contour)
        if area < params.min_area_ratio * image_area:
            break  # 면적순 정렬이므로 이후는 모두 작다
        if area > params.max_area_ratio * image_area:
            continue  # continue는 이번 원소를 건너뛰고 다음 원소로 간다. 화면 테두리 전체를 잡은 윤곽선을 뺀다.
        # arcLength(점들, True): 닫힌 도형의 둘레. 허용 오차를 둘레에 비례시켜 문서 크기와 무관하게 만든다.
        perimeter = cv2.arcLength(contour, True)
        # approxPolyDP: 원래 선에서 epsilon 이내로 벗어나는 점을 지워 꼭짓점만 남긴다(Douglas–Peucker).
        # E01: 둘레 2,229 × 0.02 = 45px 이내의 굴곡은 무시 → 점 246개가 4개로 줄어든다. shape (4, 1, 2).
        approx = cv2.approxPolyDP(contour, params.approx_epsilon * perimeter, True)
        candidates.append(approx)  # append는 리스트 끝에 원소를 추가한다(리스트를 제자리에서 바꾼다)
        # and로 이어진 조건은 왼쪽부터 검사하다 거짓이 나오면 멈춘다. 꼭짓점이 4개가 아니면 is_convex를 부르지 않는다.
        if len(approx) == 4 and geometry.is_convex(approx) and area > best_area:
            # (4, 1, 2) int32 → (4, 2) float64. 가운데 길이 1인 축을 없애고, 나중에 소수 좌표로 나누기 위해 실수로 바꾼다.
            best, best_area = approx.reshape(4, 2).astype(np.float64), area
    if best is not None:
        return contours, candidates, best, ""
    if not candidates:  # 빈 리스트는 거짓으로 취급된다. "not 빈 리스트"는 True다.
        return contours, candidates, None, "면적 조건을 만족하는 닫힌 윤곽선 없음"
    # {식 for x in 목록}은 집합(set) 컴프리헨션. 중복이 사라진다. 예: 꼭짓점 수 [9, 7, 9] → {7, 9} → [7, 9].
    counts = sorted({len(c) for c in candidates})
    # f"...{값}..."은 값을 끼워 넣은 문자열(f-string)이다.
    return contours, candidates, None, f"큰 윤곽선은 있으나 볼록 사각형이 아님 (꼭짓점 수 {counts})"


def warp_document(image, quad, aspect_mode="zhang"):
    """정렬된 네 점을 직사각형으로 펴는 투시 변환. 결과 크기는 종횡비 방법에 따라 정한다.

    getPerspectiveTransform은 네 점 쌍으로 3×3 행렬 M을 구한다. warpPerspective는 결과 이미지의 각 픽셀이
    원본 어디에서 왔는지 M으로 거꾸로 계산해 그 색을 가져온다. 원리는 study/a3-1.html 7절에 있다.

    Args:
        image: 원본 해상도 BGR 이미지 (H, W, 3).
        quad: TL·TR·BR·BL 순서로 정렬한 원본 좌표 (4, 2).
        aspect_mode: "zhang"이면 원근을 보정한 종횡비, 그 밖에는 변 길이로 크기를 정한다.

    Returns:
        tuple: (warped, matrix). warped는 (height, width, 3) 새 이미지, matrix는 (3, 3) 변환 행렬.
        E01은 (883, 623, 3)이다.
    """
    if aspect_mode == "zhang":
        width, height = geometry.output_size_by_aspect(quad, image.shape)
    else:
        width, height = geometry.output_size_by_distance(quad)
    # 목적지 네 점: 결과 이미지의 네 모서리. 순서가 quad와 같아야(TL→TL, TR→TR, ...) 뒤집히지 않는다.
    # 픽셀 번호는 0부터 width-1까지라 오른쪽 끝은 width - 1이다. OpenCV는 float32 좌표를 요구한다.
    dst = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], np.float32)
    matrix = cv2.getPerspectiveTransform(quad.astype(np.float32), dst)
    # (width, height)도 (가로, 세로) 순서다. INTER_CUBIC은 주변 16픽셀로 보간해 글자 가장자리를 부드럽게 만든다.
    warped = cv2.warpPerspective(image, matrix, (width, height), flags=cv2.INTER_CUBIC)
    return warped, matrix


def auto_block_size(shape):
    """결과 이미지 짧은 변의 약 1/20. 글자보다 충분히 커야 글자 속이 비지 않는다.

    E01 결과 (883, 623): 623 / 20 = 31.15 → 31 (이미 홀수). 아주 작은 결과도 최소 11을 쓴다.

    Args:
        shape: 이미지의 shape 튜플. (H, W) 또는 (H, W, 3).

    Returns:
        int: 3 이상인 홀수 블록 크기.
    """
    size = max(11, int(min(shape[:2]) / 20))  # int()는 소수점 아래를 버린다
    return size + 1 - size % 2  # 짝수면 1을 더해 홀수로. adaptiveThreshold는 홀수 블록만 받는다.


def enhance(warped, block_size=0, c=10):
    """적응형 이진화: 픽셀마다 주변 가우시안 가중 평균 - C를 임계값으로 쓴다.

    전역 임계값 하나(예: Otsu)는 그림자 속 종이 전체를 검정으로 만든다. 주변 평균과 비교하면
    그림자 안에서도 "주변보다 어두운 글자"만 검정이 된다. C가 클수록 흰 쪽이 늘어난다.

    Args:
        warped: 투시 변환 결과 BGR (H, W, 3) 또는 회색 (H, W).
        block_size: 주변 범위(홀수). 3보다 작으면(기본 0) auto_block_size로 정한다.
        c: 주변 평균에서 빼는 값.

    Returns:
        numpy.ndarray: (H, W) uint8 새 배열. 값은 0(글자) 또는 255(바탕).
    """
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY) if warped.ndim == 3 else warped
    block = block_size if block_size >= 3 else auto_block_size(gray.shape)
    block += 1 - block % 2  # 트랙바에서 짝수를 골라도 홀수로 맞춘다
    # 픽셀 값 > (주변 block×block의 가우시안 가중 평균 − c)이면 255, 아니면 0.
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block, c)


def scan(image, params=None, warp=True):
    """이미지 한 장을 처리해 모든 단계의 결과를 돌려준다. 문서를 못 찾으면 quad가 None이다.

    warp=False면 꼭짓점까지만 찾는다 (파라미터 탐색처럼 검출 성공 여부만 필요할 때).

    Args:
        image: 원본 BGR 이미지 (H, W, 3). 함수 안에서 바꾸지 않는다.
        params: ScanParams. None이면 기본값을 쓴다.
        warp: False면 투시 변환과 이진화를 건너뛴다.

    Returns:
        ScanResult: 단계별 중간 결과를 담은 객체. 실패하면 reason에 이유가 있다.
    """
    # "A or B"는 A가 None처럼 거짓으로 취급되는 값이면 B를 쓴다. 기본값 객체를 만든 뒤 홀수·순서를 맞춘다.
    params = (params or ScanParams()).normalized()
    t = {}  # 빈 dict. t["edges"] = 0.005처럼 이름(키)에 값을 저장한다.
    t0 = time.perf_counter()  # 초 단위 시각. 두 시각의 차이가 걸린 시간이다.
    work, scale = resize_for_work(image, params.work_size)
    gray, blurred = preprocess(work, params.blur, params.clahe)
    t["preprocess"] = time.perf_counter() - t0
    t0 = time.perf_counter()
    low, high = params.canny_low, params.canny_high
    if params.auto_canny:
        low, high = auto_canny_thresholds(blurred)
    # 괄호 안이 모두 참일 때만 컬러 축소본을 넘긴다. 기본값(color_edges=False)에서는 None이다.
    color = work if (params.color_edges and work.ndim == 3) else None
    edges, closed = detect_edges(blurred, low, high, params.close_kernel, color, params.blur)
    t["edges"] = time.perf_counter() - t0
    t0 = time.perf_counter()
    contours, candidates, quad_work, reason = find_document_quad(closed, params)
    t["contours"] = time.perf_counter() - t0
    # 이름=값 형태(키워드 인자)로 넘기면 순서를 틀릴 걱정이 없다. 적지 않은 칸은 dataclass 기본값(None 등)이 된다.
    result = ScanResult(params=params, original=image, scale=scale, work=work, gray=gray, blurred=blurred,
                        edges=edges, closed=closed, contours=contours, candidates=candidates,
                        reason=reason, timings=t)
    if quad_work is None:
        return result  # 실패: quad 이후 칸은 None인 채로 돌려준다
    t0 = time.perf_counter()
    # 근사 다각형의 네 점은 순서가 정해져 있지 않다. TL·TR·BR·BL로 정렬해야 dst와 짝이 맞는다(geometry.py).
    result.quad_work = geometry.order_points(quad_work)
    # (4, 2) / 0.75: 배열을 숫자로 나누면 모든 원소가 나뉜 새 배열이 된다(브로드캐스팅). 축소본 → 원본 좌표.
    # 예: 축소본 TL (139, 132) → 원본 (185.3, 176.0). 정답 (185.15, 175.76)과 0.3px 차이다.
    result.quad = result.quad_work / scale
    aspect, focal, method = geometry.estimate_aspect_ratio(result.quad, image.shape)
    result.aspect = {"estimated": aspect, "focal_px": focal, "method": method}
    if not warp:
        return result
    # 함수가 두 값을 돌려주는데 하나만 필요하면 나머지를 _에 받아 버린다.
    # 축소본이 아니라 원본(image)을 변환해 글자 해상도를 잃지 않는다.
    result.warped, _ = warp_document(image, result.quad, params.aspect)
    result.scanned = enhance(result.warped, params.block_size, params.thresh_c)
    t["warp_enhance"] = time.perf_counter() - t0
    return result


# ───────────────────────── 시각화 ─────────────────────────

# 튜플 (a, b, c)는 바꿀 수 없는 리스트다. 대문자 이름은 "고정값(상수)"이라는 관례다.
CORNER_NAMES = ("TL", "TR", "BR", "BL")


def draw_contours(result, show_candidates=True):
    """축소본 위에 후보 윤곽선(초록)과 선택된 사각형(빨강), 꼭짓점 순서를 그린다.

    OpenCV 색은 (B, G, R) 순서다. (0, 0, 255)가 빨강, (0, 200, 0)이 초록이다.

    Args:
        result: scan()이 돌려준 ScanResult.
        show_candidates: False면 후보 윤곽선을 그리지 않는다(웹캠 화면용).

    Returns:
        numpy.ndarray: 그림을 그린 축소본 복사본 (H, W, 3). result.work는 바뀌지 않는다.
    """
    # cv2 그리기 함수는 넘긴 배열을 제자리에서 바꾼다. 그래서 먼저 복사본을 만든다.
    canvas = result.work.copy()
    if show_candidates and result.candidates:
        # -1은 "목록의 모든 윤곽선", 2는 선 두께, LINE_AA는 계단 없는 부드러운 선이다.
        cv2.drawContours(canvas, result.candidates, -1, (0, 200, 0), 2, cv2.LINE_AA)
    if result.quad_work is not None:
        # 그리기 함수는 정수 픽셀 좌표가 필요하다. 반올림 → int32. (4, 2) shape는 그대로다.
        q = result.quad_work.round().astype(np.int32)
        cv2.polylines(canvas, [q], True, (0, 0, 255), 3, cv2.LINE_AA)
        # zip(A, B)는 두 목록에서 같은 위치 원소를 짝지어 꺼낸다: ("TL", q[0]), ("TR", q[1]), ...
        # (x, y)처럼 괄호로 받으면 q[0] = [139, 132]를 x=139, y=132로 다시 나눠 담는다.
        for name, (x, y) in zip(CORNER_NAMES, q):
            cv2.circle(canvas, (int(x), int(y)), 8, (0, 0, 255), -1, cv2.LINE_AA)  # 두께 -1은 속을 채운 원
            cv2.putText(canvas, name, (int(x) + 10, int(y) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2,
                        cv2.LINE_AA)
    else:
        cv2.putText(canvas, "NOT FOUND", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 255), 3, cv2.LINE_AA)
    return canvas


def stage_images(result):
    """단계별 윈도우에 띄울 이미지 5장 (모두 BGR).

    회색 (H, W) 이미지는 컬러 (H, W, 3)로 바꿔서, 5장을 같은 방식으로 표시·저장할 수 있게 한다.

    Args:
        result: scan()이 돌려준 ScanResult.

    Returns:
        dict: {"1 Original": 이미지, ..., "5 Result": 이미지}. 키가 창 이름이 된다.
    """
    # lambda 인자: 식 은 이름 없는 한 줄 함수다. to_bgr(g)를 부르면 cvtColor(g, GRAY2BGR)를 돌려준다.
    to_bgr = lambda g: cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)  # noqa: E731
    if result.found:
        final = to_bgr(result.scanned)
    else:
        # full_like(배열, 40): 같은 shape·자료형으로 모든 값이 40인 새 배열. 어두운 회색 화면이 된다.
        final = np.full_like(result.work, 40)
        cv2.putText(final, "NOT FOUND", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 255), 3, cv2.LINE_AA)
        # putText는 한글을 그리지 못한다. 문자열을 ASCII로 바꾸며 한글을 버린다. 다 사라지면 or 뒤의 문구를 쓴다.
        cv2.putText(final, result.reason[:60].encode("ascii", "ignore").decode() or "see console", (20, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
    return {
        "1 Original": result.work,
        "2 Preprocessed": to_bgr(result.blurred),
        "3 Edges": to_bgr(result.edges),
        "4 Contours": draw_contours(result),
        "5 Result": final,
    }
