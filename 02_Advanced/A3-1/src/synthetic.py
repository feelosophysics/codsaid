"""휴대폰 촬영을 흉내 낸 합성 문서 사진 20장과 정답 꼭짓점을 만든다.

촬영할 사진이 없을 때 파이프라인 전체를 검증하기 위한 대체 데이터다. 실제 사진과 다른 점은 README와 보고서에 적는다.

장면 구성 순서:
1. 종이 내용(글자·표·바코드)을 mm 단위 크기로 그린다. 구김은 이 단계에서 변위장과 명암 면으로 넣는다.
2. 3차원 카메라 모델로 종이 평면을 기울이고 돌려 투영한다. 투영된 네 모서리가 정답 꼭짓점이다.
3. 배경(단색·나뭇결·체크무늬·잡동사니) 위에 합성하고 가림 물체를 올린다.
4. 조명장(그라데이션·그림자·저조도)을 곱하고 반사광을 더한 뒤, 초점 흐림·센서 잡음·JPEG 압축을 적용한다.

실행:  python -m src.synthetic            # data/synthetic/에 이미지 20장과 labels.json 저장

배열 흐름 (E01, A4):
    종이 내용  (1188, 840, 3)  = 297mm × 4px, 210mm × 4px
    투영       종이 네 모서리 (4, 2) mm → 카메라 3차원 (4, 3) → 화면 (4, 2) px = 정답 꼭짓점
    합성       배경 (1280, 960, 3) float32 × (1 − α) + 펴진 종이 × α
    마무리     × 조명 (1280, 960) + 반사광 → 흐림 → 잡음 → 0~255 uint8 → JPEG
스캐너(scanner.py)는 이 과정을 거꾸로 푼다. 같은 getPerspectiveTransform을 반대 방향으로 쓰는 셈이다.
"""
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from .image_io import imwrite

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "synthetic"
IMAGE_W, IMAGE_H = 960, 1280  # 세로 사진 (3:4)
FOCAL_PX = 1000.0  # 세로 1280px 기준 화각 약 65°, 휴대폰 기본 카메라 수준
PX_PER_MM = 4.0
SEED = 20261013

PAPER_SIZES_MM = {  # (가로, 세로)
    "a4": (210, 297),
    "letter": (216, 279),
    "a5_form": (148, 210),
    "receipt": (80, 210),
    "card": (90, 50),
}

CONDITION_NAMES = {
    "easy": "단순 배경 + 정면",
    "shadow": "그림자 있음",
    "tilt": "45도 이상 기울어짐",
    "complex": "복잡한 배경",
}

# 괄호 안에 문자열을 나란히 쓰면 하나로 이어진다. split()은 공백으로 잘라 단어 리스트를 만든다.
WORDS = ("data image scan paper report total amount date order item price contour edge vision camera "
         "matrix filter pixel light shadow model sample result value table page note invoice check "
         "summary quality office store receipt card phone email address number").split()


@dataclass
class Case:
    """한 장의 촬영 조건. 각도는 도(degree) 단위다.

    Case("E01", "easy", "a4", "plain_dark", 8, 2, 3, 0.42, note=...)처럼 앞의 값은 순서대로,
    뒤의 값은 이름=값으로 넘긴다.

    Attributes:
        id: 이미지 이름. 첫 글자가 조건(E·S·T·C)이다.
        condition: "easy", "shadow", "tilt", "complex" 중 하나.
        paper: PAPER_SIZES_MM의 키.
        background: background()의 kind.
        pitch: 카메라가 종이를 내려다보는 기울기 (x축 회전).
        yaw: 좌우 기울기 (y축 회전).
        roll: 종이의 평면 내 회전 (z축 회전).
        coverage: 투영된 종이가 화면에서 차지하는 비율.
        offset: 화면 중심에서의 이동 (이미지 크기 비율).
        lighting: lighting_field()의 kind.
        lighting_note: labels.json에 적을 조명 설명.
        background_level: 배경 복잡도 설명("낮음"/"높음").
        extras: 그림자·반사·가림·구김 같은 추가 조건.
        note: 사람이 읽을 한 줄 설명.
    """
    id: str
    condition: str
    paper: str
    background: str
    pitch: float  # 카메라가 종이를 내려다보는 기울기 (x축 회전)
    yaw: float  # 좌우 기울기 (y축 회전)
    roll: float  # 종이의 평면 내 회전 (z축 회전)
    coverage: float  # 투영된 종이가 화면에서 차지하는 비율
    offset: tuple = (0.0, 0.0)  # 화면 중심에서의 이동 (이미지 크기 비율)
    lighting: str = "uniform"
    lighting_note: str = "균일한 실내 조명"
    background_level: str = "낮음"
    extras: dict = field(default_factory=dict)
    note: str = ""


CASES = [
    # 쉬운 케이스: 단순 배경, 거의 정면, 균일 조명
    Case("E01", "easy", "a4", "plain_dark", 8, 2, 3, 0.42, note="회색 책상 위 A4 보고서"),
    Case("E02", "easy", "receipt", "plain_blue", 6, -3, -6, 0.22, note="파란 매트 위 영수증"),
    Case("E03", "easy", "card", "plain_brown", 10, 4, 8, 0.18, note="갈색 책상 위 명함"),
    Case("E04", "easy", "a5_form", "plain_gray", 12, -2, -2, 0.36, note="회색 책상 위 A5 신청서"),
    Case("E05", "easy", "letter", "plain_green", 6, 3, 12, 0.40, note="초록 커팅 매트 위 레터 용지"),
    # 그림자·조명
    Case("S01", "shadow", "a4", "plain_dark", 14, 5, -4, 0.40, lighting="gradient",
         lighting_note="창가 측광, 한쪽이 45%까지 어두움", extras={"shadow": "gradient"},
         note="밝기 그라데이션"),
    Case("S02", "shadow", "receipt", "plain_blue", 12, -6, 7, 0.24, lighting="soft_shadow",
         lighting_note="손·휴대폰의 부드러운 그림자", extras={"shadow": "soft"},
         note="경계가 흐린 그림자가 영수증 절반을 덮음"),
    Case("S03", "shadow", "a4", "plain_gray", 16, -4, 5, 0.42, lighting="hard_shadow",
         lighting_note="천장 조명 아래 강한 그림자, 경계 선명", extras={"shadow": "hard"},
         note="선명한 그림자 경계가 문서를 가로지름"),
    Case("S04", "shadow", "a5_form", "plain_brown", 10, 6, -8, 0.36, lighting="low_light",
         lighting_note="어두운 방 (노출 30%) + 부드러운 그림자, 잡음 큼", extras={"shadow": "soft", "low_light": True},
         note="저조도"),
    Case("S05", "shadow", "card", "plain_dark", 15, -5, 10, 0.20, lighting="shadow_glare",
         lighting_note="그림자 + 모서리 근처 빛 반사(포화)", extras={"shadow": "soft", "glare": True},
         note="코팅 명함의 빛 반사"),
    # 45도 이상 기울어짐
    Case("T01", "tilt", "a4", "plain_dark", 50, 0, 2, 0.30, note="세로 방향으로 50° 기울여 촬영"),
    Case("T02", "tilt", "a4", "plain_gray", 55, 12, 25, 0.30, note="55° 기울기 + 평면 회전 25°"),
    Case("T03", "tilt", "receipt", "plain_blue", 58, -8, 40, 0.16, note="58° 기울기 + 평면 회전 40°"),
    Case("T04", "tilt", "card", "plain_brown", 48, 25, 45, 0.16, note="48° 기울기, 좌우 25°, 평면 회전 45°"),
    Case("T05", "tilt", "letter", "plain_green", 65, -6, -12, 0.26, note="65° 기울기 (먼 변이 크게 줄어듦)"),
    # 복잡한 배경
    Case("C01", "complex", "a4", "wood", 18, 6, -7, 0.40, background_level="높음", note="나뭇결 책상"),
    Case("C02", "complex", "receipt", "plaid", 15, -5, 9, 0.24, background_level="높음", note="체크무늬 식탁보"),
    Case("C03", "complex", "a4", "white_clutter", 15, 4, 4, 0.38, background_level="높음",
         note="흰 책상 위 다른 종이와 겹침 (배경 대비 낮음)"),
    Case("C04", "complex", "a5_form", "desk_clutter", 14, -6, -10, 0.34, background_level="높음",
         extras={"occlusion": "hand"}, note="잡동사니 책상, 손가락이 모서리를 가림"),
    Case("C05", "complex", "a4", "wood", 16, -4, 6, 0.40, background_level="높음",
         extras={"crumple": True}, note="구겨진 A4, 나뭇결 책상"),
]


# ───────────────────────── 기본 도구 ─────────────────────────

def smooth_noise(rng, h, w, scale):
    """저해상도 정규 잡음을 키워 부드러운 잡음장을 만든다. 평균 0, 표준편차 1.

    작은 격자(예: 1280 / 200 + 2 = 8칸)의 난수를 큰 이미지로 늘리면, 이웃 픽셀끼리 값이 비슷한
    완만한 얼룩이 된다. 책상 표면의 고르지 않은 밝기나 조명 얼룩에 쓴다.

    Args:
        rng: NumPy 난수 생성기.
        h: 높이(픽셀).
        w: 너비(픽셀).
        scale: 얼룩 하나의 대략적인 크기(픽셀). 클수록 완만하다.

    Returns:
        numpy.ndarray: (h, w) float32. 평균 0, 표준편차 1로 맞춘 새 배열.
    """
    gh, gw = max(2, int(h / scale) + 2), max(2, int(w / scale) + 2)
    small = rng.standard_normal((gh, gw)).astype(np.float32)
    big = cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC)
    return (big - big.mean()) / (big.std() + 1e-6)  # +1e-6은 표준편차가 0일 때 0으로 나누는 것을 막는다


def rotation(pitch, yaw, roll):
    """카메라 좌표계에서 종이 평면의 회전 행렬 Rx(pitch)·Ry(yaw)·Rz(roll).

    설명용 예: rotation(0, 0, 90)은 [[0, −1, 0], [1, 0, 0], [0, 0, 1]]로 x축 방향을 y축 방향으로 돌린다.

    Args:
        pitch: x축 회전 각도(도).
        yaw: y축 회전 각도(도).
        roll: z축 회전 각도(도).

    Returns:
        numpy.ndarray: (3, 3) 회전 행렬. 세 행렬을 곱한 순서(rx @ ry @ rz)대로 적용된다.
    """
    ax, ay, az = np.radians([pitch, yaw, roll])  # 도 → 라디안. math.cos는 라디안을 받는다
    rx = np.array([[1, 0, 0], [0, math.cos(ax), -math.sin(ax)], [0, math.sin(ax), math.cos(ax)]])
    ry = np.array([[math.cos(ay), 0, math.sin(ay)], [0, 1, 0], [-math.sin(ay), 0, math.cos(ay)]])
    rz = np.array([[math.cos(az), -math.sin(az), 0], [math.sin(az), math.cos(az), 0], [0, 0, 1]])
    return rx @ ry @ rz


def project(points_mm, rot, distance, offset):
    """종이 평면의 3차원 점(mm)을 핀홀 카메라로 투영한다. 주점은 이미지 중심이다.

    핀홀 모델: 화면 좌표 u = f · X / Z + 중심. 멀수록(Z가 클수록) 작게 찍힌다. 이것이 원근이다.
    설명용 예: 회전 없이 거리 500mm에서 종이 위 (105, 0)mm는 105 / 500 × 1000 + 480 = 690px에 찍힌다.

    Args:
        points_mm: (N, 2) 종이 평면 위 점. 종이 중심이 원점이다.
        rot: (3, 3) 회전 행렬.
        distance: 카메라에서 종이 중심까지 거리(mm).
        offset: 화면 중심에서의 이동 (가로 비율, 세로 비율).

    Returns:
        numpy.ndarray: (N, 2) 화면 픽셀 좌표 (x, y).
    """
    # column_stack: (N, 2)에 0으로 된 열을 붙여 (N, 3). 종이는 평면이라 z = 0이다.
    pts = np.column_stack([points_mm, np.zeros(len(points_mm))])
    # 행마다 점 하나이므로 R @ p 대신 pts @ R.T로 한꺼번에 돌린다. 그 뒤 카메라 앞 distance만큼 민다.
    cam = pts @ rot.T + np.array([0.0, 0.0, distance])
    # cam[:, 2:3]은 (N, 1)로 자른 Z. (N, 2) / (N, 1)은 각 행을 그 행의 Z로 나눈다(브로드캐스팅).
    uv = cam[:, :2] / cam[:, 2:3] * FOCAL_PX
    return uv + np.array([IMAGE_W / 2 + offset[0] * IMAGE_W, IMAGE_H / 2 + offset[1] * IMAGE_H])


def place_document(case, size_mm):
    """원하는 화면 비율(coverage)이 되도록 카메라 거리를 이분 탐색하고 투영 꼭짓점을 돌려준다.

    강하게 기울이면 가까운 변이 커져 화면을 벗어날 수 있다. 그때는 비율을 10%씩 줄인다.

    이분 탐색: 거리 범위 [lo, hi]의 가운데를 시험해 면적이 목표보다 크면(너무 가까우면) lo를 올리고,
    작으면 hi를 내린다. 80번 반복하면 범위가 2⁸⁰분의 1로 줄어 거리가 사실상 정확해진다.
    E01 실행 결과: 거리 347.1mm, 실제 기울기 8.2°.

    Args:
        case: Case 하나.
        size_mm: (가로, 세로) 종이 크기(mm).

    Returns:
        tuple: (quad, distance, tilt). quad는 (4, 2) 정답 꼭짓점(TL, TR, BR, BL), tilt는 종이 법선과 시선의 각도(도).

    Raises:
        ValueError: 30번 줄여도 종이가 화면 안에 들어가지 않는 경우.
    """
    w, h = size_mm
    corners_mm = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]])
    rot = rotation(case.pitch, case.yaw, case.roll)
    margin = 16
    coverage = case.coverage
    for _ in range(30):
        target = coverage * IMAGE_W * IMAGE_H
        lo, hi = 50.0, 20000.0
        for _ in range(80):
            mid = (lo + hi) / 2
            quad = project(corners_mm, rot, mid, case.offset)
            x, y = quad[:, 0], quad[:, 1]
            area = 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))  # 신발끈 공식(geometry.polygon_area와 같다)
            lo, hi = (mid, hi) if area > target else (lo, mid)
        distance = hi
        quad = project(corners_mm, rot, distance, case.offset)
        inside = quad[:, 0].min() >= margin and quad[:, 1].min() >= margin and             quad[:, 0].max() <= IMAGE_W - margin and quad[:, 1].max() <= IMAGE_H - margin
        if inside:
            break
        coverage *= 0.9
    # for ... else: 반복문이 break 없이 끝까지 돌았을 때만 else가 실행된다. 끝내 화면에 못 넣은 경우다.
    else:
        raise ValueError(f"{case.id}: 문서를 화면 안에 넣을 수 없다")
    normal = rot @ np.array([0.0, 0.0, 1.0])  # 종이 평면에 수직인 방향을 돌린 것
    tilt = math.degrees(math.acos(abs(normal[2])))  # 법선과 카메라 시선(z축) 사이 각도
    return quad, distance, tilt


# ───────────────────────── 종이 내용 ─────────────────────────

def random_line(rng, n_words):
    """WORDS에서 단어를 무작위로 골라 한 줄을 만든다.

    Args:
        rng: NumPy 난수 생성기.
        n_words: 단어 수.

    Returns:
        str: 공백으로 이은 문장. 예: "pixel order shadow".
    """
    # " ".join(목록)은 목록의 문자열 사이에 공백을 넣어 하나로 잇는다.
    return " ".join(rng.choice(WORDS, size=n_words))


def paper_base(rng, w, h, tint=(246, 246, 242)):
    """약간 미색인 종이 바탕과 섬유 질감. OpenCV 5의 putText는 uint8에만 그리므로 uint8로 돌려준다.

    Args:
        rng: NumPy 난수 생성기.
        w: 종이 너비(픽셀).
        h: 종이 높이(픽셀).
        tint: 바탕색 (B, G, R).

    Returns:
        numpy.ndarray: (h, w, 3) uint8 새 이미지.
    """
    base = np.empty((h, w, 3), np.float32)
    base[:] = tint  # [:]에 값을 넣으면 모든 픽셀이 같은 색이 된다. (3,)이 (h, w, 3) 전체로 퍼진다
    # [..., None]은 (h, w)에 마지막 축을 추가해 (h, w, 1). 세 채널에 같은 잡음을 더해 색이 변하지 않고 밝기만 흔들린다.
    base += smooth_noise(rng, h, w, 40)[..., None] * 2.0 + rng.normal(0, 1.5, (h, w, 1))
    return np.clip(base, 0, 255).astype(np.uint8)


def put(img, text, org, scale, thick=1, color=(40, 40, 40), font=cv2.FONT_HERSHEY_SIMPLEX):
    """cv2.putText를 짧게 부르는 보조 함수. 좌표를 정수로 바꿔 준다.

    Args:
        img: 글자를 그릴 이미지. 제자리에서 바뀐다.
        text: 쓸 글자(영문).
        org: 글자 왼쪽 아래 기준점 (x, y).
        scale: 글자 크기 배율.
        thick: 선 두께.
        color: (B, G, R) 색.
        font: OpenCV 글꼴.
    """
    cv2.putText(img, text, (int(org[0]), int(org[1])), font, scale, color, thick, cv2.LINE_AA)


def draw_report(rng, w, h):
    """A4·레터: 제목, 문단, 표, 막대그래프.

    Args:
        rng: NumPy 난수 생성기.
        w: 종이 너비(픽셀). A4는 840.
        h: 종이 높이(픽셀). A4는 1188.

    Returns:
        numpy.ndarray: (h, w, 3) uint8 종이 이미지.
    """
    img = paper_base(rng, w, h)
    m = int(w * 0.09)  # 여백
    put(img, "QUARTERLY " + random_line(rng, 1).upper() + " REPORT", (m, m + 30), 1.15, 2, (25, 25, 25))
    cv2.line(img, (m, m + 50), (w - m, m + 50), (60, 60, 60), 2)
    y = m + 95  # y는 다음 줄을 쓸 세로 위치. 줄을 쓸 때마다 아래로 내려간다
    for _ in range(6):
        put(img, random_line(rng, 7), (m, y), 0.62)
        y += 30
    y += 15
    rows, cols = 5, 4
    tw, th = w - 2 * m, 34
    for r in range(rows + 1):  # 가로선은 행 수 + 1개
        cv2.line(img, (m, y + r * th), (m + tw, y + r * th), (70, 70, 70), 1)
    for c in range(cols + 1):
        cv2.line(img, (m + c * tw // cols, y), (m + c * tw // cols, y + rows * th), (70, 70, 70), 1)
    for r in range(rows):
        for c in range(cols):
            # 첫 열은 단어, 나머지는 "123.45" 같은 숫자. {:02d}는 두 자리로 0을 채운다(5 → "05").
            text = random_line(rng, 1) if c == 0 else f"{rng.integers(10, 999)}.{rng.integers(0, 99):02d}"
            put(img, text, (m + c * tw // cols + 8, y + r * th + 23), 0.55)
    y += rows * th + 40
    bars = rng.uniform(0.2, 1.0, 6)
    bw = tw // 9
    for i, b in enumerate(bars):
        x0 = m + 20 + i * (bw + 25)
        cv2.rectangle(img, (x0, y + 160 - int(150 * b)), (x0 + bw, y + 160), (170, 110, 60), -1)
    cv2.line(img, (m, y + 162), (m + tw, y + 162), (60, 60, 60), 2)
    y += 210
    while y < h - m:  # 종이 아래 여백에 닿을 때까지 문단을 채운다
        put(img, random_line(rng, 7), (m, y), 0.62)
        y += 30
    return img


def draw_receipt(rng, w, h):
    """감열지 영수증: 가게 이름, 품목·가격, 점선, 바코드.

    Args:
        rng: NumPy 난수 생성기.
        w: 너비(픽셀).
        h: 높이(픽셀).

    Returns:
        numpy.ndarray: (h, w, 3) uint8 영수증 이미지.
    """
    img = paper_base(rng, w, h, tint=(240, 242, 244))
    m = 18
    put(img, "CODYSSEY MART", (m + 20, 55), 0.85, 2, (30, 30, 30))
    put(img, f"2026-10-{rng.integers(1, 28):02d}  {rng.integers(8, 22)}:{rng.integers(0, 59):02d}", (m, 90), 0.5)
    y = 120
    for _ in range(int((h - 330) / 30)):
        put(img, random_line(rng, 1)[:12], (m, y), 0.52)  # [:12]는 앞 12글자만
        put(img, f"{rng.integers(1, 99) * 100:,}", (w - m - 80, y), 0.52)  # {:,}는 1,200처럼 천 단위 쉼표
        y += 30
    for x in range(m, w - m, 14):  # range(시작, 끝, 간격): 14px마다 짧은 선 = 점선
        cv2.line(img, (x, y), (x + 7, y), (80, 80, 80), 1)
    put(img, "TOTAL", (m, y + 40), 0.75, 2)
    put(img, f"{rng.integers(50, 300) * 100:,}", (w - m - 105, y + 40), 0.75, 2)
    bx, by = m + 10, h - 110
    x = bx
    while x < w - m - 10:  # 폭이 무작위인 막대를 60% 확률로 그려 바코드처럼 만든다
        bw = int(rng.integers(1, 5))
        if rng.random() < 0.6:
            cv2.rectangle(img, (x, by), (x + bw, by + 70), (25, 25, 25), -1)
        x += bw + int(rng.integers(1, 4))
    return img


def draw_card(rng, w, h):
    """명함: 색 로고, 이름, 직함, 연락처.

    Args:
        rng: NumPy 난수 생성기.
        w: 너비(픽셀).
        h: 높이(픽셀).

    Returns:
        numpy.ndarray: (h, w, 3) uint8 명함 이미지.
    """
    img = paper_base(rng, w, h, tint=(248, 248, 248))
    cv2.rectangle(img, (25, 25), (95, 95), (160, 90, 30), -1)
    cv2.circle(img, (60, 60), 22, (248, 248, 248), -1)
    put(img, "KIM CODY", (120, 75), 1.0, 2, (20, 20, 20))
    put(img, "Vision Engineer", (122, 105), 0.6, 1, (90, 90, 90))
    for i, line in enumerate(("+82 10-1234-5678", "cody@example.com", "Seoul, Korea")):
        put(img, line, (122, 140 + i * 25), 0.5)
    # 아래쪽 띠는 파란 줄무늬다. E03에서 이 띠가 갈색 책상과 회색 밝기가 비슷해(80 vs 97) 경계가 약해진다.
    cv2.rectangle(img, (0, h - 14), (w, h), (160, 90, 30), -1)
    return img


def draw_form(rng, w, h):
    """신청서: 입력 칸, 체크박스, 서명란.

    Args:
        rng: NumPy 난수 생성기.
        w: 너비(픽셀).
        h: 높이(픽셀).

    Returns:
        numpy.ndarray: (h, w, 3) uint8 신청서 이미지.
    """
    img = paper_base(rng, w, h)
    m = 40
    put(img, "APPLICATION FORM", (m, 70), 1.0, 2, (25, 25, 25))
    y = 120
    for _ in range(7):
        put(img, random_line(rng, 1).capitalize(), (m, y + 25), 0.6)  # capitalize는 첫 글자만 대문자
        cv2.rectangle(img, (m + 170, y), (w - m, y + 38), (90, 90, 90), 1)
        y += 56
    for i in range(4):
        cv2.rectangle(img, (m, y + i * 34), (m + 20, y + 20 + i * 34), (60, 60, 60), 2)
        if rng.random() < 0.5:  # 절반 확률로 체크 표시(선 두 개)
            cv2.line(img, (m + 4, y + 10 + i * 34), (m + 9, y + 17 + i * 34), (150, 60, 30), 2)
            cv2.line(img, (m + 9, y + 17 + i * 34), (m + 18, y + 2 + i * 34), (150, 60, 30), 2)
        put(img, random_line(rng, 4), (m + 32, y + 17 + i * 34), 0.55)
    y += 170
    while y < h - 140:
        put(img, random_line(rng, 6), (m, y), 0.55)
        y += 28
    cv2.line(img, (w - m - 220, h - 70), (w - m, h - 70), (60, 60, 60), 1)
    put(img, "Signature", (w - m - 220, h - 45), 0.5, 1, (90, 90, 90))
    return img


# 종이 종류 → 그리는 함수. DRAWERS[case.paper](rng, w, h)처럼 꺼내 부른다.
DRAWERS = {"a4": draw_report, "letter": draw_report, "a5_form": draw_form, "receipt": draw_receipt, "card": draw_card}


def crumple(rng, paper, corners_fixed=True):
    """구김: 접힌 선을 경계로 밝기가 다른 면을 만들고, 부드러운 변위장으로 윤곽을 흔든다.

    네 모서리 주변의 변위는 0으로 만들어 정답 꼭짓점이 그대로 유지되게 한다.

    C05에서 이 구김이 종이 테두리를 7~9각형으로 만들어 "꼭짓점 4개" 규칙(R5)을 깨뜨린다.

    Args:
        rng: NumPy 난수 생성기.
        paper: (h, w, 3) float32 종이 이미지.
        corners_fixed: True면 네 모서리 근처는 움직이지 않는다.

    Returns:
        tuple: (out, mask, pad). out은 테두리를 pad만큼 넓힌 구겨진 종이, mask는 종이 부분이 1인 (H, W) 알파.
    """
    h, w = paper.shape[:2]
    # mgrid[0:h, 0:w]는 (2, h, w): yy[r, c] = r, xx[r, c] = c. 모든 픽셀의 좌표를 배열로 한 번에 쓴다.
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    shade = np.ones((h, w), np.float32)
    for _ in range(7):  # 접힌 선 7개
        p = np.array([rng.uniform(0, w), rng.uniform(0, h)])
        a = rng.uniform(0, np.pi)
        nx, ny = -math.sin(a), math.cos(a)
        dist = (xx - p[0]) * nx + (yy - p[1]) * ny  # 각 픽셀에서 접힌 선까지의 부호 있는 거리 (h, w)
        shade *= 1 + rng.uniform(0.05, 0.13) * np.tanh(dist / 2.5) * rng.choice([-1, 1])  # 선 양쪽 면의 밝기 차
        shade *= 1 - 0.18 * np.exp(-(dist / 2.0) ** 2)  # 접힌 자리의 어두운 골
    amp = 0.006 * max(w, h)
    dx, dy = smooth_noise(rng, h, w, 160) * amp, smooth_noise(rng, h, w, 160) * amp
    if corners_fixed:
        d = np.full((h, w), np.inf, np.float32)
        for cx, cy in ((0, 0), (w - 1, 0), (w - 1, h - 1), (0, h - 1)):
            d = np.minimum(d, np.hypot(xx - cx, yy - cy))  # 가장 가까운 모서리까지의 거리
        window = 1 - np.exp(-(d / (0.08 * max(w, h))) ** 2)  # 모서리에서 0, 멀어지면 1
        dx, dy = dx * window, dy * window
    out = paper * shade[..., None]
    mask = np.ones((h, w), np.float32)
    pad = int(amp * 3) + 2
    # 테두리가 바깥으로 흔들려도 잘리지 않게 사방에 pad만큼 0을 붙인다.
    out = cv2.copyMakeBorder(out, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
    mask = cv2.copyMakeBorder(mask, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
    dxp = cv2.copyMakeBorder(dx, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
    dyp = cv2.copyMakeBorder(dy, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
    gy, gx = np.mgrid[0:h + 2 * pad, 0:w + 2 * pad].astype(np.float32)
    # remap(이미지, 지도x, 지도y): 결과 (r, c)에 원본 (지도y[r, c], 지도x[r, c])의 색을 가져온다. 픽셀을 조금씩 민다.
    out = cv2.remap(out, gx + dxp, gy + dyp, cv2.INTER_LINEAR)
    mask = cv2.remap(mask, gx + dxp, gy + dyp, cv2.INTER_LINEAR)
    return out, mask, pad


# ───────────────────────── 배경 ─────────────────────────

def background(rng, kind):
    """화면 전체 크기의 배경을 만든다.

    Args:
        rng: NumPy 난수 생성기.
        kind: "plain_dark", "plain_blue", "plain_brown", "plain_gray", "plain_green", "wood", "plaid",
            "white_clutter", "desk_clutter" 중 하나.

    Returns:
        numpy.ndarray: (1280, 960, 3) float32 BGR 배경. 0~255 범위를 조금 벗어날 수 있다(마지막에 자른다).

    Raises:
        ValueError: 모르는 kind인 경우.
    """
    h, w = IMAGE_H, IMAGE_W
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    plain = {"plain_dark": (72, 72, 76), "plain_blue": (120, 70, 40), "plain_brown": (60, 90, 125),
             "plain_gray": (128, 130, 132), "plain_green": (60, 95, 45)}
    if kind in plain:
        bg = np.empty((h, w, 3), np.float32)
        bg[:] = plain[kind]
        bg *= (1 + 0.04 * smooth_noise(rng, h, w, 200))[..., None]  # ±4% 정도의 완만한 밝기 얼룩
        return bg
    if kind == "wood":
        a = rng.uniform(-0.3, 0.3)
        u = xx * math.cos(a) + yy * math.sin(a)
        warp = smooth_noise(rng, h, w, 220) * 40
        rings = np.sin((u + warp) / 26.0)  # 판자 방향(세로)을 따라 흐르는 나이테
        streak = cv2.GaussianBlur(rng.standard_normal((h, w)).astype(np.float32), (0, 0), sigmaX=0.8, sigmaY=30)
        tone = 0.80 + 0.10 * rings + 1.2 * streak + 0.06 * smooth_noise(rng, h, w, 120)
        bg = np.array([70, 120, 175], np.float32) * tone[..., None]
        for x in range(int(rng.integers(150, 300)), w, int(rng.integers(250, 330))):  # 판자 이음매
            cv2.line(bg, (x, 0), (x + int(h * math.tan(-a)), h), (35, 55, 80), 3)
        return bg
    if kind == "plaid":
        c1, c2, c3 = np.array([60, 60, 170.]), np.array([235, 235, 235.]), np.array([90, 140, 60.])
        # sin(x / 14) > 0.3인 세로 띠(sx)와 가로 띠(sy). 둘이 겹치면 진한 색, 하나면 중간색, 없으면 흰색.
        sx = (np.sin(xx / 14) > 0.3).astype(np.float32)
        sy = (np.sin(yy / 14) > 0.3).astype(np.float32)
        thin = ((np.sin(xx / 4.5) > 0.85) | (np.sin(yy / 4.5) > 0.85)).astype(np.float32)
        # 줄 끝의 \는 다음 줄로 식을 이어 쓴다는 표시다.
        bg = c2 * (1 - np.clip(sx + sy, 0, 1))[..., None] + c1 * (sx * sy)[..., None] + \
            (c1 * 0.5 + c2 * 0.5) * (np.clip(sx + sy, 0, 1) - sx * sy)[..., None]
        bg = bg * (1 - 0.3 * thin[..., None]) + c3 * 0.3 * thin[..., None]
        return bg * (1 + 0.05 * smooth_noise(rng, h, w, 100))[..., None]
    if kind == "white_clutter":
        bg = np.empty((h, w, 3), np.float32)
        bg[:] = (214, 216, 218)
        bg *= (1 + 0.03 * smooth_noise(rng, h, w, 150))[..., None]
        for _ in range(3):  # 문서와 겹치거나 맞닿는 다른 흰 종이
            draw_rotated_rect(bg, (rng.uniform(0, w), rng.uniform(0, h)), (rng.uniform(300, 600), rng.uniform(350, 700)),
                              rng.uniform(0, 180), (238, 238, 236))
        return bg
    if kind == "desk_clutter":
        bg = background(rng, "wood") * 0.85  # 자기 자신을 불러(재귀) 나뭇결을 만든 뒤 조금 어둡게
        for _ in range(6):
            color = [(240, 240, 240), (120, 230, 245), (200, 200, 120), (60, 60, 60)][rng.integers(0, 4)]
            draw_rotated_rect(bg, (rng.uniform(0, w), rng.uniform(0, h)), (rng.uniform(80, 260), rng.uniform(80, 260)),
                              rng.uniform(0, 180), color)
        for _ in range(4):  # 펜
            p = np.array([rng.uniform(0, w), rng.uniform(0, h)])
            d = rng.uniform(-1, 1, 2)
            d = d / np.linalg.norm(d) * rng.uniform(120, 200)
            cv2.line(bg, tuple(p.astype(int)), tuple((p + d).astype(int)), (140, 60, 30), 9, cv2.LINE_AA)
        cv2.circle(bg, (int(rng.uniform(100, w - 100)), int(rng.uniform(100, 300))), 70, (230, 230, 230), -1, cv2.LINE_AA)
        cv2.circle(bg, (int(rng.uniform(100, w - 100)), int(rng.uniform(100, 300))), 55, (40, 50, 90), -1, cv2.LINE_AA)
        return bg
    raise ValueError(kind)


def draw_rotated_rect(img, center, size, angle, color):
    """회전한 직사각형을 채워 그린다(제자리 수정).

    Args:
        img: 그릴 이미지. 제자리에서 바뀐다.
        center: 중심 (x, y).
        size: (너비, 높이).
        angle: 회전 각도(도).
        color: (B, G, R) 색.
    """
    # boxPoints((중심, 크기, 각도))는 회전한 사각형의 네 꼭짓점 (4, 2) float32를 준다. map(float, …)은 각 값을 실수로.
    box = cv2.boxPoints((tuple(map(float, center)), tuple(map(float, size)), float(angle)))
    cv2.fillPoly(img, [box.astype(np.int32)], color, cv2.LINE_AA)


def draw_hand(img, rng, target):
    """손가락 세 개가 target 점(문서 모서리) 근처를 덮도록 피부색 타원을 그린다.

    Args:
        img: 장면 이미지 (H, W, 3) float32. 제자리에서 바뀐다.
        rng: NumPy 난수 생성기(이 함수에서는 쓰지 않지만 다른 그리기 함수와 인자를 맞춘다).
        target: 가릴 점 (x, y). C04에서는 BR 모서리 근처.
    """
    skin = np.array([135, 165, 210], np.float32)
    tx, ty = target
    direction = np.array([tx - IMAGE_W / 2, ty - IMAGE_H / 2])
    direction /= np.linalg.norm(direction)  # 화면 중심 → 목표 방향의 길이 1 벡터. 손이 화면 바깥쪽에서 들어온다
    palm = np.array([tx, ty]) + direction * 260
    ang = math.degrees(math.atan2(direction[1], direction[0]))
    cv2.ellipse(img, tuple(int(v) for v in palm), (230, 150), ang, 0, 360, (skin * 0.92).tolist(), -1, cv2.LINE_AA)
    perp = np.array([-direction[1], direction[0]])  # 손가락을 옆으로 벌릴 수직 방향
    for k, off in enumerate((-55, 0, 55)):
        tip = np.array([tx, ty]) + perp * off - direction * (25 - 20 * abs(k - 1))
        mid = (tip + palm) / 2
        length = np.linalg.norm(palm - tip) / 2 + 30
        cv2.ellipse(img, tuple(int(v) for v in mid), (int(length), 26), ang, 0, 360, (skin * (0.95 + 0.04 * k)).tolist(), -1, cv2.LINE_AA)
        cv2.ellipse(img, tuple(int(v) for v in tip + direction * 12), (14, 10), ang, 0, 360, (skin * 1.08).tolist(), -1, cv2.LINE_AA)


# ───────────────────────── 조명 ─────────────────────────

def lighting_field(rng, kind, doc_quad):
    """곱해지는 조명장 L(x,y)와 더해지는 반사광 G(x,y).

    최종 장면 = 장면 × L + G. L이 0.3이면 그 자리가 30% 밝기(어둠), G가 크면 하얗게 포화된다.

    Args:
        rng: NumPy 난수 생성기.
        kind: "uniform", "gradient", "soft_shadow", "hard_shadow", "low_light", "shadow_glare" 중 하나.
        doc_quad: 문서 네 꼭짓점 (4, 2). 그림자·반사 위치를 문서 기준으로 정한다.

    Returns:
        tuple: (light, glare). 둘 다 (1280, 960) float32.
    """
    h, w = IMAGE_H, IMAGE_W
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.hypot((xx - w / 2) / w, (yy - h / 2) / h)  # 화면 중심에서의 상대 거리
    light = 1.0 - 0.18 * r ** 2  # 렌즈 주변부 감광
    glare = np.zeros((h, w), np.float32)
    center = doc_quad.mean(axis=0)

    # 함수 안의 함수(중첩 함수). 바깥 함수의 h, w, rng, center를 그대로 쓸 수 있다.
    def shadow_poly(strength, blur, reach):
        """화면 가장자리에서 문서 중심 쪽으로 들어오는 그림자 다각형 (손·휴대폰).

        Args:
            strength: 그림자 진하기. 0.5면 그림자 안 밝기가 50%.
            blur: 그림자 경계를 흐리는 정도(가우시안 sigma). 클수록 부드러운 그림자.
            reach: 그림자가 문서 중심을 넘어 들어오는 거리(픽셀).

        Returns:
            numpy.ndarray: (h, w) 배율. 그림자 밖 1, 안 1 − strength.
        """
        mask = np.zeros((h, w), np.float32)
        side = rng.choice(["left", "right", "top"])
        cx, cy = center
        if side == "left":
            pts = [(-50, cy - 400), (cx + reach, cy - 250), (cx + reach - 60, cy + 380), (-50, cy + 500)]
        elif side == "right":  # elif는 앞 조건이 거짓일 때 다음 조건을 검사한다
            pts = [(w + 50, cy - 450), (cx - reach, cy - 300), (cx - reach + 80, cy + 350), (w + 50, cy + 480)]
        else:
            pts = [(cx - 380, -50), (cx - 260, cy - 60 + reach * 0.3), (cx + 300, cy + reach * 0.4), (cx + 420, -50)]
        cv2.fillPoly(mask, [np.array(pts, np.int32)], 1.0, cv2.LINE_AA)
        if blur > 0:
            mask = cv2.GaussianBlur(mask, (0, 0), blur)
        return 1 - strength * mask

    if kind == "gradient":
        a = rng.uniform(0, 2 * np.pi)
        t = ((xx - w / 2) * math.cos(a) + (yy - h / 2) * math.sin(a)) / (0.5 * math.hypot(w, h))
        light *= 0.775 + 0.225 * np.clip(t, -1, 1)  # 0.55 ~ 1.0
    elif kind == "soft_shadow":
        light *= shadow_poly(0.55, 35, 40)
    elif kind == "hard_shadow":
        light *= shadow_poly(0.5, 2.5, 60)
    elif kind == "low_light":
        light *= 0.30 * shadow_poly(0.4, 40, 0)
    elif kind == "shadow_glare":
        light *= shadow_poly(0.45, 30, -40)
        corner = doc_quad[rng.integers(0, 4)]
        # 모서리 근처에 타원 모양으로 밝게 퍼지는 빛. 260을 더하면 255를 넘어 하얗게 포화된다(S05 실패 원인).
        g = np.exp(-(((xx - corner[0] - 25) / 70) ** 2 + ((yy - corner[1] + 10) / 45) ** 2))
        glare = 260 * g
    return light, glare


# ───────────────────────── 장면 합성 ─────────────────────────

def render_case(case, seed=SEED):
    """한 장면을 렌더링한다. 반환: (BGR uint8 이미지, 정답 꼭짓점 (4,2), 메타데이터).

    Args:
        case: Case 하나.
        seed: 전체 데이터셋의 난수 시작값.

    Returns:
        tuple: (image, quad, meta). image는 (1280, 960, 3) uint8, quad는 (4, 2) 정답 꼭짓점,
        meta는 labels.json에 들어갈 dict.
    """
    # 시드를 [전체 seed, 이미지 id를 숫자로 바꾼 값]으로 준다. "E01".encode() → 바이트 → 정수 4534321.
    # 이미지마다 다른 난수가 나오면서도, 한 장만 다시 만들어도 같은 결과가 나온다(다른 장의 순서에 영향받지 않는다).
    rng = np.random.default_rng([seed, int.from_bytes(case.id.encode(), "big")])
    w_mm, h_mm = PAPER_SIZES_MM[case.paper]
    pw, ph = int(round(w_mm * PX_PER_MM)), int(round(h_mm * PX_PER_MM))  # A4: 840 × 1188 px
    paper = DRAWERS[case.paper](rng, pw, ph).astype(np.float32)
    mask = np.ones((ph, pw), np.float32)
    pad = 0
    if case.extras.get("crumple"):
        paper, mask, pad = crumple(rng, paper)

    quad, distance, tilt = place_document(case, (w_mm, h_mm))
    # 종이 이미지의 네 모서리(src) → 화면의 정답 꼭짓점(quad). 스캐너의 warp_document와 반대 방향의 같은 변환이다.
    src = np.array([[pad, pad], [pad + pw, pad], [pad + pw, pad + ph], [pad, pad + ph]], np.float32)
    homography = cv2.getPerspectiveTransform(src, quad.astype(np.float32))
    size = (IMAGE_W, IMAGE_H)
    warped = cv2.warpPerspective(paper, homography, size, flags=cv2.INTER_LINEAR)  # (1280, 960, 3)
    # 마스크도 같은 변환을 해 α(종이 = 1, 배경 = 0, 경계 = 소수)를 얻는다. [..., None]으로 (1280, 960, 1).
    alpha = cv2.warpPerspective(mask, homography, size, flags=cv2.INTER_LINEAR)[..., None]

    bg = background(rng, case.background)
    contact = cv2.GaussianBlur(alpha[..., 0], (0, 0), 6)  # 종이 아래 접촉 그림자
    bg *= (1 - 0.35 * contact)[..., None]
    # 알파 합성: 종이 자리는 종이 색, 나머지는 배경 색. 경계 픽셀은 둘이 섞여 실제 사진처럼 부드럽다.
    scene = bg * (1 - alpha) + warped * alpha

    if case.extras.get("occlusion") == "hand":
        draw_hand(scene, rng, quad[2] + np.array([-10.0, -10.0]))
    if case.background == "white_clutter":  # 문서 일부를 덮는 다른 종이 한 장
        edge_mid = (quad[1] + quad[2]) / 2
        draw_rotated_rect(scene, edge_mid + np.array([140.0, 40.0]), (320, 420), case.roll + 8, (240, 240, 238))

    light, glare = lighting_field(rng, case.lighting, quad)
    scene = scene * light[..., None] + glare[..., None]
    scene = cv2.GaussianBlur(scene, (0, 0), 0.9)  # 초점·렌즈 흐림
    noise_sigma = 7.0 if case.extras.get("low_light") else 2.5
    scene += rng.normal(0, noise_sigma, scene.shape)
    image = np.clip(scene, 0, 255).astype(np.uint8)  # 실수 → 0~255로 자른 뒤 uint8 사진으로

    meta = {
        "id": case.id, "file": f"{case.id}.jpg", "condition": case.condition,
        "condition_name": CONDITION_NAMES[case.condition], "paper": case.paper,
        "paper_size_mm": [w_mm, h_mm], "true_aspect": round(w_mm / h_mm, 6),
        "angle": {"tilt_deg": round(tilt, 1), "pitch": case.pitch, "yaw": case.yaw, "roll": case.roll},
        "lighting": case.lighting_note, "background": case.background,
        "background_complexity": case.background_level, "extras": case.extras, "note": case.note,
        "corners": quad.round(2).tolist(),
        "camera": {"focal_px": FOCAL_PX, "distance_mm": round(distance, 1)},
    }
    return image, quad, meta


def generate(out_dir=OUT_DIR, seed=SEED):
    """20장을 만들고 labels.json을 저장한다.

    같은 seed면 같은 이미지가 나온다(tests의 test_generator_is_deterministic). 다시 만들면 data/synthetic의
    파일을 덮어쓴다.

    Args:
        out_dir: 저장 폴더.
        seed: 난수 시작값.

    Returns:
        list: 이미지마다 메타데이터 dict.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    labels = []
    for case in CASES:
        image, _, meta = render_case(case, seed)
        imwrite(out_dir / meta["file"], image, jpeg_quality=88)
        labels.append(meta)
    doc = {
        "description": "합성 문서 사진 20장. corners는 문서 내용 기준 좌상·우상·우하·좌하 픽셀 좌표다.",
        "image_size": [IMAGE_W, IMAGE_H], "seed": seed, "images": labels,
    }
    (out_dir / "labels.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return labels


if __name__ == "__main__":
    for item in generate():
        print(f"{item['id']}  {item['condition_name']:<14} tilt={item['angle']['tilt_deg']:>5}°  {item['note']}")
