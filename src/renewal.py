
from datetime import date
from calendar import monthrange
from membership import TIER_PRICES


def add_months(start_date, months):
    month = start_date.month + months
    year = start_date.year + (month - 1) // 12
    month = (month - 1) % 12 + 1

    day = min(
        start_date.day,
        monthrange(year, month)[1]
    )

    return date(year, month, day)


def calculate_renewal(member, current_date,
                      billing_cycle="MONTHLY"):

    billing_cycle = billing_cycle.upper()

    if billing_cycle not in ("MONTHLY", "ANNUAL"):
        raise ValueError("Invalid billing cycle")

    if member.status == "CANCELLED":
        raise ValueError("Cancelled membership cannot be renewed")

    if member.tier not in TIER_PRICES:
        raise ValueError("Invalid membership tier")

    monthly_price = TIER_PRICES[member.tier]

    base_price = monthly_price

    if billing_cycle == "ANNUAL":
        base_price = monthly_price * 10

    days_to_expiry = (member.end_date - current_date).days

    discount = 0
    joining_fee = 0

    if days_to_expiry < -30:
        joining_fee = 1000

    else:
        if 0 <= days_to_expiry <= 15:
            discount = 0.10

        if member.continuous_membership_years >= 2:
            discount = 1 - ((1 - discount) * 0.95)

    final_price = (
        round(base_price * (1 - discount))
        + joining_fee
    )

    return {
        "base_price": base_price,
        "discount_percentage": round(discount * 100, 2),
        "joining_fee": joining_fee,
        "final_price": final_price
    }


def renew_membership(member, current_date,
                     billing_cycle="MONTHLY"):

    result = calculate_renewal(
        member, current_date, billing_cycle
    )

    billing_cycle = billing_cycle.upper()

    days_to_expiry = (member.end_date - current_date).days

    # Treat a lapse exceeding 30 days as new enrolment
    if days_to_expiry < -30:
        renewal_start = current_date
        member.continuous_membership_years = 0
    else:
        renewal_start = max(member.end_date, current_date)

    months = 12 if billing_cycle == "ANNUAL" else 1

    member.start_date = renewal_start
    member.end_date = add_months(renewal_start, months)
    member.billing_cycle = billing_cycle
    member.status = "ACTIVE"

    return result
