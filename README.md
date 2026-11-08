# PS-102 – Gym Membership Freeze, Personal-Training Packs and Class Waitlist Engine — Sample Data Pack
Prepared by 10 SECONDS for Team T105.

## Files
| File | What it holds | Rows |
|---|---|---|
| branches.csv | Club branches | 3 |
| trainers.csv | PT trainers with daily availability | 6 |
| members.csv | Members with tier, plan and current term | 25 |
| classes.csv | Group-class schedule (12 classes) | 12 |
| commands.txt | Membership (40) + PT (60) + class (150) events plus statements, chronological | 256 |

## Column reference
Conventions: dates `YYYY-MM-DD`; timestamps `YYYY-MM-DD HH:MM:SS` (24h, IST, no timezone suffix); money in Rs as plain decimals with 2 places (no commas, no symbol); percentages as plain numbers (12.5 = 12.5%); booleans `true`/`false`; IDs uppercase with a fixed prefix. Row counts in the Files table exclude the header row (and comment lines in command files).

### branches.csv
| Column | Type | Units/format | Allowed values | Notes |
|---|---|---|---|---|
| branch_id | string | BR-NN |  | PK |
| branch_name | string |  |  |  |
| city | string |  |  |  |

### trainers.csv
| Column | Type | Units/format | Allowed values | Notes |
|---|---|---|---|---|
| trainer_id | string | TR-NN |  | PK |
| trainer_name | string |  |  |  |
| branch_id | string |  | branches.branch_id |  |
| available_from | time | HH:MM:SS |  | daily start |
| available_to | time | HH:MM:SS |  | daily end |
| weekly_off | string |  | MON..SUN | no PT sessions this weekday |

### members.csv
| Column | Type | Units/format | Allowed values | Notes |
|---|---|---|---|---|
| member_id | string | MEM-NNN |  | PK |
| member_name | string |  |  |  |
| gender | string |  | M/F |  |
| mobile | string | 10 digits |  |  |
| tier | string |  | BASIC/PLUS/ELITE |  |
| home_branch_id | string |  | branches.branch_id |  |
| plan | string |  | MONTHLY/ANNUAL |  |
| enrolment_date | date | YYYY-MM-DD |  | first-ever enrolment (continuous since) |
| term_start | date | YYYY-MM-DD |  | current paid term start; billing anniversary = this day-of-month |
| term_end | date | YYYY-MM-DD |  | current term end (exclusive of freezes already applied) |
| continuous_years | integer | years | >=0 | completed continuous years before term_start |
| frozen_days_used_this_year | integer | days | 0-60 | already consumed in this membership year |
| amount_paid_current_term | money | Rs |  | paid for the current term |

### classes.csv
| Column | Type | Units/format | Allowed values | Notes |
|---|---|---|---|---|
| class_id | string | CLS-NN |  | PK |
| branch_id | string |  | branches.branch_id |  |
| class_name | string |  |  |  |
| start_time | timestamp | YYYY-MM-DD HH:MM:SS |  |  |
| duration_min | integer | minutes |  |  |
| capacity | integer | seats |  | N |

### commands.txt
| Column | Type | Units/format | Allowed values | Notes |
|---|---|---|---|---|
| line | text | COMMAND/args | see below | first arg after the command is always the event timestamp |

## Command file format
`commands.txt` holds one command per line in the form `COMMAND_NAME|arg1|arg2|...`. Commands MUST be processed in file order (top to bottom). Lines starting with `#` are comments and blank lines are ignored. Argument order per command:

| Command | Arguments (in order) | Meaning |
|---|---|---|
| FREEZE | ts/member_id/start_date/end_date/medical_certificate | freeze request; end_date inclusive; medical true waives fee |
| UNFREEZE | ts/member_id/date | end freeze early on date |
| EXTEND_FREEZE | ts/member_id/new_end_date | FROZEN→FROZEN extension (once, within 30-day cap) |
| TRANSFER | ts/member_id/new_branch_id/effective_date | branch transfer |
| CANCEL | ts/member_id/date | cancel membership; compute refund |
| RENEW | ts/member_id/plan/date | renewal; compute price with discounts |
| STATEMENT | ts/member_id/as_of_date | print member statement |
| BUY_PT_PACK | ts/member_id/pack_size/purchase_date | pack_size 5/10/20 |
| BOOK_PT | ts/member_id/trainer_id/session_start_ts | book a 1-hour PT session |
| CANCEL_PT | ts/member_id/session_start_ts | cancel booked PT session (notice = session_start − ts) |
| COMPLETE_PT | ts/member_id/session_start_ts | session delivered → consume |
| NOSHOW_PT | ts/member_id/session_start_ts | member absent → consume |
| BOOK_CLASS | ts/member_id/class_id | book or waitlist |
| CANCEL_CLASS | ts/member_id/class_id | cancel booking/waitlist entry |
| ATTEND_CLASS | ts/member_id/class_id | attendance marked |
| NOSHOW_CLASS | ts/member_id/class_id | no-show marked |

## Planted scenarios
Every edge case from the brief is planted at a known location, followed by extra traps. Line numbers refer to `commands.txt` counting from line 1 including comment lines.
- **Freeze starting on the last day of membership with exactly 3 months remaining** — `FREEZE` for MEM-024 at line 52: term_end 2027-01-15, freeze starts 2026-10-15 (exactly 3 calendar months remaining → allowed).
- **PT pack bought the day before a 30-day freeze** — MEM-019 buys a 10-session pack on 2026-10-20 (line 118); a 30-day medical freeze 2026-10-21→2026-11-19 is filed at line 120. Pack expiry must pause for 30 days (fee waived: medical certificate).
- **Cancellation of a PT session at exactly 12 h before start** — MEM-022 session 2026-10-09 18:00:00 cancelled at 2026-10-09 06:00:00 (line 25), exactly 12 h → treat as the >12 h boundary per your BR (document choice).
- **Waitlist promotion when the class starts in exactly 2 hours** — CLS-01 (capacity 8) is overbooked; first waitlisted booking at line 86; a confirmed member cancels at exactly start−2 h (line 104). Promotion requires >2 h, so the slot stays open.
- **PLUS member's billing anniversary on the 31st in a 30-day month** — MEM-007 is PLUS/MONTHLY with term_start 2026-08-31 (anniversaries 30 Sep, 31 Oct, 30 Nov); class bookings from line 123 and a STATEMENT on 2026-11-02 (line 197).
- **Annual cancellation after 11 months and 29 days** — MEM-006 ANNUAL PLUS started 2025-11-05, `CANCEL` on 2026-11-03 (line 209) = 11 months 29 days used → 12 months rounded up.
- **Third late-cancel occurring on the 30th day after the first** — MEM-010 late-cancels (6 h notice) on 2026-10-02 (line 10), 2026-10-16 and 2026-11-01 (line 192, the 30th day after the first); the next cancellation at 48 h notice (line 218) is the one your 3-late-cancel rule decides on.
- **Member reaching 60 frozen days in the year by a single 30-day extension** — MEM-020 has frozen_days_used_this_year=30; freeze 2026-10-06→10-15 (line 13) extended to 2026-11-04 (line 38) = 30 days → 60 for the year exactly (allowed, cap reached).
- Trap — freeze on a membership with under 3 months remaining: MEM-018 line 11 (must be rejected).
- Trap — freeze start 14 days in the future accepted (line 7), 15 days rejected (line 8); 6-day freeze below the 7-day minimum rejected (line 9).
- Trap — PT booking without any pack: line 12 (reject).
- Trap — trainer TR-04 double-booked for the same slot (line 22); this line is deliberately out of timestamp order (its timestamp is later than the line that follows it) — process in file order, not timestamp order.
- Trap — duplicate BOOK_CLASS by the same member for CLS-01 (line 91); BASIC member booking a class (line 101).
- Trap — waitlist ordering: PLUS member waitlisted at line 99 before an ELITE member at line 100; ELITE must be head of the waitlist.
- Trap — second class no-show at line 72 triggers a 7-day block; the booking at line 78 falls inside the block.

## What is NOT in this pack
Expected outputs are not provided for this set. Validate your engine with your own test suite against the rules in your brief (BR-01 … BR-nn). A separate hidden input set with the same schema will be used at final evaluation; outputs are compared field-for-field, so follow the column formats above exactly in your own output.

## Output format expected at evaluation
Produce the following CSV files (header row, same conventions as above, rows in the order stated). Column names are case-sensitive.

### `command_log.csv`
One row per non-comment command line, in file order. status ∈ ACCEPTED/REJECTED; fee_or_amount = fee charged or refund/price computed (0.00 if none); message = short reason code.

Columns, in order: `line_no`, `command`, `member_id`, `status`, `fee_or_amount`, `message`

### `waitlists.csv`
After every BOOK_CLASS/CANCEL_CLASS line: the full ordered list for that class (state CONFIRMED or WAITLISTED), position starting at 1.

Columns, in order: `line_no`, `class_id`, `position`, `member_id`, `state`

### `statements.csv`
One row per STATEMENT command. pt_pack_expiry = NONE if no active pack; class_quota_remaining = UNLIMITED for ELITE, 0 for BASIC.

Columns, in order: `line_no`, `member_id`, `as_of_date`, `membership_state`, `term_end`, `frozen_days_used`, `pt_sessions_remaining`, `pt_pack_expiry`, `classes_booked_this_cycle`, `class_quota_remaining`, `no_shows_30d`, `dues`

## Notes and assumptions
- Freeze end_date is inclusive; frozen days = end − start + 1.
- A 'month' for the 3-months-remaining rule is a calendar month (same day-of-month); term_end 2027-01-15 has exactly 3 months remaining on 2026-10-15.
- PT sessions are 60 minutes; the notice period is session_start minus the CANCEL_PT timestamp.
- Renewal discounts use enrolment_date and continuous_years from members.csv.
