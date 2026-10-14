"""특징점 매칭으로 등록 물체 재인식 (미션 기능 5).

1. 등록 이미지에서 ORB(또는 SIFT) 특징점과 기술자를 미리 뽑는다.
2. 매 프레임 특징점을 뽑고, 기술자마다 가장 가까운 두 후보를 찾는다 (BFMatcher.knnMatch, k=2).
3. 비율 검정(Lowe): 1등 거리 < ratio × 2등 거리인 매칭만 남긴다. 애매한 매칭을 버리는 단계다.
4. 남은 매칭으로 RANSAC 호모그래피를 구해, 같은 평면 변환에 맞는 매칭(inlier)만 센다.
5. inlier가 min_inliers 이상이고 투영한 사각형이 볼록하면 "TARGET DETECTED".

ORB: FAST 코너 + 방향을 맞춘 BRIEF(256비트 밝기 비교). 해밍 거리로 비교한다.
SIFT: DoG 극값 + 128차원 기울기 방향 히스토그램. L2 거리로 비교한다. OpenCV 4.4부터 기본 패키지에 있다.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np


@dataclass
class MatchResult:
    found: bool
    n_scene: int                    # 프레임 전체 특징점 수
    n_good: int                     # 비율 검정 통과
    n_inliers: int                  # RANSAC inlier
    corners: np.ndarray = None      # 등록 이미지 네 꼭짓점의 프레임 좌표 (TL, TR, BR, BL)
    H: np.ndarray = None
    ref_pts: np.ndarray = field(default=None, repr=False)     # 비율 검정 통과 매칭의 등록 이미지 좌표
    scene_pts: np.ndarray = field(default=None, repr=False)   # 같은 매칭의 프레임 좌표
    inlier_mask: np.ndarray = field(default=None, repr=False)
    scene_kp: tuple = field(default=(), repr=False)


def make_detector(method, nfeatures):
    if method == "orb":
        return cv2.ORB_create(nfeatures=nfeatures), cv2.NORM_HAMMING
    if method == "sift":
        return cv2.SIFT_create(nfeatures=nfeatures), cv2.NORM_L2
    raise ValueError(f"알 수 없는 특징점 방법: {method}")


def is_convex_quad(q):
    q = np.asarray(q, float)
    cross = []
    for i in range(4):
        a, b, c = q[i], q[(i + 1) % 4], q[(i + 2) % 4]
        cross.append((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]))
    return all(c > 0 for c in cross) or all(c < 0 for c in cross)


def polygon_area(q):
    x, y = np.asarray(q, float).T
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


class TargetMatcher:
    def __init__(self, target_bgr, method="orb", nfeatures=1000, ratio=0.75, min_inliers=12, ransac_thresh=5.0):
        self.method = method
        self.ratio = ratio
        self.min_inliers = min_inliers
        self.ransac_thresh = ransac_thresh
        self.detector, norm = make_detector(method, nfeatures)
        self.matcher = cv2.BFMatcher(norm)
        gray = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2GRAY) if target_bgr.ndim == 3 else target_bgr
        self.ref_size = gray.shape[::-1]
        self.ref_kp, self.ref_des = self.detector.detectAndCompute(gray, None)
        if self.ref_des is None or len(self.ref_kp) < 4:
            raise ValueError("등록 이미지에서 특징점을 4개 이상 찾지 못했다 (무늬가 더 많은 이미지를 쓴다)")
        w, h = self.ref_size
        self.ref_corners = np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]])

    @property
    def n_ref(self):
        return len(self.ref_kp)

    def match(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        kp, des = self.detector.detectAndCompute(gray, None)
        res = MatchResult(False, len(kp), 0, 0, scene_kp=kp)
        if des is None or len(kp) < 2:
            return res
        good = []
        for pair in self.matcher.knnMatch(self.ref_des, des, k=2):
            if len(pair) == 2 and pair[0].distance < self.ratio * pair[1].distance:
                good.append(pair[0])
        res.n_good = len(good)
        if not good:
            return res
        res.ref_pts = np.float32([self.ref_kp[m.queryIdx].pt for m in good])
        res.scene_pts = np.float32([kp[m.trainIdx].pt for m in good])
        if len(good) < 4:
            return res
        H, mask = cv2.findHomography(res.ref_pts, res.scene_pts, cv2.RANSAC, self.ransac_thresh)
        if H is None:
            return res
        res.inlier_mask = mask.ravel().astype(bool)
        res.n_inliers = int(res.inlier_mask.sum())
        if res.n_inliers >= 8:  # RANSAC은 최소 표본 4점으로 고른 모델이다. inlier 전체로 최소제곱 재추정한다.
            H2, _ = cv2.findHomography(res.ref_pts[res.inlier_mask], res.scene_pts[res.inlier_mask], 0)
            H = H2 if H2 is not None else H
        res.H = H
        res.corners = cv2.perspectiveTransform(self.ref_corners[None], H)[0]
        area = polygon_area(res.corners)
        res.found = (res.n_inliers >= self.min_inliers and is_convex_quad(res.corners)
                     and 0.002 * gray.size < area < 1.5 * gray.size)
        return res


def draw_match(frame, res, color=(0, 0, 255)):
    """찾은 물체의 사각형과 "TARGET DETECTED" 문구."""
    if res.found:
        cv2.polylines(frame, [np.int32(res.corners)], True, color, 2, cv2.LINE_AA)
        cv2.putText(frame, f"TARGET DETECTED ({res.n_inliers})", (10, frame.shape[0] - 14), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, color, 2, cv2.LINE_AA)
    return frame


# ---------------------------------------------------------------- 정량 실험용 장면

def make_view(texture, background, cx, cy, scale=0.55, roll=0.0, yaw=0.0, occlusion=0.0, occ_side=0, brightness=1.0,
              blur=0.0, rng=None, noise=2.2, jpeg=85):
    """배경 위에 물체를 놓은 시험 장면. (영상, 정답 꼭짓점, 정답 호모그래피(등록 이미지 → 장면)) 반환.

    occlusion: 물체 면적 중 가리는 비율. occ_side(0~3)쪽에서 매끈한 판(손·상자)이 덮는다.
    """
    from .synthetic import card_corners, warp_layer
    rng = rng or np.random.default_rng(0)
    th, tw = texture.shape[:2]
    corners = card_corners(cx, cy, scale, roll, yaw, size=(tw, th))
    colr, a = warp_layer(texture, corners)
    img = background.astype(np.float32) * (1 - a[..., None]) + colr
    if occlusion > 0:
        hgt, wid = a.shape
        yy, xx = np.mgrid[0:hgt, 0:wid].astype(np.float32)
        ang = occ_side * np.pi / 2 + rng.uniform(-0.25, 0.25)
        d = (xx - cx) * np.cos(ang) + (yy - cy) * np.sin(ang)      # 가리는 방향으로의 좌표
        obj = a > 0.5
        dv = np.sort(d[obj])[::-1]
        thr = dv[min(len(dv) - 1, int(occlusion * len(dv)))]       # 위에서부터 occlusion 비율만큼
        x0, y0 = np.min(corners, 0) - 15
        x1, y1 = np.max(corners, 0) + 15
        occ = (d >= thr) & (xx >= x0) & (xx <= x1) & (yy >= y0) & (yy <= y1)
        base = rng.uniform(70, 200, 3).astype(np.float32)
        shade = 1 + 0.08 * cv2.GaussianBlur(rng.normal(0, 1, (hgt, wid)).astype(np.float32), (0, 0), 6)
        img[occ] = (base[None, :] * shade[occ][:, None])
    img *= brightness
    if blur > 0:
        img = cv2.GaussianBlur(img, (0, 0), blur)
    img += rng.normal(0, noise, img.shape)
    img = np.clip(img + 0.5, 0, 255).astype(np.uint8)
    if jpeg:
        img = cv2.imdecode(cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, jpeg])[1], cv2.IMREAD_COLOR)
    src = np.float32([[0, 0], [tw - 1, 0], [tw - 1, th - 1], [0, th - 1]])
    return img, corners, cv2.getPerspectiveTransform(src, np.float32(corners))


def score_view(matcher, image, H_gt, corners_gt, tol=5.0):
    """특징점 매칭 성능: 등록·장면 특징점 수, 비율 검정 통과, 정답 매칭(정답 호모그래피 재투영 오차 < tol px)."""
    res = matcher.match(image)
    poly = np.float32(corners_gt).reshape(-1, 1, 2)
    in_target = sum(1 for k in res.scene_kp if cv2.pointPolygonTest(poly, k.pt, False) >= 0)
    correct = 0
    if res.n_good:
        proj = cv2.perspectiveTransform(res.ref_pts[None], H_gt)[0]
        correct = int((np.linalg.norm(proj - res.scene_pts, axis=1) < tol).sum())
    corner_err = float(np.linalg.norm(res.corners - corners_gt, axis=1).mean()) if res.corners is not None else None
    ok = bool(res.found and corner_err is not None and corner_err < 10.0)
    return {"n_ref": matcher.n_ref, "n_scene": res.n_scene, "n_scene_target": in_target, "n_good": res.n_good,
            "n_correct": correct, "n_inliers": res.n_inliers, "found": bool(res.found), "localized": ok,
            "corner_error": corner_err, "match_rate": correct / matcher.n_ref,
            "precision": correct / res.n_good if res.n_good else 0.0}
