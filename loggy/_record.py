"""
File: log_factory.py

Description: Factory for producing standardized log messages

@author Derek Garcia
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any

from loggy._levels import Level, Severity, WHITE_ON_RED, CLEAR, COLORS


@dataclass(frozen=True, slots=True)
class LogRecord:
    """
    Log DTO
    """
    level: Level
    severity: Severity
    msg: str
    timestamp: datetime = field(default_factory=datetime.now)
    caller: str | None = None
    exception: Exception | None = None
    details: Dict[str, Any] | None = None

    def format(self, include_details: bool = True) -> str:
        """
        Format the record for printing

        :param include_details: Include details in the log message (Default: True)
        :return: Formatted log message
        """
        color = WHITE_ON_RED if self.severity == Severity.FATAL else COLORS[(self.level, self.severity)]
        tag = f"{color}{self.severity.name:<5}{CLEAR}"
        parts = [
            self.timestamp.isoformat(),
            f"{tag}",  # fixed-width column
        ]
        # add caller if provided
        if self.caller:
            parts.append(self.caller)

        # add exception name if provided, use exception message if no message is provided
        if self.exception:
            parts.append(type(self.exception).__name__)

        # Add message
        parts.append(self.msg)

        # append details if included
        if include_details and self.details:
            parts.extend([f"{k}={v}" for k, v in self.details.items()])

        # format the final message
        return " | ".join(parts)
