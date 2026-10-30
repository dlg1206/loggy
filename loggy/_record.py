"""
File: log_factory.py

Description: Factory for producing standardized log messages

@author Derek Garcia
"""
from dataclasses import dataclass, field
from datetime import datetime, tzinfo
from typing import Dict, Any

from loggy._levels import Level, Severity, CLEAR, map_color

_SEVERITY_WIDTH = max(len(s.name) for s in Severity)


def now(tz: tzinfo | None = None) -> datetime:
    """
    Get the current time

    :param tz: Timezone for the timestamp, device-local timezone if tz is None
    :return: Current timestamp
    """
    return datetime.now(tz).astimezone() if tz is None else datetime.now(tz)


@dataclass(frozen=True, slots=True)
class LogRecord:
    """
    Log DTO
    """
    level: Level
    severity: Severity
    msg: str
    timestamp: datetime = field(default_factory=now)
    caller: str | None = None
    exception: Exception | None = None
    details: Dict[str, Any] | None = None

    def format(self, include_details: bool = True, use_color: bool = True) -> str:
        """
        Format the record for printing

        :param include_details: Include details in the log message (Default: True)
        :param use_color: Use color when formating messages (Default: True)
        :return: Formatted log message
        """
        color = map_color(self.level, self.severity) if use_color else ''
        clear = CLEAR if use_color else ''
        parts = [
            self.timestamp.isoformat(timespec="milliseconds"),
            f"{color}{self.severity.name:<{_SEVERITY_WIDTH}}{clear}",
        ]

        # add caller if provided
        if self.caller:
            parts.append(self.caller)

        # add exception name if provided, use exception message if no message is provided
        msg = self.msg
        if self.exception:
            parts.append(type(self.exception).__name__)
            if not msg:
                msg = str(self.exception)

        # Add message
        if msg:
            parts.append(msg)

        # append details if included
        if include_details and self.details:
            parts.extend([f"{k}={_fmt_value(v)}" for k, v in self.details.items()])

        # format the final message
        return " | ".join(parts)


def _fmt_value(v: Any) -> str:
    """
    Format a string value

    :param v: Value to format
    :return: string value
    """
    s = str(v)
    needs_quote = not s or any(c.isspace() for c in s) or "|" in s
    return repr(s) if needs_quote else s
