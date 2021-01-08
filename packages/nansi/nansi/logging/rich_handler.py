from __future__ import annotations
import logging
import sys
from typing import *

# Some way of complaining (ideally) _outside_ the logging system, to (try) to
# avoid recursive self-destruction (yeah, I did see something about telling the
# warning system to go through logging, so it might still explode...)
# from warnings import warn

from rich.table import Table
from rich.console import Console
from rich.text import Text
from rich.style import Style
from rich.containers import Renderables
from rich.traceback import Traceback
from rich.pretty import Pretty

OUT_CONSOLE = Console(file=sys.stdout)
ERR_CONSOLE = Console(file=sys.stderr)


class RichHandler(logging.Handler):
    # Default consoles, pointing to the two standard output streams
    DEFAULT_CONSOLES = dict(
        out=OUT_CONSOLE,
        err=ERR_CONSOLE,
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

    def __init__(
        self,
        level: int = logging.NOTSET,
        *,
        consoles: Optional[Mapping[str, Console]] = None,
        level_map: Optional[Mapping[str, str]] = None,
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
        '''
        Overridden to send log records to Ansible's display.
        '''
        try:
            self._emit_table(record)
        except (KeyboardInterrupt, SystemExit):
            # We want these guys to bub' up
            raise
        except Exception as error:
            OUT_CONSOLE.print_exception()
            # self.handleError(record)

    def _emit_table(self, record):
        # SEE   https://github.com/willmcgugan/rich/blob/25a1bf06b4854bd8d9239f8ba05678d2c60a62ad/rich/_log_render.py#L26

        console = self.consoles.get(
            self.level_map.get(record.levelno, "err"),
            ERR_CONSOLE,
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

        output.add_row(None, Text(msg))

        if hasattr(record, "data") and record.data:
            table = Table.grid(padding=(0, 1))
            table.expand = True
            table.add_column()
            table.add_column()
            for key, value in record.data.items():
                table.add_row(
                    Text(key, Style(color="blue", italic=True)), Pretty(value)
                )
            output.add_row(None, table)

        if record.exc_info:
            output.add_row(None, Traceback.from_exception(*record.exc_info))

        console.print(output)
