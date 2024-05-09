import re

import pandas as pd


def posix_to_iso(posix_day):
    """
    Convert a POSIX day to an ISO format date string.
    """

    return pd.to_datetime(posix_day, unit="D", origin="unix").date().isoformat()


def convert_posix_dates_in_script(file_path):
    """
    Reads a Python script, converts all POSIX day dates (within a specific range) to ISO format,
    and saves the modified script.
    """
    # Read the script
    with open(file_path, "r") as file:
        script_content = file.read()

    # Regex pattern to find POSIX day dates within the specified range (2460 to 19800)
    # This pattern matches any number between 2460 and 19800
    posix_pattern = r"\b([2-9]\d{3}|1[0-8]\d{3}|19800)\b"

    # Function to replace POSIX day with ISO date string, formatted as a string literal
    def replace_with_iso(match):
        posix_day = int(match.group())
        iso_date_str = posix_to_iso(posix_day)
        return f'"{iso_date_str}"'  # Adding quotes to make it a string literal

    # Replace all found POSIX days with ISO date strings
    modified_script = re.sub(posix_pattern, replace_with_iso, script_content)

    # Write the modified script to a new file
    new_file_path = file_path.replace(".py", "_modified.py")
    with open(new_file_path, "w") as new_file:
        new_file.write(modified_script)

    return new_file_path
