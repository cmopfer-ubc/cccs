"""
Created: Camden Opfer, June 2025
Modified: Camden Opfer, March 2026

A variety of utility functions that are helpful for getting Python to do things, but not necessarily specific to computational climate, or even science in general.
"""

from typing import Sequence
import logging
import sys
import os

def createLogger(logFile:str|None = None, loggerName:str = __name__, propagatedLoggerNames:Sequence[str]|None = None) -> logging.Logger:
    """
    Uses the logging package to create a logger, which also handles warnings and errors. Optionally, write logs to a file, and/or propagate other loggers to this new logger.

    Note: This function will override some basic settings about where warnings and errors are reported, and is intended to be used as a main logger. If you have other important loggers, this function may cause unwanted behaviour.

    :param logFile: A file to which the log is written. Default is None, so output is only printed to the terminal.
    :type logFile: str or None, optional
    :param loggerName: The name of the created logger. Default is __name__, which evaluates to 'cccs.utils'.
    :type loggerName: str, optional
    :param propagatedLoggerNames: A sequence of additional loggers to propagate into this new one.
    :type propagatedLoggerNames: Sequence[str] or None, optional
    """
    # Argument handling
    if propagatedLoggerNames is None:
        propagatedLoggerNames = set()
    else:
        propagatedLoggerNames = set(propagatedLoggerNames)

    # Basic logger setup
    logger = logging.getLogger(loggerName)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    # Log to terminal (a stream to sys.stderr)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Log to a file
    if logFile is not None:
        logDir = os.path.dirname(logFile)
        if logDir: # Log is not in the working directory, so its directory may not exist
            os.makedirs(logDir, exist_ok=True)

        fh = logging.FileHandler(logFile, mode='a')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    # Log warnings
    logging.captureWarnings(True)
    propagatedLoggerNames.add('py.warnings')

    # Log uncaught exceptions
    def logException(excType, excValue, excTraceback):
        """
        Intented to overwrite the built-in sys.excepthook function so that exceptions are nicely funneled into the logger
        """
        if issubclass(excType, KeyboardInterrupt):
            sys.__excepthook__(excType, excValue, excTraceback)
            return

        logger.error('Uncaught Exception:', exc_info=(excType, excValue, excTraceback))
    sys.excepthook = logException

    # Propagate the other package's loggers to this new logger
    def propagateLogger(loggerName):
        """
        Checks if the fh and ch handlers are already used by the provided logger and, if not, adds them.
        """
        propagatedLogger = logging.getLogger(loggerName)

        existingHandlers = propagatedLogger.handlers
        needFh, needCh = True, True
        for existingHandler in existingHandlers:
            if isinstance(existingHandler, logging.FileHandler) and existingHandler.baseFilename == fh.baseFilename:
                needFh = False
            elif isinstance(existingHandler, logging.StreamHandler) and existingHandler.stream == ch.stream:
                needCh = False

        if needFh:
            propagatedLogger.addHandler(fh)
        if needCh:
            propagatedLogger.addHandler(ch)

    for propagatedLoggerName in propagatedLoggerNames:
        propagateLogger(propagatedLoggerName)

    return logger

def log(message:str|Exception, logLevel:int|str=logging.INFO, loggerName:str=__name__):
    """
    Logs a message, either by printing (if no logger of the provided name exists) or by logging with a specified severity level.

    :param message: The message to log. If an exception (usually in a try/except clause), traceback information will be retained.
    :type message: str or Exception
    :param logLevel: Severity of logged item. In order of importance, should be one of 'debug', 'info', 'warning', 'error', or 'critical'. These strings will be mapped to their corresponding integer levels, or you can provide an integer (e.g. logging.DEBUF or logging.WARNING). Default is logging.INFO.
    :type logLevel: int or str, optional
    :param loggerName: The internal name of the logger to use. Default is __name__, which will be 'cccs.utils'.
    :str loggerName: str, optional
    """
    logger = logging.getLogger(loggerName)

    if not logger.hasHandlers(): # Logger has not been initialized
        print(message)
        return

    if isinstance(message, Exception):
        logger.exception(message)
        return

    if isinstance(logLevel, str):
        try:
            logLevel = {'debug':logging.DEBUG, 'info':logging.INFO, 'warning':logging.WARNING, 'error':logging.ERROR, 'critical':logging.CRITICAL}[logLevel.lower()]
        except KeyError:
            logger.log(level = logging.WARNING, msg = f'Invalid log level "{logLevel}". Will default to info.')
            logLevel = logging.INFO
        except Exception as e:
            logger.exception(e)
            logger.log(level = logging.WARNING, msg = f'Something unexpected happened when parsing log level "{logLevel}". Will default to info.')
            logLevel = logging.INFO

    if not isinstance(logLevel, int):
        logger.log(level = logging.WARNING, msg = f'Got unexpected log level "{logLevel}". Will default to info.')
        logLevel = logging.INFO

    logger.log(level=logLevel, msg=message)
