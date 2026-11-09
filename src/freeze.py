
from datetime import date, timedelta
from calendar import monthrange


def add_months(original_date, months):
    """Add calendar months while handling month-end dates."""
    month = original_date.month - 1 + months
    year = original_date.year + month // 12
    month = month % 12 + 1

    day = min(
        original_date.day,
        monthrange(year, month)[1]
    )

    return date(year, month, day)


def freeze_membership(member, freeze_start, days,
                      medical_certificate=False):

    if member.status != "ACTIVE":
        raise ValueError("Only active members can freeze")

    if member.freeze_start_date is not None:
        raise ValueError("A freeze is already scheduled or active")

    today = date.today()

    if freeze_start < today:
        raise ValueError("Freeze cannot start in the past")

    if freeze_start > today + timedelta(days=14):
        raise ValueError("Freeze cannot start more than 14 days ahead")

    if days < 7 or days > 30:
        raise ValueError("Freeze must be between 7 and 30 days")

    # Check for 3 calendar months remaining
    minimum_end_date = add_months(freeze_start, 3)

    if member.end_date < minimum_end_date:
        raise ValueError("At least 3 months must remain")

    if member.frozen_days_this_year + days > 60:
        raise ValueError("60-day yearly freeze limit exceeded")

    fee = 0

    if member.tier != "ELITE" and not medical_certificate:
        fee = 300

    member.freeze_start_date = freeze_start
    member.freeze_end_date = freeze_start + timedelta(days=days)

    # Reserve the freeze days and membership extension
    member.frozen_days_this_year += days
    member.end_date += timedelta(days=days)

    member.freeze_extension_used = False

    # Activate immediately only if the freeze starts today
    if freeze_start == today:
        member.status = "FROZEN"

    return fee


def activate_scheduled_freeze(member, current_date):

    if member.status != "ACTIVE":
        raise ValueError("Member is not active")

    if member.freeze_start_date is None:
        raise ValueError("No scheduled freeze found")

    if current_date < member.freeze_start_date:
        raise ValueError("Scheduled freeze has not started")

    member.status = "FROZEN"

    return "Scheduled freeze activated"


def unfreeze_membership(member, current_date):

    # Activate a scheduled freeze if its start date has arrived
    if (
        member.status == "ACTIVE"
        and member.freeze_start_date is not None
        and current_date >= member.freeze_start_date
    ):
        activate_scheduled_freeze(member, current_date)

    if member.status != "FROZEN":
        raise ValueError("Member is not currently frozen")

    if current_date < member.freeze_end_date:
        raise ValueError("Freeze period is still active")

    member.status = "ACTIVE"
    member.freeze_start_date = None
    member.freeze_end_date = None

    return "Membership successfully unfrozen"


def extend_freeze(member, additional_days):

    if member.status != "FROZEN":
        raise ValueError("Member is not frozen")

    if member.freeze_extension_used:
        raise ValueError("Freeze extension already used")

    current_days = (
        member.freeze_end_date - member.freeze_start_date
    ).days

    if additional_days <= 0:
        raise ValueError("Extension days must be positive")

    if current_days + additional_days > 30:
        raise ValueError("Total freeze cannot exceed 30 days")

    if member.frozen_days_this_year + additional_days > 60:
        raise ValueError("60-day yearly freeze limit exceeded")

    member.freeze_end_date += timedelta(days=additional_days)
    member.end_date += timedelta(days=additional_days)
    member.frozen_days_this_year += additional_days
    member.freeze_extension_used = True

    return "Freeze successfully extended"

