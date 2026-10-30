"""
File: level.py

Description: Logging levels available

@author Derek Garcia
"""
from enum import IntEnum

# ansi color codes
CLEAR = '\033[00m'
RED = '\033[91m'
YELLOW = '\033[93m'
WHITE = '\033[97m'
WHITE_ON_CYAN = '\033[46;97m'
YELLOW_ON_CYAN = '\033[46;93m'
RED_ON_CYAN = '\033[46;91m'
WHITE_ON_RED = '\033[41;97m'


class Level(IntEnum):
    """
    Logging level
    """
    NONE = 0
    DEBUG = 1
    INFO = 2

    @classmethod
    def from_string(cls, value: str) -> Level:
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


COLORS = {
    (Level.DEBUG, Severity.INFO): WHITE_ON_CYAN,
    (Level.DEBUG, Severity.WARN): YELLOW_ON_CYAN,
    (Level.DEBUG, Severity.ERROR): RED_ON_CYAN,
    (Level.INFO, Severity.INFO): WHITE,
    (Level.INFO, Severity.WARN): YELLOW,
    (Level.INFO, Severity.ERROR): RED,
}
