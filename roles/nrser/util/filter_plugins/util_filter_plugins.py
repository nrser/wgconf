# Ugh it seems like you can't split these up into separate files while sharing
# functions in a simple way... whatever Assible cooks up doesn't get this 
# directory in the Python import path of some shit... this doesn't work:
# 
#       from .other_filter_plugins import sucks
# 
# You get "No module named 'ansible.plugins.filter.other'"... yeah.
# 
# I'm sure it _could_ be worked around by putting the functions in a 
# 

from pathlib import Path
import shlex
from functools import reduce
from os import path, PathLike
from typing import *

def ini_enc_value(value):
    """Encode `value` for use in the `ini_file` module's `value:` parameter.
    """
    if value is True:
        return 'yes'
    elif value is False:
        return 'no'
    else:
        return value

def dict_merge(*dicts):
    return reduce(lambda d1, d2: {**d1, **d2}, dicts)

def dict_defaults(*dicts):
    return dict_merge(*reversed(dicts))

def f(s: str) -> str:
    '''Format things (in `name:`). Only handles paths rn.
    '''
    if s.startswith('/') or s.startswith('./'):
        return f"<{rel(s)}>"
    return f"`{s}`"

def rel(path: str, to: Optional[str] = None) -> str:
    if to is None:
        to = Path.cwd()
    try:
        if rel := Path(path).relative_to(to):
            return f"./{rel}"
    except:
        pass
    return path

def join(frags) -> str:
    '''Preferred usage style (Jinja2):
    
        {{ (part1, part2, part3) | join }}
    
    '''
    return path.join(*frags)

class FilterModule:
    def filters(self):
        return dict(
            ini_enc_value=ini_enc_value,
            f=f,
            join=join,
            rel=rel,
            dict_merge=dict_merge,
            dict_defaults=dict_defaults,
        )
    