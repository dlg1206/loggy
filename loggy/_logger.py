"""
File: logger.py
Description: Logger for actions

@author Derek Garcia
"""

import asyncio
import csv
import inspect
import os
import sys
from concurrent import futures
from concurrent.futures import Future
from datetime import tzinfo
from typing import Any, Iterable, Dict, NoReturn, Coroutine, overload, TextIO

from tqdm import tqdm

from loggy._levels import Level, Severity
from loggy._record import LogRecord, now

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

    def __init__(self,
                 log_level: Level = DEFAULT_LOG_LEVEL,
                 log_file: str | None = None,
                 tz: tzinfo | None = None,
                 stream: TextIO | None = None,
                 force_color: bool = False):
        """
        Create new logger

        :param log_level: Logging level (Default: INFO)
        :param tz: Optional timezone for timestamps (Default: device tz)
        :param stream: Optional output stream (Default: stdout)
        :param force_color: Force color output instead of using stream to determine (Default: False)
        :raises ValueError: If log_level is in valid
        """
        self._log_level = log_level
        self._suppress_depth = 0
        self._log_file = log_file
        self._tz = tz
        self._stream = stream or sys.stdout  # default stdout
        self._supports_color = force_color or self._detect_color(self._stream)

        # init log file
        if self._log_file:
            with open(self._log_file, 'w', encoding="utf-8") as f:
                csv.writer(f).writerow(('timestamp', 'level', 'severity', 'message', 'exception', 'details'))

    @staticmethod
    def _detect_color(stream: TextIO) -> bool:
        """
        Check if the terminal output supports color

        :param stream: Output stream writing to
        :return: True if color, false otherwise
        """
        if os.environ.get("NO_COLOR"):
            return False
        if os.environ.get("FORCE_COLOR"):
            return True
        if os.environ.get("TERM") == "dumb":
            return False
        return hasattr(stream, "isatty") and stream.isatty()

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
        log_record = LogRecord(level, severity, msg,
                               caller=_resolve_caller(), exception=exception, details=details, timestamp=now(self._tz))

        # save to log file
        if self._log_file:
            with open(self._log_file, 'a', encoding="utf-8") as f:
                csv.writer(f).writerow(log_record.to_csv())

        # always print fatal or print if logger not silenced
        if severity == Severity.FATAL or (
                self._log_level != Level.NONE and level >= self._log_level
        ):
            msg = log_record.format(emit_details, use_color=self._supports_color)
            print(msg, file=self._stream)

        return log_record

    def _create_tqdm(self,
                     total: int,
                     description: str,
                     unit: str,
                     data: Iterable[Any] | None = None,
                     suppress_logs: bool = False) -> _DataQueue | tqdm:
        """
        Create a standardized tqdm progress bar

        :param total: Total units of work
        :param description: Description of the process
        :param unit: Unit of the process
        :param suppress_logs: Temporarily suppress other INFO level messages (Default: False)
        :param data: Optional iterable of to wrap with tqdm (Default: None)
        :return: tqdm loading bar
        """
        show = self._log_level == Level.INFO
        desc = LogRecord(Level.INFO, Severity.INFO, description,
                         caller=_resolve_caller(),
                         timestamp=now(self._tz)).format(False)

        is_root = suppress_logs and show and self._suppress_depth == 0
        # wrap data in tqdm
        if data is not None:
            bar = tqdm(data, total=total, desc=desc, unit=unit, file=self._stream, disable=not show)
            if is_root:
                self._suppress_depth += 1
            return _DataQueue(self, bar, is_root)

        # manual bars: don't touch _suppress_depth unless a wrapper releases it
        bar = tqdm(total=total, desc=desc, unit=unit, file=self._stream, disable=not show)
        return bar

    def set_log_level(self, level: Level | str | None) -> None:
        """
         Set log level, NONE to silence

         :param level: Logging level
         """
        if level is None:
            self._log_level = Level.NONE
        elif isinstance(level, str):
            self._log_level = Level.from_string(level)
        else:
            self._log_level = level

    def set_log_file(self, log_file: str) -> None:
        """
        Set path to save logs to

        :param log_file: Path to log file
        """
        self._log_file = log_file
        with open(self._log_file, 'w', encoding="utf-8") as f:
            csv.writer(f).writerow(('timestamp', 'level', 'severity', 'message', 'exception', 'details'))

    def set_tz(self, tz: tzinfo) -> None:
        """
        Set logging timezone

        :param tz: Timezone for logging
        """
        self._tz = tz

    def set_output_stream(self, stream: TextIO, force_color: bool = False) -> None:
        """
        Set the logging output stream

        :param stream: Output stream
        :param force_color: Force color output instead of using stream to determine (Default: False)
        :return:
        """
        self._stream = stream
        self._supports_color = force_color or self._detect_color(self._stream)

    def set_force_color(self, forced: bool) -> None:
        """
        Force color output

        :param forced: True if force color, False otherwise
        """
        self._supports_color = forced

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
        bar = self._create_tqdm(len(tasks), description, unit, completed, suppress_logs)
        if not isinstance(bar, _DataQueue):
            # should not reach here
            raise RuntimeError("Expected DataQueue got tqdm")
        return bar

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

        bar = self._create_tqdm(len(futures_list), description, unit, completed, suppress_logs)
        if not isinstance(bar, _DataQueue):
            # should not reach here
            raise RuntimeError("Expected DataQueue got tqdm")
        return bar

    def data_queue(self,
                   data: Iterable[Any],
                   description: str,
                   unit: str,
                   suppress_logs: bool = False) -> Iterable[Any]:
        """
        Create a dynamic loading bar if in INFO mode for sync tasks.
        Use `async_data_queue` or `threaded_data_queue` for respective tasks

        :param data: Iterable to wrap with tqdm
        :param description: Description of the process
        :param unit: Unit of the process
        :param suppress_logs: Temporarily suppress other INFO level messages (Default: False)
        :return: tqdm loading bar or completed data
        """
        bar = self._create_tqdm(len(list(data)), description, unit, data, suppress_logs)
        if not isinstance(bar, _DataQueue):
            # should not reach here
            raise RuntimeError("Expected DataQueue got tqdm")
        return bar

    def progress_bar(self,
                     total: int,
                     description: str,
                     unit: str,
                     suppress_logs: bool = False) -> tqdm[Any]:
        """
        Create a process bar if in INFO mode that can be manually updated with .update(N)

        :param total: Total length to wrap with tqdm
        :param description: Description of the process
        :param unit: Unit of the process
        :param suppress_logs: Temporarily suppress other INFO level messages (Default: False)
        :return: tqdm loading bar or None if not in INFO mode
        """
        bar = self._create_tqdm(total, description, unit, suppress_logs=suppress_logs)
        if not isinstance(bar, tqdm):
            # should not reach here
            raise RuntimeError("Expected tqdm got DataQueue")
        return bar

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
                   msg: str | Exception,
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
        if isinstance(msg, Exception):
            actual_msg = str(msg)
            exception = msg
        else:
            actual_msg = msg
        return self._emit(Level.DEBUG, Severity.WARN, actual_msg, emit_details, exception, details)

    @overload
    def debug_error(self, msg: str, *, exception: Exception | None = None, emit_details: bool = True,
                    **details: Any) -> LogRecord:
        ...

    @overload
    def debug_error(self, exception: Exception, *, emit_details: bool = True, **details: Any) -> LogRecord:
        ...

    def debug_error(self,
                    msg: str | Exception,
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
        if isinstance(msg, Exception):
            actual_msg = str(msg)
            exception = msg
        else:
            actual_msg = msg
        return self._emit(Level.DEBUG, Severity.ERROR, actual_msg, emit_details, exception, details)

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
             msg: str | Exception,
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
        if isinstance(msg, Exception):
            actual_msg = str(msg)
            exception = msg
        else:
            actual_msg = msg
        return self._emit(Level.INFO, Severity.WARN, actual_msg, emit_details, exception, details)

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

    @overload
    def fatal(self, msg: str, *, exception: Exception | None = None, emit_details: bool = True,
              exit_code: int = 1, **details: Any) -> LogRecord:
        ...

    @overload
    def fatal(self, exception: Exception, *, emit_details: bool = True, exit_code: int = 1,
              **details: Any) -> LogRecord:
        ...

    def fatal(self,
              msg: str | Exception,
              *,
              exception: Exception | None = None,
              emit_details: bool = True,
              exit_code: int = 1,
              **details: Any) -> NoReturn:
        """
        Report fail message and exit 1

        :param msg: Message to print
        :param exception: Optional exception type to print (Default: None)
        :param emit_details: Include details when printing debug info (Default: True)
        :param exit_code: Optional custom exit code (Default: 1)
        :param details: Optional details for the log message
        """
        if isinstance(msg, Exception):
            actual_msg = str(msg)
            exception = msg
        else:
            actual_msg = msg
        self._emit(Level.INFO, Severity.FATAL, actual_msg, emit_details, exception, details)
        sys.exit(exit_code)


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
