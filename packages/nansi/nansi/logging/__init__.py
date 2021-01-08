from typing import *
import logging

from nansi.utils.path import rel

from .kwds_logger import KwdsLogger
from .rich_handler import RichHandler
from .display_handler import DisplayHandler

LOG = logging.getLogger(__name__)

NANSI_LOGGER = logging.getLogger("nansi")
NANSI_COLLECTION_LOGGER = logging.getLogger("ansible_collections.nrser.nansi")
NRSER_NANSI_LOGGER = logging.getLogger("nrser.nansi")

def setup_for_display():
    logging.setLoggerClass(KwdsLogger)

    # Need to let everything through, then `DisplayHandler` filters using
    # Ansible's verbose settings
    for logger in (NANSI_LOGGER, NANSI_COLLECTION_LOGGER, NRSER_NANSI_LOGGER):
        if logger.level is not logging.DEBUG:
            logger.setLevel(logging.DEBUG)
        logger.addHandler(DisplayHandler.singleton())


def setup_for_console(level: Optional[int] = None):
    logging.setLoggerClass(KwdsLogger)

    if level is not None:
        NANSI_LOGGER.setLevel(level)

    NANSI_LOGGER.addHandler(RichHandler.singleton())


def get_plugin_logger(file_path):
    setup_for_display()
    return logging.getLogger(f"nansi.<{rel(file_path)}>")
