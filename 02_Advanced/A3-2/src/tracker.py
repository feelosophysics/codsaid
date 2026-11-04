"""객체 추적기: 프레임마다 검출 결과를 이전 객체와 짝지어 고유 ID를 유지한다.

기본 동작 (미션 기능 4):
1. 이전 프레임 객체들과 현재 검출들 사이의 거리 행렬을 만든다 (중심점 유클리드 거리).
2. 가장 가까운 쌍부터 같은 ID로 잇는다 (탐욕 매칭). max_distance보다 먼 쌍은 잇지 않는다.
3. 짝이 없는 검출에는 새 ID를 준다.
4. 짝이 없는 객체는 missed를 1 늘리고, max_missed 프레임을 넘기면 지운다.
5. 객체마다 중심점 이동 경로(trail)를 저장한다.

비교 실험용 선택지:
- matcher="hungarian": 비용 합이 최소인 할당 (보너스 1, src/hungarian.py)
- cost="iou": 중심점 거리 대신 1 − IoU (보너스 3)
- kalman=True: cv2.KalmanFilter(등속 모델)로 다음 위치를 예측해 그 예측과 비교 (보너스 4)
- appearance_weight>0: 색 히스토그램 거리를 비용에 섞는다 (보고서 4장 '규칙 추가' 실험)
"""
from collections import OrderedDict, deque
from dataclasses import dataclass, field

import cv2
import numpy as np

from .hungarian import gated_assignment


def iou(a, b):
    """두 박스 (x, y, w, h)의 Intersection over Union."""
    ax0, ay0, aw, ah = a
    bx0, by0, bw, bh = b
    ix = max(0.0, min(ax0 + aw, bx0 + bw) - max(ax0, bx0))
    iy = max(0.0, min(ay0 + ah, by0 + bh) - max(ay0, by0))
    inter = ix * iy
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def iou_matrix(boxes_a, boxes_b):
    """박스 목록 둘의 IoU 행렬 (벡터화)."""
    if len(boxes_a) == 0 or len(boxes_b) == 0:
        return np.zeros((len(boxes_a), len(boxes_b)))
    a = np.asarray(boxes_a, float)[:, None, :]
    b = np.asarray(boxes_b, float)[None, :, :]
    ix = np.clip(np.minimum(a[..., 0] + a[..., 2], b[..., 0] + b[..., 2]) - np.maximum(a[..., 0], b[..., 0]), 0, None)
    iy = np.clip(np.minimum(a[..., 1] + a[..., 3], b[..., 1] + b[..., 3]) - np.maximum(a[..., 1], b[..., 1]), 0, None)
    inter = ix * iy
    union = a[..., 2] * a[..., 3] + b[..., 2] * b[..., 3] - inter
    return np.where(union > 0, inter / np.maximum(union, 1e-9), 0.0)


def bhattacharyya(h1, h2):
    """정규화된 히스토그램 두 개의 바타차리야 거리 (0 = 같음, 1 = 겹침 없음)."""
    bc = float(np.sum(np.sqrt(h1 * h2)))
    return float(np.sqrt(max(0.0, 1.0 - bc)))


def make_kalman(cx, cy, process_noise=0.05, measurement_noise=4.0):
    """상태 [x, y, vx, vy], 측정 [x, y]인 등속 칼만 필터 (float64: 학습 자료의 JS 구현과 같은 결과를 내기 위해)."""
    kf = cv2.KalmanFilter(4, 2, 0, cv2.CV_64F)
    kf.transitionMatrix = np.array([[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], np.float64)
    kf.measurementMatrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], np.float64)
    kf.processNoiseCov = np.eye(4) * process_noise
    kf.measurementNoiseCov = np.eye(2) * measurement_noise
    kf.errorCovPost = np.diag([10.0, 10.0, 100.0, 100.0])
    kf.statePost = np.array([[cx], [cy], [0.0], [0.0]])
    return kf


@dataclass
class Track:
    id: int
    bbox: tuple
    centroid: tuple
    trail: deque
    missed: int = 0                  # 연속으로 짝을 못 찾은 프레임 수
    hits: int = 1                    # 짝을 찾은 총 프레임 수
    age: int = 1                     # 생성 후 지난 프레임 수
    kf: object = field(default=None, repr=False)
    hist: np.ndarray = field(default=None, repr=False)
    predicted: tuple = None          # 이번 프레임 매칭에 쓴 예측 중심점

    @property
    def visible(self):
        return self.missed == 0


class Tracker:
    """중심점 거리 기반 다중 객체 추적기."""

    def __init__(self, max_distance=60.0, max_missed=20, trail_length=64, matcher="greedy", cost="centroid",
                 kalman=False, appearance_weight=0.0, min_iou=0.05):
        if matcher not in ("greedy", "hungarian"):
            raise ValueError("matcher는 greedy 또는 hungarian")
        if cost not in ("centroid", "iou"):
            raise ValueError("cost는 centroid 또는 iou")
        self.max_distance = float(max_distance)
        self.max_missed = int(max_missed)
        self.trail_length = int(trail_length)
        self.matcher = matcher
        self.cost = cost
        self.kalman = bool(kalman)
        self.appearance_weight = float(appearance_weight)
        self.min_iou = float(min_iou)
        self.tracks = OrderedDict()
        self.next_id = 1
        self.frame_index = -1

    # ---------------------------------------------------------- 내부 단계

    def _predict(self):
        """매칭 기준 위치. 칼만이면 등속 예측, 아니면 마지막으로 본 위치."""
        for t in self.tracks.values():
            if t.kf is not None:
                s = t.kf.predict()
                t.predicted = (float(s[0, 0]), float(s[1, 0]))
            else:
                t.predicted = t.centroid

    def _pred_box(self, t):
        dx, dy = t.predicted[0] - t.centroid[0], t.predicted[1] - t.centroid[1]
        x, y, w, h = t.bbox
        return (x + dx, y + dy, w, h)

    def cost_matrix(self, tracks, detections):
        """(행렬, 게이트). 게이트보다 큰 비용의 쌍은 짝짓지 않는다."""
        n, m = len(tracks), len(detections)
        if n == 0 or m == 0:
            return np.zeros((n, m)), 1.0
        if self.cost == "centroid":
            p = np.array([t.predicted for t in tracks], float)
            c = np.array([d.centroid for d in detections], float)
            dist = np.hypot(p[:, None, 0] - c[None, :, 0], p[:, None, 1] - c[None, :, 1])
            base, gate = dist / self.max_distance, 1.0            # 0~1로 정규화, 1 = max_distance
        else:
            ious = iou_matrix([self._pred_box(t) for t in tracks], [d.bbox for d in detections])
            base, gate = 1.0 - ious, 1.0 - self.min_iou
        if self.appearance_weight <= 0:
            return base, gate
        app = np.zeros((n, m))
        for i, t in enumerate(tracks):
            for j, d in enumerate(detections):
                if t.hist is not None and d.hist is not None:
                    app[i, j] = bhattacharyya(t.hist, d.hist)
        w = self.appearance_weight
        cost = (1 - w) * base + w * app
        # 위치 게이트는 그대로 유지한다. 통과한 쌍의 섞인 비용은 항상 1 이하다.
        return np.where(base <= gate, cost, 2.0), 1.0

    def _new_track(self, d):
        t = Track(self.next_id, d.bbox, d.centroid, deque([tuple(map(int, d.centroid))], maxlen=self.trail_length))
        if self.kalman:
            t.kf = make_kalman(*d.centroid)
        t.hist = d.hist
        self.tracks[t.id] = t
        self.next_id += 1
        return t

    # ---------------------------------------------------------- 공개 API

    def update(self, detections):
        """검출 목록(motion.Detection)으로 한 프레임 갱신. 현재 살아 있는 Track 목록을 돌려준다."""
        self.frame_index += 1
        self._predict()
        tracks = list(self.tracks.values())
        cost, gate = self.cost_matrix(tracks, detections)
        pairs, lost, new = gated_assignment(cost, gate, self.matcher)
        for i, j in pairs:
            t, d = tracks[i], detections[j]
            t.bbox, t.centroid = d.bbox, d.centroid
            t.trail.append(tuple(map(int, d.centroid)))
            t.missed = 0
            t.hits += 1
            if t.kf is not None:
                t.kf.correct(np.array([[d.centroid[0]], [d.centroid[1]]], np.float64))
            if d.hist is not None:
                t.hist = d.hist if t.hist is None else 0.8 * t.hist + 0.2 * d.hist
        for i in lost:
            t = tracks[i]
            t.missed += 1
            if t.missed > self.max_missed:
                del self.tracks[t.id]
        for j in new:
            self._new_track(detections[j])
        for t in self.tracks.values():
            t.age += 1
        return list(self.tracks.values())

    def visible_tracks(self):
        return [t for t in self.tracks.values() if t.visible]

    def reset(self):
        self.tracks.clear()
        self.next_id = 1
        self.frame_index = -1
