
import sys
import unittest
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src")
)

from models import Member
from membership import transfer_branch


class TestBranchTransfer(unittest.TestCase):

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

    def test_plus_transfer_fee(self):
        fee, cancelled = transfer_branch(
            self.member, "Mysore", date.today()
        )
        self.assertEqual(fee, 500)

    def test_elite_transfer_free(self):
        self.member.tier = "ELITE"

        fee, cancelled = transfer_branch(
            self.member, "Mysore", date.today()
        )
        self.assertEqual(fee, 0)

    def test_branch_is_updated(self):
        transfer_branch(
            self.member, "Mysore", date.today()
        )
        self.assertEqual(self.member.home_branch, "Mysore")

    def test_transfer_to_same_branch_rejected(self):
        with self.assertRaises(ValueError):
            transfer_branch(
                self.member, "Bangalore", date.today()
            )


if __name__ == "__main__":
    unittest.main()
