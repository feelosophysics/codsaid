"""프레임 하나를 분석하고 결과를 그린다: 배경 차분 → 객체 감지 → 추적 → 특징점 매칭 → 침입 구역.

앱(src/app.py), 헤드리스 실행, 테스트가 모두 이 클래스를 쓴다.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np

from .features import draw_match
from .motion import MotionDetector, MotionParams
from .tracker import Tracker

BOX = (60, 200, 60)        # 초록 박스
TRAIL = (40, 40, 230)      # 빨간 궤적


def id_color(tid):
    """ID마다 고정된 색 (ID가 바뀌는 순간을 눈으로 알아보기 위해 라벨 바탕에 쓴다)."""
    rng = np.random.default_rng(tid * 7919)
    c = rng.uniform(60, 255, 3)
    return tuple(int(v) for v in c)


@dataclass
class FrameResult:
    index: int
    detections: list
    tracks: list                   # 이번 프레임에 검출과 짝지어진 추적
    coasting: list                 # 짝은 없지만 아직 지우지 않은 추적
    mask: np.ndarray = field(repr=False)
    raw_mask: np.ndarray = field(repr=False)
    target: object = None          # features.MatchResult
    zone_events: list = field(default_factory=list)


class VideoAnalyzer:
    def __init__(self, motion=None, tracker=None, target_matcher=None, zone=None, target_every=1):
        self.motion_params = motion or MotionParams()
        self.detector = MotionDetector(self.motion_params)
        self.tracker = tracker or Tracker()
        self.target_matcher = target_matcher
        self.zone = zone
        self.target_every = max(1, int(target_every))
        self.index = -1
        self._last_target = None

    def set_learning_rate(self, lr):
        self.motion_params.learning_rate = lr

    def process(self, frame):
        self.index += 1
        dets, mask, raw = self.detector(frame)
        self.tracker.update(dets)
        tracks = self.tracker.visible_tracks()
        coasting = [t for t in self.tracker.tracks.values() if not t.visible]
        if self.target_matcher is not None and self.index % self.target_every == 0:
            self._last_target = self.target_matcher.match(frame)
        events = []
        if self.zone is not None:
            events = self.zone.update(tracks, self.index, alive_ids=set(self.tracker.tracks))
        return FrameResult(self.index, dets, tracks, coasting, mask, raw, self._last_target, events)

    def draw(self, frame, res, fps=None, proc_fps=None, paused=False, show_coasting=True):
        out = frame.copy()
        if self.zone is not None:
            self.zone.draw(out)
        for t in res.tracks:
            if len(t.trail) > 1:
                cv2.polylines(out, [np.int32(t.trail)], False, TRAIL, 2, cv2.LINE_AA)
        if show_coasting:
            for t in res.coasting:
                p = t.predicted or t.centroid
                cv2.circle(out, (int(p[0]), int(p[1])), 4, (160, 160, 160), 1, cv2.LINE_AA)
                cv2.putText(out, f"{t.id}?", (int(p[0]) + 5, int(p[1]) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                            (160, 160, 160), 1, cv2.LINE_AA)
        for t in res.tracks:
            x, y, w, h = t.bbox
            cv2.rectangle(out, (x, y), (x + w, y + h), BOX, 2)
            label = f"ID:{t.id}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(out, (x, y - th - 6), (x + tw + 6, y), id_color(t.id), -1)
            cv2.putText(out, label, (x + 3, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
            cv2.circle(out, (int(t.centroid[0]), int(t.centroid[1])), 3, TRAIL, -1, cv2.LINE_AA)
        if res.target is not None:
            draw_match(out, res.target)
        lines = []
        if fps is not None:
            lines.append(f"FPS: {fps:.1f}" + (f"  (proc {proc_fps:.0f})" if proc_fps else ""))
        lr = self.motion_params.learning_rate
        lines.append(f"{self.motion_params.method} lr={lr:g}  objects={len(res.tracks)}")
        if paused:
            lines.append("PAUSED")
        for k, s in enumerate(lines):
            cv2.putText(out, s, (10, 22 + 20 * k), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(out, s, (10, 22 + 20 * k), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        return out
