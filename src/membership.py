from datetime import timedelta
from models import Member


# Monthly membership prices
TIER_PRICES = {
    "BASIC": 1500,
    "PLUS": 2500,
    "ELITE": 4000
}


def get_membership_price(tier, billing_cycle="MONTHLY"):
    tier = tier.upper()
    billing_cycle = billing_cycle.upper()

    if tier not in TIER_PRICES:
        raise ValueError("Invalid membership tier")

    if billing_cycle == "MONTHLY":
        return TIER_PRICES[tier]

    elif billing_cycle == "ANNUAL":
        # Annual payment = 10 months' price
        return TIER_PRICES[tier] * 10

    else:
        raise ValueError("Invalid billing cycle")


def register_member(member_id, name, tier, start_date,
                    end_date, home_branch,
                    billing_cycle="MONTHLY"):

    tier = tier.upper()
    billing_cycle = billing_cycle.upper()

    if tier not in TIER_PRICES:
        raise ValueError("Invalid membership tier")

    if end_date <= start_date:
        raise ValueError("End date must be after start date")

    if not member_id or not name or not home_branch:
        raise ValueError("Member details cannot be empty")

    member = Member(
        member_id=member_id,
        name=name,
        tier=tier,
        start_date=start_date,
        end_date=end_date,
        home_branch=home_branch,
        billing_cycle=billing_cycle
    )

    return member


def can_attend_classes(tier):
    tier = tier.upper()

    if tier == "BASIC":
        return False

    if tier in ("PLUS", "ELITE"):
        return True

    raise ValueError("Invalid membership tier")

from datetime import date
import calendar


def add_six_months(original_date):
    month = original_date.month + 6
    year = original_date.year + (month - 1) // 12
    month = (month - 1) % 12 + 1

    day = min(
        original_date.day,
        calendar.monthrange(year, month)[1]
    )

    return date(year, month, day)


def transfer_branch(member, new_branch, current_date, bookings=None):

    if member.status != "ACTIVE":
        raise ValueError("Only active members can transfer")

    if not new_branch:
        raise ValueError("New branch cannot be empty")

    if new_branch == member.home_branch:
        raise ValueError("Member is already in this branch")

    fee = 0

    if member.tier != "ELITE":
        fee = 500

        if member.last_transfer_date is not None:
            allowed_date = add_six_months(member.last_transfer_date)

            if current_date < allowed_date:
                raise ValueError("Transfer allowed only once every 6 months")

    old_branch = member.home_branch

    member.home_branch = new_branch
    member.last_transfer_date = current_date

    cancelled_bookings = []

    if bookings:
        for booking in bookings:
            if (
                booking.get("branch") == old_branch
                and booking.get("class_date")
                and booking["class_date"] > current_date + timedelta(days=7)
            ):
                booking["status"] = "CANCELLED"
                booking["quota_returned"] = True
                cancelled_bookings.append(booking)

    return fee, cancelled_bookings
