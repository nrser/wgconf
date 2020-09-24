from typing import *
from io import StringIO

from rich.console import Console

def dumps(*objects, **kwds):
    console = Console(file=StringIO(), force_terminal=True)
    console.print(*objects, **kwds)
    return console.file.getvalue()
