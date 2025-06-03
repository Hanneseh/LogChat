from datetime import datetime

from src.logger import logger


def safe_cast(value, target_type=str | int):
    """Safely cast a value to a string, returning None if the value is -1."""
    if value in ("None", "null", None, -1, "-1", ""):
        return None
    else:
        try:
            return target_type(value)
        except Exception:
            logger.error(f"Error in safe_cast casting {value} to {target_type}")
            return None


def safe_cast_to_datetime(value: str):
    """Safely cast a value to a datetime object, returning a default value if the cast fails."""
    if value in ("None", "null", None, -1, "-1", ""):
        return None
    else:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except Exception:
            logger.error(f"Error in safe_cast_to_datetime casting {value} to datetime")
            return None
