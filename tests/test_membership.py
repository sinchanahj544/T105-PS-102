
import sys
import unittest
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src")
)

from membership import (
    get_membership_price,
    register_member,
    transfer_branch
)


class TestMembership(unittest.TestCase):

    def test_basic_monthly_price(self):
        self.assertEqual(
            get_membership_price("BASIC"), 1500
        )

    def test_plus_annual_price(self):
        self.assertEqual(
            get_membership_price("PLUS", "ANNUAL"), 25000
        )

    def test_elite_monthly_price(self):
        self.assertEqual(
            get_membership_price("ELITE"), 4000
        )

    def test_invalid_tier(self):
        with self.assertRaises(ValueError):
            get_membership_price("GOLD")

    def test_member_registration(self):
        today = date.today()

        member = register_member(
            "M001",
            "Ananya",
            "PLUS",
            today,
            today + timedelta(days=30),
            "Bangalore"
        )

        self.assertEqual(member.name, "Ananya")
        self.assertEqual(member.tier, "PLUS")
        self.assertEqual(member.status, "ACTIVE")

    def test_elite_free_branch_transfer(self):
        today = date.today()

        member = register_member(
            "M002",
            "Rahul",
            "ELITE",
            today,
            today + timedelta(days=180),
            "Bangalore"
        )

        fee, cancelled = transfer_branch(
            member, "Mysore", today
        )

        self.assertEqual(fee, 0)
        self.assertEqual(member.home_branch, "Mysore")

    def test_plus_branch_transfer_fee(self):
        today = date.today()

        member = register_member(
            "M003",
            "Priya",
            "PLUS",
            today,
            today + timedelta(days=180),
            "Bangalore"
        )

        fee, cancelled = transfer_branch(
            member, "Mysore", today
        )

        self.assertEqual(fee, 500)


if __name__ == "__main__":
    unittest.main()
