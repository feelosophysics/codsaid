"""미션 요구사항별 테스트. 실행: python -m unittest discover -s tests -v"""
import ast
import csv
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from src import evaluate as E
from src import synthetic as S
from src.app import FpsMeter, handle_key, main as app_main
from src.features import TargetMatcher, is_convex_quad, make_view, score_view
from src.hungarian import brute_force, gated_assignment, greedy, hungarian
from src.motion import Detection, MotionDetector, MotionParams, RunningAverageSubtractor
from src.pipeline import VideoAnalyzer
from src.tracker import Tracker, iou, iou_matrix
from src.zone import IntrusionZone

ROOT = Path(__file__).resolve().parents[1]
cv2.setNumThreads(1)


def det(cx, cy, w=30, h=80, hist=None):
    return Detection((int(cx - w / 2), int(cy - h / 2), w, h), (float(cx), float(cy)), float(w * h), hist)


class TestTracker(unittest.TestCase):
    """기능 4: Tracker 클래스 (tracker.py)"""

    def test_tracker_is_separate_file_with_class(self):
        tree = ast.parse((ROOT / "src" / "tracker.py").read_text(encoding="utf-8"))
        self.assertIn("Tracker", [n.name for n in tree.body if isinstance(n, ast.ClassDef)])

    def test_new_object_gets_new_id_and_keeps_it_while_moving(self):
        tr = Tracker(max_distance=50)
        tr.update([det(100, 100)])
        tr.update([det(100, 100), det(400, 100)])
        ids = {t.id for t in tr.visible_tracks()}
        self.assertEqual(ids, {1, 2})
        for k in range(1, 20):
            tr.update([det(100 + 5 * k, 100), det(400 - 5 * k, 100)])
        pos = {t.id: t.centroid[0] for t in tr.visible_tracks()}
        self.assertEqual(pos, {1: 195.0, 2: 305.0})

    def test_nearest_pair_is_matched_first(self):
        tr = Tracker(max_distance=100)
        tr.update([det(100, 100), det(200, 100)])
        tr.update([det(190, 100), det(110, 100)])     # 순서를 바꿔 넣어도 가까운 쪽으로 이어진다
        pos = {t.id: t.centroid[0] for t in tr.visible_tracks()}
        self.assertEqual(pos, {1: 110.0, 2: 190.0})

    def test_far_detection_beyond_max_distance_gets_new_id(self):
        tr = Tracker(max_distance=40)
        tr.update([det(100, 100)])
        tr.update([det(150, 100)])
        self.assertEqual(sorted(t.id for t in tr.tracks.values()), [1, 2])

    def test_disappeared_object_is_deleted_after_max_missed(self):
        tr = Tracker(max_missed=3)
        tr.update([det(100, 100)])
        for k in range(3):
            tr.update([])
            self.assertIn(1, tr.tracks)
        tr.update([])
        self.assertNotIn(1, tr.tracks)
        tr.update([det(100, 100)])
        self.assertEqual(list(tr.tracks), [2])          # 다시 나타나면 새 ID

    def test_trail_is_stored_and_capped(self):
        tr = Tracker(trail_length=10)
        for k in range(30):
            tr.update([det(100 + k, 100)])
        t = tr.tracks[1]
        self.assertEqual(len(t.trail), 10)
        self.assertEqual(t.trail[-1], (129, 100))

    def test_kalman_predicts_through_short_gap(self):
        """칼만: 검출이 끊긴 동안 등속으로 예측해, 다시 나타난 위치(먼 곳)와 이어 준다."""
        plain, kal = Tracker(max_distance=30), Tracker(max_distance=30, kalman=True)
        for tr in (plain, kal):
            for k in range(20):
                tr.update([det(100 + 6 * k, 100)])
            for _ in range(6):
                tr.update([])
            tr.update([det(100 + 6 * 26, 100)])
        self.assertEqual([t.id for t in kal.visible_tracks()], [1])
        self.assertEqual([t.id for t in plain.visible_tracks()], [2])

    def test_iou_cost_and_matrix(self):
        self.assertAlmostEqual(iou((0, 0, 10, 10), (5, 0, 10, 10)), 50 / 150)
        self.assertEqual(iou((0, 0, 10, 10), (20, 20, 5, 5)), 0.0)
        m = iou_matrix([(0, 0, 10, 10), (5, 5, 10, 10)], [(0, 0, 10, 10)])
        np.testing.assert_allclose(m[:, 0], [1.0, 25 / 175])
        tr = Tracker(cost="iou", min_iou=0.2)
        tr.update([det(100, 100)])
        tr.update([det(105, 100)])
        self.assertEqual(list(tr.tracks), [1])

    def test_appearance_weight_separates_equal_distances(self):
        red, blue = np.zeros(128), np.zeros(128)
        red[3], blue[100] = 1, 1
        tr = Tracker(max_distance=100, appearance_weight=0.6)
        tr.update([det(100, 100, hist=red), det(140, 100, hist=blue)])
        tr.update([det(140, 100, hist=red), det(100, 100, hist=blue)])   # 자리를 바꿨다: 위치만으론 반대로 잇는다
        pos = {t.id: t.centroid[0] for t in tr.visible_tracks()}
        self.assertEqual(pos, {1: 140.0, 2: 100.0})


class TestHungarian(unittest.TestCase):
    """보너스 1: NumPy만으로 구현한 Hungarian"""

    def test_matches_brute_force_on_random_matrices(self):
        rng = np.random.default_rng(1)
        for _ in range(200):
            n, m = rng.integers(1, 6, 2)
            c = rng.integers(0, 9, (n, m)).astype(float)
            r, k = hungarian(c)
            self.assertEqual(len(r), min(n, m))
            self.assertEqual(len(set(k)), len(k))
            self.assertAlmostEqual(c[r, k].sum(), brute_force(c))

    def test_greedy_can_be_suboptimal(self):
        c = np.array([[1.0, 2.0], [2.0, 100.0]])
        r, k = greedy(c)
        self.assertEqual(c[r, k].sum(), 101.0)
        r, k = hungarian(c)
        self.assertEqual(c[r, k].sum(), 4.0)

    def test_gate_leaves_far_pairs_unmatched(self):
        c = np.array([[0.1, 5.0], [5.0, 5.0]])
        for method in ("greedy", "hungarian"):
            pairs, rows, cols = gated_assignment(c, 1.0, method)
            self.assertEqual(pairs, [(0, 0)])
            self.assertEqual((rows, cols), ([1], [1]))

    def test_no_scipy_import(self):
        src = (ROOT / "src" / "hungarian.py").read_text(encoding="utf-8")
        self.assertNotIn("scipy", src.split('"""', 2)[2])


def moving_box_frames(n=60, stop_from=None):
    """회색 배경 위를 지나가는 어두운 사각형."""
    rng = np.random.default_rng(0)
    bg = np.full((180, 320, 3), 150, np.uint8)
    frames = []
    for i in range(n):
        f = bg.copy()
        x = 20 + 3 * (i if stop_from is None else min(i, stop_from))
        if i >= 10:
            cv2.rectangle(f, (x, 60), (x + 24, 130), (40, 60, 200), -1)
        f = np.clip(f + rng.normal(0, 2, f.shape), 0, 255).astype(np.uint8)
        frames.append((f, x))
    return frames


class TestMotion(unittest.TestCase):
    """기능 2·3: 배경 차분, 모폴로지, 윤곽선·면적 필터, 박스와 중심점"""

    def test_mog2_detects_moving_box(self):
        dm = MotionDetector(MotionParams(min_area=200))
        for f, x in moving_box_frames():
            dets, mask, raw = dm(f)
        self.assertEqual(len(dets), 1)
        bx, by, bw, bh = dets[0].bbox
        self.assertLess(abs(bx - x), 4)
        self.assertLess(abs(bh - 71), 6)
        self.assertEqual(dets[0].centroid, (bx + bw / 2, by + bh / 2))

    def test_area_filter_ignores_small_motion(self):
        dm = MotionDetector(MotionParams(min_area=5000))
        for f, _ in moving_box_frames():
            dets, _, _ = dm(f)
        self.assertEqual(dets, [])

    def test_all_background_methods_run(self):
        for method in ("mog2", "running_avg", "frame_diff"):
            dm = MotionDetector(MotionParams(method=method, min_area=150))
            for f, _ in moving_box_frames(40):
                dets, mask, _ = dm(f)
            self.assertGreaterEqual(len(dets), 1, method)
            self.assertEqual(mask.dtype, np.uint8)

    def test_higher_learning_rate_absorbs_stopped_object_sooner(self):
        """학습률이 클수록 멈춘 물체가 빨리 배경이 된다 (기능 2: 학습률 3가지 이상 관찰)."""
        lasted = {}
        for lr in (0.001, 0.01, 0.1):
            dm = MotionDetector(MotionParams(learning_rate=lr, min_area=200))
            n = 0
            for i, (f, _) in enumerate(moving_box_frames(250, stop_from=20)):
                dets, _, _ = dm(f)
                if i >= 20 and dets:
                    n += 1
            lasted[lr] = n
        self.assertGreater(lasted[0.001], lasted[0.01])
        self.assertGreater(lasted[0.01], lasted[0.1])

    def test_running_average_update_rule(self):
        s = RunningAverageSubtractor(threshold=10)
        a = np.full((4, 4, 3), 100, np.uint8)
        s.apply(a)
        s.apply(np.full((4, 4, 3), 200, np.uint8), 0.25)
        self.assertAlmostEqual(float(s.bg[0, 0, 0]), 125.0)


class TestFeatures(unittest.TestCase):
    """기능 5: ORB/SIFT 특징점 매칭과 TARGET DETECTED"""

    @classmethod
    def setUpClass(cls):
        cls.tex = S.make_cover(7, "OPEN CV")
        cls.bg = S.make_background(np.random.default_rng(3))

    def test_target_found_in_frontal_view(self):
        for method in ("orb", "sift"):
            m = TargetMatcher(self.tex, method)
            img, c, H = make_view(self.tex, self.bg, 320, 180)
            r = score_view(m, img, H, c)
            self.assertTrue(r["localized"], method)
            self.assertGreater(r["n_correct"], 20)

    def test_not_found_without_target(self):
        m = TargetMatcher(self.tex, "orb")
        scene = np.clip(self.bg, 0, 255).astype(np.uint8)
        self.assertFalse(m.match(scene).found)

    def test_convexity(self):
        self.assertTrue(is_convex_quad([[0, 0], [10, 0], [10, 10], [0, 10]]))
        self.assertFalse(is_convex_quad([[0, 0], [10, 10], [10, 0], [0, 10]]))


class TestEvaluation(unittest.TestCase):
    """기능 6: ID Switch·추적 실패 판정 기준"""

    def test_switch_needs_five_frames(self):
        sw, _ = E.stable_switches([1] * 10 + [2] * 4 + [1] * 10)
        self.assertEqual(sw, [])
        sw, _ = E.stable_switches([1] * 10 + [2] * 5 + [1] * 10)
        self.assertEqual(sw, [(10, 1, 2), (15, 2, 1)])
        sw, _ = E.stable_switches([1] * 5 + [None, E.MERGED] * 10 + [1] * 5)
        self.assertEqual(sw, [])

    def test_failure_needs_ten_visible_frames(self):
        self.assertEqual(E.failure_runs([1] * 5 + [None] * 9 + [1], [1.0] * 15), [])
        self.assertEqual(E.failure_runs([1] * 5 + [None] * 10 + [1], [1.0] * 16), [(5, 14)])
        vis = [1.0] * 5 + [1.0] * 5 + [0.3] + [1.0] * 5 + [1.0]
        self.assertEqual(E.failure_runs([1] * 5 + [None] * 11 + [1], vis), [])   # 가림 프레임이 구간을 끊는다

    def test_merged_box_is_not_assigned_to_either_person(self):
        gt = [{"id": "A", "bbox": [100, 50, 30, 80], "vis": 1.0}, {"id": "B", "bbox": [115, 55, 30, 80], "vis": 0.8}]
        m = E.match_frame(gt, [(7, (98, 48, 50, 90), (123, 93))])
        self.assertEqual(m, {"A": E.MERGED, "B": E.MERGED})
        m = E.match_frame(gt, [(7, (100, 50, 30, 80), (115, 90)), (8, (115, 55, 30, 80), (130, 95))])
        self.assertEqual(m, {"A": 7, "B": 8})


class TestSynthetic(unittest.TestCase):
    """테스트 영상 가이드: 시나리오별 20~30초, 이벤트 수가 표의 테스트 횟수와 같다"""

    def test_scenarios_match_report_table(self):
        expect = {"single": 10, "crossing": 10, "crossing_same": 10, "pause": 5, "lighting": 5}
        for split in S.SPLITS:
            for sc, n in expect.items():
                path = S.DATA / f"{sc}_{split}.json"
                if not path.exists():
                    self.skipTest("합성 영상이 없다 (python -m src.synthetic)")
                gt = S.load_gt(sc, split)
                counted = [e for e in gt["events"] if not e.get("extra")]
                self.assertEqual(len(counted), n, (sc, split))
                self.assertTrue(20 * S.FPS <= gt["frames"] <= 30 * S.FPS, (sc, split, gt["frames"]))
                self.assertEqual(len(gt["gt"]), gt["frames"])

    def test_renderer_is_deterministic_and_ground_truth_matches_mask(self):
        sc = S.build("crossing", "dev")
        r = S.Renderer(sc)
        a, gta, ma = r.frame(120)
        b, gtb, mb = r.frame(120)
        np.testing.assert_array_equal(a, b)
        self.assertEqual(gta, gtb)
        for o in gta:
            x, y, w, h = o["bbox"]
            self.assertTrue(ma[y:y + h, x:x + w].any())


class TestAppAndZone(unittest.TestCase):
    """기능 1(입출력·FPS·키)과 보너스 2(침입 구역)"""

    def test_keys(self):
        an = VideoAnalyzer(MotionParams(learning_rate=0.004))
        st = {"paused": False, "show_mask": False}
        self.assertEqual(handle_key(ord("q"), st, an), "quit")
        self.assertEqual(handle_key(27, st, an), "quit")
        self.assertEqual(handle_key(ord("s"), st, an), "snapshot")
        handle_key(ord("p"), st, an)
        self.assertTrue(st["paused"])
        self.assertEqual(handle_key(ord("n"), st, an), "step")
        handle_key(ord("]"), st, an)
        self.assertAlmostEqual(an.motion_params.learning_rate, 0.008)

    def test_fps_meter(self):
        m = FpsMeter(alpha=1.0)
        m.tick(0.0)
        self.assertAlmostEqual(m.tick(0.04), 25.0)

    def test_zone_enter_exit_and_log(self):
        with tempfile.TemporaryDirectory() as d:
            z = IntrusionZone((100, 100, 50, 50), log_path=Path(d) / "log.csv", echo=False)
            tr = Tracker(max_distance=200)
            evs = []
            for x in (50, 90, 120, 140, 200, 240):
                tr.update([det(x, 125)])
                evs += [(e[0], e[1]) for e in z.update(tr.visible_tracks(), 0)]
            z.close()
            self.assertEqual(evs, [("enter", 1), ("exit", 1)])
            with (Path(d) / "log.csv").open(encoding="utf-8-sig") as fh:
                rows = list(csv.reader(fh))
            self.assertEqual([r[3] for r in rows[1:]], ["enter", "exit"])

    def test_headless_run_writes_video(self):
        src = S.DATA / "single_test.mp4"
        if not src.exists():
            self.skipTest("합성 영상이 없다")
        with tempfile.TemporaryDirectory() as d:
            out = app_main(["--source", str(src), "--no-gui", "--out", d, "--max-frames", "45", "--snap-every", "40",
                            "--threads", "1"])
            self.assertEqual(out["frames"], 45)
            self.assertTrue((Path(d) / "annotated.mp4").stat().st_size > 1000)
            self.assertTrue((Path(d) / "snapshot_00040.png").exists())


class TestConstraints(unittest.TestCase):
    """제약: 딥러닝 탐지 모델·dnn 모듈·고수준 AI 라이브러리 금지"""

    def test_no_forbidden_imports_or_dnn(self):
        banned = ("torch", "tensorflow", "keras", "ultralytics", "mediapipe", "onnxruntime", "sklearn", "scipy")
        for path in list((ROOT / "src").glob("*.py")) + list((ROOT / "tools").glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    names = []
                for n in names:
                    self.assertFalse(n.split(".")[0] in banned, f"{path.name}: {n}")
                if isinstance(node, ast.Attribute) and node.attr == "dnn":
                    self.fail(f"{path.name}: cv2.dnn 사용")


if __name__ == "__main__":
    unittest.main()
