import logging
import sys

from rich.table import Table
from rich.console import Console
from rich.text import Text
from rich.style import Style
from rich.containers import Renderables
from rich.traceback import Traceback

OUT_CONSOLE = Console(file=sys.stdout)


class Lagger(logging.getLoggerClass()):
    def _log(
        self,
        level,
        msg,
        args,
        exc_info=None,
        extra=None,
        stack_info=False,
        **data,
    ):
        """
        Low-level log implementation, proxied to allow nested logger adapters.
        """

        if extra is not None:
            if isinstance(extra, dict):
                extra = {'data': data, **extra}
        else:
            extra = {'data': data}

        super()._log(
            level,
            msg,
            args,
            exc_info=exc_info,
            stack_info=stack_info,
            extra=extra,
        )


class Handler(logging.Handler):
    def _objects_for(self, record):
        if record.args:
            msg = str(record.msg) % record.args
        else:
            msg = str(record.msg)

        objects = [msg]
        if hasattr(record, "data") and record.data:
            objects.append(record.data)
        if record.exc_info:
            objects.append(Traceback.from_exception(*record.exc_info))
        return objects

    def emit(self, record):
        console = OUT_CONSOLE

        output = Table.grid(padding=(0, 1))
        output.expand = True

        # Left column -- log level, time
        output.add_column(
            style=f"logging.level.{record.levelname.lower()}",
            width=8,
        )

        # Main column -- log name, message, args
        output.add_column(ratio=1, style="log.message", overflow="fold")

        left = Renderables((Text(record.levelname),))

        right = Renderables(
            (
                Text(record.name, Style(color="blue", dim=True)),
                *getattr(console, "_collect_renderables")(
                    self._objects_for(record),
                    sep=" ",
                    end="\n",
                ),
            )
        )

        output.add_row(left, right)

        console.print(output)


on = True

if on:
    logging.setLoggerClass(Lagger)
else:
    logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger("scratchers")
log.setLevel(logging.DEBUG)

if on:
    log.addHandler(Handler())

# log.info("hey ho %(what)s", {'what': "let's go!"})
log.info("hey ho %s %s", "let's", "go!", ho=1, go=2)
