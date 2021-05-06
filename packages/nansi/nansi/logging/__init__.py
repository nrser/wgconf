# pylint: disable=global-statement

from __future__ import annotations
import logging
from typing import (
    Literal,
    Optional,
    Union,
    Dict,
    cast,
    Tuple,
)

# Some way of complaining (ideally) _outside_ the logging system, to (try) to
# avoid recursive self-destruction (yeah, I did see something about telling the
# warning system to go through logging, so it might still explode...)
# from warnings import warn

from ansible.utils.display import Display

from .kwds_logger import KwdsLogger
from .log_getter import LogGetter
from .rich_handler import RichHandler

# Stdlib's `logging` level values, which are integers.
TLevel = Literal[
    logging.CRITICAL,
    logging.ERROR,
    logging.WARNING,
    logging.INFO,
    logging.DEBUG,
    logging.NOTSET,
]

# String versions of the log levels, which are also accepted as level "values"
TLevelStr = Literal[
    str(logging.CRITICAL),
    str(logging.ERROR),
    str(logging.WARNING),
    str(logging.INFO),
    str(logging.DEBUG),
    str(logging.NOTSET),
]

# ...and the names of stdlib `logging` constants, which are easier for us mere
# humans to remember.
TLevelName = Literal[
    "CRITICAL",
    "FATAL",
    "ERROR",
    "WARNING",
    "WARN",
    "INFO",
    "DEBUG",
    "NOTSET",
]

# Something that can be turned into a log level defined in `logging` -- one of:
#
# 1.  An `int` level itself (`TLevel`)
# 2.  One of those `int` levels as a `str` (`TLevelStr`)
# 3.  The name of a level constant. In practice, we ignore case, but that is
#     not reflected in the type for (hopefully) obvious reasons.
#
TLevelValue = Union[TLevel, TLevelStr, TLevelName]

# Valid _verbose_ switch values, provided like `-v` (1), `-vv` (2), etc.
TVerbosity = Literal[0, 1, 2, 3]

# Union type representing when we don't know (or care) if we're getting a
# LogGetter proxy or an actual Logger
TLogger = Union[logging.Logger, LogGetter]

# Re-defining log levels allows using this module to be swapped in for basic
# uses of stdlib `logging`.
CRITICAL = logging.CRITICAL  # 50
FATAL = logging.FATAL  # ↑
ERROR = logging.ERROR  # 40
WARNING = logging.WARNING  # 30
WARN = logging.WARN  # ↑
INFO = logging.INFO  # 20
DEBUG = logging.DEBUG  # 10
NOTSET = logging.NOTSET  # 0

# Default log level for `nansi.*` loggers
DEFAULT_LEVEL = WARNING

# Map of log levels... by (constant) name.
LEVELS_BY_NAME: Dict[TLevelName, TLevel] = dict(
    CRITICAL=CRITICAL,
    FATAL=FATAL,
    ERROR=ERROR,
    WARNING=WARNING,
    WARN=WARN,
    INFO=INFO,
    DEBUG=DEBUG,
    NOTSET=NOTSET,
)

COLLECTION_NAMESPACE = "nrser"
COLLECTION_NAME = "nansi"
PKG_LOGGER_NAME = __name__.split(".")[0]
COLLECTION_LOGGER_NAME = f"{COLLECTION_NAMESPACE}.{COLLECTION_NAME}"
ANSIBLE_COLLECTIONS_LOGGER_NAME = (
    f"ansible_collections.{COLLECTION_LOGGER_NAME}"
)

ROOT_LOGGER_NAMES = (
    PKG_LOGGER_NAME,
    COLLECTION_LOGGER_NAME,
    ANSIBLE_COLLECTIONS_LOGGER_NAME,
)


_is_setup: bool = False


def level_for(value: TLevelValue) -> TLevel:
    """
    Make a `logging` level `int` from things you might get from an ENV var or,
    say, a human being.

    Examples:

    1.  Integer levels can be provided as strings:

            >>> level_for("10")
            10

    2.  Levels we don't know get a puke:

            >>> level_for("8")
            Traceback (most recent call last):
                ...
            ValueError: Unknown log level integer 8; known levels are 50 (CRITICAL), 50 (FATAL), 40 (ERROR), 30 (WARNING), 30 (WARN), 20 (INFO), 10 (DEBUG), 0 (NOTSET)

    3.  We also accept level *names* (gasp!), case-insensitive:


            >>> level_for("debug")
            10
            >>> level_for("DEBUG")
            10

    4.  Everything else can kick rocks:

            >>> level_for([])
            Traceback (most recent call last):
                ...
            TypeError: Expected `value` to be str or int, given <class 'list'>: []
    """

    if isinstance(value, str):
        if value.isdigit():
            return level_for(int(value))
        cap_value = value.upper()
        if cap_value in LEVELS_BY_NAME:
            return LEVELS_BY_NAME[cap_value]
        raise ValueError(
            f"Unknown log level name {repr(value)}; known level names are "
            f"{', '.join(LEVELS_BY_NAME.keys())} (case-insensitive)"
        )
    if isinstance(value, int):
        if value in LEVELS_BY_NAME.values():
            return cast(TLevel, value)
        levels = ", ".join(f"{v} ({k})" for k, v in LEVELS_BY_NAME.items())
        raise ValueError(
            f"Unknown log level integer {value}; known levels are {levels}"
        )
    raise TypeError(
        "Expected `value` to be str or int, "
        f"given {type(value)}: {repr(value)}"
    )


def get_logger(*name: str) -> LogGetter:
    """\
    Returns a proxy to a logger where construction is deferred until first use.

    See `nansi.logging.LogGetter`.
    """
    return LogGetter(*name)


def root_loggers() -> Tuple[LogGetter]:
    return (get_logger(name) for name in ROOT_LOGGER_NAMES)


def set_level(level: Optional[TLevelValue] = None) -> None:
    if level is None:
        return

    level = level_for(level)

    for logger in root_loggers():
        if logger.level != level:
            logger.setLevel(level)
            if level == DEBUG:
                logger.debug(
                    "[logging.level.debug]DEBUG[/logging.level.debug] logging "
                    f"[on]ENABLED[/on] for {logger.name}.*"
                )


def setup(level: TLevelValue = DEFAULT_LEVEL) -> None:
    global _is_setup

    if _is_setup is False:
        logging.setLoggerClass(KwdsLogger)

        rich_handler = RichHandler.singleton()
        for logger in root_loggers():
            logger.addHandler(rich_handler)

        _is_setup = True

    set_level(level)


def setup_for_display():
    display = Display()
    if display.verbosity > 1:
        level = DEBUG
    elif display.verbosity > 0:
        level = INFO
    else:
        level = WARNING

    setup(level)


# Support the weird camel-case that stdlib `logging` uses...
getLogger = get_logger
setLevel = set_level


if __name__ == "__main__":
    import doctest

    doctest.testmod()
