"""합성 테스트 영상과 정답 생성.

시나리오마다 20~30초 영상(640×360, 30fps)과 정답 JSON을 만든다. 정답에는 프레임별 객체 박스·가시율(가려지거나
화면 밖으로 나간 비율을 뺀 값)과 이벤트 구간(교차, 정지, 조명 변화 등)이 들어 있어서, ID Switch와 추적 실패를
사람이 세지 않고 프레임 단위로 판정할 수 있다.

| 시나리오 | 내용 | 이벤트 |
| --- | --- | --- |
| single | 한 사람이 10구간을 걷는다 (기둥 뒤 통과 2회, 원근에 따른 크기 변화, 빠름·느림) | 10 |
| crossing | 두 사람(파란·빨간 셔츠)이 10가지 방식으로 마주친다 (통과, 되돌아감, 나란히 걷기 등) | 10 |
| crossing_same | crossing과 같은 동선, 두 사람 모두 A와 같은 옷 (외형 규칙의 효과를 가르는 대조군) | 10 |
| pause | 한 사람이 0.5~5초씩 5번 멈춘다, 마지막에 나갔다가 다시 들어온다 | 5 (+재등장 1) |
| lighting | 한 사람이 걷는 동안 조명이 5번 바뀐다 (켜짐, 꺼짐, 서서히, 국소 조명, 깜빡임) | 5 |
| target | 등록 물체(책 표지)가 나타나 회전·기울어짐·가림을 겪고 사라진다 | 구간별 |

분할은 두 개다. dev(시드 11)로 파라미터를 고르고 test(시드 23)로 보고한다. 두 분할은 동선 구조가 같고
위치·속도·배경 무늬가 다르다. 테스트 영상에서 파라미터를 고르면 성능이 부풀려진다(A5-1의 데이터 누수와 같은 원리).

실행: python -m src.synthetic                 # 전체 (약 1분)
      python -m src.synthetic --only crossing --split test
"""
import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

W, H, FPS = 640, 360, 30
HORIZON = 150          # 벽과 바닥의 경계 y
WARMUP = 30            # 첫 1초는 빈 배경 (배경 모델이 배경을 익히는 시간)
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "synthetic"
TARGET_DIR = ROOT / "data" / "target"
SPLITS = {"dev": 11, "test": 23}
SCENARIOS = ("single", "crossing", "crossing_same", "pause", "lighting", "target")
NOISE_SIGMA = 2.2      # 센서 잡음 (밝기 단계)

# BGR
COLORS = {
    "blue": (150, 75, 30), "red": (45, 45, 185), "green": (70, 135, 45), "gray": (118, 118, 122),
    "yellow": (40, 175, 215), "navy": (90, 45, 25), "black": (40, 38, 36), "khaki": (95, 135, 150),
    "denim": (120, 85, 60), "skin": (120, 160, 205), "skin2": (85, 120, 165), "hair": (30, 30, 35),
}


def person_height(foot_y):
    """발 위치 y에서의 사람 키(px). 카메라에서 멀수록(위쪽일수록) 작다."""
    return 62.0 + (foot_y - HORIZON) * 0.36


# ---------------------------------------------------------------- 동선

class Route:
    """(프레임, x, y) 키프레임을 이어 만든 동선. 키프레임 사이는 등속 직선 이동."""

    def __init__(self, frame, x, y):
        self.keys = [(int(frame), float(x), float(y))]

    @property
    def end(self):
        return self.keys[-1][0]

    @property
    def pos(self):
        return self.keys[-1][1:]

    def go(self, x, y, frames):
        self.keys.append((self.end + max(1, int(round(frames))), float(x), float(y)))
        return self

    def hold(self, frames):
        return self.go(*self.pos, frames)

    def hold_until(self, frame):
        if frame > self.end:
            self.hold(frame - self.end)
        return self

    def sample(self, n_frames):
        """프레임별 위치(없으면 NaN)와 누적 이동 거리."""
        f = np.array([k[0] for k in self.keys], float)
        t = np.arange(n_frames, dtype=float)
        x = np.interp(t, f, [k[1] for k in self.keys])
        y = np.interp(t, f, [k[2] for k in self.keys])
        alive = (t >= f[0]) & (t <= f[-1])
        step = np.hypot(np.diff(x, prepend=x[0]), np.diff(y, prepend=y[0])) * alive
        x[~alive] = np.nan
        y[~alive] = np.nan
        return x, y, np.cumsum(step)


def sync(*routes):
    """모든 동선을 가장 늦게 끝나는 동선에 맞춰 기다리게 하고 그 프레임을 돌려준다."""
    end = max(r.end for r in routes)
    for r in routes:
        r.hold_until(end)
    return end


@dataclass
class Actor:
    id: str
    label: str
    route: Route
    shirt: tuple
    pants: tuple
    skin: tuple = COLORS["skin"]
    stripes: bool = False
    depth_bias: float = 0.0


@dataclass
class Scenario:
    name: str
    split: str
    seed: int
    n_frames: int
    actors: list
    events: list
    background: np.ndarray = None
    pillar: tuple = None                 # (x0, x1) 기둥: 모든 사람보다 앞
    lighting: list = field(default_factory=list)   # 조명 이벤트 설명
    gain: np.ndarray = None              # 프레임별 전역 밝기 배율
    lamp: np.ndarray = None              # 프레임별 국소 조명 세기
    lamp_profile: np.ndarray = None
    target: dict = None                  # target 시나리오: 프레임별 포즈
    posters: list = field(default_factory=list)


# ---------------------------------------------------------------- 그리기

def make_background(rng):
    """벽(패널·창·게시물)과 원근 타일 바닥, 소품이 있는 실내 배경 (float32 BGR)."""
    img = np.zeros((H, W, 3), np.float32)
    wall = np.array([182, 188, 192], np.float32) + rng.uniform(-12, 12, 3)
    floor = np.array([128, 140, 152], np.float32) + rng.uniform(-10, 10, 3)
    img[:HORIZON] = wall
    img[HORIZON:] = floor
    # 벽 패널 줄눈과 걸레받이
    for x in range(int(rng.uniform(20, 60)), W, int(rng.uniform(90, 120))):
        cv2.line(img, (x, 0), (x, HORIZON - 12), (wall * 0.86).tolist(), 2, cv2.LINE_AA)
    cv2.rectangle(img, (0, HORIZON - 12), (W, HORIZON), (wall * 0.62).tolist(), -1)
    # 창문
    wx = int(rng.uniform(30, 120))
    cv2.rectangle(img, (wx, 22), (wx + 110, 92), (215, 205, 190), -1)
    cv2.rectangle(img, (wx, 22), (wx + 110, 92), (95, 95, 100), 3)
    cv2.line(img, (wx + 55, 22), (wx + 55, 92), (95, 95, 100), 3)
    # 게시물(사각형 무늬)
    px = int(rng.uniform(470, 540))
    for i in range(3):
        c = rng.uniform(60, 230, 3).tolist()
        cv2.rectangle(img, (px + i * 30, 40 + i * 6), (px + i * 30 + 24, 78 + i * 6), c, -1)
    # 원근 타일 바닥: 소실점에서 퍼지는 선 + 아래로 갈수록 간격이 넓은 가로선
    vx, vy = W / 2 + rng.uniform(-40, 40), -260
    for bx in range(-600, W + 600, 70):
        cv2.line(img, (int(vx + (bx - vx) * (HORIZON - vy) / (H - vy)), HORIZON), (bx, H),
                 (floor * 0.9).tolist(), 1, cv2.LINE_AA)
    y = HORIZON + 6.0
    step = 8.0
    while y < H:
        cv2.line(img, (0, int(y)), (W, int(y)), (floor * 0.9).tolist(), 1, cv2.LINE_AA)
        step *= 1.32
        y += step
    # 소품: 화분과 벤치 (벽 아래, 사람보다 뒤)
    gx = int(rng.uniform(250, 330))
    cv2.rectangle(img, (gx, 128), (gx + 26, 158), (60, 80, 120), -1)
    for _ in range(9):
        cv2.circle(img, (gx + 13 + int(rng.uniform(-16, 16)), 118 + int(rng.uniform(-18, 6))),
                   int(rng.uniform(7, 11)), (55, 120 + int(rng.uniform(0, 30)), 50), -1, cv2.LINE_AA)
    bx = int(rng.uniform(380, 440))
    cv2.rectangle(img, (bx, 136), (bx + 80, 146), (50, 90, 130), -1)
    cv2.rectangle(img, (bx + 6, 146), (bx + 10, 162), (40, 60, 80), -1)
    cv2.rectangle(img, (bx + 70, 146), (bx + 74, 162), (40, 60, 80), -1)
    # 저주파 얼룩과 비네팅
    blot = cv2.resize(rng.normal(0, 1, (9, 16)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
    img *= (1 + 0.035 * blot)[..., None]
    yy, xx = np.mgrid[0:H, 0:W]
    vign = 1 - 0.18 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / H) ** 2)
    img *= vign[..., None].astype(np.float32)
    return img


def draw_person(foot_x, foot_y, phase, amp, actor):
    """사람 한 명을 작은 패치에 그린다. (색 패치(미리 곱한 알파), 알파, 패치 좌상단) 반환."""
    h = person_height(foot_y)
    s = h / 100.0
    pw, ph = int(0.75 * h) + 8, int(1.03 * h) + 8
    x0, y0 = int(round(foot_x - pw / 2)), int(round(foot_y - h - 4))
    bx, by = foot_x - x0, foot_y - y0
    col = np.zeros((ph, pw, 3), np.uint8)
    alpha = np.zeros((ph, pw), np.uint8)
    S = 4  # 서브픽셀 좌표 비트 (cv2 shift)

    def P(x, y):
        return int(round(x * (1 << S))), int(round(y * (1 << S)))

    def line(p, q, color, t):
        t = max(1, int(round(t)))
        cv2.line(col, P(*p), P(*q), color, t, cv2.LINE_AA, S)
        cv2.line(alpha, P(*p), P(*q), 255, t, cv2.LINE_AA, S)

    def circle(c, r, color):
        cv2.circle(col, P(*c), int(round(r * (1 << S))), color, -1, cv2.LINE_AA, S)
        cv2.circle(alpha, P(*c), int(round(r * (1 << S))), 255, -1, cv2.LINE_AA, S)

    sw = np.sin(phase) * amp
    pants, shirt, skin = actor.pants, actor.shirt, actor.skin
    # 다리와 신발
    for side, sgn in ((-1, 1), (1, -1)):
        hip = (bx + side * 3.6 * s, by - 47 * s)
        foot = (bx + side * 2.6 * s + sgn * sw * 13 * s, by - 2.5 * s)
        line(hip, foot, pants, 7.2 * s)
        line((foot[0] - 1.5 * s, foot[1]), (foot[0] + 3.5 * s, foot[1]), COLORS["black"], 3.4 * s)
    # 몸통 (줄무늬는 몸통 영역 안에서만)
    torso = np.array([P(bx - 10.5 * s, by - 82 * s), P(bx + 10.5 * s, by - 82 * s),
                      P(bx + 8.5 * s, by - 45 * s), P(bx - 8.5 * s, by - 45 * s)], np.int32)
    tmask = np.zeros_like(alpha)
    cv2.fillConvexPoly(tmask, torso, 255, cv2.LINE_AA, S)
    cv2.fillConvexPoly(col, torso, shirt, cv2.LINE_AA, S)
    cv2.fillConvexPoly(alpha, torso, 255, cv2.LINE_AA, S)
    if actor.stripes:
        rows = (np.arange(ph)[:, None] // max(2, int(3.2 * s))) % 2 == 0
        dark = (tmask > 128) & rows
        col[dark] = (col[dark] * 0.72).astype(np.uint8)
    # 팔 (다리와 반대로 흔든다)
    for side, sgn in ((-1, -1), (1, 1)):
        sh = (bx + side * 9.6 * s, by - 79 * s)
        hand = (bx + side * 11.5 * s + sgn * sw * 9 * s, by - 50 * s)
        line(sh, hand, shirt, 5.2 * s)
        circle(hand, 2.6 * s, skin)
    # 목·머리·머리카락
    line((bx, by - 84 * s), (bx, by - 86 * s), skin, 4 * s)
    circle((bx, by - 91.5 * s), 7.6 * s, skin)
    cv2.ellipse(col, P(bx, by - 93 * s), P(7.9 * s, 6.4 * s), 0, 180, 360, COLORS["hair"], -1, cv2.LINE_AA, S)
    cv2.ellipse(alpha, P(bx, by - 93 * s), P(7.9 * s, 6.4 * s), 0, 180, 360, 255, -1, cv2.LINE_AA, S)
    # 원통 음영: 가운데가 밝고 옆이 어둡다
    xs = (np.arange(pw) - bx) / (11 * s)
    shade = np.clip(1.06 - 0.28 * xs ** 2, 0.72, 1.06).astype(np.float32)
    colf = col.astype(np.float32) * shade[None, :, None]
    return colf, alpha.astype(np.float32) / 255.0, (x0, y0)


def make_cover(seed, title="OPEN CV", layout_seed=None, size=(320, 240)):
    """특징점이 풍부한 책 표지 이미지 (등록 물체). layout_seed가 같으면 테두리·글자 배치가 같은 '같은 시리즈'다."""
    w, h = size
    rng = np.random.default_rng(seed)
    lrng = np.random.default_rng(seed if layout_seed is None else layout_seed)
    c1, c2 = rng.uniform(40, 230, 3), rng.uniform(40, 230, 3)
    t = np.linspace(0, 1, h)[:, None, None]
    img = np.ascontiguousarray((c1 * (1 - t) + c2 * t).repeat(w, axis=1).astype(np.uint8))
    for _ in range(14):
        kind = rng.integers(3)
        c = rng.uniform(0, 255, 3).tolist()
        x, y = int(rng.uniform(0, w)), int(rng.uniform(60, h))
        r = int(rng.uniform(8, 40))
        th = -1 if rng.random() < 0.6 else int(rng.integers(2, 5))
        if kind == 0:
            cv2.circle(img, (x, y), r, c, th, cv2.LINE_AA)
        elif kind == 1:
            cv2.rectangle(img, (x - r, y - r // 2), (x + r, y + r // 2), c, th, cv2.LINE_AA)
        else:
            pts = (np.array([[x, y - r], [x + r, y + r], [x - r, y + r]])).astype(np.int32)
            cv2.polylines(img, [pts], True, c, max(2, th), cv2.LINE_AA) if th > 0 else cv2.fillPoly(img, [pts], c, cv2.LINE_AA)
    # 같은 시리즈 공통 요소: 테두리, 제목 띠, 바코드 위치
    frame_c = lrng.uniform(10, 60, 3).tolist()
    cv2.rectangle(img, (6, 6), (w - 7, h - 7), frame_c, 4)
    cv2.rectangle(img, (6, 6), (w - 7, 52), frame_c, -1)
    cv2.putText(img, title, (16, 42), cv2.FONT_HERSHEY_DUPLEX, 1.25, (240, 240, 240), 2, cv2.LINE_AA)
    cv2.putText(img, f"vol.{seed % 97}", (w - 92, h - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20, 20, 20), 2, cv2.LINE_AA)
    # 6×6 이진 블록 (QR 비슷한 무늬)
    grid = rng.integers(0, 2, (6, 6))
    gx, gy = 18, h - 74
    for i in range(6):
        for j in range(6):
            if grid[i, j]:
                cv2.rectangle(img, (gx + j * 9, gy + i * 9), (gx + j * 9 + 8, gy + i * 9 + 8), (15, 15, 15), -1)
    return np.clip(img + rng.normal(0, 4, img.shape), 0, 255).astype(np.uint8)


def card_corners(cx, cy, scale, roll_deg, yaw_deg, size=(320, 240), focal=700.0):
    """평면 물체의 네 꼭짓점 영상 좌표(TL, TR, BR, BL). yaw는 세로축 기준 3D 기울임, roll은 영상 평면 회전."""
    w, h = size
    pts = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]], float) * scale
    yaw = np.deg2rad(yaw_deg)
    x3, z3 = pts[:, 0] * np.cos(yaw), pts[:, 0] * np.sin(yaw)
    px = focal * x3 / (focal + z3)
    py = focal * pts[:, 1] / (focal + z3)
    r = np.deg2rad(roll_deg)
    rx = px * np.cos(r) - py * np.sin(r)
    ry = px * np.sin(r) + py * np.cos(r)
    return np.stack([rx + cx, ry + cy], 1).astype(np.float32)


def warp_layer(texture, corners):
    """텍스처를 꼭짓점 위치로 투시 변환한 전체 프레임 크기 (색, 알파)."""
    th, tw = texture.shape[:2]
    src = np.float32([[0, 0], [tw - 1, 0], [tw - 1, th - 1], [0, th - 1]])
    M = cv2.getPerspectiveTransform(src, np.float32(corners))
    colr = cv2.warpPerspective(texture, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    a = cv2.warpPerspective(np.full((th, tw), 255, np.uint8), M, (W, H), flags=cv2.INTER_LINEAR)
    af = a.astype(np.float32) / 255.0
    return colr.astype(np.float32) * af[..., None], af


# ---------------------------------------------------------------- 시나리오 동선

def _j(rng, v, d):
    return v + rng.uniform(-d, d)


def _n(rng, frames):
    return int(round(frames * rng.uniform(0.92, 1.08)))


def scenario_single(rng):
    """한 사람이 10구간을 걷는다. 기둥(x 410~446) 뒤를 두 번 지난다."""
    r = Route(WARMUP, -25, _j(rng, 300, 6))
    events = []

    def leg(kind, label, x, y, speed):
        start = r.end
        dx, dy = x - r.pos[0], y - r.pos[1]
        r.go(x, y, np.hypot(dx, dy) / (speed * 0.75))  # 0.75: 전체 약 26초
        events.append({"kind": kind, "label": label, "start": start, "end": r.end, "objects": ["A"]})

    leg("enter", "왼쪽에서 들어와 오른쪽으로", _j(rng, 220, 8), _j(rng, 300, 6), 3.6)
    leg("away", "대각선 위로 (멀어지며 작아짐)", _j(rng, 360, 8), _j(rng, 215, 5), 3.0)
    leg("pillar", "기둥 뒤를 지나감", _j(rng, 560, 8), _j(rng, 225, 5), 3.2)
    leg("toward", "카메라 쪽으로 (커짐)", _j(rng, 520, 8), _j(rng, 335, 4), 2.8)
    leg("run", "빠르게 뛰어 왼쪽으로", _j(rng, 150, 8), _j(rng, 325, 5), 7.0)
    leg("slow", "천천히 위로", _j(rng, 120, 6), _j(rng, 205, 5), 1.5)
    leg("right", "오른쪽으로", _j(rng, 300, 8), _j(rng, 210, 5), 3.4)
    leg("diag", "대각선 아래로", _j(rng, 360, 8), _j(rng, 300, 5), 3.2)
    leg("pillar2", "기둥 뒤를 다시 지나감", _j(rng, 590, 6), _j(rng, 292, 5), 3.6)
    leg("exit", "화면 밖으로 나감", 690, _j(rng, 280, 5), 3.6)
    actors = [Actor("A", "사람 A (초록 줄무늬)", r, COLORS["green"], COLORS["denim"], stripes=True)]
    return actors, events, r.end + 20, {"pillar": (410, 446)}


def _crossing_routes(rng):
    """두 사람이 10번 마주치는 동선. 왼쪽 L, 오른쪽 R, 가운데 C."""
    L, R, C = _j(rng, 200, 6), _j(rng, 440, 6), _j(rng, 320, 4)
    ya, yb = _j(rng, 276, 3), _j(rng, 290, 3)
    a = Route(WARMUP, -30, ya)
    b = Route(WARMUP, W + 30, yb)
    a.go(L, ya, 40)
    b.go(R, yb, 40)
    events = []
    t = sync(a, b)

    def done(kind, label):
        nonlocal t
        end = sync(a, b)
        events.append({"kind": kind, "label": label, "start": t, "end": end, "objects": ["A", "B"]})
        t = end

    n = lambda f: _n(rng, f)  # noqa: E731
    # 1 같은 속도로 교차 통과
    a.go(R, ya, n(60)); b.go(L, yb, n(60)); done("pass", "같은 속도로 교차 통과")
    # 2 가운데서 만나 되돌아감
    a.go(C + 10, ya, n(30)).hold(6).go(R, ya, n(30)); b.go(C - 10, yb, n(30)).hold(6).go(L, yb, n(30))
    done("bounce", "가운데서 만나 되돌아감")
    # 3 속도가 다른 교차 (빠른 A, 느린 B)
    a.go(L, ya, n(42)).go(L - 30, ya, n(36)); b.go(R, yb, n(78)); done("speed", "속도가 다른 교차")
    # 4 B가 가운데 멈춘 사이 A가 지나감
    b.go(C, yb, n(30)).hold(n(70)).go(L, yb, n(30)); a.hold(30).go(R + 30, ya, n(70)).go(R, ya, n(20))
    done("one_stops", "한 명이 멈춘 사이 통과")
    # 5 위아래로 비껴 지나감 (부분 겹침)
    ya2, yb2 = ya - 36, yb + 40
    a.go(L, ya2, n(60)); b.go(R, yb2, n(60)); done("offset", "위아래로 비껴 지나감 (부분 겹침)")
    # 6 X자 대각 교차
    ya3, yb3 = yb2 - 8, ya2 - 6
    a.go(R, ya3, n(60)); b.go(L, yb3, n(60)); done("diagonal", "X자 대각 교차")
    # 7 겹친 채 멈췄다가 통과
    a.go(C + 6, ya + 22, n(30)).hold(22).go(L, ya, n(30)); b.go(C - 6, yb + 4, n(30)).hold(22).go(R, yb, n(30))
    done("stop_pass", "겹친 채 멈췄다가 통과")
    # 8 겹친 채 멈췄다가 되돌아감
    a.go(C - 6, ya, n(30)).hold(22).go(L, ya, n(30)); b.go(C + 6, yb, n(30)).hold(22).go(R, yb, n(30))
    done("stop_bounce", "겹친 채 멈췄다가 되돌아감")
    # 9 나란히 함께 걷다가 갈라짐
    a.go(C - 15, ya, n(28)).go(C - 15, ya - 50, n(36)).go(L, ya - 50, n(28))
    b.go(C + 15, yb, n(28)).go(C + 15, yb - 50, n(36)).go(R, yb - 42, n(28))
    done("group", "나란히 함께 걷다가 갈라짐")
    # 10 만난 자리에서 방향 전환 (A는 아래로, B는 위로)
    a.go(C - 3, ya - 18, n(30)).go(C - 25, 345, n(26)); b.go(C + 3, ya - 16, n(30)).go(C + 25, 196, n(26))
    done("turn", "만난 자리에서 방향을 꺾음")
    a.go(-40, 345, 28)
    b.go(W + 40, 196, 34)
    return a, b, events, sync(a, b) + 10


def scenario_crossing(rng, same=False):
    a, b, events, n = _crossing_routes(rng)
    if same:
        # 대조군: 두 사람 모두 A와 같은 옷. 배경 대비가 crossing과 같아서 검출 품질은 그대로 두고 외형 차이만 없앤다.
        actors = [Actor("A", "사람 A (파란 셔츠)", a, COLORS["blue"], COLORS["khaki"]),
                  Actor("B", "사람 B (파란 셔츠, A와 같은 옷)", b, COLORS["blue"], COLORS["khaki"])]
    else:
        actors = [Actor("A", "사람 A (파란 셔츠)", a, COLORS["blue"], COLORS["khaki"]),
                  Actor("B", "사람 B (빨간 셔츠)", b, COLORS["red"], COLORS["navy"], skin=COLORS["skin2"])]
    return actors, events, n, {}


def scenario_pause(rng):
    """다섯 번 멈춘다 (0.5, 1, 2, 3, 5초). 마지막에 화면 밖으로 나갔다가 2초 뒤 다시 들어온다."""
    y = _j(rng, 285, 4)
    r = Route(WARMUP, -25, y)
    events = []
    stops = [15, 30, 60, 90, 150]
    xs = [_j(rng, v, 8) for v in (130, 250, 380, 480, 330)]
    ys = [_j(rng, v, 5) for v in (290, 250, 300, 260, 320)]
    for i, (x, yy, d) in enumerate(zip(xs, ys, stops)):
        dist = np.hypot(x - r.pos[0], yy - r.pos[1])
        r.go(x, yy, dist / 3.4)
        start = r.end
        r.hold(d)
        resume = r.end
        r.go(x + (40 if i % 2 == 0 else -40), yy - 10, 14)
        events.append({"kind": f"stop{d / FPS:g}s", "label": f"{d / FPS:g}초 정지 후 다시 걷기", "start": start,
                       "end": r.end + 30, "resume": resume, "objects": ["A"]})
    r.go(-40, r.pos[1], (r.pos[0] + 40) / 3.6)
    out = r.end
    r.hold(60)  # 화면 밖 2초
    r2_start = r.end
    r.go(140, 300, 52)
    r.go(260, 300, 34)
    events.append({"kind": "reappear", "label": "화면 밖으로 나갔다가 다시 들어옴", "start": out - 20, "end": r.end,
                   "objects": ["A"], "extra": True, "reenter": r2_start})
    actors = [Actor("A", "사람 A (노란 셔츠)", r, COLORS["yellow"], COLORS["black"])]
    return actors, events, r.end + 15, {}


def scenario_lighting(rng):
    """한 사람이 좌우로 계속 걷는 동안 조명이 다섯 번 바뀐다."""
    y = _j(rng, 288, 4)
    r = Route(WARMUP, -25, y)
    xs = [_j(rng, 520, 8), _j(rng, 120, 8), _j(rng, 520, 8), _j(rng, 120, 8), _j(rng, 520, 8), _j(rng, 260, 8)]
    for k, x in enumerate(xs):
        r.go(x, y + (k % 2) * 18, abs(x - r.pos[0]) / 3.0)
    n = r.end + 20
    gain = np.ones(n, np.float32)
    lamp = np.zeros(n, np.float32)
    e = [int(_j(rng, v, 6)) for v in (130, 250, 380, 520, 650)]
    gain[e[0]:] = 1.35                       # 1 조명 켜짐 (갑자기 밝아짐)
    gain[e[1]:] = 0.55                       # 2 조명 꺼짐 (갑자기 어두워짐)
    ramp = np.clip((np.arange(n) - e[2]) / 60.0, 0, 1)
    gain[e[2]:] = 0.55 + 0.45 * ramp[e[2]:]  # 3 2초에 걸쳐 서서히 밝아짐
    lamp[e[3]:] = 1.0                        # 4 왼쪽 위 국소 조명 켜짐
    flick = np.arange(n) - e[4]               # 5 형광등 깜빡임 (4프레임 간격, 0.8초)
    on = (flick >= 0) & (flick < 24) & ((flick // 4) % 2 == 0)
    gain[on] *= 0.7
    labels = ["조명 켜짐 (밝기 ×1.35)", "조명 꺼짐 (밝기 ×0.55)", "2초에 걸쳐 서서히 밝아짐", "국소 조명 켜짐 (왼쪽 위)",
              "형광등 깜빡임 (0.8초)"]
    kinds = ["on", "off", "gradual", "lamp", "flicker"]
    events = [{"kind": k, "label": lb, "start": s, "end": min(n - 1, s + 75), "objects": ["A"]}
              for k, lb, s in zip(kinds, labels, e)]
    yy, xx = np.mgrid[0:H, 0:W]
    profile = np.exp(-(((xx - 150) / 210.0) ** 2 + ((yy - 90) / 170.0) ** 2)).astype(np.float32) * 0.85
    actors = [Actor("A", "사람 A (남색 셔츠)", r, COLORS["navy"], COLORS["khaki"])]
    return actors, events, n, {"gain": gain, "lamp": lamp, "lamp_profile": profile, "lighting": labels}


def scenario_target(rng):
    """등록 물체가 벽에 나타나 회전·기울어짐·가림을 겪고 사라진다. 사람 한 명이 앞을 지나며 가린다."""
    segs = [("absent", 30), ("enter", 50), ("frontal", 40), ("roll", 50), ("roll_back", 30), ("yaw", 50),
            ("yaw_back", 30), ("occluded", 70), ("shrink", 40), ("absent", 40)]
    n = WARMUP + sum(d for _, d in segs)
    cx0, cy0, sc0 = _j(rng, 330, 10), _j(rng, 112, 4), 0.42
    pose = []
    for _ in range(WARMUP):
        pose.append(None)
    for name, d in segs:
        for i in range(d):
            u = i / max(1, d - 1)
            if name == "absent":
                pose.append(None)
            elif name == "enter":
                pose.append((W + 80 - (W + 80 - cx0) * u, cy0, sc0, 0, 0, "entering"))
            elif name in ("frontal", "occluded"):
                pose.append((cx0, cy0, sc0, 0, 0, name))
            elif name == "roll":
                pose.append((cx0, cy0, sc0, 60 * u, 0, "roll"))
            elif name == "roll_back":
                pose.append((cx0, cy0, sc0, 60 * (1 - u), 0, "roll"))
            elif name == "yaw":
                pose.append((cx0, cy0, sc0, 0, 65 * u, "yaw"))
            elif name == "yaw_back":
                pose.append((cx0, cy0, sc0, 0, 65 * (1 - u), "yaw"))
            elif name == "shrink":
                pose.append((cx0 - 60 * u, cy0, sc0 * (1 - 0.6 * u), 0, 0, "shrink"))
    occ_start = WARMUP + sum(d for nm, d in segs[:7])
    r = Route(occ_start - 10, -30, 205)
    r.go(cx0 - 20, 206, 34).hold(26).go(W + 30, 210, 50)
    actors = [Actor("P", "지나가는 사람", r, COLORS["red"], COLORS["black"])]
    posters = [(make_cover(int(rng.integers(1000, 9999)), title="NEWS"), (int(_j(rng, 120, 10)), 70, 0.22)),
               (make_cover(int(rng.integers(1000, 9999)), title="MAP"), (int(_j(rng, 560, 10)), 72, 0.2))]
    events = []
    f = WARMUP
    for name, d in segs:
        events.append({"kind": name, "label": name, "start": f, "end": f + d - 1, "objects": ["T"]})
        f += d
    return actors, events, n, {"target": {"pose": pose, "texture": make_cover(7, "OPEN CV")}, "posters": posters}


BUILDERS = {
    "single": scenario_single,
    "crossing": scenario_crossing,
    "crossing_same": lambda rng: scenario_crossing(rng, same=True),
    "pause": scenario_pause,
    "lighting": scenario_lighting,
    "target": scenario_target,
}


def build(name, split):
    seed = SPLITS[split]
    # 시나리오마다 다른 난수열 (crossing과 crossing_same은 동선과 배경이 같아야 하므로 같은 시드)
    key = {"crossing_same": "crossing"}.get(name, name)
    rng = np.random.default_rng([seed, sum(map(ord, key))])
    actors, events, n, extra = BUILDERS[name](rng)
    sc = Scenario(name, split, seed, n, actors, events)
    sc.background = make_background(np.random.default_rng([seed, 7]))
    sc.pillar = extra.get("pillar")
    sc.gain = extra.get("gain", np.ones(n, np.float32))
    sc.lamp = extra.get("lamp", np.zeros(n, np.float32))
    sc.lamp_profile = extra.get("lamp_profile")
    sc.lighting = extra.get("lighting", [])
    sc.target = extra.get("target")
    sc.posters = extra.get("posters", [])
    if sc.posters:  # 벽에 붙은 정지 게시물 (오검출 유발용)
        for tex, (cx, cy, s) in sc.posters:
            colr, a = warp_layer(tex, card_corners(cx, cy, s, 0, 0))
            sc.background = sc.background * (1 - a[..., None]) + colr
    for i, e in enumerate(sc.events, 1):
        e["index"] = i
    return sc


# ---------------------------------------------------------------- 렌더링

class Renderer:
    """시나리오의 프레임을 결정적으로 그린다. 같은 (시나리오, 프레임)은 항상 같은 그림·정답이다."""

    def __init__(self, sc):
        self.sc = sc
        self.tracks = {}
        for a in sc.actors:
            x, y, dist = a.route.sample(sc.n_frames)
            vx = np.abs(np.gradient(np.nan_to_num(x)))
            vy = np.abs(np.gradient(np.nan_to_num(y)))
            self.tracks[a.id] = (x, y, dist, vx, vy)

    def frame(self, i, with_noise=True):
        """(BGR uint8 프레임, 정답 목록, 사람 전경 마스크) 반환."""
        sc = self.sc
        img = sc.background.copy()
        layers = []  # (깊이, id, 색, 알파, x0, y0)
        shadow = np.zeros((H, W), np.float32)
        for a in sc.actors:
            x, y, dist, vx, vy = self.tracks[a.id]
            if np.isnan(x[i]):
                continue
            h = person_height(y[i])
            moving = (vx[i] + vy[i]) > 0.3
            amp = (0.25 + 0.75 * min(1.0, vx[i] / max(vx[i] + vy[i], 1e-6))) if moving else 0.0
            phase = dist[i] / (0.5 * h) * np.pi
            colr, al, (x0, y0) = draw_person(x[i], y[i], phase, amp, a)
            layers.append((y[i] + a.depth_bias, a.id, colr, al, x0, y0))
            cv2.ellipse(shadow, (int(x[i] + 0.16 * h), int(y[i])), (int(0.27 * h), max(2, int(0.055 * h))), 0, 0, 360,
                        1.0, -1, cv2.LINE_AA)
        if sc.target is not None and sc.target["pose"][i] is not None:
            cx, cy, s, roll, yaw, _ = sc.target["pose"][i]
            corners = card_corners(cx, cy, s, roll, yaw)
            colr, al = warp_layer(sc.target["texture"], corners)
            layers.append((HORIZON - 1, "T", colr, al, 0, 0))
        if sc.pillar is not None:
            x0p, x1p = sc.pillar
            pw = x1p - x0p
            colr = np.zeros((352, pw, 3), np.float32)
            xs = (np.arange(pw) - pw / 2) / (pw / 2)
            shade = np.clip(1.05 - 0.45 * xs ** 2, 0.5, 1.05)
            colr[:] = (np.array([150, 160, 172], np.float32)[None, :] * shade[:, None])[None]
            colr[340:] *= 0.6
            layers.append((H + 100, None, colr, np.ones((352, pw), np.float32), x0p, 0))
        if shadow.any():
            shadow = cv2.GaussianBlur(shadow, (0, 0), 3.0)
            shadow[:HORIZON] = 0
            img *= (1 - 0.38 * shadow)[..., None]
        owner = np.full((H, W), -1, np.int16)
        full = {}
        layers.sort(key=lambda L: L[0])
        for k, (_, oid, colr, al, x0, y0) in enumerate(layers):
            ph, pw = al.shape
            xa, ya = max(0, x0), max(0, y0)
            xb, yb = min(W, x0 + pw), min(H, y0 + ph)
            if oid is not None:
                full[k] = (oid, float((al > 0.5).sum()))
            if xa >= xb or ya >= yb:
                continue
            a = al[ya - y0:yb - y0, xa - x0:xb - x0]
            c = colr[ya - y0:yb - y0, xa - x0:xb - x0]
            reg = img[ya:yb, xa:xb]
            reg *= (1 - a[..., None])
            reg += c
            owner[ya:yb, xa:xb][a > 0.5] = k
        gt = []
        person_mask = np.zeros((H, W), bool)
        for k, (oid, n_full) in full.items():
            m = owner == k
            n_vis = int(m.sum())
            if oid != "T":
                person_mask |= m
            if n_vis == 0:
                gt.append({"id": oid, "bbox": None, "vis": 0.0})
                continue
            ys, xs = np.nonzero(m)
            gt.append({"id": oid, "bbox": [int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1),
                                           int(ys.max() - ys.min() + 1)],
                       "vis": round(n_vis / max(n_full, 1.0), 3)})
        g = sc.gain[i] * (1 + sc.lamp[i] * sc.lamp_profile) if sc.lamp_profile is not None else sc.gain[i]
        img = img * (g[..., None] if np.ndim(g) == 2 else g)
        if with_noise:
            img += np.random.default_rng([sc.seed, 99, i]).standard_normal(img.shape, np.float32) * NOISE_SIGMA
        out = np.clip(img + 0.5, 0, 255).astype(np.uint8)
        if sc.target is not None and sc.target["pose"][i] is not None:
            cx, cy, s, roll, yaw, cond = sc.target["pose"][i]
            for o in gt:
                if o["id"] == "T":
                    o["corners"] = np.round(card_corners(cx, cy, s, roll, yaw), 2).tolist()
                    o["cond"] = cond
                    o["roll"], o["yaw"], o["scale"] = round(roll, 2), round(yaw, 2), round(s, 3)
        return out, gt, person_mask


def ground_truth(sc, gts):
    return {
        "scenario": sc.name, "split": sc.split, "seed": sc.seed, "fps": FPS, "size": [W, H],
        "frames": sc.n_frames, "video": f"{sc.name}_{sc.split}.mp4", "warmup": WARMUP,
        "objects": {**{a.id: a.label for a in sc.actors}, **({"T": "등록 물체 (책 표지)"} if sc.target else {})},
        "events": sc.events, "lighting": sc.lighting, "pillar": sc.pillar,
        "gain": [round(float(g), 3) for g in sc.gain], "lamp": [round(float(v), 3) for v in sc.lamp],
        "gt": gts,
    }


def write_scenario(name, split, out_dir=DATA):
    sc = build(name, split)
    rend = Renderer(sc)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}_{split}.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    if not writer.isOpened():
        raise RuntimeError(f"VideoWriter를 열 수 없다: {path}")
    gts = []
    for i in range(sc.n_frames):
        frame, gt, _ = rend.frame(i)
        writer.write(frame)
        gts.append(gt)
    writer.release()
    (out_dir / f"{name}_{split}.json").write_text(json.dumps(ground_truth(sc, gts), ensure_ascii=False,
                                                             separators=(",", ":")), encoding="utf-8")
    return path, sc.n_frames


def load_gt(name, split="test", data_dir=DATA):
    return json.loads((Path(data_dir) / f"{name}_{split}.json").read_text(encoding="utf-8"))


def write_targets():
    """등록 물체, 같은 시리즈 다른 권(일반화 실험), 무관한 표지."""
    from .image_io import imwrite
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    imwrite(TARGET_DIR / "target.png", make_cover(7, "OPEN CV"))
    imwrite(TARGET_DIR / "same_series.png", make_cover(8, "OPEN CV", layout_seed=7))
    imwrite(TARGET_DIR / "other.png", make_cover(4242, "NEWS"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", nargs="*", choices=SCENARIOS, default=list(SCENARIOS))
    ap.add_argument("--split", nargs="*", choices=list(SPLITS), default=list(SPLITS))
    args = ap.parse_args(argv)
    cv2.setNumThreads(2)
    write_targets()
    for split in args.split:
        for name in args.only:
            path, n = write_scenario(name, split)
            print(f"{path.relative_to(ROOT)}: {n} frames ({n / FPS:.1f}s), {path.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
