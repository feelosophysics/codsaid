"""학습·시연에 필요한 시간 상태와 실행 자료의 일치를 검증한다."""
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from src import app, evaluate
from src.motion import MotionDetector, MotionParams
from src.pipeline import VideoAnalyzer
from src.zone import IntrusionZone

ROOT=Path(__file__).resolve().parents[1]


class TestLearningFlow(unittest.TestCase):
    def test_background_requires_history(self):
        background=np.full((80,100,3),50,np.uint8)
        frame=background.copy()
        frame[20:60,30:60]=180
        settings=MotionParams(blur=1,min_area=50,open_ksize=1,close_ksize=1)
        learned=MotionDetector(settings)
        for _ in range(30):
            learned(background)
        _,learned_mask,_=learned(frame)
        _,cold_mask,_=MotionDetector(settings)(frame)
        # 초기 MOG2 마스크는 그림자 값 127일 수도 있어, 더 넓다는 방향을 가정하지 않는다.
        self.assertFalse(np.array_equal(cold_mask,learned_mask))
        self.assertEqual(np.count_nonzero(learned_mask[20:60,30:60]),1200)

    def test_switch_observations_skip_merged_and_missing(self):
        sequence=[1]*5+[2,2,evaluate.MERGED,None,2,2,2]
        switches,_=evaluate.stable_switches(sequence)
        self.assertEqual(switches,[(5,1,2)])
        # 가시율이 낮은 한 프레임은 미검출 실패의 연속 구간을 끊는다.
        self.assertEqual(evaluate.failure_runs([None]*19,[1.0]*9+[0.4]+[1.0]*9),[])

    def test_gui_pause_step_snapshot_and_settings(self):
        analyzer=VideoAnalyzer(zone=IntrusionZone(echo=False))
        keys=[ord(k) for k in ['p','n','s',']','m','c','q']]
        with tempfile.TemporaryDirectory() as folder:
            args=app.parse_args(['--source',str(ROOT/'data/synthetic/crossing_test.mp4'),
                                 '--target=','--no-realtime','--out',folder])
            analyzer.zone.set((10,10,20,20))
            with patch.object(app,'build_analyzer',return_value=analyzer), \
                 patch.object(cv2,'namedWindow'), patch.object(cv2,'setMouseCallback'), \
                 patch.object(cv2,'imshow'), patch.object(cv2,'getWindowProperty',return_value=1), \
                 patch.object(cv2,'destroyWindow'), patch.object(cv2,'destroyAllWindows') as close, \
                 patch.object(cv2,'waitKey',side_effect=keys):
                app.run_gui(args)
            self.assertEqual(analyzer.index,1)
            self.assertEqual(analyzer.motion_params.learning_rate,0.004)
            self.assertIsNone(analyzer.zone.rect)
            for name in ['snapshot_00001.png','raw_00001.jpg','mask_00001.png']:
                self.assertTrue((Path(folder)/name).is_file(),name)
            close.assert_called_once()

    def test_notebook_matches_generator_and_has_outputs(self):
        import nbformat
        spec=importlib.util.spec_from_file_location('tracking_builder',ROOT/'tools/build_learning_notebook.py')
        builder=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        expected=builder.build()
        saved=nbformat.read(ROOT/'notebooks/tracking_walkthrough.ipynb',as_version=4)
        nbformat.validate(saved)
        self.assertEqual([(c.cell_type,c.source,c.id) for c in expected.cells],
                         [(c.cell_type,c.source,c.id) for c in saved.cells])
        for cell in saved.cells:
            if cell.cell_type=='code':
                self.assertIsNotNone(cell.execution_count)
                self.assertFalse(any(o.output_type=='error' for o in cell.outputs))

    def test_html_code_excerpts_match_current_modules(self):
        html=(ROOT/'study/a3-2.html').read_text(encoding='utf-8')
        bundled=json.loads(re.search(r'<script>const DATA = (.*?);</script>',html,re.S).group(1))
        for excerpt in bundled['code']:
            lines=(ROOT/excerpt['file']).read_text(encoding='utf-8').splitlines()
            actual='\n'.join(lines[excerpt['start']-1:excerpt['end']])
            self.assertEqual(actual,excerpt['text'],excerpt['name'])


if __name__=='__main__':
    unittest.main()
