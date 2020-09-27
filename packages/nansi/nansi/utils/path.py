from typing import *
from pathlib import Path
from os import PathLike

def rel(path: PathLike, to: Optional[PathLike] = None) -> str:
    '''Relativize a path if it's a descendant, otherwise just return as-is.
    
    >>> rel(f"{Path.cwd()}/a/b/c")
    './a/b/c'
    
    >>> rel('/usr/bin')
    '/usr/bin'
    '''
    try:
        rel = Path(path).relative_to(to or Path.cwd())
        if rel:
            return f"./{rel}"
    except:
        pass
    return path
