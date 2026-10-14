"""미션 요구 기준을 데이터와 결과물로 확인한다. outputs/가 필요한 테스트는 run_all을 먼저 실행해야 한다."""
import json
import unittest
from pathlib import Path

from src.aspect import AspectAnalyzer
from src.eval_sentiment import read_jsonl
from src.lexicon import load_sentiment_tsv

ROOT = Path(__file__).resolve().parents[1]
HANDMADE = ROOT / "data" / "handmade"
OUT = ROOT / "outputs"


class TestDataRequirements(unittest.TestCase):
    def test_extraction_test_sentences(self):
        """테스트 문장 50개 이상, 패턴별 10문장 이상"""
        cases = read_jsonl(HANDMADE / "extraction_cases.jsonl")
        self.assertGreaterEqual(len(cases), 50)
        for kind in ("email", "phone", "date", "money", "url"):
            self.assertGreaterEqual(sum(c["focus"] == kind for c in cases), 10, kind)

    def test_lexicon_size(self):
        """감성 사전 200단어 이상, 도메인 특화어 30개 이상"""
        lex = load_sentiment_tsv()
        words = [e for e in lex if e.kind == "SENTI"]
        self.assertGreaterEqual(len(words), 200)
        self.assertGreaterEqual(sum(e.domain in ("movie", "service") for e in words), 30)

    def test_failure_and_error_annotations(self):
        """추출 실패 사례 5건 이상(유형 표시), 감성 오분류 분석 10건 이상"""
        cases = read_jsonl(HANDMADE / "extraction_cases.jsonl")
        self.assertGreaterEqual(sum("fail" in c for c in cases), 5)
        notes = json.loads((HANDMADE / "test_error_annotations.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(notes), 10)
        self.assertGreaterEqual(len({n["category"] for n in notes}), 5)

    def test_aspect_example(self):
        pairs = AspectAnalyzer().pairs("음식은 맛있는데 가격이 비싸요")
        self.assertEqual(pairs, {("맛", "pos"), ("가격", "neg")})


@unittest.skipUnless((OUT / "summary.json").exists(), "python -m src.run_all 을 먼저 실행")
class TestOutputs(unittest.TestCase):
    def test_sentiment_evaluation(self):
        s = json.loads((OUT / "sentiment_eval.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(s["test"]["final_report"]["n"], 100)  # 레이블 데이터 100개 이상
        self.assertGreaterEqual(len(s["test_errors"]), 10)
        steps = [r["step"] for r in s["test"]["ablation"]]
        self.assertEqual(len(steps), 9)  # 부정어·강조어 적용 전후 비교
        # 필수 규칙(E)이 사전 합산(A)보다 나빠지지 않는다
        acc = {r["step"][0]: r["accuracy"] for r in s["test"]["ablation"]}
        self.assertGreaterEqual(acc["E"], acc["A"])

    def test_bonus_outputs(self):
        tf = json.loads((OUT / "rule_vs_tfidf.json").read_text(encoding="utf-8"))
        self.assertTrue({10, 100, 1000} <= {r["n"] for r in tf["curve"]})
        mask = json.loads((OUT / "masking_eval.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(mask["n_sentences"], 20)


if __name__ == "__main__":
    unittest.main()
