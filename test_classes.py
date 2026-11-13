
import unittest
from datetime import date, datetime, timedelta

from class_booking import (
    ClassBookingManager,
    Member,
    FitnessClass
)


class TestClassBooking(unittest.TestCase):

    def setUp(self):
        self.manager = ClassBookingManager()

        self.manager.add_member(
            Member("M01", "ELITE", date(2026, 1, 1), "BranchA")
        )

        self.manager.add_member(
            Member("M02", "PLUS", date(2026, 1, 1), "BranchA")
        )

        self.manager.add_member(
            Member("M03", "BASIC", date(2026, 1, 1), "BranchA")
        )

        self.now = datetime(2026, 1, 10, 9, 0)

    def create_class(self, class_id, capacity=2, hours=5):
        fitness_class = FitnessClass(
            class_id,
            "Yoga",
            "BranchA",
            self.now + timedelta(hours=hours),
            capacity
        )

        self.manager.add_class(fitness_class)

        return fitness_class

    # BR-06: Successful class booking
    def test_class_booking(self):
        self.create_class("C01")

        result = self.manager.book_class(
            "B01", "M01", "C01", self.now
        )

        self.assertEqual(result, "Class booked successfully")

    # BR-06: Class capacity and waitlist
    def test_waitlist_when_class_full(self):
        self.create_class("C02", capacity=1)

        self.manager.book_class(
            "B01", "M01", "C02", self.now
        )

        result = self.manager.book_class(
            "B02", "M02", "C02", self.now
        )

        self.assertEqual(
            result,
            "Class full. Member added to waitlist"
        )

        self.assertEqual(
            len(self.manager.classes["C02"].waitlist), 1
        )

    # BR-06: ELITE waitlist priority
    def test_elite_waitlist_priority(self):
        self.manager.add_member(
            Member("M04", "ELITE", date(2026, 1, 1), "BranchA")
        )

        self.create_class("C03", capacity=1)

        self.manager.book_class(
            "B01", "M01", "C03", self.now
        )

        self.manager.book_class(
            "B02", "M02", "C03", self.now
        )

        self.manager.book_class(
            "B03", "M04", "C03",
            self.now + timedelta(minutes=1)
        )

        waitlist = self.manager.classes["C03"].waitlist

        self.assertEqual(waitlist[0], "B03")
        self.assertEqual(waitlist[1], "B02")

    # BR-06: Automatic waitlist promotion
    def test_waitlist_promotion(self):
        self.create_class("C04", capacity=1)

        self.manager.book_class(
            "B01", "M01", "C04", self.now
        )

        self.manager.book_class(
            "B02", "M02", "C04", self.now
        )

        cancellation_time = self.now + timedelta(minutes=30)

        self.manager.cancel_class(
            "B01", cancellation_time
        )

        self.assertEqual(
            self.manager.bookings["B02"].status,
            "CONFIRMED"
        )

    # BR-06: No promotion exactly 2 hours before class
    def test_promotion_exactly_two_hours_before(self):
        self.create_class("C05", capacity=1, hours=5)

        self.manager.book_class(
            "B01", "M01", "C05", self.now
        )

        self.manager.book_class(
            "B02", "M02", "C05", self.now
        )

        fitness_class = self.manager.classes["C05"]

        promotion_time = (
            fitness_class.start_time - timedelta(hours=2)
        )

        result = self.manager.promote_waitlist(
            "C05", promotion_time
        )

        self.assertEqual(
            result,
            "Promotion not allowed within 2 hours of class"
        )

    # BR-07: PLUS quota of 8 classes
    def test_plus_class_quota(self):
        for i in range(8):
            class_id = f"Q{i}"

            self.create_class(class_id, capacity=10)

            result = self.manager.book_class(
                f"B{i}", "M02", class_id, self.now
            )

            self.assertEqual(result, "Class booked successfully")

        self.create_class("Q9", capacity=10)

        result = self.manager.book_class(
            "B9", "M02", "Q9", self.now
        )

        self.assertEqual(
            result,
            "Monthly class quota exceeded"
        )

    # BR-07: Billing anniversary on 31st
    def test_billing_anniversary_31st(self):
        billing_date = date(2026, 1, 31)

        result = self.manager.get_billing_anniversary(
            billing_date, 2026, 2
        )

        self.assertEqual(result, date(2026, 2, 28))

    # BR-08: First no-show
    def test_first_no_show(self):
        self.create_class("C06")

        self.manager.book_class(
            "B01", "M01", "C06", self.now
        )

        class_time = self.manager.classes["C06"].start_time

        result = self.manager.mark_no_show(
            "B01", class_time
        )

        self.assertEqual(result, "No-show recorded")

    # BR-08: Two no-shows block member for 7 days
    def test_two_no_shows_block_member(self):
        for i in range(2):
            class_id = f"N{i}"

            self.create_class(class_id, capacity=5)

            self.manager.book_class(
                f"NB{i}", "M01", class_id, self.now
            )

            class_time = self.manager.classes[
                class_id
            ].start_time

            self.manager.mark_no_show(
                f"NB{i}", class_time
            )

        member = self.manager.members["M01"]

        self.assertEqual(
            member.blocked_until,
            self.now + timedelta(hours=5) + timedelta(days=7)
        )

    # BR-08: Blocked member cannot book class
    def test_blocked_member_cannot_book(self):
        self.manager.members["M01"].blocked_until = (
            self.now + timedelta(days=7)
        )

        self.create_class("C07")

        result = self.manager.book_class(
            "B07", "M01", "C07", self.now
        )

        self.assertEqual(
            result,
            "Member is blocked from class booking"
        )

    # BASIC members cannot book classes
    def test_basic_member_cannot_book(self):
        self.create_class("C08")

        result = self.manager.book_class(
            "B08", "M03", "C08", self.now
        )

        self.assertEqual(
            result,
            "BASIC members cannot book group classes"
        )


if __name__ == "__main__":
    unittest.main()
