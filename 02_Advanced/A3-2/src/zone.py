"""침입 감지 구역 (보너스 2).

마우스로 사각형을 끌어 구역을 정한다. 추적 객체의 중심점이 구역에 들어오면 화면에 경고를 띄우고,
들어감·나감을 CSV 로그(시각, 프레임, ID, 이벤트, 좌표)로 남긴다.
"""
import csv
import time
from pathlib import Path

import cv2


class IntrusionZone:
    def __init__(self, rect=None, log_path=None, echo=True):
        self.rect = tuple(int(v) for v in rect) if rect else None
        self.inside = set()
        self.events = []
        self.log_path = Path(log_path) if log_path else None
        self.echo = echo
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            new = not self.log_path.exists()
            self._fh = self.log_path.open("a", newline="", encoding="utf-8-sig")
            self._csv = csv.writer(self._fh)
            if new:
                self._csv.writerow(["time", "frame", "track_id", "event", "cx", "cy", "zone"])
        else:
            self._fh = self._csv = None

    def set(self, rect):
        x, y, w, h = rect
        if w < 0:
            x, w = x + w, -w
        if h < 0:
            y, h = y + h, -h
        self.rect = (int(x), int(y), int(w), int(h)) if w > 3 and h > 3 else None
        self.inside.clear()

    def clear(self):
        self.rect = None
        self.inside.clear()

    def contains(self, point):
        if self.rect is None:
            return False
        x, y, w, h = self.rect
        return x <= point[0] <= x + w and y <= point[1] <= y + h

    def update(self, tracks, frame_index, alive_ids=None):
        """보이는 추적 객체(tracks)로 구역 상태를 갱신하고 이번 프레임의 들어감·나감 이벤트를 돌려준다.

        alive_ids: 아직 지워지지 않은 전체 추적 ID. 구역 안에서 잠깐 가려진 객체는 계속 '안'으로 둔다.
        """
        if self.rect is None:
            return []
        now_inside = {t.id: t.centroid for t in tracks if self.contains(t.centroid)}
        visible = {t.id for t in tracks}
        out = []
        for tid, c in now_inside.items():
            if tid not in self.inside:
                out.append(("enter", tid, c))
        for tid in self.inside - set(now_inside):
            # 가려져서 안 보이는 경우는 나감으로 치지 않는다 (사라진 추적은 다음 갱신에서 정리)
            if tid in visible:
                t = next(t for t in tracks if t.id == tid)
                out.append(("exit", tid, t.centroid))
        hidden = {i for i in self.inside if i not in visible and (alive_ids is None or i in alive_ids)}
        self.inside = hidden | set(now_inside)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        for ev, tid, (cx, cy) in out:
            rec = {"time": ts, "frame": frame_index, "track_id": tid, "event": ev, "cx": round(cx, 1),
                   "cy": round(cy, 1), "zone": self.rect}
            self.events.append(rec)
            if self._csv:
                self._csv.writerow([ts, frame_index, tid, ev, rec["cx"], rec["cy"], "x{0} y{1} w{2} h{3}".format(*self.rect)])
                self._fh.flush()
            if self.echo and ev == "enter":
                print(f"[경고] 침입 감지: ID {tid} (프레임 {frame_index}, 중심 {cx:.0f},{cy:.0f})", flush=True)
        return out

    def draw(self, frame):
        if self.rect is None:
            return frame
        x, y, w, h = self.rect
        alarm = bool(self.inside)
        color = (0, 0, 255) if alarm else (0, 220, 255)
        if alarm:
            overlay = frame.copy()
            cv2.rectangle(overlay, (x, y), (x + w, y + h), color, -1)
            cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
            ids = ",".join(str(i) for i in sorted(self.inside))
            cv2.putText(frame, f"INTRUSION! ID {ids}", (x + 4, max(14, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        color, 2, cv2.LINE_AA)
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        return frame

    def close(self):
        if self._fh:
            self._fh.close()
            self._fh = None


class ZoneSelector:
    """창에서 왼쪽 버튼을 끌어 구역을 그린다. scale은 표시 배율(처리 해상도 → 창 좌표)."""

    def __init__(self, zone, scale=1.0):
        self.zone = zone
        self.scale = scale
        self.start = None
        self.preview = None

    def __call__(self, event, x, y, flags, param):
        x, y = x / self.scale, y / self.scale
        if event == cv2.EVENT_LBUTTONDOWN:
            self.start = (x, y)
            self.preview = None
        elif event == cv2.EVENT_MOUSEMOVE and self.start is not None:
            self.preview = (self.start[0], self.start[1], x - self.start[0], y - self.start[1])
        elif event == cv2.EVENT_LBUTTONUP and self.start is not None:
            self.zone.set((self.start[0], self.start[1], x - self.start[0], y - self.start[1]))
            self.start = self.preview = None

    def draw(self, frame):
        if self.preview is not None:
            x, y, w, h = (int(v) for v in self.preview)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 0), 1, cv2.LINE_AA)
        return frame
