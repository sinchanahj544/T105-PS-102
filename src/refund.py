
from datetime import date
from calendar import monthrange


def add_months(original_date, months):
    month = original_date.month - 1 + months
    year = original_date.year + month // 12
    month = month % 12 + 1

    day = min(
        original_date.day,
        monthrange(year, month)[1]
    )

    return date(year, month, day)


def calculate_months_used(start_date, cancellation_date):

    if cancellation_date <= start_date:
        return 0

    # Round up using calendar-month anniversaries
    months = 0

    while add_months(start_date, months) < cancellation_date:
        months += 1

    return months


def calculate_membership_refund(
    tier,
    billing_cycle,
    paid_amount,
    first_enrolment_date,
    cancellation_date
):
    tier_prices = {
        "BASIC": 1500,
        "PLUS": 2500,
        "ELITE": 4000
    }

    tier = tier.upper()
    billing_cycle = billing_cycle.upper()

    if tier not in tier_prices:
        raise ValueError("Invalid membership tier")

    if billing_cycle not in ["MONTHLY", "ANNUAL"]:
        raise ValueError("Invalid billing cycle")

    if paid_amount < 0:
        raise ValueError("Paid amount cannot be negative")

    if cancellation_date < first_enrolment_date:
        raise ValueError("Invalid cancellation date")

    days_used = (
        cancellation_date - first_enrolment_date
    ).days

    # Cooling-off period: 7 days
    if days_used <= 7:
        return max(0, paid_amount - 500)

    # Monthly membership: no refund after 7 days
    if billing_cycle == "MONTHLY":
        return 0

    # Annual membership refund
    months_used = calculate_months_used(
        first_enrolment_date,
        cancellation_date
    )

    refund = (
        paid_amount
        - (months_used * tier_prices[tier])
        - (0.10 * paid_amount)
    )

    return max(0, round(refund))


def calculate_pt_refund(
    pack_price,
    total_sessions,
    unused_sessions,
    pack_expiry_date,
    cancellation_date
):
    if pack_price < 0:
        raise ValueError("Pack price cannot be negative")

    if total_sessions <= 0:
        raise ValueError("Invalid total sessions")

    if unused_sessions < 0 or unused_sessions > total_sessions:
        raise ValueError("Invalid unused sessions")

    if cancellation_date > pack_expiry_date:
        return 0

    price_per_session = pack_price / total_sessions

    return round(
        unused_sessions * price_per_session * 0.50
    )


def cancel_membership(member):

    if member.status == "CANCELLED":
        raise ValueError("Membership is already cancelled")

    member.status = "CANCELLED"

    return "Membership successfully cancelled"
