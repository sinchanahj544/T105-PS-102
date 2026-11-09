
import sys
import unittest
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src")
)

from refund import (
    calculate_membership_refund,
    calculate_pt_refund
)
from renewal import calculate_renewal
from models import Member


class TestRefunds(unittest.TestCase):

    def test_monthly_refund_after_seven_days(self):
        today = date.today()

        refund = calculate_membership_refund(
            "PLUS", "MONTHLY", 2500,
            today - timedelta(days=10), today
        )

        self.assertEqual(refund, 0)

    def test_annual_refund(self):
        today = date.today()

        refund = calculate_membership_refund(
            "PLUS", "ANNUAL", 25000,
            today - timedelta(days=90), today
        )

        self.assertEqual(refund, 15000)

    def test_unused_pt_refund(self):
        today = date.today()

        refund = calculate_pt_refund(
            6000, 5, 3,
            today + timedelta(days=45), today
        )

        self.assertEqual(refund, 1800)

    def test_expired_pt_pack_refund(self):
        today = date.today()

        refund = calculate_pt_refund(
            6000, 5, 3,
            today - timedelta(days=1), today
        )

        self.assertEqual(refund, 0)

    def test_early_renewal_discount(self):
        today = date.today()

        member = Member(
            "M001", "Ananya", "PLUS",
            today, today + timedelta(days=10),
            "Bangalore"
        )

        result = calculate_renewal(member, today)

        self.assertEqual(
            result["discount_percentage"], 10.0
        )


if __name__ == "__main__":
    unittest.main()
