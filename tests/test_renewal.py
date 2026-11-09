
import sys
import unittest
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src")
)

from models import Member
from renewal import add_months, calculate_renewal, renew_membership


class TestRenewal(unittest.TestCase):

    def setUp(self):
        self.member = Member(
            "M001",
            "Ananya",
            "PLUS",
            date(2026, 1, 1),
            date(2026, 12, 31),
            "Bangalore"
        )

    def test_january_31_to_february(self):
        result = add_months(date(2025, 1, 31), 1)
        self.assertEqual(result, date(2025, 2, 28))

    def test_leap_year_february(self):
        result = add_months(date(2024, 1, 31), 1)
        self.assertEqual(result, date(2024, 2, 29))

    def test_early_renewal_discount(self):
        result = calculate_renewal(
            self.member,
            date(2026, 12, 20)
        )
        self.assertEqual(result["discount_percentage"], 10)

    def test_lapsed_membership_joining_fee(self):
        result = calculate_renewal(
            self.member,
            date(2027, 2, 5)
        )
        self.assertEqual(result["joining_fee"], 1000)

    def test_renewal_updates_end_date(self):
        renew_membership(
            self.member,
            date(2026, 12, 31)
        )
        self.assertEqual(
            self.member.end_date,
            date(2027, 1, 31)
        )


if __name__ == "__main__":
    unittest.main()
