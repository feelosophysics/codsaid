"""미션 요구사항별 검증. 실행: python -m unittest discover -s tests -v"""
import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import convolution, eda, evaluate, geometry  # noqa: E402
from src.image_io import imread, imwrite  # noqa: E402
from src.pdf_export import save_pdf  # noqa: E402
from src.scanner import ScanParams, enhance, scan, stage_images  # noqa: E402
from src.synthetic import CASES, render_case  # noqa: E402

DATA = ROOT / "data" / "synthetic"


def rotated_rect(cx, cy, w, h, deg):
    """중심·크기·회전각으로 TL, TR, BR, BL을 만든다 (회전 0이면 화면과 정렬)."""
    t = np.radians(deg)
    r = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
    base = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]])
    return base @ r.T + [cx, cy]


def projected_quad(w_mm=210, h_mm=280, pitch=35, yaw=10, roll=-8, size=(900, 700), f=800.0, dist=520.0):
    """실제 핀홀 카메라(주점 = 이미지 중심)로 종이를 찍었을 때의 네 꼭짓점."""
    from src.synthetic import rotation
    pts = np.array([[-w_mm / 2, -h_mm / 2, 0], [w_mm / 2, -h_mm / 2, 0], [w_mm / 2, h_mm / 2, 0], [-w_mm / 2, h_mm / 2, 0]])
    cam = pts @ rotation(pitch, yaw, roll).T + [0, 0, dist]
    return cam[:, :2] / cam[:, 2:] * f + [size[1] / 2, size[0] / 2]


def synthetic_scene(quad, size=(900, 700), bg=60, paper=235):
    """단색 배경 위 흰 사각형 하나와 글자 몇 줄."""
    h, w = size
    img = np.full((h, w, 3), bg, np.uint8)
    doc = np.full((400, 300, 3), paper, np.uint8)
    for i in range(8):
        cv2.putText(doc, "scan test line", (20, 50 + 40 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 30), 2)
    src = np.float32([[0, 0], [300, 0], [300, 400], [0, 400]])
    m = cv2.getPerspectiveTransform(src, np.float32(quad))
    warped = cv2.warpPerspective(doc, m, (w, h))
    mask = cv2.warpPerspective(np.ones((400, 300), np.uint8), m, (w, h)).astype(bool)
    img[mask] = warped[mask]
    return img


class TestCoordinateOrdering(unittest.TestCase):
    """기능 5: 좌상-우상-우하-좌하 정렬을 기하학적으로 직접 구현."""

    def test_order_any_input_permutation(self):
        rng = np.random.default_rng(0)
        for deg in (-40, -20, 0, 10, 30, 44):
            truth = rotated_rect(400, 300, 300, 200, deg)
            for _ in range(5):
                shuffled = truth[rng.permutation(4)]
                np.testing.assert_allclose(geometry.order_points(shuffled), truth, atol=1e-9)

    def test_perspective_quads(self):
        quad = np.array([[120, 80], [610, 140], [560, 520], [90, 470]], float)
        for perm in ([0, 1, 2, 3], [2, 0, 3, 1], [3, 2, 1, 0]):
            np.testing.assert_allclose(geometry.order_points(quad[perm]), quad)

    def test_sum_diff_rule_breaks_at_45_degrees(self):
        """흔한 합·차 규칙은 45°에서 같은 점을 두 번 고른다. 직접 구현은 네 점을 모두 쓴다."""
        quad = rotated_rect(400, 400, 200, 200, 45)
        naive = geometry.order_points_sum_diff(quad)
        self.assertLess(len({tuple(p) for p in naive.round(6)}), 4)
        ours = geometry.order_points(quad)
        self.assertEqual(len({tuple(p) for p in ours.round(6)}), 4)

    def test_no_external_geometry_library(self):
        """제약: scipy·shapely·딥러닝·OCR 라이브러리를 import하지 않는다."""
        banned = {"scipy", "shapely", "torch", "tensorflow", "keras", "pytesseract", "tesserocr", "easyocr"}
        for path in (ROOT / "src").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    names = [node.module]
                for n in names:
                    self.assertNotIn(n.split(".")[0], banned, f"{path.name}: {n}")

    def test_geometry_does_not_use_opencv(self):
        source = (ROOT / "src" / "geometry.py").read_text(encoding="utf-8")
        self.assertNotIn("import cv2", source)


class TestGeometryHelpers(unittest.TestCase):
    def test_polygon_area_and_convexity(self):
        sq = [[0, 0], [10, 0], [10, 10], [0, 10]]
        self.assertAlmostEqual(geometry.polygon_area(sq), 100.0)
        self.assertTrue(geometry.is_convex(sq))
        self.assertFalse(geometry.is_convex([[0, 0], [10, 0], [2, 2], [0, 10]]))

    def test_corner_error_ignores_start_vertex(self):
        quad = rotated_rect(300, 300, 200, 100, 0)
        rolled = np.roll(quad, 1, axis=0)
        max_err, _, shift = geometry.corner_error(rolled + 1.0, quad)
        self.assertAlmostEqual(max_err, np.sqrt(2), places=6)
        self.assertEqual(shift, 0)


class TestAspectRatio(unittest.TestCase):
    """보너스 2: 원본 좌표 간 거리로 결과 크기 결정 + 원근 보정 확장."""

    def project(self, w, h, pitch, yaw, roll, f=1000.0, size=(1280, 960)):
        from src.synthetic import rotation
        pts = np.array([[-w / 2, -h / 2, 0], [w / 2, -h / 2, 0], [w / 2, h / 2, 0], [-w / 2, h / 2, 0]])
        cam = pts @ rotation(pitch, yaw, roll).T + [0, 0, 700]
        return cam[:, :2] / cam[:, 2:] * f + [size[1] / 2, size[0] / 2]

    def test_distance_size_uses_longer_side(self):
        quad = np.array([[0, 0], [100, 0], [90, 50], [10, 50]], float)
        self.assertEqual(geometry.output_size_by_distance(quad), (100, 51))

    def test_zhang_recovers_true_ratio(self):
        for w, h, pitch, yaw, roll in ((210, 297, 50, 0, 5), (80, 210, 30, 25, -20), (90, 50, 55, 10, 40)):
            quad = geometry.order_points(self.project(w, h, pitch, yaw, roll))
            aspect, focal, method = geometry.estimate_aspect_ratio(quad, (1280, 960))
            self.assertEqual(method, "zhang")
            # 강한 원근에서 45° 가까이 돌아간 명함은 결과가 90° 돌아 나올 수 있다 (가로/세로가 뒤바뀜)
            ratio = w / h
            self.assertAlmostEqual(min(abs(aspect - ratio), abs(aspect - 1 / ratio)), 0.0, delta=1e-6)
            self.assertAlmostEqual(focal, 1000.0, delta=1e-3)

    def test_distance_method_distorts_strong_tilt(self):
        quad = geometry.order_points(self.project(210, 297, 55, 0, 0))
        w, h = geometry.output_size_by_distance(quad)
        self.assertGreater(abs(w / h - 210 / 297) / (210 / 297), 0.3)

    def test_frontal_falls_back_to_distance(self):
        quad = rotated_rect(480, 640, 210, 297, 0)
        aspect, focal, method = geometry.estimate_aspect_ratio(quad, (1280, 960))
        self.assertEqual(method, "distance")
        self.assertAlmostEqual(aspect, 210 / 297, delta=0.01)


class TestPipeline(unittest.TestCase):
    """기능 3~6: 전처리·엣지·윤곽선·투시 변환·적응형 이진화."""

    @classmethod
    def setUpClass(cls):
        cls.quad = projected_quad()  # 3:4 종이를 35° 기울여 찍은 장면
        cls.image = synthetic_scene(cls.quad)
        cls.result = scan(cls.image)

    def test_finds_document_corners(self):
        self.assertTrue(self.result.found, self.result.reason)
        max_err, _, shift = geometry.corner_error(self.result.quad, self.quad)
        self.assertLess(max_err, 4.0)
        self.assertEqual(shift, 0)

    def test_stage_shapes(self):
        r = self.result
        self.assertEqual(r.gray.ndim, 2)
        self.assertEqual(r.edges.shape, r.gray.shape)
        self.assertEqual(set(np.unique(r.edges)) <= {0, 255}, True)
        self.assertEqual(list(stage_images(r)), ["1 Original", "2 Preprocessed", "3 Edges", "4 Contours", "5 Result"])

    def test_warp_is_upright_rectangle(self):
        """펴진 결과의 종횡비가 원래 종이(3:4)에 가깝고, 글자 줄이 수평이다.

        종횡비 보정은 주점이 이미지 중심인 실제 카메라를 가정한다. 임의로 그린 사각형이나 잘라 낸 사진에는 맞지 않는다.
        """
        h, w = self.result.warped.shape[:2]
        self.assertAlmostEqual(w / h, 0.75, delta=0.03)
        gray = cv2.cvtColor(self.result.warped, cv2.COLOR_BGR2GRAY)
        rows = (gray < 128).sum(axis=1)
        self.assertGreater((rows == 0).mean(), 0.4)  # 줄 사이 빈 행이 뚜렷하면 수평으로 펴진 것

    def test_adaptive_threshold_is_binary(self):
        self.assertEqual(set(np.unique(self.result.scanned)) <= {0, 255}, True)

    def test_adaptive_beats_global_threshold_under_shadow(self):
        """그림자로 오른쪽 절반이 어두운 종이: 적응형은 배경을 흰색으로 유지한다."""
        page = np.full((300, 400), 230, np.uint8)
        for i in range(6):
            cv2.putText(page, "shadow text", (20, 40 + 45 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 20, 2)
        shade = np.ones_like(page, float)
        shade[:, 200:] = 0.4
        dark = (page * shade).astype(np.uint8)
        _, otsu = cv2.threshold(dark, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        adaptive = enhance(dark)
        paper = page == 230
        self.assertGreater((adaptive[paper] == 255).mean(), 0.97)
        self.assertLess((otsu[:, 200:][paper[:, 200:]] == 255).mean(), 0.5)

    def test_no_document_reports_reason(self):
        r = scan(np.full((480, 640, 3), 128, np.uint8))
        self.assertFalse(r.found)
        self.assertIn("윤곽선", r.reason)

    def test_params_normalized(self):
        p = ScanParams(blur=4, canny_low=200, canny_high=100).normalized()
        self.assertEqual((p.blur, p.canny_low, p.canny_high), (5, 100, 200))


class TestConvolutionBonus(unittest.TestCase):
    """보너스 1: NumPy 가우시안 블러가 OpenCV와 같은 값을 낸다."""

    def test_kernel_matches_opencv(self):
        for k in (1, 3, 5, 7, 9, 11, 15):
            np.testing.assert_allclose(convolution.gaussian_kernel_1d(k), cv2.getGaussianKernel(k, 0).ravel(),
                                       atol=1e-12)
            self.assertAlmostEqual(convolution.gaussian_kernel_2d(k).sum(), 1.0)

    def test_all_methods_match_opencv(self):
        img = np.random.default_rng(1).integers(0, 256, (37, 53)).astype(np.float64)
        for k in (3, 5, 9):
            ref = cv2.GaussianBlur(img, (k, k), 0)
            kernel = convolution.gaussian_kernel_2d(k)
            for fn in (convolution.convolve_loops, convolution.convolve_vectorized, convolution.convolve_strided):
                np.testing.assert_allclose(fn(img, kernel), ref, atol=1e-9)
            np.testing.assert_allclose(convolution.blur_separable(img, k), ref, atol=1e-9)

    def test_convolution_is_dot_product(self):
        img = np.arange(49, dtype=float).reshape(7, 7)
        kernel = convolution.gaussian_kernel_2d(3)
        out = convolution.convolve_vectorized(img, kernel)
        self.assertAlmostEqual(out[3, 3], float(np.sum(img[2:5, 2:5] * kernel)))

    def test_uint8_color_blur(self):
        img = np.random.default_rng(2).integers(0, 256, (20, 30, 3)).astype(np.uint8)
        out = convolution.gaussian_blur(img, 5)
        self.assertEqual(out.shape, img.shape)
        self.assertLessEqual(np.abs(out.astype(int) - cv2.GaussianBlur(img, (5, 5), 0)).max(), 1)


class TestPdfBonus(unittest.TestCase):
    """보너스 3: 여러 장을 한 PDF로 저장."""

    def test_multi_page_pdf(self):
        pages = [np.full((200, 150), 255, np.uint8), np.zeros((120, 90, 3), np.uint8)]
        with tempfile.TemporaryDirectory() as tmp:
            path = save_pdf(pages, Path(tmp) / "out.pdf")
            data = path.read_bytes()
        self.assertTrue(data.startswith(b"%PDF"))
        self.assertEqual(data.count(b"/Type /Page\n") + data.count(b"/Type /Page\r") + data.count(b"/Type /Page "), 2)


class TestDatasetAndEvaluation(unittest.TestCase):
    """기능 1·7: 데이터 20장, 조건 기록, 정량 평가."""

    @classmethod
    def setUpClass(cls):
        cls.labels = json.loads((DATA / "labels.json").read_text(encoding="utf-8"))["images"]

    def test_twenty_images_five_per_condition(self):
        self.assertEqual(len(self.labels), 20)
        counts = {}
        for lab in self.labels:
            counts[lab["condition"]] = counts.get(lab["condition"], 0) + 1
            self.assertTrue((DATA / lab["file"]).is_file())
            for key in ("lighting", "angle", "background_complexity", "corners"):
                self.assertIn(key, lab)
        self.assertEqual(counts, {"easy": 5, "shadow": 5, "tilt": 5, "complex": 5})

    def test_tilt_cases_are_at_least_45_degrees(self):
        for lab in self.labels:
            if lab["condition"] == "tilt":
                self.assertGreaterEqual(lab["angle"]["tilt_deg"], 45)

    def test_generator_is_deterministic(self):
        case = CASES[0]
        a, qa, _ = render_case(case)
        b, qb, _ = render_case(case)
        np.testing.assert_array_equal(a, b)
        stored = imread(DATA / "E01.jpg")
        self.assertLess(np.abs(stored.astype(int) - a.astype(int)).mean(), 3.0)  # JPEG 손실만 차이

    def test_judge_thresholds(self):
        truth = rotated_rect(400, 400, 300, 400, 0).tolist()
        label = {"id": "x", "condition": "easy", "corners": truth, "true_aspect": 0.75}

        class Fake:
            found, reason, contours, candidates = True, "", [], []

            def __init__(self, quad):
                self.quad = np.array(quad, float)
                self.aspect = {"method": "distance", "estimated": 0.75}

        diag = 500.0
        self.assertEqual(evaluate.judge(Fake(np.array(truth) + [0.015 * diag, 0]), label)["status"], "success")
        self.assertEqual(evaluate.judge(Fake(np.array(truth) + [0.04 * diag, 0]), label)["status"], "partial")
        self.assertEqual(evaluate.judge(Fake(np.array(truth) + [0.08 * diag, 0]), label)["status"], "fail")

    def test_easy_case_succeeds_with_defaults(self):
        lab = self.labels[0]
        row = evaluate.judge(scan(imread(DATA / lab["file"]), warp=False), lab)
        self.assertEqual(row["status"], "success")

    def test_summary_table(self):
        rows = [{"condition": "easy", "condition_name": "쉬움", "status": s} for s in ("success", "partial", "fail")]
        table = evaluate.summarize(rows)
        self.assertEqual(table[0]["success"], 1)
        self.assertEqual(table[-1]["name"], "전체")
        self.assertAlmostEqual(table[-1]["success_rate"], 1 / 3)


class TestEda(unittest.TestCase):
    """기능 2: 어두워지면 경계 기울기가 줄어 고정 임계값 Canny가 경계를 잃는다."""

    def test_darkening_reduces_border_gradient(self):
        quad = np.array([[180, 120], [520, 170], [560, 700], [130, 650]], float)
        img = synthetic_scene(quad)
        rows = eda.darkening_experiment(img, quad, factors=(1.0, 0.5, 0.15), noise_sigma=2.0)
        grads = [r["boundary_gradient_median"] for r in rows]
        self.assertTrue(grads[0] > grads[1] > grads[2])
        self.assertAlmostEqual(grads[1] / grads[0], 0.5, delta=0.08)
        self.assertEqual(rows[0]["boundary_edge_recall"], 1.0)
        self.assertLess(rows[2]["boundary_edge_recall"], 0.5)

    def test_histogram_sums_to_one(self):
        gray = np.random.default_rng(3).integers(0, 256, (50, 50)).astype(np.uint8)
        self.assertAlmostEqual(eda.histogram(gray).sum(), 1.0)


class TestImageIo(unittest.TestCase):
    def test_korean_path_roundtrip(self):
        img = np.random.default_rng(4).integers(0, 256, (20, 30, 3)).astype(np.uint8)
        with tempfile.TemporaryDirectory() as tmp:
            path = imwrite(Path(tmp) / "한글 폴더" / "문서.png", img)
            np.testing.assert_array_equal(imread(path), img)


class TestWebcamFrame(unittest.TestCase):
    """선택 과제: 웹캠 프레임 처리 함수 (카메라 없이 검증)."""

    def test_process_frame(self):
        from src.webcam import process_frame
        quad = np.array([[180, 120], [520, 170], [560, 700], [130, 650]], float)
        frame = synthetic_scene(quad)
        view, result = process_frame(frame, ScanParams(work_size=640).normalized())
        self.assertTrue(result.found)
        self.assertEqual(view.shape[2], 3)


if __name__ == "__main__":
    unittest.main()
