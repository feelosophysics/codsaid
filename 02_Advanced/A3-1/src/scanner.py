"""문서 스캐너 파이프라인: 전처리 → 엣지 → 윤곽선 → 꼭짓점 정렬 → 투시 변환 → 적응형 이진화.

검출은 긴 변이 `work_size`인 축소본에서 한다. 사진 해상도가 달라도 블러 커널·면적 기준이 같은 의미를 갖게 하려는 것이다.
찾은 꼭짓점은 원본 좌표로 되돌려 원본 해상도에서 변환한다.
"""
import time
from dataclasses import asdict, dataclass, field, replace

import cv2
import numpy as np

from . import geometry


@dataclass(frozen=True)
class ScanParams:
    """트랙바·명령줄로 바꾸는 값과 고정 규칙의 기준값."""
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
        """커널 크기는 홀수로, 임계값은 low ≤ high로 맞춘다."""
        blur = max(1, int(self.blur))
        blur += 1 - blur % 2
        low, high = sorted((int(self.canny_low), int(self.canny_high)))
        close = max(0, int(self.close_kernel))
        return replace(self, blur=blur, canny_low=low, canny_high=high, close_kernel=close)

    def to_dict(self):
        return asdict(self)


@dataclass
class ScanResult:
    """각 단계의 중간 결과. 시각화·평가·보고서가 모두 이 객체를 쓴다."""
    params: ScanParams
    original: np.ndarray
    scale: float  # 원본 → 축소본 배율
    work: np.ndarray
    gray: np.ndarray
    blurred: np.ndarray
    edges: np.ndarray
    closed: np.ndarray
    contours: list
    candidates: list = field(default_factory=list)  # 면적 조건을 통과한 윤곽선의 근사 다각형
    quad_work: np.ndarray = None  # 축소본 좌표, TL·TR·BR·BL
    quad: np.ndarray = None  # 원본 좌표, TL·TR·BR·BL
    reason: str = ""  # 실패 이유
    warped: np.ndarray = None
    scanned: np.ndarray = None
    aspect: dict = None
    timings: dict = field(default_factory=dict)

    @property
    def found(self):
        return self.quad is not None


def resize_for_work(image, work_size):
    """긴 변이 work_size가 되도록 줄인다. 이미 작으면 그대로 둔다."""
    h, w = image.shape[:2]
    scale = min(1.0, work_size / max(h, w))
    if scale == 1.0:
        return image.copy(), 1.0
    return cv2.resize(image, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA), scale


def preprocess(work, blur, clahe=False):
    """BGR → Grayscale → 가우시안 블러. 블러는 Canny가 잡음을 엣지로 착각하지 않게 한다."""
    gray = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY) if work.ndim == 3 else work
    if clahe:
        gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    blurred = cv2.GaussianBlur(gray, (blur, blur), 0) if blur > 1 else gray.copy()
    return gray, blurred


def auto_canny_thresholds(blurred, sigma=0.33):
    """밝기 중앙값 기준 임계값. 어두운 사진에서는 임계값도 함께 낮아진다."""
    median = float(np.median(blurred))
    return int(max(0, (1 - sigma) * median)), int(min(255, (1 + sigma) * median))


def detect_edges(blurred, low, high, close_kernel, color_source=None, blur=1):
    """Canny 엣지와, 작은 틈을 메운 닫힘 연산 결과.

    color_source를 주면 B·G·R 각 채널의 Canny 결과를 OR로 합친다.
    """
    if color_source is not None:
        edges = np.zeros(blurred.shape, np.uint8)
        for channel in cv2.split(color_source):
            ch = cv2.GaussianBlur(channel, (blur, blur), 0) if blur > 1 else channel
            edges |= cv2.Canny(ch, low, high)
    else:
        edges = cv2.Canny(blurred, low, high)
    if close_kernel > 0:
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
    반환: (모든 윤곽선, 면적 통과 후보 목록, 선택된 사각형 또는 None, 실패 이유)
    """
    contours, _ = cv2.findContours(closed, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    image_area = closed.shape[0] * closed.shape[1]
    candidates = []
    best, best_area = None, 0.0
    for contour in sorted(contours, key=cv2.contourArea, reverse=True):
        area = cv2.contourArea(contour)
        if area < params.min_area_ratio * image_area:
            break  # 면적순 정렬이므로 이후는 모두 작다
        if area > params.max_area_ratio * image_area:
            continue
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, params.approx_epsilon * perimeter, True)
        candidates.append(approx)
        if len(approx) == 4 and geometry.is_convex(approx) and area > best_area:
            best, best_area = approx.reshape(4, 2).astype(np.float64), area
    if best is not None:
        return contours, candidates, best, ""
    if not candidates:
        return contours, candidates, None, "면적 조건을 만족하는 닫힌 윤곽선 없음"
    counts = sorted({len(c) for c in candidates})
    return contours, candidates, None, f"큰 윤곽선은 있으나 볼록 사각형이 아님 (꼭짓점 수 {counts})"


def warp_document(image, quad, aspect_mode="zhang"):
    """정렬된 네 점을 직사각형으로 펴는 투시 변환. 결과 크기는 종횡비 방법에 따라 정한다."""
    if aspect_mode == "zhang":
        width, height = geometry.output_size_by_aspect(quad, image.shape)
    else:
        width, height = geometry.output_size_by_distance(quad)
    dst = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], np.float32)
    matrix = cv2.getPerspectiveTransform(quad.astype(np.float32), dst)
    warped = cv2.warpPerspective(image, matrix, (width, height), flags=cv2.INTER_CUBIC)
    return warped, matrix


def auto_block_size(shape):
    """결과 이미지 짧은 변의 약 1/20. 글자보다 충분히 커야 글자 속이 비지 않는다."""
    size = max(11, int(min(shape[:2]) / 20))
    return size + 1 - size % 2


def enhance(warped, block_size=0, c=10):
    """적응형 이진화: 픽셀마다 주변 가우시안 가중 평균 - C를 임계값으로 쓴다."""
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY) if warped.ndim == 3 else warped
    block = block_size if block_size >= 3 else auto_block_size(gray.shape)
    block += 1 - block % 2
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block, c)


def scan(image, params=None, warp=True):
    """이미지 한 장을 처리해 모든 단계의 결과를 돌려준다. 문서를 못 찾으면 quad가 None이다.

    warp=False면 꼭짓점까지만 찾는다 (파라미터 탐색처럼 검출 성공 여부만 필요할 때).
    """
    params = (params or ScanParams()).normalized()
    t = {}
    t0 = time.perf_counter()
    work, scale = resize_for_work(image, params.work_size)
    gray, blurred = preprocess(work, params.blur, params.clahe)
    t["preprocess"] = time.perf_counter() - t0
    t0 = time.perf_counter()
    low, high = params.canny_low, params.canny_high
    if params.auto_canny:
        low, high = auto_canny_thresholds(blurred)
    color = work if (params.color_edges and work.ndim == 3) else None
    edges, closed = detect_edges(blurred, low, high, params.close_kernel, color, params.blur)
    t["edges"] = time.perf_counter() - t0
    t0 = time.perf_counter()
    contours, candidates, quad_work, reason = find_document_quad(closed, params)
    t["contours"] = time.perf_counter() - t0
    result = ScanResult(params=params, original=image, scale=scale, work=work, gray=gray, blurred=blurred,
                        edges=edges, closed=closed, contours=contours, candidates=candidates,
                        reason=reason, timings=t)
    if quad_work is None:
        return result
    t0 = time.perf_counter()
    result.quad_work = geometry.order_points(quad_work)
    result.quad = result.quad_work / scale
    aspect, focal, method = geometry.estimate_aspect_ratio(result.quad, image.shape)
    result.aspect = {"estimated": aspect, "focal_px": focal, "method": method}
    if not warp:
        return result
    result.warped, _ = warp_document(image, result.quad, params.aspect)
    result.scanned = enhance(result.warped, params.block_size, params.thresh_c)
    t["warp_enhance"] = time.perf_counter() - t0
    return result


# ───────────────────────── 시각화 ─────────────────────────

CORNER_NAMES = ("TL", "TR", "BR", "BL")


def draw_contours(result, show_candidates=True):
    """축소본 위에 후보 윤곽선(초록)과 선택된 사각형(빨강), 꼭짓점 순서를 그린다."""
    canvas = result.work.copy()
    if show_candidates and result.candidates:
        cv2.drawContours(canvas, result.candidates, -1, (0, 200, 0), 2, cv2.LINE_AA)
    if result.quad_work is not None:
        q = result.quad_work.round().astype(np.int32)
        cv2.polylines(canvas, [q], True, (0, 0, 255), 3, cv2.LINE_AA)
        for name, (x, y) in zip(CORNER_NAMES, q):
            cv2.circle(canvas, (int(x), int(y)), 8, (0, 0, 255), -1, cv2.LINE_AA)
            cv2.putText(canvas, name, (int(x) + 10, int(y) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2,
                        cv2.LINE_AA)
    else:
        cv2.putText(canvas, "NOT FOUND", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 255), 3, cv2.LINE_AA)
    return canvas


def stage_images(result):
    """단계별 윈도우에 띄울 이미지 5장 (모두 BGR)."""
    to_bgr = lambda g: cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)  # noqa: E731
    if result.found:
        final = to_bgr(result.scanned)
    else:
        final = np.full_like(result.work, 40)
        cv2.putText(final, "NOT FOUND", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 255), 3, cv2.LINE_AA)
        cv2.putText(final, result.reason[:60].encode("ascii", "ignore").decode() or "see console", (20, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
    return {
        "1 Original": result.work,
        "2 Preprocessed": to_bgr(result.blurred),
        "3 Edges": to_bgr(result.edges),
        "4 Contours": draw_contours(result),
        "5 Result": final,
    }
