
import unittest
from datetime import date, datetime, timedelta

from personal_training import (
    PersonalTrainingManager,
    Trainer
)


class TestPersonalTraining(unittest.TestCase):

    def setUp(self):
        self.manager = PersonalTrainingManager()

        self.manager.add_trainer(
            Trainer(
                "T01",
                [
                    (
                        datetime(2026, 1, 11, 9, 0),
                        datetime(2026, 1, 12, 18, 0)
                    )
                ]
            )
        )

        self.manager.purchase_pack(
            "M01", "P01", 10, date(2026, 1, 1)
        )

    # BR-04: Test PT pack purchase
    def test_pack_purchase(self):
        pack = self.manager.packs["P01"]

        self.assertEqual(pack.total_sessions, 10)
        self.assertEqual(pack.remaining_sessions, 10)
        self.assertEqual(pack.price, 11000)

    # BR-04: Test pack expiry
    def test_pack_expiry(self):
        pack = self.manager.packs["P01"]

        self.assertEqual(
            pack.expiry_date,
            date(2026, 4, 1)
        )

    # BR-04: Test freeze pauses expiry
    def test_freeze_expiry_extension(self):
        self.manager.register_freeze(
            "M01",
            date(2026, 2, 1),
            date(2026, 2, 10)
        )

        pack = self.manager.packs["P01"]

        self.assertEqual(
            self.manager.get_expiry_date(pack),
            date(2026, 4, 11)
        )

    # BR-05: Test PT session booking
    def test_session_booking(self):
        result = self.manager.book_session(
            "B01",
            "M01",
            "P01",
            "T01",
            datetime(2026, 1, 11, 10, 0)
        )

        self.assertEqual(
            result,
            "PT session booked successfully"
        )

        self.assertEqual(
            self.manager.bookings["B01"].status,
            "BOOKED"
        )

    # BR-05: Test session completion
    def test_session_completion(self):
        self.manager.book_session(
            "B02", "M01", "P01", "T01",
            datetime(2026, 1, 11, 10, 0)
        )

        self.manager.complete_session("B02")

        self.assertEqual(
            self.manager.packs["P01"].remaining_sessions,
            9
        )

    # BR-05: Test no-show consumes session
    def test_no_show(self):
        self.manager.book_session(
            "B03", "M01", "P01", "T01",
            datetime(2026, 1, 11, 10, 0)
        )

        self.manager.mark_no_show("B03")

        self.assertEqual(
            self.manager.packs["P01"].remaining_sessions,
            9
        )

    # BR-05: Cancellation more than 12 hours before
    def test_early_cancellation(self):
        self.manager.book_session(
            "B04", "M01", "P01", "T01",
            datetime(2026, 1, 11, 10, 0)
        )

        self.manager.cancel_session(
            "B04",
            datetime(2026, 1, 10, 20, 0)
        )

        self.assertEqual(
            self.manager.packs["P01"].remaining_sessions,
            10
        )

    # BR-05: Exactly 12 hours before start
    def test_exactly_12_hours_cancellation(self):
        self.manager.book_session(
            "B05", "M01", "P01", "T01",
            datetime(2026, 1, 11, 10, 0)
        )

        self.manager.cancel_session(
            "B05",
            datetime(2026, 1, 10, 22, 0)
        )

        self.assertEqual(
            self.manager.bookings["B05"].status,
            "LATE_CANCEL"
        )

        self.assertEqual(
            self.manager.packs["P01"].remaining_sessions,
            10
        )

    # BR-05: Cancellation less than 4 hours before
    def test_late_cancellation_consumes_session(self):
        self.manager.book_session(
            "B06", "M01", "P01", "T01",
            datetime(2026, 1, 11, 10, 0)
        )

        self.manager.cancel_session(
            "B06",
            datetime(2026, 1, 11, 7, 0)
        )

        self.assertEqual(
            self.manager.packs["P01"].remaining_sessions,
            9
        )

    # BR-05: Three late cancellations make
    # the next cancellation consume a session
    def test_three_late_cancellations(self):

        start_times = [
            datetime(2026, 1, 11, 10, 0),
            datetime(2026, 1, 11, 12, 0),
            datetime(2026, 1, 11, 14, 0)
        ]

        for i, start in enumerate(start_times):
            booking_id = f"L{i}"

            self.manager.book_session(
                booking_id, "M01", "P01", "T01", start
            )

            self.manager.cancel_session(
                booking_id,
                start - timedelta(hours=6)
            )

        # Fourth cancellation is more than 12 hours early
        # but must consume a session after 3 late cancels
        self.manager.book_session(
            "L3", "M01", "P01", "T01",
            datetime(2026, 1, 12, 16, 0)
        )

        self.manager.cancel_session(
            "L3",
            datetime(2026, 1, 11, 20, 0)
        )

        self.assertEqual(
            self.manager.bookings["L3"].status,
            "CONSUMED"
        )

        self.assertEqual(
            self.manager.packs["P01"].remaining_sessions,
            9
        )


if __name__ == "__main__":
    unittest.main()
