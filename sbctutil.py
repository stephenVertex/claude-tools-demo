from time import time
from datetime import datetime, timedelta
import pytz

def get_most_recent_sunday_as_timestamp():
    today = datetime.now()
    # Calculate how many days to subtract to get to the most recent Sunday
    days_since_sunday = (
        today.weekday() + 1
    )  # weekday() returns 0 for Monday, ..., 6 for Sunday
    most_recent_sunday = today - timedelta(days=days_since_sunday)
    # Convert to Unix timestamp in milliseconds
    most_recent_sunday_timestamp = int(most_recent_sunday.timestamp() * 1000)
    return most_recent_sunday_timestamp


# Function to convert Unix timestamp (in milliseconds) to human-readable date in Pacific Time Zone
def convert_unix_to_readable_pacific(unix_timestamp):
    # Convert milliseconds to seconds
    unix_timestamp = int(unix_timestamp) / 1000
    # Convert to datetime object in UTC
    dt_utc = datetime.utcfromtimestamp(unix_timestamp)
    # Define the Pacific Time Zone
    pacific_tz = pytz.timezone("America/Los_Angeles")
    # Convert UTC datetime to Pacific Time Zone
    dt_pacific = dt_utc.replace(tzinfo=pytz.utc).astimezone(pacific_tz)
    # Format to human-readable date
    readable_date = dt_pacific.strftime("%Y-%m-%d %H:%M:%S %Z")
    return readable_date


# Function to convert Unix timestamp (in milliseconds) to ISO 8601 compliant date with timezone offset in Pacific Time Zone
def convert_unix_to_iso8601_pacific(unix_timestamp):
    # Convert milliseconds to seconds
    unix_timestamp = int(unix_timestamp) / 1000
    # Convert to datetime object in UTC
    dt_utc = datetime.utcfromtimestamp(unix_timestamp)
    # Define the Pacific Time Zone
    pacific_tz = pytz.timezone("America/Los_Angeles")
    # Convert UTC datetime to Pacific Time Zone
    dt_pacific = dt_utc.replace(tzinfo=pytz.utc).astimezone(pacific_tz)
    # Format to ISO 8601 with timezone offset
    iso8601_date = dt_pacific.isoformat()
    return iso8601_date


def seconds_to_hh_mm_ss(seconds):
    """
    Converts seconds to a string in HH:MM:SS format.
    :param seconds: Total seconds as an integer.
    :return: String in HH:MM:SS format.
    """
    hours = seconds // 3600  # Calculate total hours
    minutes = (seconds % 3600) // 60  # Calculate remaining minutes
    seconds_remainder = seconds % 60  # Calculate remaining seconds
    return f"{hours:02}:{minutes:02}:{seconds_remainder:02}"


def seconds_to_hh_mm_ss_pretty(seconds):
    """
    Converts seconds to a string in a human-readable format.
    :param seconds: Total seconds as an integer.
    :return: String in human-readable format.
    """
    hours = seconds // 3600  # Calculate total hours
    minutes = (seconds % 3600) // 60  # Calculate remaining minutes
    seconds_remainder = seconds % 60  # Calculate remaining seconds
    result = []
    if hours > 0:
        result.append(f"{hours}h")
    if minutes > 0:
        result.append(f"{minutes}m")
    if (
        seconds_remainder > 0 or len(result) == 0
    ):  # Include seconds if there are no hours or minutes
        result.append(f"{seconds_remainder}s")
    return " ".join(result)


def milliseconds_to_hh_mm_ss(millis):
    return seconds_to_hh_mm_ss_pretty(millis / 1000)

