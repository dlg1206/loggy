"""
File: level.py

Description: Logging levels available

@author Derek Garcia
"""
from enum import IntEnum

# ansi color codes
CLEAR = '\033[0m'
DIM = '\033[2m'
BOLD = '\033[1m'

RED = '\033[31m'
YELLOW = '\033[33m'
CYAN = '\033[36m'
WHITE_ON_RED = '\033[1;97;41m'


class Level(IntEnum):
    """
    Logging level
    """
    NONE = 0
    DEBUG = 1
    INFO = 2

    @classmethod
    def from_string(cls, value: str) -> "Level":
        """
        Create level from string value

        :param value: String name of log level
        :return: :class:`Level`
        :raises ValueError: If value is not a valid level
        """
        try:
            return cls[value.upper()]
        except KeyError:
            raise ValueError(
                f"Invalid log level '{value}', must be one of {cls.names()}"
            ) from None

    @classmethod
    def names(cls) -> list[str]:
        """
        :return: List of names of available levels
        """
        return [member.name.lower() for member in cls]

    def __str__(self) -> str:
        """
        :return: Name of level
        """
        return self.name.lower()


class Severity(IntEnum):
    """
    Severity of logging level
    """
    INFO = 0
    WARN = 1
    ERROR = 2
    FATAL = 3


_COLORS = {
    (Level.DEBUG, Severity.INFO): DIM + CYAN,
    (Level.DEBUG, Severity.WARN): DIM + YELLOW,
    (Level.DEBUG, Severity.ERROR): DIM + RED,
    (Level.INFO, Severity.INFO): '',  # terminal default
    (Level.INFO, Severity.WARN): YELLOW,
    (Level.INFO, Severity.ERROR): BOLD + RED,
}


def map_color(level: Level, severity: Severity) -> str:
    """
    Map the level and severity to color

    :param level: Logging level
    :param severity: Severity level
    :return: Starting color code for the level and severity paring
    """
    if severity == Severity.FATAL:
        return WHITE_ON_RED
    return _COLORS.get((level, severity), '')
