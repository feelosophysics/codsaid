"""설명 원본·코드 발췌·생성 자료·소스 해시·설명용 숫자를 함께 검사한다."""
from __future__ import annotations

import ast
import hashlib
import html as html_lib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_study_guide import code_excerpts, learning_panels
from src.bm25 import BM25
from src.experiments import average_precision_at
from src.inverted_index import InvertedIndex
from src.preprocess import preprocess, tokenize
from src.tfidf import TfidfVectorizerNP, document_frequency, term_frequency


def main():
    import re
    study = ROOT / 'study'
    page = (study / 'a4-1.html').read_text(encoding='utf-8')
    data = json.loads(re.search(r'<script id="study-data" type="application/json">(.*?)</script>', page, re.S)[1])
    assert data['code'] == code_excerpts(), 'HTML의 코드 또는 줄 번호가 현재 소스와 다름'
    notes = json.loads((study / 'learning-notes.json').read_text(encoding='utf-8'))
    panels, md = learning_panels()
    assert (study / 'code-walkthrough.md').read_text(encoding='utf-8') == md
    for note in notes:
        assert panels[note['section']] in page, note['section']
        for value in [note['title'], *note['paragraphs'], note['trace'], note['question'], note['answer']]:
            assert html_lib.escape(value) in page
    assert not re.search(r'__LEARNING_|__STUDY_DATA__', page)
    manifest = json.loads((study / 'source-manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest.items():
        assert hashlib.sha256((ROOT / name).read_text(encoding='utf-8').encode('utf-8')).hexdigest() == expected, name
    docs = []
    for path in [ROOT / 'main.py', *sorted((ROOT / 'src').glob('*.py'))]:
        tree = ast.parse(path.read_text(encoding='utf-8'))
        assert ast.get_docstring(tree), f'모듈 설명 없음: {path.name}'
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                assert ast.get_docstring(node), (path.name, node.name)
                docs.append(node.name)
                if isinstance(node, ast.ClassDef):
                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            assert ast.get_docstring(child), (path.name, node.name, child.name)
                            docs.append(node.name + '.' + child.name)
    print(f'[자료] 설명 {len(notes)}개, 발췌 {len(data["code"])}개, 해시 {len(manifest)}개, 함수·클래스 {len(docs)}개 정합성 PASS')

    # 설명용 값은 실제 결과와 섞지 않고 고정된 작은 입력에서 확인한다.
    assert preprocess("I don't like the colour of this window") == ['color', 'window']
    assert tokenize('X11 3d 1993 a mpeg2') == ['x11', 'mpeg2']
    v = TfidfVectorizerNP()
    X = v.fit_transform([['space', 'space', 'orbit'], ['goalie', 'orbit']])
    assert v.terms_ == ['goalie', 'orbit', 'space']
    counts = v.counts([['space', 'space', 'orbit'], ['goalie', 'orbit']])
    np.testing.assert_array_equal(counts, [[0, 1, 2], [1, 1, 0]])
    np.testing.assert_array_equal(document_frequency(counts), [1, 2, 1])
    np.testing.assert_allclose(v.idf_, [1.405465, 1, 1.405465], atol=5e-7, rtol=0)
    np.testing.assert_allclose(X, [[0, .335176, .942156], [.814802, .579739, 0]], atol=5e-7, rtol=0)
    q = v.transform([['space', 'unknown']])[0]
    np.testing.assert_array_equal(q, [0, 0, 1])
    np.testing.assert_allclose(X @ q, [.942156, 0], atol=5e-7, rtol=0)
    for tf, expected in [('raw', [4, 1, 0]), ('log', [2.386294, 1, 0]), ('double', [1, .625, 0]), ('binary', [1, 1, 0])]:
        np.testing.assert_allclose(term_frequency(np.array([[4., 1., 0.]]), tf), [expected], atol=5e-7, rtol=0)
    bm = BM25().fit(np.array([[2., 0.], [1., 1.], [0., 3.]]))
    assert abs(bm.score([0])[0] - .703749) < 5e-7
    np.testing.assert_allclose(bm.score([0, 0]), bm.score([0]))
    index = InvertedIndex(np.array([[.6, 0], [.8, 1], [0, .5]]), ['a', 'b'])
    candidates, values, visited = index.score({0: .5, 1: 1.})
    np.testing.assert_array_equal(candidates, [0, 1, 2])
    np.testing.assert_allclose(values, [.3, 1.4, .5])
    assert visited == 4
    assert abs(average_precision_at(np.array([1., 0., 1.]), 2, 3) - 5 / 6) < 1e-12
    print('[설명용 계산] 전처리·어휘·빈도·DF/IDF·L2·질의·TF 4종·BM25·역색인·AP 손계산 PASS')


if __name__ == '__main__':
    main()
