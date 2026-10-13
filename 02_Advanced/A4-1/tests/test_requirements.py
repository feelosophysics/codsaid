"""요구사항별 검증. 작은 손계산 예제와 실제 데이터 검사를 함께 둔다.

    python -m unittest discover -s tests -v
"""
import math
import unittest

import numpy as np

from src.bm25 import BM25
from src.inverted_index import InvertedIndex
from src.preprocess import clean, preprocess, tokenize
from src.search import SearchEngine, SearchHit, cosine_similarity, make_snippet, top_k
from src.tfidf import (
    TfidfVectorizerNP, build_vocabulary, count_matrix, inverse_document_frequency, term_frequency,
)

TOY = [
    ["space", "shuttle", "launch", "launch"],
    ["hockey", "goalie", "playoff"],
    ["space", "station", "orbit"],
    ["baseball", "pitcher", "launch"],
]


class TestPreprocess(unittest.TestCase):
    def test_clean_removes_email_url_and_symbols(self):
        text = "Mail me at John.Doe@nasa.gov or see http://www.nasa.gov/x!! It's GREAT."
        self.assertEqual(clean(text), "mail me at or see its great")

    def test_tokenize_keeps_alnum_terms_drops_numbers_and_single_chars(self):
        self.assertEqual(tokenize("X11 and mpeg2, 1993 3d a b"), ["x11", "and", "mpeg2"])

    def test_preprocess_removes_stopwords_and_unifies_spelling(self):
        self.assertEqual(preprocess("I don't like the colour of this window"), ["color", "window"])

    def test_negation_is_lost_by_design(self):
        self.assertEqual(preprocess("not a good team"), preprocess("a good team"))


class TestTfidf(unittest.TestCase):
    def test_vocabulary_sorted_and_df_filtered(self):
        self.assertEqual(build_vocabulary(TOY, min_df=2), ["launch", "space"])
        self.assertNotIn("launch", build_vocabulary(TOY, max_df=0.4))  # df=2 > 0.4·4

    def test_count_matrix_counts_repeats(self):
        vocab = {t: j for j, t in enumerate(build_vocabulary(TOY))}
        counts = count_matrix(TOY, vocab)
        self.assertEqual(counts[0, vocab["launch"]], 2)
        self.assertEqual(counts.sum(), sum(len(d) for d in TOY))

    def test_idf_hand_calculation(self):
        # n=4, df(launch)=2 → ln(5/3)+1, df(goalie)=1 → ln(5/2)+1
        idf = inverse_document_frequency(np.array([2, 1]), 4, smooth=True)
        self.assertAlmostEqual(idf[0], math.log(5 / 3) + 1)
        self.assertAlmostEqual(idf[1], math.log(5 / 2) + 1)
        self.assertAlmostEqual(inverse_document_frequency(np.array([2]), 4, smooth=False)[0], math.log(2) + 1)

    def test_tf_variants(self):
        counts = np.array([[4.0, 1.0, 0.0]])
        np.testing.assert_allclose(term_frequency(counts, "raw"), [[4, 1, 0]])
        np.testing.assert_allclose(term_frequency(counts, "log"), [[1 + math.log(4), 1, 0]])
        np.testing.assert_allclose(term_frequency(counts, "double"), [[1.0, 0.625, 0]])
        np.testing.assert_allclose(term_frequency(counts, "binary"), [[1, 1, 0]])

    def test_rows_are_unit_length(self):
        X = TfidfVectorizerNP().fit_transform(TOY)
        np.testing.assert_allclose(np.linalg.norm(X, axis=1), 1.0)

    def test_matches_sklearn_on_toy_for_all_settings(self):
        from sklearn.feature_extraction.text import TfidfVectorizer

        for smooth in (True, False):
            for sub in (False, True):
                for norm in ("l2", "l1", None):
                    ours = TfidfVectorizerNP(tf="log" if sub else "raw", smooth_idf=smooth, norm=norm)
                    ref = TfidfVectorizer(analyzer=lambda d: d, smooth_idf=smooth, sublinear_tf=sub, norm=norm)
                    diff = np.abs(ours.fit_transform(TOY) - ref.fit_transform(TOY).toarray()).max()
                    self.assertLess(diff, 1e-12, (smooth, sub, norm))

    def test_transform_ignores_unknown_words(self):
        vec = TfidfVectorizerNP().fit(TOY)
        self.assertEqual(np.count_nonzero(vec.transform([["unknown", "space"]])), 1)


class TestSearch(unittest.TestCase):
    def test_cosine_hand_calculation(self):
        q = np.array([1.0, 2.0, 0.0])
        D = np.array([[2.0, 4.0, 0.0], [0.0, 0.0, 3.0], [1.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
        np.testing.assert_allclose(cosine_similarity(q, D), [1.0, 0.0, 1 / math.sqrt(5), 0.0])

    def test_top_k_orders_by_score_then_position_and_drops_zero(self):
        scores = np.array([0.2, 0.9, 0.0, 0.9, 0.5])
        self.assertEqual(top_k(scores, 5).tolist(), [1, 3, 4, 0])

    def test_snippet_centers_on_query_word(self):
        text = "a " * 200 + "the shuttle launched today"
        self.assertIn("shuttle", make_snippet(text, ["shuttle"]))


class TestBM25AndIndex(unittest.TestCase):
    def test_bm25_hand_calculation(self):
        counts = np.array([[2.0, 0.0], [1.0, 1.0], [0.0, 3.0]])
        model = BM25(k1=1.5, b=0.75).fit(counts)  # 길이 2,2,3 / avgdl=7/3
        df, n = 2, 3
        idf = math.log((n - df + 0.5) / (df + 0.5) + 1)
        norm0 = 1.5 * (1 - 0.75 + 0.75 * 2 / (7 / 3))
        expected0 = idf * 2 * 2.5 / (2 + norm0)
        self.assertAlmostEqual(model.score([0])[0], expected0)
        np.testing.assert_allclose(model.weight_matrix()[:, 0], model.score([0]))

    def test_bm25_term_frequency_saturates(self):
        counts = np.array([[1.0], [10.0], [100.0], [0.0]])
        s = BM25(k1=1.2, b=0.0).fit(counts).score([0])
        self.assertTrue(s[0] < s[1] < s[2])
        self.assertLess(s[2] / s[0], 2.2 / 1.0 * 1.0001)  # 상한 (k1+1)/1 배

    def test_inverted_index_matches_full_scan(self):
        X = TfidfVectorizerNP().fit_transform(TOY)
        vec = TfidfVectorizerNP().fit(TOY)
        index = InvertedIndex(X, vec.terms_)
        self.assertEqual(index.documents("launch").tolist(), [0, 3])
        q = vec.transform([["space", "launch"]])[0]
        cand, scores, visited = index.score({int(j): float(q[j]) for j in np.flatnonzero(q)})
        np.testing.assert_allclose(scores, (X @ q)[cand])
        self.assertEqual(visited, 4)  # df(space)=2 + df(launch)=2


class TestOnRealData(unittest.TestCase):
    """실제 20 Newsgroups 데이터(첫 실행 시 sklearn이 내려받음)."""

    @classmethod
    def setUpClass(cls):
        from src.data import load_corpus

        cls.corpus = load_corpus()
        cls.engine = SearchEngine(cls.corpus)

    def test_dataset_requirements(self):
        self.assertGreaterEqual(len(self.corpus), 500)
        self.assertGreaterEqual(len(set(self.corpus.labels.tolist())), 2)
        self.assertTrue(all(len(t) >= 5 for t in self.corpus.tokens))

    def test_tfidf_matches_sklearn_within_1e6(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from src.search import MAX_DF, MIN_DF

        ref = TfidfVectorizer(analyzer=lambda d: d, min_df=MIN_DF, max_df=MAX_DF,
                              smooth_idf=True, sublinear_tf=False, norm="l2")
        R = ref.fit_transform(self.corpus.tokens).toarray()
        self.assertEqual(list(ref.get_feature_names_out()), self.engine.vectorizer.terms_)
        self.assertLess(np.abs(self.engine.matrix - R).max(), 1e-6)

    def test_search_returns_top5_tuples(self):
        hits = self.engine.search("space shuttle launch")
        self.assertEqual(len(hits), 5)
        self.assertIsInstance(hits[0], SearchHit)
        score, doc_id, snippet = hits[0]
        self.assertIsInstance(score, float)
        self.assertIsInstance(doc_id, int)
        self.assertIsInstance(snippet, str)
        self.assertEqual([h.score for h in hits], sorted((h.score for h in hits), reverse=True))
        names = self.corpus.target_names
        cats = {names[self.corpus.labels[self.engine.position(h.doc_id)]] for h in hits}
        self.assertEqual(cats, {"sci.space"})

    def test_index_and_bm25_paths(self):
        for method in ("tfidf", "bm25"):
            full = self.engine.search("nasa orbit satellite", method=method)
            fast = self.engine.search("nasa orbit satellite", method=method, use_index=True)
            self.assertEqual([h.doc_id for h in full], [h.doc_id for h in fast])
            np.testing.assert_allclose([h.score for h in full], [h.score for h in fast])

    def test_unknown_query_returns_empty(self):
        self.assertEqual(self.engine.search("the and of"), [])


if __name__ == "__main__":
    unittest.main()
