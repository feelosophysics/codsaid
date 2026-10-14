"""감성 분석 규칙 손계산 테스트."""
import unittest

from src.lexicon import Entry, Matcher, predicate_variants
from src.metrics import bootstrap_ci, classification_report, mcnemar_exact, prf
from src.sentiment import FINAL_CONFIG, Config, SentimentAnalyzer, canonical_emo, explain

A = SentimentAnalyzer()


def score(text, cfg=Config()):
    return A.analyze(text, cfg).score


class TestMissionExample(unittest.TestCase):
    def test_calculation(self):
        r = A.analyze("이 식당은 정말 맛있지 않았어요")
        self.assertEqual([p for p, _ in r.pieces], ["이", "식당", "은", "정말", "맛있", "지", "않았어요"])
        self.assertEqual(r.score, -3.0)  # (+2) × (-1) × 1.5
        self.assertEqual(r.label, 0)
        self.assertIn("(+2) × (-1) × 1.5 = -3", explain(r))


class TestRules(unittest.TestCase):
    def test_negation(self):
        self.assertEqual(score("좋다"), 2)
        self.assertEqual(score("좋지 않다"), -2)
        self.assertEqual(score("안 좋다"), -2)
        self.assertEqual(score("안좋아요"), -2)
        self.assertEqual(score("재미가 없어요"), -1)
        self.assertEqual(score("몰입이 안 된다"), -2)  # 짝 없는 '안'이 앞 감성어를 꾸민다

    def test_negation_off(self):
        self.assertEqual(score("좋지 않다", Config(negation=False)), 2)

    def test_intensifier(self):
        self.assertEqual(score("매우 좋다"), 3.0)
        self.assertEqual(score("좀 별로"), -1.0)  # 약화어 ×0.5
        self.assertEqual(score("매우 좋다", Config(intensifier=False)), 2.0)

    def test_double_negation(self):
        self.assertEqual(score("재미있지 않을 수 없다"), 2.0)
        self.assertEqual(score("최고가 아닐 수 없다"), 3.0)
        self.assertEqual(score("재미있지 않을 수 없다", Config(double_negation=False)), -2.0)

    def test_scope_stops_at_next_sentiment_word(self):
        # '않'은 '좋'만 뒤집고 다음 감성어 '재미없'은 건드리지 않는다
        self.assertEqual(score("좋지않고 재미없다"), -4.0)

    def test_keep_flag(self):
        self.assertEqual(score("별로 현실적이지 않다"), -2.0)

    def test_afterji(self):
        self.assertEqual(score("재미있지 못하다"), -2.0)
        # '~지' 없이 쓴 '못함'은 앞 감성어를 뒤집지 않는다
        self.assertEqual(score("망한 영화 연기까지 못함"), -2.0)

    def test_contrast(self):
        cfg = Config(contrast=True)
        self.assertEqual(score("좋았지만 별로", cfg), 2 * 0.5 - 2 * 1.5)

    def test_emoticon_is_not_negated(self):
        cfg = Config(emoticon=True)
        self.assertEqual(score("ㅡㅡ 볼 게 없다", cfg), -2.0)
        self.assertEqual(canonical_emo("jamo", "ㅜㅜㅜ"), "ㅠㅠ")
        self.assertEqual(canonical_emo("jamo", "ㅋㅋㅋㅋ"), "ㅋㅋ")

    def test_rating(self):
        cfg = Config(rating=True)
        self.assertEqual(score("10점 만점에 1점", cfg), -2.0)
        self.assertEqual(score("별 한개", cfg), -2.0)

    def test_substring_blockers(self):
        self.assertEqual(score("옛날꺼지만"), 0)    # '꺼지'가 걸리지 않는다
        self.assertEqual(score("어쩔 수 없다"), 0)  # '쩔'이 걸리지 않는다


class TestMorphology(unittest.TestCase):
    def test_variants(self):
        self.assertIn("지루해", predicate_variants("지루하"))
        self.assertIn("멋져", predicate_variants("멋지"))
        self.assertIn("나빠", predicate_variants("나쁘"))
        self.assertIn("슬퍼", predicate_variants("슬프"))
        self.assertIn("아까워", predicate_variants("아깝"))
        self.assertIn("달라", predicate_variants("다르"))

    def test_final_consonant_extension_and_longest_match(self):
        m = Matcher([Entry("재미", "SENTI", 1), Entry("재밌", "SENTI", 2), Entry("재미없", "SENTI", -2),
                     Entry("지루하", "SENTI", -2, "P")])
        self.assertEqual([h.entry.term for h in m.find("재미없다")], ["재미없"])
        self.assertEqual([h.entry.term for h in m.find("재밌다")], ["재밌"])  # 정확 일치가 받침 확장보다 우선
        self.assertEqual([h.entry.term for h in m.find("지루한")], ["지루하"])  # 하 + ㄴ
        self.assertEqual([h.entry.term for h in m.find("지루했다")], ["지루하"])  # 해 + ㅆ


class TestMetrics(unittest.TestCase):
    def test_against_sklearn(self):
        from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score

        y = [0, 0, 1, 1, 1, 0, 1, 0, 1, 1]
        p = [0, 1, 1, 0, 1, 0, 1, 1, 1, 0]
        r = classification_report(y, p)
        self.assertAlmostEqual(r["accuracy"], accuracy_score(y, p))
        self.assertAlmostEqual(r["positive"]["precision"], precision_score(y, p))
        self.assertAlmostEqual(r["positive"]["recall"], recall_score(y, p))
        self.assertAlmostEqual(r["macro_f1"], f1_score(y, p, average="macro"))
        self.assertEqual(r["confusion"], confusion_matrix(y, p).tolist())

    def test_prf_hand(self):
        self.assertEqual(prf(8, 2, 4)["precision"], 0.8)
        self.assertAlmostEqual(prf(8, 2, 4)["recall"], 8 / 12)

    def test_mcnemar_and_bootstrap(self):
        y = [1] * 20
        a = [1] * 10 + [0] * 10
        b = [1] * 20
        self.assertLess(mcnemar_exact(y, a, b)["p_value"], 0.01)  # B만 맞힌 문장 10개, 반대 0개
        lo, hi = bootstrap_ci(y, a, n_boot=200)
        self.assertLessEqual(lo, 0.5)
        self.assertGreaterEqual(hi, 0.5)


class TestFinalConfig(unittest.TestCase):
    def test_final_enables_extensions(self):
        self.assertTrue(FINAL_CONFIG.emoticon and FINAL_CONFIG.contrast and FINAL_CONFIG.orphan and FINAL_CONFIG.rating)


if __name__ == "__main__":
    unittest.main()
