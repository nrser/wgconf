from typing import *
import logging
from collections.abc import Mapping
from ansible.utils.display import Display
import os
import sys

from rich.table import Table
from rich.console import Console
from rich.text import Text
from rich.style import Style
from rich.containers import Renderables

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

class DisplayHandler(logging.Handler):
    '''
    A handler class that writes messages to Ansible's
    `ansible.utils.display.Display`, which then writes them to the user output.
    '''
    
    display: Display
    
    def __init__(self, display: Optional[Display]=None):
        # Fuckin'-A... this *has* to come before the super-call, because it does
        # some weak-ref shit that tries to hash the instances, and since our
        # equality is based on `#display` equality, we need to have `#display`
        # assigned *before* it does that crap.
        if display is None:
            display = Display()
        self._display = display
        
        super().__init__()
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
            if method is not None:
                method(record)
        except (KeyboardInterrupt, SystemExit):
            # We want these guys to bub' up
            raise
        except Exception as error:
            OUT_CONSOLE.print_exception()
            # self.handleError(record)
    
    # Data-Model Methods
    # ========================================================================
    # 
    # Want `__eq__()` to return `True` for `DisplayHandler` instances that
    # write to the same `ansible.display.Display` so that
    # `logging.Logger.addHandler()` does not add many handlers that do the same
    # thing.
    # 
    # This seems to work because logging.Logger.addHandler()` has a check like:
    # 
    #       if not (hdlr in self.handlers):
    #           self.handlers.append(hdlr)
    # 
    # At least in modern Ansible, `Display` is a singleton, so unless someone 
    # rolls their own `Display` somehow, **all `DisplayHandler` are equal to
    # eachother**.
    # 
    # Then `__hash__()` has to get implemented too since over-riding `#__eq__()`
    # knocks out the built-in `__hash__()` implementation (because
    # `#__hash__()` must be the same when `#__eq__()` is `True`).
    #  
    
    def __eq__(self, other: Any) -> bool:
        '''`DisplayHandler` instances are equal to all other `DisplayHandler`
        instances in normal circumstances.
        
        This is because the instances are equal if their `#display` attributes
        are equal, which -- since `ansible.utils.display.Display` is a singleton
        -- is `True` in any normal situation.
        '''
        return (
            getattr(other, '__class__') is self.__class__
            and other._display == self._display
        )
    
    def __hash__(self) -> int:
        '''Equality is based on `#display` equality, so hash is `#display` hash.
        '''
        return hash(self._display)
    
    def _objects_for(self, record):
        if isinstance(record.args, Mapping):
            return (record.msg, record.args)
        else:
            return (record.msg, *record.args)
    
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
        if self._display.verbosity > 1:
            self._emit_table(record)
    
    def _emit_INFO(self, record) -> None:
        if self._display.verbosity > 0:
            self._display.verbose(self._format_for_display(record), caplevel=0)
    
    def _emit_WARNING(self, record) -> None:
        self._display.warning(self._format_for_display(record), formatted=True)
    
    def _emit_ERROR(self, record) -> None:
        self._display.error(self._format_for_display(record), wrap_text=False)
    
    def _emit_CRITICAL(self, record) -> None:
        self._display.error(
            f"(CRITICAL) {self._format_for_display(record)}",
            wrap_text=False
        )
    
    def _emit_table(self, record) -> None:
        # SEE   https://github.com/willmcgugan/rich/blob/25a1bf06b4854bd8d9239f8ba05678d2c60a62ad/rich/_log_render.py#L26
        
        # TODO  Figure out if should use STDERR
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
        
        left = Renderables((
            Text(record.levelname),
        ))
        
        right = Renderables((
            Text(record.name, Style(color='blue', dim=True)),
            *console._collect_renderables(
                self._objects_for(record),
                sep=" ",
                end="\n",
            ),
        ))
        
        output.add_row(left, right)
        
        console.print(output)
        