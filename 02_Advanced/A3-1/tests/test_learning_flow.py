"""학습과 앱 시연이 의존하는 상태·저장·생성 계약을 검증한다."""
import importlib.util
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from src import app, scanner
from src.image_io import imread

ROOT = Path(__file__).resolve().parents[1]


class TestLearningFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.image = imread(ROOT / 'data/synthetic/E01.jpg')

    def test_threshold_changes_preserve_geometry_and_input(self):
        original = self.image.copy()
        first = scanner.scan(self.image)
        changed = scanner.scan(self.image, replace(first.params, thresh_c=20))
        np.testing.assert_array_equal(first.quad, changed.quad)
        np.testing.assert_array_equal(first.warped, changed.warped)
        self.assertTrue(np.any(first.scanned != changed.scanned))
        # 정수 C가 커지면 같은 픽셀은 흰색에서 검정으로 바뀌지 않는다.
        self.assertTrue(np.all(changed.scanned >= first.scanned))
        np.testing.assert_array_equal(original, self.image)

    def test_gui_loop_recomputes_on_change_and_saves_latest(self):
        """OS 창 대신 화면 경계를 대체하고 실제 계산·PNG 저장을 사용한다."""
        first = scanner.ScanParams()
        changed = replace(first, thresh_c=20)
        keys = [-1, -1, ord('s'), ord('q')]
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(app, 'create_trackbars'), \
                 patch.object(app, 'read_trackbars', side_effect=[first, first, changed, changed]), \
                 patch.object(cv2, 'namedWindow'), patch.object(cv2, 'moveWindow'), \
                 patch.object(cv2, 'imshow') as display, \
                 patch.object(cv2, 'waitKey', side_effect=keys), \
                 patch.object(cv2, 'getWindowProperty', return_value=1), \
                 patch.object(cv2, 'destroyAllWindows') as close, \
                 patch.object(app, 'scan', wraps=scanner.scan) as process:
                final = app.run_gui(self.image, 'E01', first, folder)
            self.assertEqual(final, changed)
            self.assertEqual(process.call_count, 2)
            self.assertEqual(display.call_count, 10)
            close.assert_called_once()
            png = imread(Path(folder) / 'scanned_E01.png', cv2.IMREAD_GRAYSCALE)
            expected = scanner.scan(self.image, changed).scanned
            np.testing.assert_array_equal(png, expected)

    def test_notebook_matches_generator(self):
        import nbformat
        spec = importlib.util.spec_from_file_location('learning_builder', ROOT/'tools/build_learning_notebook.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        expected = builder.build()
        saved = nbformat.read(ROOT/'notebooks/scanner_walkthrough.ipynb', as_version=4)
        nbformat.validate(saved)
        self.assertEqual([(c.cell_type,c.source,c.id) for c in saved.cells],
                         [(c.cell_type,c.source,c.id) for c in expected.cells])
        for cell in saved.cells:
            if cell.cell_type == 'code':
                self.assertIsNotNone(cell.execution_count)
                self.assertFalse(any(output.output_type == 'error' for output in cell.outputs))


if __name__ == '__main__':
    unittest.main()
