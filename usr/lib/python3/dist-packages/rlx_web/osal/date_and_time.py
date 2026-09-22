from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Union
from zoneinfo import ZoneInfo

from rlx_osal.errors import OSALError
from rlx_osal.osal import OSAL

from ..log import logger


@dataclass
class DateTimeInfo:
    year: int = None
    month: int = None
    day: int = None
    hours: int = None
    minutes: int = None
    seconds: int = None
    tz_name: str = None
    tz_offset: str = None
    tz_code: str = None

    def to_dict(self):
        return asdict(self)


def dt_info() -> Optional[DateTimeInfo]:
    try:
        time_and_date_info = OSAL().GetDateTime()
        response = time_and_date_info.response
        dt = DateTimeInfo(
            year=response.year,
            month=response.month,
            day=response.day,
            hours=response.hours,
            minutes=response.minutes,
            seconds=response.seconds,
            tz_offset=response.tz_offset,
            tz_name=response.tz_name,
            tz_code=response.tz_code,
        )
    except (AttributeError, OSALError) as err:
        logger.error(err)
        dt = None
    return dt


def format_dt_info(info: Union[DateTimeInfo, datetime] = None):
    """
    Formats the provided date and time information into a standardized string representation.

    This function supports input as either a custom `DateTimeInfo` object or a Python `datetime` object.
    The formatted string includes the date in the format "Weekday Abbrev Month Day, Year Hour:Minute:Second"
    followed by the timezone offset.

    Parameters:
    - info (Union[DateTimeInfo, datetime], optional): The date and time information to format. This can be
      either an instance of a custom `DateTimeInfo` class or a Python `datetime` object. If not provided,
      the function returns None.

    Returns:
    - str or None: A string representing the formatted date and time, including the timezone offset,
      or None if no input is provided.

    Raises:
    - ValueError: If the `info` argument is provided but is neither an instance of `DateTimeInfo`
      nor a `datetime` object.
    """
    if info:
        if isinstance(info, DateTimeInfo):
            dt = datetime(
                info.year, info.month, info.day, info.hours, info.minutes, info.seconds, tzinfo=ZoneInfo(info.tz_name)
            )
        elif isinstance(info, datetime):
            dt = datetime(
                info.year, info.month, info.day, info.hour, info.minute, info.second, tzinfo=info.tzinfo
            )
        else:
            raise ValueError("Unsupported type for info argument")
        return f"{dt.strftime('%a %b %d, %Y %H:%M:%S %z')}"
    return None
