
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Optional


# BR-04: PT Pack Details

PACK_DETAILS = {
    5: {"price": 6000, "validity": 45},
    10: {"price": 11000, "validity": 90},
    20: {"price": 20000, "validity": 180}
}


@dataclass
class PTPack:
    pack_id: str
    member_id: str
    total_sessions: int
    remaining_sessions: int
    purchase_date: date
    expiry_date: date
    price: int


@dataclass
class Trainer:
    trainer_id: str
    available_slots: List[tuple] = field(default_factory=list)


@dataclass
class PTBooking:
    booking_id: str
    member_id: str
    trainer_id: str
    pack_id: str
    start_time: datetime
    end_time: datetime
    status: str = "BOOKED"


class PersonalTrainingManager:

    def __init__(self):
        self.packs = {}
        self.bookings = {}
        self.trainers = {}
        self.freeze_periods = {}
        self.late_cancellations = {}

    # Register trainer availability
    def add_trainer(self, trainer):
        self.trainers[trainer.trainer_id] = trainer

    # BR-04: Purchase PT pack
    def purchase_pack(self, member_id, pack_id, sessions, purchase_date):

        if sessions not in PACK_DETAILS:
            raise ValueError("Invalid PT pack")

        details = PACK_DETAILS[sessions]

        pack = PTPack(
            pack_id=pack_id,
            member_id=member_id,
            total_sessions=sessions,
            remaining_sessions=sessions,
            purchase_date=purchase_date,
            expiry_date=purchase_date + timedelta(days=details["validity"]),
            price=details["price"]
        )

        if pack_id in self.packs:
            raise ValueError("Pack ID already exists")

        self.packs[pack_id] = pack

        return f"PT pack purchased successfully: {sessions} sessions"

    # BR-04: Register membership freeze
    def register_freeze(self, member_id, start_date, end_date):

        if end_date < start_date:
            raise ValueError("Invalid freeze dates")

        self.freeze_periods.setdefault(member_id, []).append(
            (start_date, end_date)
        )

    # Calculate expiry after pausing it during freezes
    def get_expiry_date(self, pack):

        expiry = pack.expiry_date
        periods = sorted(
            self.freeze_periods.get(pack.member_id, [])
        )

        # Merge overlapping freeze periods
        merged = []

        for start, end in periods:
            if not merged or start > merged[-1][1] + timedelta(days=1):
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)

        for start, end in merged:

            if start <= expiry and end >= pack.purchase_date:
                effective_start = max(start, pack.purchase_date)
                paused_days = (end - effective_start).days + 1
                expiry += timedelta(days=paused_days)

        return expiry

    # Check pack validity
    def check_pack_validity(self, pack_id, check_date):

        if pack_id not in self.packs:
            raise ValueError("PT pack not found")

        pack = self.packs[pack_id]

        if check_date > self.get_expiry_date(pack):
            return False

        return pack.remaining_sessions > 0

    # BR-05: Book a PT session
    def book_session(self, booking_id, member_id, pack_id,
                     trainer_id, start_time, duration=60):

        if booking_id in self.bookings:
            raise ValueError("Booking ID already exists")

        if pack_id not in self.packs:
            raise ValueError("PT pack not found")

        if trainer_id not in self.trainers:
            raise ValueError("Trainer not found")

        pack = self.packs[pack_id]

        if pack.member_id != member_id:
            raise ValueError("PT pack does not belong to member")

        if not self.check_pack_validity(pack_id, start_time.date()):
            raise ValueError("PT pack expired or no sessions available")

        trainer = self.trainers[trainer_id]
        end_time = start_time + timedelta(minutes=duration)

        # Check trainer availability
        available = any(
            start <= start_time and end_time <= end
            for start, end in trainer.available_slots
        )

        if not available:
            raise ValueError("Trainer is not available")

        # Prevent double booking
        for booking in self.bookings.values():

            if (booking.trainer_id == trainer_id
                and booking.status == "BOOKED"
                and start_time < booking.end_time
                and end_time > booking.start_time):

                raise ValueError("Trainer already has a booking")

        reserved = sum(
            1 for b in self.bookings.values()
            if b.pack_id == pack_id and b.status == "BOOKED"
        )

        if pack.remaining_sessions - reserved <= 0:
            raise ValueError("No PT sessions available")

        booking = PTBooking(
            booking_id,
            member_id,
            trainer_id,
            pack_id,
            start_time,
            end_time
        )

        self.bookings[booking_id] = booking

        return "PT session booked successfully"

    # BR-05: Complete a PT session
    def complete_session(self, booking_id):

        booking = self._get_booking(booking_id)

        pack = self.packs[booking.pack_id]

        pack.remaining_sessions -= 1
        booking.status = "COMPLETED"

        return "Session completed and consumed"

    # BR-05: No-show consumes one session
    def mark_no_show(self, booking_id):

        booking = self._get_booking(booking_id)

        pack = self.packs[booking.pack_id]

        pack.remaining_sessions -= 1
        booking.status = "NO_SHOW"

        return "No-show recorded. Session consumed"

    # BR-05: Cancel PT session
    def cancel_session(self, booking_id, cancellation_time):

        booking = self._get_booking(booking_id)

        pack = self.packs[booking.pack_id]

        hours_before = (
            booking.start_time - cancellation_time
        ).total_seconds() / 3600

        history = self.late_cancellations.setdefault(
            booking.member_id, []
        )

        # Keep late cancellations within the last 30 days
        cutoff = cancellation_time - timedelta(days=30)

        history[:] = [
            t for t in history if cutoff <= t <= cancellation_time
        ]

        # Three late cancellations make the NEXT
        # cancellation consume a session
        if len(history) >= 3:

            pack.remaining_sessions -= 1
            booking.status = "CONSUMED"

            return "Session consumed due to repeated late cancellations"

        # More than 12 hours: session returned
        if hours_before > 12:

            booking.status = "CANCELLED"

            return "Session cancelled. Session returned"

        # Between 4 and 12 hours, including exactly 12
        if 4 <= hours_before <= 12:

            history.append(cancellation_time)
            booking.status = "LATE_CANCEL"

            return "Late cancellation recorded. Session returned"

        # Less than 4 hours: session consumed
        pack.remaining_sessions -= 1
        booking.status = "CONSUMED"

        return "Late cancellation. Session consumed"

    # Get booking safely
    def _get_booking(self, booking_id):

        if booking_id not in self.bookings:
            raise ValueError("Booking not found")

        booking = self.bookings[booking_id]

        if booking.status != "BOOKED":
            raise ValueError("Booking already processed")

        return booking

    # Display PT pack balance
    def get_pack_balance(self, pack_id, check_date):

        if pack_id not in self.packs:
            raise ValueError("PT pack not found")

        pack = self.packs[pack_id]

        if check_date > self.get_expiry_date(pack):
            return 0

        reserved = sum(
            1 for b in self.bookings.values()
            if b.pack_id == pack_id and b.status == "BOOKED"
        )

        return max(0, pack.remaining_sessions - reserved)

    # Display member PT details
    def member_pt_statement(self, member_id, check_date):

        result = []

        for pack in self.packs.values():

            if pack.member_id == member_id:

                result.append({
                    "Pack ID": pack.pack_id,
                    "Total Sessions": pack.total_sessions,
                    "Remaining Sessions": self.get_pack_balance(
                        pack.pack_id, check_date
                    ),
                    "Expiry Date": self.get_expiry_date(pack),
                    "Price": pack.price
                })

        return result
