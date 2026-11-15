
import csv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"


class ReportWriter:

    def __init__(self):
        OUTPUT_DIR.mkdir(exist_ok=True)

        self.command_logs = []
        self.waitlist_logs = []
        self.statement_logs = []

    def log_command(
        self, line_no, command, member_id,
        status, fee_or_amount=0, message=""
    ):
        self.command_logs.append({
            "line_no": line_no,
            "command": command,
            "member_id": member_id,
            "status": status,
            "fee_or_amount": f"{float(fee_or_amount):.2f}",
            "message": message
        })

    def log_waitlist(self, line_no, class_id, bookings):
        for position, booking in enumerate(bookings, start=1):
            self.waitlist_logs.append({
                "line_no": line_no,
                "class_id": class_id,
                "position": position,
                "member_id": booking.member_id,
                "state": booking.status
            })

    def log_statement(self, data):
        self.statement_logs.append(data)

    def save_csv(self, filename, rows, columns):
        file_path = OUTPUT_DIR / filename

        with open(
            file_path, "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=columns,
                extrasaction="ignore"
            )
            writer.writeheader()
            writer.writerows(rows)

    def save_all(self):
        self.save_csv(
            "command_log.csv",
            self.command_logs,
            [
                "line_no", "command", "member_id",
                "status", "fee_or_amount", "message"
            ]
        )

        self.save_csv(
            "waitlists.csv",
            self.waitlist_logs,
            [
                "line_no", "class_id", "position",
                "member_id", "state"
            ]
        )

        self.save_csv(
            "statements.csv",
            self.statement_logs,
            [
                "line_no", "member_id", "as_of_date",
                "membership_state", "term_end",
                "frozen_days_used", "pt_sessions_remaining",
                "pt_pack_expiry", "classes_booked_this_cycle",
                "class_quota_remaining", "no_shows_30d", "dues"
            ]
        )
