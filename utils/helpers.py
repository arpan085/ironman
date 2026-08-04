"""Small utility helpers used across the app."""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def safe_format_time(dt: datetime | None = None) -> str:
    dt = dt or datetime.now()
    return dt.strftime('%Y-%m-%d %H:%M:%S')
