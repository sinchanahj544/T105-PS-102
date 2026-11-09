
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Member:
    member_id: str
    name: str
    tier: str
    start_date: date
    end_date: date
    home_branch: str

    status: str = "ACTIVE"
    billing_cycle: str = "MONTHLY"

    # Freeze information
    frozen_days_this_year: int = 0
    freeze_start_date: Optional[date] = None
    freeze_end_date: Optional[date] = None
    freeze_extension_used: bool = False

    # Branch transfer information
    last_transfer_date: Optional[date] = None

    # Membership loyalty information
    continuous_membership_years: int = 0
