import logging
import re
from datetime import timedelta

def setup_logging(log_path="/var/log/xui-tg-bot.log"):
    """Configure logging for the bot."""
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

def parse_duration(duration_str: str) -> timedelta:
    """
    Convert a string like '30m', '2h', '1d' into a timedelta object.
    Default = 24h if parsing fails.
    """
    pattern = r"(\d+)([mhd])"
    match = re.match(pattern, duration_str.strip().lower())
    if not match:
        return timedelta(hours=24)

    value, unit = match.groups()
    value = int(value)

    if unit == "m":
        return timedelta(minutes=value)
    elif unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)
    else:
        return timedelta(hours=24)
