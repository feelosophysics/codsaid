"""표현 학습의 경계와 설명 점수의 재구성을 검증한다."""
import contextlib
import io
import unittest
from unittest.mock import patch

import numpy as np

from src.classify import select_C
from src.data import Corpus
from src.preprocess import preprocess
from src.search import SearchEngine
from src.tfidf import TfidfVectorizerNP


class TestLearningFlow(unittest.TestCase):
    def test_cli_rejects_nonpositive_topk_before_loading_corpus(self):
        import main

        for value in ['0', '-1']:
            with patch('sys.argv', ['main.py', '--query', 'space', '--topk', value]), \
                    patch('main.load_corpus') as load, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main.main()
                self.assertEqual(raised.exception.code, 2)
                load.assert_not_called()

    def test_cv_fits_only_fold_training_tokens_and_keeps_tf(self):
        # 각 문서에 고유 토큰을 두면 검증 문서가 fit에 섞였는지 알 수 있다.
        tokens = [['orbit', 'space', f'unique{i}'] if i % 2 else
                  ['hockey', 'goalie', f'unique{i}'] for i in range(20)]
        labels = np.array([i % 2 for i in range(20)])
        fitted, transformed = [], []

        class RecordingVectorizer(TfidfVectorizerNP):
            def fit_transform(self, docs):
                fitted.append((self.tf, {t for doc in docs for t in doc}))
                return super().fit_transform(docs)

            def transform(self, docs):
                transformed.append({t for doc in docs for t in doc})
                return super().transform(docs)

        with patch('src.classify.TfidfVectorizerNP', RecordingVectorizer):
            scores = select_C(tokens, labels, grid=(1., 10.), tf='log')
        self.assertEqual(set(scores), {1., 10.})
        self.assertEqual(len(fitted), 5)  # C 후보마다 반복하지 않고 fold마다 표현 학습
        for (tf, fit_terms), valid_terms in zip(fitted, transformed):
            self.assertEqual(tf, 'log')
            fit_unique = {t for t in fit_terms if t.startswith('unique')}
            valid_unique = {t for t in valid_terms if t.startswith('unique')}
            self.assertEqual(len(fit_unique), 16)
            self.assertEqual(len(valid_unique), 4)
            self.assertTrue(fit_unique.isdisjoint(valid_unique))

    def test_search_explanation_and_edges_share_frozen_coordinates(self):
        texts = ['space space orbit', 'goalie orbit', '', 'the and of', 'space space orbit']
        tokens = [preprocess(t) for t in texts]
        corpus = Corpus(texts, tokens, np.zeros(5, dtype=int), np.array([0, 2, 3, 5, 9]), ['toy'], 10)
        engine = SearchEngine(corpus, min_df=1, max_df=1.0)
        idf = engine.vectorizer.idf_.copy()
        hits = engine.search('space orbit unknown')
        self.assertEqual([h.doc_id for h in hits], [0, 9, 2])
        for hit in hits:
            explanation = engine.explain('space orbit unknown', hit.doc_id)
            total = sum(item[3] for item in explanation['shared'])
            self.assertAlmostEqual(total, explanation['dot'])
            self.assertAlmostEqual(explanation['cosine'], hit.score)
        for query in ['', 'the and of', 'unknown', '한국어']:
            for method in ['tfidf', 'bm25']:
                self.assertEqual(engine.search(query, method=method), [])
                self.assertEqual(engine.search(query, method=method, use_index=True), [])
        np.testing.assert_array_equal(idf, engine.vectorizer.idf_)


if __name__ == '__main__':
    unittest.main()
