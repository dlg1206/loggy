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
    DEBUG = 1
    INFO = 2


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
