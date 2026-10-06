import unittest
from datetime import date
from decimal import Decimal as D

from app.logic import (FcoFigures, calculate, disqualification_reasons, last_friday,
                       pick_winner, rank_fcos)

MIN_B, MIN_D = D(85), D(20_000_000)


def fig(i, name, disb, over):
    return FcoFigures(i, name, None, D(disb), D(over))


class LastFridayTests(unittest.TestCase):
    def test_spec_examples(self):
        self.assertEqual(last_friday(2026, 1), date(2026, 1, 30))
        self.assertEqual(last_friday(2026, 2), date(2026, 2, 27))
        self.assertEqual(last_friday(2025, 12), date(2025, 12, 26))

    def test_month_ending_on_friday_and_on_saturday(self):
        self.assertEqual(last_friday(2025, 10), date(2025, 10, 31))  # 31st is a Friday
        self.assertEqual(last_friday(2026, 10), date(2026, 10, 30))  # 31st is a Saturday

    def test_always_a_friday(self):
        for y in (2024, 2025, 2026, 2027):
            for m in range(1, 13):
                self.assertEqual(last_friday(y, m).weekday(), 4)


class CalculateTests(unittest.TestCase):
    def test_spec_example_ayo(self):
        bal, pct = calculate(D(25_000_000), D(1_500_000))
        self.assertEqual(bal, D(23_500_000))
        self.assertEqual(pct, D(94))

    def test_overdue_zero_is_100(self):
        self.assertEqual(calculate(D(30_000_000), D(0))[1], D(100))

    def test_zero_disbursement_is_zero_not_error(self):
        self.assertEqual(calculate(D(0), D(0)), (D(0), D(0)))


class RankingTests(unittest.TestCase):
    def setUp(self):
        self.ranked = rank_fcos([
            fig(1, "Ayo", 25_000_000, 1_500_000),
            fig(2, "Blessing", 22_000_000, 2_000_000),
            fig(3, "Emeka", 18_000_000, 1_000_000),   # 94.4% but < 20M
        ], MIN_B, MIN_D)

    def test_matches_spec_dashboard_order(self):
        self.assertEqual([r.name for r in self.ranked], ["Ayo", "Blessing", "Emeka"])
        self.assertEqual([r.qualified for r in self.ranked], [True, True, False])

    def test_winner_is_top_qualified(self):
        self.assertEqual(pick_winner(self.ranked).name, "Ayo")

    def test_thresholds_are_inclusive(self):
        r = rank_fcos([fig(1, "Edge", 20_000_000, 3_000_000)], MIN_B, MIN_D)  # exactly 85% & 20M
        self.assertTrue(r[0].qualified)
        r = rank_fcos([fig(1, "Under", 20_000_000, 3_000_001)], MIN_B, MIN_D)
        self.assertFalse(r[0].qualified)

    def test_tie_goes_to_higher_disbursement(self):
        r = rank_fcos([fig(1, "Small", 20_000_000, 1_000_000),
                       fig(2, "Big", 40_000_000, 2_000_000)], MIN_B, MIN_D)  # both 95%
        self.assertEqual(r[0].name, "Big")

    def test_nobody_qualified(self):
        r = rank_fcos([fig(1, "A", 10_000_000, 0), fig(2, "B", 30_000_000, 9_000_000)], MIN_B, MIN_D)
        self.assertIsNone(pick_winner(r))

    def test_reasons_text(self):
        self.assertEqual(disqualification_reasons(D(18_000_000), D(94), MIN_B, MIN_D),
                         ["Disbursement below \u20a620M"])
        self.assertEqual(disqualification_reasons(D(30_000_000), D(80), MIN_B, MIN_D),
                         ["Bonus % below 85%"])


if __name__ == "__main__":
    unittest.main()
