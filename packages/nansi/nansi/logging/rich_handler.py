"""\
Contains the `RichHandler` class.
"""

from __future__ import annotations
from typing import (
    Any,
    Optional,
    Mapping,
)
import logging
import inspect
import sys

from rich.table import Table
from rich.console import Console, ConsoleRenderable, RichCast
from rich.text import Text
from rich.style import Style
from rich.traceback import Traceback
from rich.pretty import Pretty
from rich.highlighter import ReprHighlighter

DEFAULT_VALUE_TYPE_SPLIT_MIN = 24


def is_rich(x: Any) -> bool:
    return isinstance(x, (ConsoleRenderable, RichCast))


def value_type(value: Any, *, split_min: int=DEFAULT_VALUE_TYPE_SPLIT_MIN):
    typ = type(value)
    if hasattr(typ, "__name__"):
        # Just omit the module name for now, it gets to take up too much
        # space...

        # if (
        #     hasattr(typ, "__module__")
        #     and typ.__module__ != "builtins"
        # ):
        #     if len(typ.__module__) + len(typ.__name__) < split_min:
        #         return f"{typ.__module__}.{typ.__name__}"
        #     else:
        #         return f"{typ.__module__}\n.{typ.__name__}"
        # else:
        #     return typ.__name__

        return typ.__name__
    else:
        return Pretty(typ)


def table(mapping: Mapping) -> Table:
    tbl = Table.grid(padding=(0, 1))
    tbl.expand = True
    tbl.add_column(style=Style(color="blue", italic=True))
    tbl.add_column(style=Style(color="#4ec9b0", italic=True))
    tbl.add_column()
    for key in sorted(mapping.keys()):
        value = mapping[key]
        if is_rich(value):
            rich_value_type = None
            rich_value = value
        else:
            rich_value_type = value_type(value)
            if isinstance(value, str):
                rich_value = value
            elif (
                inspect.isfunction(value)
                and hasattr(value, "__module__")
                and hasattr(value, "__name__")
            ):
                rich_value = ReprHighlighter()(
                    f"<function {value.__module__}.{value.__name__}>"
                )
            else:
                rich_value = Pretty(value)
        tbl.add_row(key, rich_value_type, rich_value)
    return tbl


class RichHandler(logging.Handler):
    """\
    A `logging.Handler` extension that uses [rich][] to print pretty nice log
    entries to the console.

    Output is meant for specifically humans.
    """

    # Default consoles, pointing to the two standard output streams
    DEFAULT_CONSOLES = dict(
        out=Console(file=sys.stdout),
        err=Console(file=sys.stderr),
    )

    # By default, all logging levels log to the `err` console
    DEFAULT_LEVEL_MAP = {
        logging.CRITICAL: "err",
        logging.ERROR: "err",
        logging.WARNING: "err",
        logging.INFO: "err",
        logging.DEBUG: "err",
    }

    @classmethod
    def singleton(cls) -> RichHandler:
        instance = getattr(cls, "__singleton", None)
        if instance is not None and instance.__class__ == cls:
            return instance
        instance = cls()
        setattr(cls, "__singleton", instance)
        return instance

    consoles: Mapping[str, Console]
    level_map: Mapping[int, str]

    def __init__(
        self,
        level: int = logging.NOTSET,
        *,
        consoles: Optional[Mapping[str, Console]] = None,
        level_map: Optional[Mapping[int, str]] = None,
    ):
        super().__init__(level=level)

        if consoles is None:
            self.consoles = self.DEFAULT_CONSOLES.copy()
        else:
            self.consoles = {**self.DEFAULT_CONSOLES, **consoles}

        if level_map is None:
            self.level_map = self.DEFAULT_LEVEL_MAP.copy()
        else:
            self.level_map = {**self.DEFAULT_LEVEL_MAP, **level_map}

    def emit(self, record):
        # pylint: disable=broad-except
        try:
            self._emit_table(record)
        except (KeyboardInterrupt, SystemExit) as error:
            # We want these guys to bub' up
            raise error
        except Exception as error:
            self.DEFAULT_CONSOLES["err"].print_exception()
            # self.handleError(record)

    def _emit_table(self, record):
        # SEE   https://github.com/willmcgugan/rich/blob/25a1bf06b4854bd8d9239f8ba05678d2c60a62ad/rich/_log_render.py#L26

        console = self.consoles.get(
            self.level_map.get(record.levelno, "err"),
            self.DEFAULT_CONSOLES["err"],
        )

        output = Table.grid(padding=(0, 1))
        output.expand = True

        # Left column -- log level, time
        output.add_column(
            style=f"logging.level.{record.levelname.lower()}",
            width=8,
        )

        # Main column -- log name, message, args
        output.add_column(ratio=1, style="log.message", overflow="fold")

        output.add_row(
            Text(record.levelname),
            Text(record.name, Style(color="blue", dim=True)),
        )

        if record.args:
            msg = str(record.msg) % record.args
        else:
            msg = str(record.msg)

        output.add_row(None, msg)

        if hasattr(record, "data") and record.data:
            output.add_row(None, table(record.data))

        if record.exc_info:
            output.add_row(None, Traceback.from_exception(*record.exc_info))

        console.print(output)
