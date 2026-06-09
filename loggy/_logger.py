"""
File: logger.py
Description: Logger for actions

@author Derek Garcia
"""

import asyncio
import inspect
import sys
from concurrent import futures
from concurrent.futures import Future
from typing import Any, Iterable, Dict, NoReturn, Coroutine, overload

from tqdm import tqdm

from loggy._levels import Level, Severity
from loggy._record import LogRecord

DEFAULT_LOG_LEVEL = Level.INFO
CALLER_FRAME_DISTANCE = 3


class _DataQueue:
    def __init__(self, logger: "Logger", iterable: Iterable[Any], is_root: bool):
        """
        Data wrapper for iterables

        :param logger: Logger singleton
        :param iterable: Iterable to wrap
        :param is_root: If this is the root iterable
        """
        self._logger = logger
        self._iterable = iterable
        self._is_root = is_root

    def __iter__(self):
        try:
            yield from self._iterable
        finally:
            if self._is_root:
                self._logger._suppress_depth -= 1


class Logger:
    """
    Logger
    """

    def __init__(self, log_level: Level | str | None = DEFAULT_LOG_LEVEL):
        """
        Create new logger

        :param log_level: Logging level (default: INFO)
        :raises ValueError: If log_level is in valid
        """
        if isinstance(log_level, str):
            try:
                log_level = Level[log_level.upper()]
            except KeyError:
                raise ValueError(f"Invalid log level '{log_level}', must be one of {[l.name for l in Level]}")

        self._log_level = log_level
        self._suppress_depth = 0

    def _emit(self,
              level: Level,
              severity: Severity,
              msg: str,
              emit_details: bool,
              exception: Exception | None = None,
              details: Dict[str, Any] | None = None) -> LogRecord:
        """
        Emit log message for appropriate level

        :param level: Logging level
        :param severity: Severity of log message
        :param msg: Message to print
        :param emit_details: Include details when printing info
        :param exception: Optional exception type to print (Default: None)
        :param details: Optional details for the log message (Default: None)
        :return: Log record
        """
        log_record = LogRecord(level, severity, msg, caller=_resolve_caller(), exception=exception, details=details)

        # always print fatal
        if level == Severity.FATAL:
            print(log_record.format(emit_details))
            return log_record

        # else print if logger not silenced
        if self._log_level is not None and level >= self._log_level:
            print(log_record.format(emit_details))

        return log_record

    def set_log_level(self, level: Level | None) -> None:
        """
         Set log level, NONE to silence

         :param level: Logging level
         """
        self._log_level = level

    #
    # Pretty data queues
    #
    def async_data_queue(self,
                         data: Iterable[Coroutine],
                         description: str,
                         unit: str,
                         suppress_logs: bool = False) -> _DataQueue:
        """
        Create a dynamic loading bar if in INFO mode for async tasks

        :param data: Iterable of to wrap with tqdm
        :param description: Description of the process
        :param unit: Unit of the process
        :param suppress_logs: Temporarily suppress other INFO level messages (Default: False)
        :return: tqdm loading bar or awaited data
        """
        tasks = list(data)
        completed = asyncio.as_completed(tasks)

        # track if suppressing logs -- only if logger is in info mode
        is_root = suppress_logs and self._log_level == Level.INFO and self._suppress_depth == 0
        if is_root:
            self._suppress_depth += 1

        # wrap in tqdm if correct mode
        iterable = tqdm(completed, desc=_make_tqdm_desc(description), unit=unit, file=sys.stdout, total=len(tasks)) \
            if self._log_level == Level.INFO \
            else completed

        return _DataQueue(self, iterable, is_root)

    def threaded_data_queue(self,
                            data: Iterable[Future],
                            description: str,
                            unit: str,
                            suppress_logs: bool = False) -> Iterable[Any]:
        """
        Create a dynamic loading bar if in INFO mode for threaded tasks

        :param data: Iterable to wrap with tqdm
        :param description: Description of the process
        :param unit: Unit of the process
        :param suppress_logs: Temporarily suppress other INFO level messages (Default: False)
        :return: tqdm loading bar or completed data
        """
        futures_list = list(data)
        completed = futures.as_completed(futures_list)

        # track if suppressing logs -- only if logger is in info mode
        is_root = suppress_logs and self._log_level == Level.INFO and self._suppress_depth == 0
        if is_root:
            self._suppress_depth += 1

        # wrap in tqdm if correct mode
        iterable = tqdm(completed, desc=_make_tqdm_desc(description), unit=unit, file=sys.stdout,
                        total=len(futures_list)) \
            if self._log_level == Level.INFO \
            else completed

        return _DataQueue(self, iterable, is_root)

    def manual_data_queue(self,
                          total: int,
                          description: str,
                          unit: str,
                          suppress_logs: bool = False) -> _DataQueue | None:
        """
        Create a dynamic loading bar if in INFO mode that can be manually updated with .update(N)

        :param total: Total length to wrap with tqdm
        :param description: Description of the process
        :param unit: Unit of the process
        :param suppress_logs: Temporarily suppress other INFO level messages (Default: False)
        :return: tqdm loading bar or None if not in INFO mode
        """

        # track if suppressing logs -- only if logger is in info mode
        is_root = suppress_logs and self._log_level == Level.INFO and self._suppress_depth == 0
        if is_root:
            self._suppress_depth += 1

        # wrap in tqdm if correct mode
        iterable = tqdm(desc=_make_tqdm_desc(description), unit=unit, file=sys.stdout, total=total) \
            if self._log_level == Level.INFO \
            else None

        return _DataQueue(self, iterable, is_root) if iterable else None

    #
    # Wrapper debug log methods
    #

    def debug_info(self, msg: str, *, emit_details: bool = True, **details: Any) -> LogRecord:
        """
        Print debug info message

        :param msg: Message to print
        :param emit_details: Include details when printing debug info (Default: True)
        :param details: Optional details for the log message
        :return: LogRecord
        """
        return self._emit(Level.DEBUG, Severity.INFO, msg, emit_details, None, details)

    @overload
    def debug_warn(self, msg: str, *, exception: Exception | None = None, emit_details: bool = True,
                   **details: Any) -> LogRecord:
        ...

    @overload
    def debug_warn(self, exception: Exception, *, emit_details: bool = True, **details: Any) -> LogRecord:
        ...

    def debug_warn(self,
                   msg: str,
                   *,
                   exception: Exception | None = None,
                   emit_details: bool = True,
                   **details: Any) -> LogRecord:
        """
        Print debug warn message

        :param msg: Message to print
        :param exception: Optional exception type to print (Default: None)
        :param emit_details: Include details when printing debug info (Default: True)
        :param details: Optional details for the log message
        :return: LogRecord
        """
        return self._emit(Level.DEBUG, Severity.WARN, msg, emit_details, exception, details)

    @overload
    def debug_error(self, msg: str, *, exception: Exception | None = None, emit_details: bool = True,
                    **details: Any) -> LogRecord:
        ...

    @overload
    def debug_error(self, exception: Exception, *, emit_details: bool = True, **details: Any) -> LogRecord:
        ...

    def debug_error(self,
                    msg: str,
                    *,
                    exception: Exception | None = None,
                    emit_details: bool = True,
                    **details: Any) -> LogRecord:
        """
        Print debug error message

        :param msg: Message to print
        :param exception: Optional exception type to print (Default: None)
        :param emit_details: Include details when printing debug info (Default: True)
        :param details: Optional details for the log message
        :return: LogRecord
        """
        return self._emit(Level.DEBUG, Severity.ERROR, msg, emit_details, exception, details)

    #
    # Wrapper info log methods
    #
    def info(self, msg: str, *, emit_details: bool = True, **details: Dict[str, Any]) -> LogRecord:
        """
        Print info message

        :param msg: Message to print
        :param emit_details: Include details when printing debug info (Default: True)
        :param details: Optional details for the log message
        :return: LogRecord
        """
        return self._emit(Level.INFO, Severity.INFO, msg, emit_details, None, details)

    @overload
    def warn(self, msg: str, *, exception: Exception | None = None, emit_details: bool = True,
             **details: Any) -> LogRecord:
        ...

    @overload
    def warn(self, exception: Exception, *, emit_details: bool = True, **details: Any) -> LogRecord:
        ...

    def warn(self,
             msg: str,
             *,
             exception: Exception | None = None,
             emit_details: bool = True,
             **details: Any) -> LogRecord:
        """
        Print warn message

        :param msg: Message to print
        :param exception: Optional exception type to print (Default: None)
        :param emit_details: Include details when printing debug info (Default: True)
        :param details: Optional details for the log message
        :return: LogRecord
        """
        return self._emit(Level.INFO, Severity.WARN, msg, emit_details, exception, details)

    @overload
    def error(self, msg: str, *, exception: Exception | None = None, emit_details: bool = True,
              **details: Any) -> LogRecord:
        ...

    @overload
    def error(self, exception: Exception, *, emit_details: bool = True, **details: Any) -> LogRecord:
        ...

    def error(self,
              msg: str | Exception,
              *,
              exception: Exception | None = None,
              emit_details: bool = True,
              **details: Any) -> LogRecord:
        """
        Print error message

        :param msg: Message or exception to print
        :param exception: Optional exception type to print (Default: None)
        :param emit_details: Include details when printing debug info (Default: True)
        :param details: Optional details for the log message
        :return: LogRecord
        """
        if isinstance(msg, Exception):
            actual_msg = str(msg)
            exception = msg
        else:
            actual_msg = msg
        return self._emit(Level.INFO, Severity.ERROR, actual_msg, emit_details, exception, details)

    #
    # Fatal wrapper
    #

    def fatal(self,
              msg: str,
              *,
              exception: Exception | None = None,
              emit_details: bool = True,
              **details: Any) -> NoReturn:
        """
        Report fail message and exit 1

        :param msg: Message to print
        :param exception: Optional exception type to print (Default: None)
        :param emit_details: Include details when printing debug info (Default: True)
        :param details: Optional details for the log message
        """
        self._emit(Level.INFO, Severity.FATAL, msg, emit_details, exception, details)
        sys.exit(1)


def _make_tqdm_desc(description: str) -> str:
    """
    Create the standard tqdm description

    :param description: Text description of process
    :return: Full formatted description
    """
    log_record = LogRecord(Level.INFO, Severity.INFO, description, caller=_resolve_caller())
    return log_record.format(False)


def _resolve_caller(caller_frame_distance: int = CALLER_FRAME_DISTANCE) -> str | None:
    """
    Resolve the name of the caller frame

    :param caller_frame_distance: Distance from the caller (Default: 3)
    :return: Name of caller frame
    """
    frame = inspect.currentframe()
    for _ in range(caller_frame_distance):
        frame = frame.f_back
    module = inspect.getmodule(frame)
    return module.__name__ if module else None
