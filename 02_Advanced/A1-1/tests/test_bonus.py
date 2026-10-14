"""Bonus semantics: image evidence, signup denominators and censoring."""
import unittest

import numpy as np
import pandas as pd

from src.bonus import image_features, interactive_rfm, signup_cohorts


class ImageFeatureTests(unittest.TestCase):
    def test_known_histogram_and_edges(self):
        pixels = np.array([[[0, 0], [255, 255]], [[32, 32], [32, 32]]], dtype=np.uint8)
        features = image_features(pixels)
        np.testing.assert_allclose(features.filter(like='image_hist_').sum(axis=1), 1)
        self.assertEqual(features.loc[0, 'image_hist_0'], .5)
        self.assertEqual(features.loc[0, 'image_hist_7'], .5)
        self.assertEqual(features.loc[0, 'image_edge_mean'], 127.5)
        self.assertEqual(features.loc[0, 'image_entropy'], 1)
        self.assertEqual(features.loc[1, 'image_hist_1'], 1)
        self.assertEqual(features.loc[1, 'image_edge_mean'], 0)
        self.assertEqual(features.loc[1, 'image_entropy'], 0)

    def test_rgb_luminance_and_single_pixel(self):
        f = image_features(np.array([[[[255, 0, 0]]]]))
        self.assertEqual(f.loc[0, 'image_hist_1'], 1)
        self.assertEqual(f.loc[0, 'image_edge_mean'], 0)

    def test_reject_invalid_scale(self):
        for values in (np.array([[[256]]]), np.array([[[np.nan]]]), np.array([[[-1]]])):
            with self.assertRaises(ValueError):
                image_features(values)


class CohortTests(unittest.TestCase):
    def setUp(self):
        self.customers = pd.DataFrame({'customer_id': ['A', 'B', 'C'],
                                       'signup_date': ['2026-01-01', '2026-01-10', '2026-02-01']})
        self.transactions = pd.DataFrame({'customer_id': ['A', 'A', 'A', 'C', 'B'],
                                         'order_date': ['2026-01-15', '2026-01-15', '2026-02-10', '2026-02-10', '2026-02-12'],
                                         'amount': [10, 20, 10, 10, -10], 'unit_price': [10, 20, 10, 10, 10],
                                         'quantity': [1, 1, 1, 1, -1]})

    def test_signups_not_buyers_and_distinct_monthly_activity(self):
        sizes, counts, rates = signup_cohorts(self.transactions, self.customers, '2026-02-28')
        jan, feb = pd.Period('2026-01'), pd.Period('2026-02')
        self.assertEqual(sizes.loc[jan], 2)
        self.assertEqual(counts.loc[jan, 0], 1)  # two lines, one customer; B never bought
        self.assertEqual(rates.loc[jan, 0], .5)
        self.assertEqual(rates.loc[jan, 1], .5)  # refund doesn't count as activity
        self.assertEqual(rates.loc[feb, 0], 1)
        self.assertTrue(np.isnan(rates.loc[feb, 1]))

    def test_incomplete_month_is_masked_not_zero(self):
        _, counts, rates = signup_cohorts(self.transactions, self.customers, '2026-02-15')
        self.assertTrue(rates[1].isna().all())
        self.assertTrue(np.isnan(counts.loc[pd.Period('2026-02'), 0]))
        self.assertEqual(rates.loc[pd.Period('2026-01'), 0], .5)

    def test_observed_zero_and_nonpurchasing_cohort(self):
        customers = pd.concat([self.customers, pd.DataFrame({'customer_id': ['D'], 'signup_date': ['2025-12-01']})])
        _, counts, rates = signup_cohorts(self.transactions, customers, '2026-02-28')
        self.assertEqual(rates.loc[pd.Period('2025-12'), 2], 0)
        self.assertEqual(counts.loc[pd.Period('2025-12'), 0], 0)

    def test_signup_after_purchase_and_unknown_customer_rejected(self):
        self.customers.loc[0, 'signup_date'] = '2026-02-01'
        with self.assertRaisesRegex(ValueError, 'precede signup'):
            signup_cohorts(self.transactions, self.customers)
        with self.assertRaisesRegex(ValueError, 'needs a signup'):
            signup_cohorts(self.transactions, self.customers.iloc[1:])

    def test_cutoff_and_duplicate_signup_rejected(self):
        with self.assertRaisesRegex(ValueError, 'precede observed'):
            signup_cohorts(self.transactions, self.customers, '2026-02-05')
        with self.assertRaisesRegex(ValueError, 'unique'):
            signup_cohorts(self.transactions, pd.concat([self.customers, self.customers]))


class InteractiveTests(unittest.TestCase):
    def test_all_customers_and_hover_match_source(self):
        frame = pd.DataFrame({'frequency': [1, 3], 'monetary': [20, 50], 'recency': [5, 10],
                              'r_score': [5, 4], 'f_score': [1, 5], 'm_score': [2, 5],
                              'segment': ['New', 'Loyal']}, index=['A', 'B'])
        figure = interactive_rfm(frame)
        self.assertEqual(sum(len(trace.x) for trace in figure.data), 2)
        for trace in figure.data:
            for x, y, custom in zip(trace.x, trace.y, trace.customdata):
                row = frame.loc[custom[0]]
                self.assertEqual(x, row.frequency)
                self.assertEqual(y, row.monetary)
                self.assertEqual(int(custom[1]), row.recency)
        html = figure.to_html(include_plotlyjs=True, full_html=True)
        self.assertIn('plotly.js', html)
        self.assertNotIn('<script src=', html)


if __name__ == '__main__':
    unittest.main()
