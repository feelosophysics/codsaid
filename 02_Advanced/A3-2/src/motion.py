"""배경 차분 → 모폴로지 → 윤곽선·면적 필터 → 바운딩 박스와 중심점.

세 가지 배경 모델을 같은 인터페이스(apply(frame, learning_rate) → 전경 마스크)로 쓴다.

- mog2: cv2.createBackgroundSubtractorMOG2. 픽셀마다 가우시안 여러 개로 배경을 표현한다. 그림자는 127로 표시된다.
- running_avg: 직접 구현한 이동 평균 배경. bg ← (1−α)·bg + α·frame, |frame − bg| > T 이면 전경.
- frame_diff: 직접 구현한 연속 프레임 차영상. |frame_t − frame_{t−1}| > T. 배경 모델이 없어 학습률이 없다.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np


@dataclass
class MotionParams:
    method: str = "mog2"           # mog2 | running_avg | frame_diff
    learning_rate: float = 0.002   # 배경 학습률 α (−1이면 MOG2 자동: 1/history)
    history: int = 500
    var_threshold: float = 16.0    # MOG2: 마할라노비스 거리² 임계값
    detect_shadows: bool = True    # MOG2: 그림자를 127로 표시 (이후 제거)
    diff_threshold: int = 25       # running_avg·frame_diff: 밝기 차 임계값
    blur: int = 3                  # 배경 차분 전 가우시안 블러 (0이면 끔)
    open_ksize: int = 3            # 열림: 작은 점 잡음 제거
    close_ksize: int = 11          # 닫힘: 몸통·다리 사이 틈 메우기
    min_area: int = 350            # 이보다 작은 윤곽선은 무시 (px²)
    compute_hist: bool = False     # 외형 규칙 실험용 HSV 히스토그램


@dataclass
class Detection:
    bbox: tuple                    # (x, y, w, h)
    centroid: tuple                # (cx, cy) — 박스 중심
    area: float                    # 윤곽선 면적
    hist: np.ndarray = field(default=None, repr=False)


class RunningAverageSubtractor:
    """이동 평균 배경 모델 (absdiff 직접 구현)."""

    def __init__(self, threshold=25):
        self.threshold = threshold
        self.bg = None

    def apply(self, frame, learning_rate=0.002):
        f = frame.astype(np.float32)
        if self.bg is None:
            self.bg = f.copy()
            return np.zeros(frame.shape[:2], np.uint8)
        diff = np.abs(f - self.bg).max(axis=2)
        mask = np.where(diff > self.threshold, 255, 0).astype(np.uint8)
        a = 1.0 / 500 if learning_rate < 0 else learning_rate
        self.bg += a * (f - self.bg)        # bg ← (1−α)·bg + α·frame
        return mask

    def background(self):
        return None if self.bg is None else np.clip(self.bg, 0, 255).astype(np.uint8)


class FrameDiffSubtractor:
    """연속 프레임 차영상. 움직이는 물체의 '가장자리'만 잡히고, 멈추면 즉시 사라진다."""

    def __init__(self, threshold=25):
        self.threshold = threshold
        self.prev = None

    def apply(self, frame, learning_rate=None):
        g = frame.astype(np.int16)
        if self.prev is None:
            self.prev = g
            return np.zeros(frame.shape[:2], np.uint8)
        diff = np.abs(g - self.prev).max(axis=2)
        self.prev = g
        return np.where(diff > self.threshold, 255, 0).astype(np.uint8)

    def background(self):
        return None


def make_subtractor(params):
    if params.method == "mog2":
        return cv2.createBackgroundSubtractorMOG2(params.history, params.var_threshold, params.detect_shadows)
    if params.method == "running_avg":
        return RunningAverageSubtractor(params.diff_threshold)
    if params.method == "frame_diff":
        return FrameDiffSubtractor(params.diff_threshold)
    raise ValueError(f"알 수 없는 배경 모델: {params.method}")


def foreground_mask(subtractor, frame, params):
    """배경 차분 원본 마스크. MOG2 그림자(127)는 배경으로 본다."""
    src = cv2.GaussianBlur(frame, (params.blur, params.blur), 0) if params.blur > 1 else frame
    raw = subtractor.apply(src, learningRate=params.learning_rate) if params.method == "mog2" \
        else subtractor.apply(src, params.learning_rate)
    return np.where(raw > 200, 255, 0).astype(np.uint8), raw


def clean_mask(mask, params):
    """열림(침식→팽창)으로 점 잡음을 지우고, 닫힘(팽창→침식)으로 한 사람의 조각을 한 덩어리로 잇는다."""
    out = mask
    if params.open_ksize > 1:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (params.open_ksize, params.open_ksize))
        out = cv2.morphologyEx(out, cv2.MORPH_OPEN, k)
    if params.close_ksize > 1:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (params.close_ksize, params.close_ksize))
        out = cv2.morphologyEx(out, cv2.MORPH_CLOSE, k)
    return out


def appearance_hist(frame, mask, bbox):
    """박스 안 전경 픽셀의 HSV 색상·채도 히스토그램 (밝기 V는 조명에 민감해서 뺀다). 합이 1."""
    x, y, w, h = bbox
    hsv = cv2.cvtColor(frame[y:y + h, x:x + w], cv2.COLOR_BGR2HSV)
    m = mask[y:y + h, x:x + w]
    hist = cv2.calcHist([hsv], [0, 1], m, [16, 8], [0, 180, 0, 256]).ravel()
    s = hist.sum()
    return hist / s if s > 0 else hist


def find_detections(mask, params, frame=None):
    """정리된 마스크에서 외곽 윤곽선을 찾고, 면적 필터를 통과한 것만 박스·중심점으로 바꾼다."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    dets = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < params.min_area:
            continue
        x, y, w, h = cv2.boundingRect(c)
        hist = appearance_hist(frame, mask, (x, y, w, h)) if params.compute_hist and frame is not None else None
        dets.append(Detection((x, y, w, h), (x + w / 2.0, y + h / 2.0), float(area), hist))
    return dets


class MotionDetector:
    """프레임 하나를 받아 (검출 목록, 정리된 마스크, 원본 마스크)를 돌려준다."""

    def __init__(self, params=None):
        self.params = params or MotionParams()
        self.subtractor = make_subtractor(self.params)

    def __call__(self, frame):
        mask, raw = foreground_mask(self.subtractor, frame, self.params)
        cleaned = clean_mask(mask, self.params)
        return find_detections(cleaned, self.params, frame), cleaned, raw

    def background(self):
        s = self.subtractor
        return s.getBackgroundImage() if hasattr(s, "getBackgroundImage") else s.background()
