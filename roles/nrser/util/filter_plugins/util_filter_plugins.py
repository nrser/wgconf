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
from collections.abc import Mapping, Iterable

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
    '''Format things (use in `name:`, etc.). Only handles paths rn.
    
    >>> f('/bin/bash')
    "</bin/bash>"
    
    >>> f('./blah/blah')
    "<./blah/blah>"
    
    >>> f('not_a_path')
    "`not_a_path`"
    
    Relativizes paths if they're under the current directory (on the host
    machine) to help limit output length. But that's trickier to show a 
    Doctest for than I'm up for at the moment.
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
    '''It's just `os.path.join`, man.
    
    >>> join('a', 'b', 'c')
    "a/b/c"
    
    Preferred usage style (Jinja2):
    
    ```yaml
    my_path: "{{ ('a', 'b', 'c') | join }}"
    # ->
    my_path: "a/b/c"
    '''
    return path.join(*frags)

def dig(target, *key_path):
    '''Like Ruby - get the value at a key-path, or `None` if any keys in the
    path are missing.
    
    Will puke if an intermediate key's value is **not** a `dict`.
    '''
    for key in key_path:
        if key in target:
            target = target[key]
        else:
            return None
    return target

def find(itr, predicate):
    for item in itr:
        if predicate(item):
            return item

def mapping_has_all(mapping, **key_values):
    for key, value in key_values.items():
        if key not in mapping or mapping[key] != value:
            return False
    return True

def mapping_has_any(mapping, **key_values):
    for key, value in key_values.items():
        if key in mapping and mapping[key] == value:
            return True
    return False

def iterable_has_all(itr, *items):
    missing = set(items)
    for item in itr:
        if item in missing:
            missing.remove(item)
        if len(missing) == 0:
            return True
    return False

def iterable_has_any(itr, *items):
    for item in itr:
        if item in items:
            return True
    return False

def object_has_all(obj, **attrs):
    for name, value in attrs.items():
        if not hasattr(obj, name) or getattr(obj, name) != value:
            return False
    return True

def has_all(obj, *args, **kwds):
    if isinstance(obj, Mapping):
        return mapping_has_all(obj, *args, **kwds)
    elif isinstance(obj, Iterable):
        return iterable_has_all(obj, *args, **kwds)
    else:
        return object_has_all(obj, *args, **kwds)

def find_has_all(itr, *args, **kwds):
    return find(itr, lambda item: has_all(item, *args, **kwds))

def find_has_any(itr, *args, **kwds):
    return find(itr, lambda item: has_any(item, *args, **kwds))

class FilterModule:
    def filters(self):
        return dict(
            ini_enc_value=ini_enc_value,
            f=f,
            join=join,
            rel=rel,
            # dict_merge is included by Ansible as `combine`.
            # 
            # https://docs.ansible.com/ansible/latest/user_guide/playbooks_filters.html#combining-hashes-dictionaries
            # 
            defaults=dict_defaults,
            dig=dig,
            find_by=find_has_all,
            find_has_all=find_has_all,
            find_has_any=find_has_any,
        )
    