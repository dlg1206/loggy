"""
File: __init__.py

Description: Public facing methods for loggy

@author Derek Garcia
"""
from datetime import timezone
from functools import partial

from ._levels import Level
from ._logger import Logger, DEFAULT_LOG_LEVEL
from .util import Timer, format_time

_logger = Logger()

set_log_level = _logger.set_log_level
set_tz = _logger.set_tz
set_output_stream = _logger.set_output_stream
set_force_color = _logger.set_force_color

debug_info = _logger.debug_info
debug_warn = _logger.debug_warn
debug_error = _logger.debug_error

info = _logger.info
warn = _logger.warn
error = _logger.error

fatal = _logger.fatal

async_data_queue = _logger.async_data_queue
threaded_data_queue = _logger.threaded_data_queue
manual_data_queue = _logger.manual_data_queue

__all__ = ['Level', 'Timer', 'format_time', 'DEFAULT_LOG_LEVEL']
