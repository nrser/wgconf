import logging

from .display_handler import DisplayHandler
from .log_record import LogRecord

from nansi.utils.path import rel

LOG = logging.getLogger(__name__)

_handler = None

def get_handler() -> DisplayHandler:
    global _handler
    if _handler is None:
        _handler = DisplayHandler()
    return _handler

def setup_for_display():
    if logging.getLogRecordFactory() is not LogRecord:
        logging.setLogRecordFactory(LogRecord)
    
    pkg_logger = logging.getLogger('nansi')
    if pkg_logger.level is not logging.DEBUG:
        pkg_logger.setLevel(logging.DEBUG)
    
    handler = get_handler()
    if handler not in pkg_logger.handlers:
        pkg_logger.addHandler(get_handler())

def get_plugin_logger(file_path):
    setup_for_display()
    return logging.getLogger(f"nansi.<{rel(file_path)}>")
