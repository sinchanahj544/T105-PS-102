
from datetime import datetime


def parse_command(line, line_no=0):
    """
    Parse one command line from commands.txt.

    Format:
    COMMAND_NAME|timestamp|arg1|arg2|...
    """

    line = line.strip()

    if not line or line.startswith("#"):
        return None

    parts = [part.strip() for part in line.split("|")]

    command_name = parts[0].upper()

    if len(parts) < 2:
        raise ValueError(
            f"Line {line_no}: Missing command timestamp"
        )

    timestamp = datetime.strptime(
        parts[1], "%Y-%m-%d %H:%M:%S"
    )

    return {
        "line_no": line_no,
        "command": command_name,
        "timestamp": timestamp,
        "args": parts[2:]
    }


def read_commands(file_path):
    """Read commands in their original file order."""

    commands = []

    with open(file_path, "r", encoding="utf-8") as file:
        for line_no, line in enumerate(file, start=1):
            parsed = parse_command(line, line_no)

            if parsed is not None:
                commands.append(parsed)

    return commands
