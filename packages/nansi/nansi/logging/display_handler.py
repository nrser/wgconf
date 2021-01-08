from typing import *
import logging
from collections import abc
import sys

from ansible.utils.display import Display

from rich.table import Table
from rich.console import Console
from rich.text import Text
from rich.style import Style
from rich.containers import Renderables
from rich.traceback import Traceback

from .rich_handler import RichHandler

from nansi.utils.dumpster import dumps

OUT_CONSOLE = Console(file=sys.stdout)
ERR_CONSOLE = Console(file=sys.stderr)

# `ansible.utils.display.Display` is *wonky* with little differences between
# the level-methods... these levels need to be `str#rstrip()` *before* being
# sent to `Display`. `logging.WARNING` is not in here, well, because Ansi'
# *always* adds a line above formatted warnings, so why bother...
RSTRIP_FOR_DISPLAY = {
    logging.INFO,
    logging.ERROR,
    logging.CRITICAL
}

class DisplayHandler(RichHandler):
    '''
    A handler class that writes messages to Ansible's
    `ansible.utils.display.Display`, which then writes them to the user output.
    '''

    display: Display

    def __init__(
        self,
        level: int=logging.NOTSET,
        *,
        consoles: Optional[Mapping[str, Console]]=None,
        level_map: Optional[Mapping[str, str]]=None,
        display: Optional[Display]=None
    ):
        super().__init__(level=level, consoles=consoles, level_map=level_map)
        # Fuckin'-A... this *has* to come before the super-call, because it does
        # some weak-ref shit that tries to hash the instances, and since our
        # equality is based on `#display` equality, we need to have `#display`
        # assigned *before* it does that crap.
        if display is None:
            display = Display()
        self.display = display

    # #__init__

    # `logging.Handler` API
    # ========================================================================

    def emit(self, record):
        '''
        Overridden to send log records to Ansible's display.
        '''
        try:
            # Grab `#_emit_DEBUG()`, `#_emit_INFO()`, etc.
            method = getattr(self, f"_emit_{record.levelname}", None)
            # I guess just skip-out when something doesn't work..?
            if method is None:
                super().emit(record)
            else:
                method(record)
        except (KeyboardInterrupt, SystemExit):
            # We want these guys to bub' up
            raise
        except Exception as error:
            OUT_CONSOLE.print_exception()
            # self.handleError(record)

    def _objects_for(self, record):
        objects = [record.msg]
        if isinstance(record.args, abc.Mapping):
            objects.append(record.args)
        else:
            objects += record.args
        if record.exc_info:
            objects.append(Traceback.from_exception(*record.exc_info))
        return objects


    def _format_for_display(self, record):
        formatted = dumps(*self._objects_for(record))
        if record.levelno in RSTRIP_FOR_DISPLAY:
            return formatted.rstrip()
        return formatted

    # Internal Emit Methods
    # ========================================================================
    #
    # Do the actual emitting work.
    #

    def _emit_DEBUG(self, record) -> None:
        if self.display.verbosity > 1:
            self._emit_table(record)

    def _emit_INFO(self, record) -> None:
        if self.display.verbosity > 0:
            self._emit_table(record)
            # self.display.verbose(self._format_for_display(record), caplevel=0)

    # def _emit_WARNING(self, record) -> None:
    #     self.display.warning(self._format_for_display(record), formatted=True)

    # def _emit_ERROR(self, record) -> None:
    #     self.display.error(self._format_for_display(record), wrap_text=False)

    # def _emit_CRITICAL(self, record) -> None:
    #     self.display.error(
    #         f"(CRITICAL) {self._format_for_display(record)}",
    #         wrap_text=False
    #     )
