
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from calendar import monthrange


# BR-06, BR-07 and BR-08


@dataclass
class Member:
    member_id: str
    tier: str
    billing_date: date
    home_branch: str
    status: str = "ACTIVE"
    blocked_until: datetime = None


@dataclass
class FitnessClass:
    class_id: str
    class_name: str
    branch: str
    start_time: datetime
    capacity: int
    confirmed: list = field(default_factory=list)
    waitlist: list = field(default_factory=list)


@dataclass
class ClassBooking:
    booking_id: str
    member_id: str
    class_id: str
    booking_time: datetime
    status: str = "CONFIRMED"


class ClassBookingManager:

    def __init__(self):
        self.members = {}
        self.classes = {}
        self.bookings = {}
        self.quota_usage = {}
        self.no_show_history = {}

    # Register a gym member
    def add_member(self, member):
        self.members[member.member_id] = member
        self.quota_usage[member.member_id] = []

    # Add a fitness class
    def add_class(self, fitness_class):
        self.classes[fitness_class.class_id] = fitness_class

    # BR-07: Calculate billing anniversary
    # Handles dates such as 31st in a 30-day month
    def get_billing_anniversary(self, billing_date, year, month):

        last_day = monthrange(year, month)[1]
        day = min(billing_date.day, last_day)

        return date(year, month, day)

    # Find the current billing cycle
    def get_billing_cycle_start(self, member, check_date):

        original = member.billing_date

        anniversary = self.get_billing_anniversary(
            original,
            check_date.year,
            check_date.month
        )

        if anniversary > check_date:
            if check_date.month == 1:
                year, month = check_date.year - 1, 12
            else:
                year, month = check_date.year, check_date.month - 1

            anniversary = self.get_billing_anniversary(
                original, year, month
            )

        return max(anniversary, original)

    # BR-07: Check PLUS class quota
    def get_classes_used(self, member_id, check_date):

        member = self.members[member_id]

        cycle_start = self.get_billing_cycle_start(
            member, check_date
        )

        return sum(
            1 for usage_date in self.quota_usage[member_id]
            if cycle_start <= usage_date <= check_date
        )

    def has_quota(self, member_id, check_date):

        member = self.members[member_id]

        if member.tier == "ELITE":
            return True

        if member.tier == "PLUS":
            return self.get_classes_used(
                member_id, check_date
            ) < 8

        return False

    # Check membership and booking restrictions
    def check_member_eligibility(self, member, fitness_class, now):

        if member.status != "ACTIVE":
            return "Membership is not active"

        if member.blocked_until and now < member.blocked_until:
            return "Member is blocked from class booking"

        if member.tier == "BASIC":
            return "BASIC members cannot book group classes"

        if member.tier == "PLUS":
            if fitness_class.branch != member.home_branch:
                return "PLUS members can book only at home branch"

        elif member.tier != "ELITE":
            return "Invalid membership tier"

        return None

    # BR-06 and BR-07: Book a class
    def book_class(self, booking_id, member_id, class_id, booking_time):

        if booking_id in self.bookings:
            return "Booking ID already exists"

        if member_id not in self.members:
            return "Member not found"

        if class_id not in self.classes:
            return "Class not found"

        member = self.members[member_id]
        fitness_class = self.classes[class_id]

        # Check membership state before capacity
        error = self.check_member_eligibility(
            member, fitness_class, booking_time
        )

        if error:
            return error

        if booking_time >= fitness_class.start_time:
            return "Class booking is closed"

        # Capacity is checked before quota and waitlist placement
        is_full = len(fitness_class.confirmed) >= fitness_class.capacity

        # Check quota before waitlist placement
        if not self.has_quota(member_id, booking_time.date()):
            return "Monthly class quota exceeded"

        booking = ClassBooking(
            booking_id,
            member_id,
            class_id,
            booking_time
        )

        self.bookings[booking_id] = booking

        if is_full:
            booking.status = "WAITLISTED"
            fitness_class.waitlist.append(booking_id)

            self.sort_waitlist(class_id)

            return "Class full. Member added to waitlist"

        fitness_class.confirmed.append(booking_id)

        # Confirmed booking consumes quota
        self.quota_usage[member_id].append(booking_time.date())

        return "Class booked successfully"

    # BR-06: Sort waitlist by tier and booking time
    def sort_waitlist(self, class_id):

        fitness_class = self.classes[class_id]

        priority = {
            "ELITE": 1,
            "PLUS": 2,
            "BASIC": 3
        }

        fitness_class.waitlist.sort(
            key=lambda booking_id: (
                priority.get(
                    self.members[
                        self.bookings[booking_id].member_id
                    ].tier, 99
                ),
                self.bookings[booking_id].booking_time
            )
        )

    # BR-06: Automatically promote waitlisted member
    def promote_waitlist(self, class_id, current_time):

        fitness_class = self.classes[class_id]

        if current_time >= fitness_class.start_time - timedelta(hours=2):
            return "Promotion not allowed within 2 hours of class"

        if len(fitness_class.confirmed) >= fitness_class.capacity:
            return "Class is still full"

        if not fitness_class.waitlist:
            return "Waitlist is empty"

        # Only the head of the waitlist is considered
        booking_id = fitness_class.waitlist[0]
        booking = self.bookings[booking_id]

        member = self.members[booking.member_id]

        error = self.check_member_eligibility(
            member, fitness_class, current_time
        )

        if error:
            return "Promotion unavailable: " + error

        if not self.has_quota(
            member.member_id, current_time.date()
        ):
            return "Promotion unavailable: Monthly quota exceeded"

        fitness_class.waitlist.pop(0)
        fitness_class.confirmed.append(booking_id)

        booking.status = "CONFIRMED"

        # Quota is consumed only after promotion
        self.quota_usage[member.member_id].append(
            current_time.date()
        )

        return "Waitlisted member promoted successfully"

    # BR-06: Cancel a class booking
    def cancel_class(self, booking_id, cancellation_time):

        if booking_id not in self.bookings:
            return "Booking not found"

        booking = self.bookings[booking_id]

        if booking.status not in ("CONFIRMED", "WAITLISTED"):
            return "Booking already processed"

        fitness_class = self.classes[booking.class_id]

        if booking.status == "WAITLISTED":

            fitness_class.waitlist.remove(booking_id)
            booking.status = "CANCELLED"

            return "Waitlist booking cancelled"

        fitness_class.confirmed.remove(booking_id)

        hours_before = (
            fitness_class.start_time - cancellation_time
        ).total_seconds() / 3600

        if hours_before > 2:

            usage = self.quota_usage[booking.member_id]

            if booking.booking_time.date() in usage:
                usage.remove(booking.booking_time.date())

            booking.status = "CANCELLED"

        else:
            # Cancellation within 2 hours consumes quota
            booking.status = "LATE_CANCEL"

        # Try automatic promotion
        promotion_result = self.promote_waitlist(
            booking.class_id, cancellation_time
        )

        return "Class booking cancelled. " + promotion_result

    # BR-08: Record a class no-show
    def mark_no_show(self, booking_id, current_time):

        if booking_id not in self.bookings:
            return "Booking not found"

        booking = self.bookings[booking_id]

        if booking.status != "CONFIRMED":
            return "Invalid booking status"

        fitness_class = self.classes[booking.class_id]

        if current_time < fitness_class.start_time:
            return "Class has not started yet"

        fitness_class.confirmed.remove(booking_id)

        booking.status = "NO_SHOW"

        history = self.no_show_history.setdefault(
            booking.member_id, []
        )

        cutoff = current_time - timedelta(days=30)

        history[:] = [
            t for t in history if cutoff <= t <= current_time
        ]

        history.append(current_time)

        # Two no-shows within 30 days cause a 7-day block
        if len(history) >= 2:

            member = self.members[booking.member_id]

            member.blocked_until = current_time + timedelta(days=7)

            return "No-show recorded. Member blocked for 7 days"

        return "No-show recorded"

    # Check whether a member is blocked
    def is_member_blocked(self, member_id, current_time):

        if member_id not in self.members:
            return False

        blocked_until = self.members[member_id].blocked_until

        return (
            blocked_until is not None
            and current_time < blocked_until
        )

    # Display class booking details
    def get_class_details(self, class_id):

        if class_id not in self.classes:
            return "Class not found"

        fitness_class = self.classes[class_id]

        return {
            "Class ID": fitness_class.class_id,
            "Class Name": fitness_class.class_name,
            "Capacity": fitness_class.capacity,
            "Confirmed Bookings": fitness_class.confirmed,
            "Waitlist": fitness_class.waitlist
        }

    # Display member class history
    def get_member_history(self, member_id):

        if member_id not in self.members:
            return []

        return [
            {
                "Booking ID": booking.booking_id,
                "Class ID": booking.class_id,
                "Status": booking.status
            }
            for booking in self.bookings.values()
            if booking.member_id == member_id
        ]
