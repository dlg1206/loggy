"""
File: __init__.py

Description: Public facing methods for loggy

@author Derek Garcia
"""
from _levels import Level
from _logger import Logger

_logger = Logger()

set_log_level = _logger.set_log_level
debug_info = _logger.debug_info
debug_warn = _logger.debug_warn
debug_error = _logger.debug_error

info = _logger.info
warn = _logger.warn
error = _logger.error

fatal = _logger.fatal

__all__ = ['Level']
