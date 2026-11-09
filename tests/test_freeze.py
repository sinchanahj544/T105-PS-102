
import sys
import unittest
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src")
)

from models import Member
from freeze import (
    freeze_membership,
    extend_freeze,
    unfreeze_membership
)


class TestFreeze(unittest.TestCase):

    def setUp(self):
        today = date.today()

        self.member = Member(
            "M001",
            "Ananya",
            "PLUS",
            today,
            today + timedelta(days=180),
            "Bangalore"
        )

    def test_normal_freeze(self):
        fee = freeze_membership(
            self.member, date.today(), 10
        )

        self.assertEqual(fee, 300)
        self.assertEqual(self.member.status, "FROZEN")

    def test_elite_freeze_is_free(self):
        self.member.tier = "ELITE"

        fee = freeze_membership(
            self.member, date.today(), 10
        )

        self.assertEqual(fee, 0)

    def test_medical_freeze_is_free(self):
        fee = freeze_membership(
            self.member,
            date.today(),
            10,
            medical_certificate=True
        )

        self.assertEqual(fee, 0)

    def test_invalid_freeze_period(self):
        with self.assertRaises(ValueError):
            freeze_membership(
                self.member, date.today(), 5
            )

    def test_freeze_extension(self):
        today = date.today()

        freeze_membership(self.member, today, 10)
        result = extend_freeze(self.member, 5)

        self.assertEqual(
            result, "Freeze successfully extended"
        )
        self.assertEqual(self.member.frozen_days_this_year, 15)

    def test_unfreeze(self):
        today = date.today()

        freeze_membership(self.member, today, 10)

        result = unfreeze_membership(
            self.member, today + timedelta(days=10)
        )

        self.assertEqual(self.member.status, "ACTIVE")


if __name__ == "__main__":
    unittest.main()
