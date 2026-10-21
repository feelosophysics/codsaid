"""계산 해설·좌표·평가·학습 경계가 실제 동작과 맞는지 검증한다."""
import contextlib
import io
import json
import unittest
from unittest.mock import mock_open, patch

from main import hide_entities, main
from src import bonus_tfidf, eval_extraction, extract, sentiment


class TestLearningFlow(unittest.TestCase):
    def test_explanation_uses_effective_negation_factor(self):
        analyzer = sentiment.SentimentAnalyzer()
        text = '재미있지 않을 수 없다'
        for enabled, sign in [(False, -1), (True, 1)]:
            result = analyzer.analyze(text, sentiment.Config(double_negation=enabled))
            self.assertEqual(len(result.items[0].negators), 2)
            self.assertEqual(result.items[0].negation_factor, sign)
            self.assertIn(f'(+2) × ({sign:+g}) = {2 * sign:g}', sentiment.explain(result))

    def test_scores_reconstruct_across_rule_settings_and_tie_types(self):
        analyzer = sentiment.SentimentAnalyzer()
        examples = ['정말 맛있지 않았어요', '좋지만 별로', '재미있지 않을 수 없다',
                    '10점 만점에 1점', '이건 아니다', 'ㅋㅋㅋㅋ', '좋다 나쁘다', '문의만 남깁니다', '']
        for _, config in sentiment.ABLATION_STEPS:
            for text in examples:
                result = analyzer.analyze(text, config)
                total = 0.
                for item in result.items:
                    value = item.base * item.negation_factor * item.contrast
                    for _, factor in item.modifiers:
                        value *= factor
                    self.assertAlmostEqual(value, item.value)
                    total += value
                total += sum(o['value'] for o in result.orphans)
                total += result.rating['value'] if result.rating else 0
                self.assertEqual(round(total, 6), result.score)
        cancelled = analyzer.analyze('좋다 나쁘다')
        empty = analyzer.analyze('문의만 남깁니다')
        self.assertTrue(cancelled.decided_by_tie and empty.decided_by_tie)
        self.assertGreater(len(cancelled.items), 0)
        self.assertEqual(len(empty.items), 0)
        self.assertIn('기여 상쇄', sentiment.explain(cancelled))

    def test_entity_slices_and_hidden_text_use_distinct_coordinates(self):
        text = '날짜 2023년 2월 29일, 문의 demo@example.com. 정말 맛있지 않았어요'
        entities = extract.extract(text)
        self.assertFalse(any(e.type == 'date' for e in entities))
        for e in entities:
            self.assertEqual(text[e.start:e.end], e.text)
        hidden = hide_entities(text, entities)
        self.assertNotIn('demo@example.com', hidden)
        self.assertNotEqual(text.index('정말'), hidden.index('정말'))
        self.assertEqual(sentiment.SentimentAnalyzer().analyze(hidden).score, -3)

    def test_extraction_matching_counts_duplicates_not_positions(self):
        pred = [('email', 'demo@example.com')] * 2
        gold = [('email', 'demo@example.com')]
        hit, extra, missed = eval_extraction._match(pred, gold)
        self.assertEqual((len(hit), len(extra), len(missed)), (1, 1, 0))

    def test_empty_file_json_is_an_empty_list(self):
        output = io.StringIO()
        with patch('builtins.open', mock_open(read_data='\n \n')), contextlib.redirect_stdout(output):
            self.assertEqual(main(['--file', 'empty.txt', '--json']), 0)
        self.assertEqual(json.loads(output.getvalue()), [])

    def test_statistical_vectorizer_fits_training_texts_only(self):
        from sklearn.feature_extraction.text import TfidfVectorizer

        train = [{'text': '좋은 영화', 'label': 1}, {'text': '멋진 작품', 'label': 1},
                 {'text': '나쁜 영화', 'label': 0}, {'text': '지루한 작품', 'label': 0}]
        test = ['🦄 테스트 전용 표현']
        fit_inputs, transform_inputs, instances = [], [], []

        class RecordingVectorizer(TfidfVectorizer):
            def fit_transform(self, documents, y=None):
                fit_inputs.append(list(documents))
                instances.append(self)
                return super().fit_transform(documents, y)

            def transform(self, documents):
                transform_inputs.append(list(documents))
                return super().transform(documents)

        with patch('src.bonus_tfidf.TfidfVectorizer', RecordingVectorizer):
            prediction, dimensions = bonus_tfidf.fit_predict(train, test)
        self.assertEqual(fit_inputs, [[row['text'] for row in train]])
        self.assertEqual(transform_inputs, [test])
        self.assertNotIn('🦄', instances[0].vocabulary_)
        self.assertEqual(len(prediction), 1)
        self.assertEqual(dimensions, len(instances[0].vocabulary_))


if __name__ == '__main__':
    unittest.main()
