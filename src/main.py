
from renewal import renew_membership
from membership import add_six_months
from statements import ReportWriter
from freeze import (
    freeze_membership,
    unfreeze_membership,
    extend_freeze
)
from refund import (
    calculate_membership_refund,
    calculate_pt_refund,
    cancel_membership
)
import csv
from pathlib import Path
from datetime import date, datetime, time, timedelta

from models import Member
from command_parser import read_commands
from personal_training import PersonalTrainingManager, Trainer
from class_booking import (
    ClassBookingManager,
    Member as ClassMember,
    FitnessClass
)


# Project folders
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

def process_freeze_command(command, members, pt_manager):
    """
    Process FREEZE, UNFREEZE and EXTEND_FREEZE commands.
    """

    command_name = command["command"]
    args = command["args"]
    current_date = command["timestamp"].date()

    member_id = args[0]

    if member_id not in members:
        raise ValueError(f"Member {member_id} not found")

    member = members[member_id]

    if command_name == "FREEZE":
        start_date = date.fromisoformat(args[1])
        end_date = date.fromisoformat(args[2])

        medical_certificate = args[3].strip().upper() in (
            "TRUE", "YES", "1"
        )

        days = (end_date - start_date).days + 1

        fee = freeze_membership(
            member,
            start_date,
            days,
            medical_certificate,
            current_date
        )

        pt_manager.register_freeze(
            member_id,
            start_date,
            end_date
        )

        return fee, "Freeze accepted"

    elif command_name == "UNFREEZE":
        unfreeze_date = date.fromisoformat(args[1])

        message = unfreeze_membership(
            member,
            unfreeze_date
        )

        return 0, message

    elif command_name == "EXTEND_FREEZE":
        new_end_date = date.fromisoformat(args[1])

        message = extend_freeze(
            member,
            new_end_date
        )

        return 0, message

    raise ValueError("Unsupported freeze command")



def load_members():
    members = {}

    with open(
        DATA_DIR / "members.csv",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            member = Member(
                member_id=row["member_id"],
                name=row["member_name"],
                tier=row["tier"].upper(),
                start_date=date.fromisoformat(row["term_start"]),
                end_date=date.fromisoformat(row["term_end"]),
                home_branch=row["home_branch_id"],
                billing_cycle=row["plan"].upper(),
                continuous_membership_years=int(row["continuous_years"]),
                frozen_days_this_year=int(row["frozen_days_used_this_year"]),
                enrolment_date=date.fromisoformat(row["enrolment_date"]),
                amount_paid_current_term=float(
                    row["amount_paid_current_term"]
                )
            )

            members[member.member_id] = member

    return members



def load_branches():
    branches = {}

    with open(DATA_DIR / "branches.csv", newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            branches[row["branch_id"]] = row["branch_name"]

    return branches




def load_trainers(pt_manager, commands):
    with open(DATA_DIR / "trainers.csv", newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):

            trainer = Trainer(row["trainer_id"], [])

            weekly_off = row["weekly_off"].upper()
            available_from = time.fromisoformat(row["available_from"])
            available_to = time.fromisoformat(row["available_to"])

            # Create availability intervals for dates used by PT commands
            for command in commands:
                if command["command"] != "BOOK_PT":
                    continue

                session_time = datetime.strptime(
                    command["args"][2],
                    "%Y-%m-%d %H:%M:%S"
                )

                if session_time.strftime("%a").upper() == weekly_off:
                    continue

                start = datetime.combine(
                    session_time.date(), available_from
                )
                end = datetime.combine(
                    session_time.date(), available_to
                )

                if (start, end) not in trainer.available_slots:
                    trainer.available_slots.append((start, end))

            pt_manager.add_trainer(trainer)




def load_classes(class_manager):
    with open(DATA_DIR / "classes.csv", newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            fitness_class = FitnessClass(
                row["class_id"],
                row["class_name"],
                row["branch_id"],
                datetime.strptime(
                    row["start_time"], "%Y-%m-%d %H:%M:%S"
                ),
                int(row["capacity"])
            )

            class_manager.add_class(fitness_class)


def initialize_system(commands):
    members = load_members()

    pt_manager = PersonalTrainingManager()
    class_manager = ClassBookingManager()

    for member in members.values():
        class_member = ClassMember(
            member.member_id,
            member.tier,
            member.start_date,
            member.home_branch,
            member.status
        )
        class_manager.add_member(class_member)

    load_trainers(pt_manager, commands)
    load_classes(class_manager)

    return members, pt_manager, class_manager
def process_buy_pt_pack(command, pt_manager):
    args = command["args"]

    member_id = args[0]
    sessions = int(args[1])
    purchase_date = date.fromisoformat(args[2])

    pack_id = f"PACK-{command['line_no']}"

    message = pt_manager.purchase_pack(
        member_id,
        pack_id,
        sessions,
        purchase_date
    )

    pack = pt_manager.packs[pack_id]

    return pack.price, message
def process_book_pt(command, pt_manager):
    args = command["args"]

    member_id = args[0]
    trainer_id = args[1]

    session_start = datetime.strptime(
        args[2],
        "%Y-%m-%d %H:%M:%S"
    )

    available_packs = [
        pack for pack in pt_manager.packs.values()
        if pack.member_id == member_id
        and pt_manager.check_pack_validity(
            pack.pack_id, session_start.date()
        )
        and pt_manager.get_pack_balance(
            pack.pack_id, session_start.date()
        ) > 0
    ]

    if not available_packs:
        raise ValueError("No valid PT pack or sessions available")

    pack = min(
        available_packs,
        key=lambda item: pt_manager.get_expiry_date(item)
    )

    booking_id = f"PT-{command['line_no']}"

    message = pt_manager.book_session(
        booking_id,
        member_id,
        pack.pack_id,
        trainer_id,
        session_start
    )

    return 0, message
def find_pt_booking(pt_manager, member_id, session_start):
    for booking in pt_manager.bookings.values():
        if (
            booking.member_id == member_id
            and booking.start_time == session_start
            and booking.status == "BOOKED"
        ):
            return booking

    raise ValueError("PT booking not found")


def process_cancel_pt(command, pt_manager):
    args = command["args"]

    member_id = args[0]
    session_start = datetime.strptime(
        args[1], "%Y-%m-%d %H:%M:%S"
    )

    booking = find_pt_booking(
        pt_manager, member_id, session_start
    )

    message = pt_manager.cancel_session(
        booking.booking_id,
        command["timestamp"]
    )

    return 0, message
def process_complete_pt(command, pt_manager):
    args = command["args"]

    member_id = args[0]
    session_start = datetime.strptime(
        args[1], "%Y-%m-%d %H:%M:%S"
    )

    booking = find_pt_booking(
        pt_manager, member_id, session_start
    )

    message = pt_manager.complete_session(
        booking.booking_id
    )

    return 0, message
def process_noshow_pt(command, pt_manager):
    args = command["args"]

    member_id = args[0]
    session_start = datetime.strptime(
        args[1], "%Y-%m-%d %H:%M:%S"
    )

    booking = find_pt_booking(
        pt_manager, member_id, session_start
    )

    message = pt_manager.mark_no_show(
        booking.booking_id
    )

    return 0, message
def process_book_class(command, class_manager, report):
    args = command["args"]

    member_id = args[0]
    class_id = args[1]

    booking_id = f"CLASS-{command['line_no']}"

    message = class_manager.book_class(
        booking_id,
        member_id,
        class_id,
        command["timestamp"]
    )

    fitness_class = class_manager.classes[class_id]

    bookings = [
        class_manager.bookings[b_id]
        for b_id in (
            fitness_class.confirmed + fitness_class.waitlist
        )
    ]

    report.log_waitlist(
        command["line_no"],
        class_id,
        bookings
    )

    if message == "Class booked successfully":
        return 0, message

    if message == "Class full. Member added to waitlist":
        return 0, message

    raise ValueError(message)

def process_cancel_class(command, class_manager, report):
    args = command["args"]
    member_id = args[0]
    class_id = args[1]

    booking = None

    for item in class_manager.bookings.values():
        if (
            item.member_id == member_id
            and item.class_id == class_id
            and item.status in ("CONFIRMED", "WAITLISTED")
        ):
            booking = item
            break

    if booking is None:
        raise ValueError("Active class booking not found")

    message = class_manager.cancel_class(
        booking.booking_id,
        command["timestamp"]
    )

    if message.startswith("Booking not found") or message.startswith("Booking already processed"):
        raise ValueError(message)

    fitness_class = class_manager.classes[class_id]

    bookings = [
        class_manager.bookings[b_id]
        for b_id in fitness_class.confirmed + fitness_class.waitlist
    ]

    report.log_waitlist(command["line_no"], class_id, bookings)

    return 0, message


def process_noshow_class(command, class_manager):
    args = command["args"]
    member_id = args[0]
    class_id = args[1]

    booking = None

    for item in class_manager.bookings.values():
        if (
            item.member_id == member_id
            and item.class_id == class_id
            and item.status == "CONFIRMED"
        ):
            booking = item
            break

    if booking is None:
        raise ValueError("Confirmed class booking not found")

    message = class_manager.mark_no_show(
        booking.booking_id,
        command["timestamp"]
    )

    if message.startswith("Booking not found") or message.startswith("Invalid") or message.startswith("Class has not started"):
        raise ValueError(message)

    return 0, message


def process_attend_class(command, class_manager):
    args = command["args"]
    member_id = args[0]
    class_id = args[1]

    booking = None

    for item in class_manager.bookings.values():
        if (
            item.member_id == member_id
            and item.class_id == class_id
            and item.status == "CONFIRMED"
        ):
            booking = item
            break

    if booking is None:
        raise ValueError("Confirmed class booking not found")

    message = class_manager.mark_attended(
        booking.booking_id,
        command["timestamp"]
    )

    if message != "Class attendance recorded successfully":
        raise ValueError(message)

    return 0, message

def execute_freeze_commands(commands, members, pt_manager, class_manager, report):
    freeze_commands = {
        "FREEZE",
        "UNFREEZE",
        "EXTEND_FREEZE"
    }

    for command in commands:
        name = command["command"]

        if name not in freeze_commands and name not in ("TRANSFER", "RENEW", "CANCEL", "BUY_PT_PACK", "BOOK_PT", "CANCEL_PT", "COMPLETE_PT", "NOSHOW_PT", "BOOK_CLASS", "CANCEL_CLASS",
"ATTEND_CLASS","NOSHOW_CLASS", "STATEMENT"):
           continue

        args = command["args"]
        member_id = args[0]

        try:
            if name == "BUY_PT_PACK":
                 fee, message = process_buy_pt_pack(
                 command, pt_manager
    )
            elif name == "BOOK_PT":
                fee, message = process_book_pt(
               command, pt_manager
    )
            elif name == "CANCEL_PT":
                 fee, message = process_cancel_pt(
        command, pt_manager
    )
            elif name == "COMPLETE_PT":
               fee, message = process_complete_pt(
        command, pt_manager
    )
            elif name == "NOSHOW_PT":
               fee, message = process_noshow_pt(
        command, pt_manager
    )
            elif name == "BOOK_CLASS":
               fee, message = process_book_class(
        command, class_manager, report
    )
            elif name == "CANCEL_CLASS":
                fee, message = process_cancel_class(
                    command, class_manager, report
                )

            elif name == "NOSHOW_CLASS":
                fee, message = process_noshow_class(
                    command, class_manager
                )
            elif name == "ATTEND_CLASS":
                fee, message = process_attend_class(
                    command, class_manager
                )
            elif name == "CANCEL":
                fee, message = process_cancel(
        command, members, pt_manager
    )
            
            elif name == "TRANSFER":
                fee, cancelled = process_transfer(
                    command,
                    members,
                    class_manager
             )
                message = f"Transfer accepted. Cancelled bookings: {cancelled}"

            elif name == "RENEW":
                fee, message = process_renewal(
                    command,
                    members
    )
            elif name == "STATEMENT":
                fee, message = process_statement(
                    command,
                    members,
                    pt_manager,
                    class_manager,
                    report
                )
            else:
                fee, message = process_freeze_command(
                command,
        members,
         pt_manager
    )
                 # Synchronize membership status with class booking
            if member_id in class_manager.members:
                class_manager.members[member_id].status = (
                    members[member_id].status
                )
                report.log_command(
                command["line_no"],
                name,
                member_id,
                "ACCEPTED",
                fee,
                message
            )

        except (ValueError, KeyError, IndexError) as error:
            report.log_command(
                command["line_no"],
                name,
                member_id,
                "REJECTED",
                0,
                str(error)
            )
def process_statement(command, members, pt_manager, class_manager, report):

    args = command["args"]
    member_id = args[0]
    as_of_date = date.fromisoformat(args[1])

    if member_id not in members:
        raise ValueError("Member not found")

    member = members[member_id]

    # 1. Calculate PT session balance and active pack expiry
    pt_sessions_remaining = 0
    active_expiries = []

    for pack in pt_manager.packs.values():

        if pack.member_id == member_id:

            balance = pt_manager.get_pack_balance(
                pack.pack_id, as_of_date
            )

            pt_sessions_remaining += balance

            if balance > 0:
                active_expiries.append(
                    pt_manager.get_expiry_date(pack)
                )

    pt_pack_expiry = (
        min(active_expiries).isoformat()
        if active_expiries else "NONE"
    )

    # 2. Calculate classes booked in the current billing cycle
    classes_used = class_manager.get_classes_used(
        member_id, as_of_date
    )

    if member.tier == "ELITE":
        class_quota_remaining = "UNLIMITED"
    elif member.tier == "BASIC":
        class_quota_remaining = 0
    else:
        class_quota_remaining = max(0, 8 - classes_used)

    # 3. Count class no-shows in the previous 30 days
    as_of_datetime = datetime.combine(as_of_date, time.max)
    cutoff = as_of_datetime - timedelta(days=30)

    no_show_history = class_manager.no_show_history.get(
        member_id, []
    )

    no_shows_30d = sum(
        1 for event_time in no_show_history
        if cutoff <= event_time <= as_of_datetime
    )

    # 4. Dues are zero because no outstanding-balance
    # calculation or unpaid ledger is defined in the brief.
    dues = "0.00"

    # 5. Save the statement row
    report.log_statement({
        "line_no": command["line_no"],
        "member_id": member_id,
        "as_of_date": as_of_date.isoformat(),
        "membership_state": member.status,
        "term_end": member.end_date.isoformat(),
        "frozen_days_used": member.frozen_days_this_year,
        "pt_sessions_remaining": pt_sessions_remaining,
        "pt_pack_expiry": pt_pack_expiry,
        "classes_booked_this_cycle": classes_used,
        "class_quota_remaining": class_quota_remaining,
        "no_shows_30d": no_shows_30d,
        "dues": dues
    })

    return 0, "Statement generated successfully"
def process_transfer(command, members, class_manager):
    args = command["args"]

    member_id = args[0]
    new_branch_id = args[1]
    effective_date = date.fromisoformat(args[2])

    if member_id not in members:
        raise ValueError("Member not found")

    member = members[member_id]

    if member.status != "ACTIVE":
        raise ValueError("Only active members can transfer")

    if new_branch_id == member.home_branch:
        raise ValueError("Member is already in this branch")

    fee = 0

    if member.tier != "ELITE":
        fee = 500

        if member.last_transfer_date is not None:
            allowed_date = add_six_months(
                member.last_transfer_date
            )

            if effective_date < allowed_date:
                raise ValueError(
                    "Transfer allowed only once every 6 months"
                )

    old_branch = member.home_branch

    # Update the common member record
    member.home_branch = new_branch_id
    member.last_transfer_date = effective_date

    # Synchronize the class-booking member record
    if member_id in class_manager.members:
        class_member = class_manager.members[member_id]
        class_member.home_branch = new_branch_id

    cancelled_count = 0

    # Cancel old-branch bookings more than 7 days away
    for booking in class_manager.bookings.values():

        if booking.member_id != member_id:
            continue

        if booking.status not in ("CONFIRMED", "WAITLISTED"):
            continue

        fitness_class = class_manager.classes[booking.class_id]

        if fitness_class.branch != old_branch:
            continue

        if fitness_class.start_time.date() <= (
            effective_date + timedelta(days=7)
        ):
            continue

        if booking.status == "CONFIRMED":
            if booking.booking_id in fitness_class.confirmed:
                fitness_class.confirmed.remove(
                    booking.booking_id
                )

            usage = class_manager.quota_usage[member_id]

            if booking.booking_time.date() in usage:
                usage.remove(booking.booking_time.date())

        elif booking.status == "WAITLISTED":
            if booking.booking_id in fitness_class.waitlist:
                fitness_class.waitlist.remove(
                    booking.booking_id
                )

        booking.status = "CANCELLED"
        cancelled_count += 1

    return fee, cancelled_count

def process_renewal(command, members):
    args = command["args"]

    member_id = args[0]
    billing_cycle = args[1].upper()
    current_date = date.fromisoformat(args[2])

    if member_id not in members:
        raise ValueError("Member not found")

    member = members[member_id]

    result = renew_membership(
        member,
        current_date,
        billing_cycle
    )

    price = result.get("final_price", result.get("price", 0))

    return price, "Membership renewed successfully"

def process_cancel(command, members, pt_manager):
    args = command["args"]

    member_id = args[0]
    cancellation_date = date.fromisoformat(args[1])

    if member_id not in members:
        raise ValueError("Member not found")

    member = members[member_id]

    refund = calculate_membership_refund(
        tier=member.tier,
        billing_cycle=member.billing_cycle,
        paid_amount=member.amount_paid_current_term,
        first_enrolment_date=member.enrolment_date,
        cancellation_date=cancellation_date
    )

    pt_refund = 0

    for pack in pt_manager.packs.values():
        if pack.member_id == member_id:
            effective_expiry = pt_manager.get_expiry_date(pack)

            unused_sessions = pack.remaining_sessions

            pack_refund = calculate_pt_refund(
                pack_price=pack.price,
                total_sessions=pack.total_sessions,
                unused_sessions=unused_sessions,
                pack_expiry_date=effective_expiry,
                cancellation_date=cancellation_date
            )

            pt_refund += pack_refund

    cancel_membership(member)

    total_refund = refund + pt_refund

    return total_refund, (
        f"Membership refund: {refund}; PT refund: {pt_refund}"
    )

def main():
    commands_file = DATA_DIR / "commands.txt"
    commands = read_commands(commands_file)

    members, pt_manager, class_manager = initialize_system(commands)

    report = ReportWriter()

    print("GYM MANAGEMENT SYSTEM")
    print("---------------------")
    print(f"Members loaded: {len(members)}")
    print(f"Commands loaded: {len(commands)}")
    print(f"Trainers loaded: {len(pt_manager.trainers)}")
    print(f"Classes loaded: {len(class_manager.classes)}")

    execute_freeze_commands(
    commands,
    members,
    pt_manager,
    class_manager,
    report
)

    report.save_all()

    print("\nFreeze commands processed.")
    print("Reports saved in output folder.")

    print("\nCommand types found:")

    command_types = {}

    for command in commands:
        name = command["command"]
        command_types[name] = command_types.get(name, 0) + 1

    for name, count in sorted(command_types.items()):
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()








