from __future__ import annotations
from pathlib import Path
from os import PathLike
from typing import Optional, Union, Iterable

from nansi.utils import doctesting

Pathable =  Union[str, Path, Iterable["Pathable"]]

def rel(path: PathLike, to: Optional[PathLike] = None) -> str:
    '''Relativize a path if it's a descendant, otherwise just return as-is.

    >>> rel(f"{Path.cwd()}/a/b/c")
    './a/b/c'

    >>> rel('/usr/bin')
    '/usr/bin'
    '''
    # pylint: disable=bare-except
    try:
        rel_path = Path(path).relative_to(to or Path.cwd())
        if rel_path:
            return f"./{rel}"
    except:
        pass
    return path

doctesting.testmod(__name__)
