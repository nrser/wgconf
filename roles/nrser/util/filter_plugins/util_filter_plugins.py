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
import urllib.parse

import os
import sys
LIB_DIR = os.path.realpath(
    os.path.join(
        os.path.dirname(__file__),
        '..', '..', '..', '..', 'lib'
    )
)
sys.path.insert(0, LIB_DIR)

from nansi.os_resolve import os_map_resolve
from nansi.git_util import repo_pathspace

def splat(f):
    return lambda seq: f(*seq)

def dictsplat(f):
    return lambda dct: f(**dct)

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
    '</bin/bash>'
    
    >>> f('./blah/blah')
    '<./blah/blah>'
    
    >>> f('not_a_path')
    '`not_a_path`'
    
    Relativizes paths if they're under the current directory (on the host
    machine) to help limit output length. But that's trickier to show a 
    Doctest for than I'm up for at the moment.
    '''
    if s.startswith('/') or s.startswith('./'):
        return f"<{rel(s)}>"
    return f"`{s}`"

def rel(path: str, to: Optional[str] = None) -> str:
    '''Relativize a path if it's a child, otherwise just return as-is.
    
    >>> rel(f"{Path.cwd()}/a/b/c")
    './a/b/c'
    
    >>> rel('/usr/bin')
    '/usr/bin'
    '''
    if to is None:
        to = Path.cwd()
    try:
        if rel := Path(path).relative_to(to):
            return f"./{rel}"
    except:
        pass
    return path

def path_join(frags) -> str:
    '''It's just `os.path.join`, man.
    
    >>> join(('a', 'b', 'c'))
    'a/b/c'
    
    Preferred usage style (Jinja2):
    
    ```yaml
    my_path: "{{ ('a', 'b', 'c') | path }}"
    # ->
    my_path: "a/b/c"
    '''
    return path.join(*frags)
    
def urljoin(frags) -> str:
    '''It's just `urllib.parse.urljoin()`. Don't use `join()`, it gets weird if
    any segments start with a `/`.
    
    >>> urljoin(('http://example.com', '/a/b/c'))
    'http://example.com/a/b/c'
    
    Preferred usage style (Jinja2):
    
    ```yaml
    my_path: "{{ ('http://example.com', '/a/b/c') | urljoin }}"
    # ->
    my_path: "http://example.com/a/b/c"
    '''
    return urllib.parse.urljoin(*frags)

def dig(target, *key_path):
    '''Like Ruby - get the value at a key-path, or `None` if any keys in the
    path are missing.
    
    Will puke if an intermediate key's value is **not** a `dict`.
    
    >>> d = {'A': {'B': 'V'}}
    >>> dig(d, 'A', 'B')
    'V'
    >>> dig(d, 'A', 'C') is None
    True
    '''
    for key in key_path:
        if key in target:
            target = target[key]
        else:
            return None
    return target

def find(itr, predicate):
    '''Like Ruby - find the first entry where `predicate` returns truthy.
    
    >>> find((1, 2, 3, 4), lambda x: x % 2 == 0)
    2
    
    Returns `None` if, well... none is found.
    
    >>> find((1, 2, 3, 4), lambda x: False) is None
    True
    '''
    for item in itr:
        if predicate(item):
            return item

def mapping_has_all(mapping, **key_values):
    '''Test if a `Mapping` has all key/value pairs in `key_values` (by
    equality).
    
    Or: is `key_values` a "sub-mapping" of `mapping` (as sets of key/value
    pairs)?
    
    >>> dct = {'A': 1, 'B': 2, 'C': 3}
    >>> mapping_has_all(dct, A=1, B=2)
    True
    >>> mapping_has_all(dct, A=1, B=1)
    False
    >>> mapping_has_all(dct, A=1, D=4)
    False
    '''
    for key, value in key_values.items():
        if key not in mapping or mapping[key] != value:
            return False
    return True

def mapping_has_any(mapping, **key_values):
    '''Test if a `Mapping` has any key/value pairs in `key_values` (by 
    equality).
    
    Or: does `key_values` intersect `mapping` (as sets of key/value pairs)?
    
    >>> dct = {'A': 1, 'B': 2, 'C': 3}
    >>> mapping_has_all(dct, A=1, B=2)
    True
    >>> mapping_has_all(dct, A=1, B=1)
    False
    >>> mapping_has_all(dct, A=1, D=4)
    False
    '''
    for key, value in key_values.items():
        if key in mapping and mapping[key] == value:
            return True
    return False

def iterable_has_all(itr, *items):
    '''Test if an interable includes all of `items` (by equality).
    
    >>> iterable_has_all((1, 2, 3), 1, 3)
    True
    >>> iterable_has_all((1, 2, 3), 1, 4)
    False
    '''
    missing = set(items)
    for item in itr:
        if item in missing:
            missing.remove(item)
        if len(missing) == 0:
            return True
    return False

def iterable_has_any(itr, *items):
    '''Test if an interable includes all of `items` (by equality).
    
    >>> iterable_has_any((1, 2, 3), 1, 3)
    True
    >>> iterable_has_any((1, 2, 3), 1, 4)
    True
    '''
    for item in itr:
        if item in items:
            return True
    return False

def object_has_all(obj, **attrs):
    '''Test if an object has all of `attrs` name/value pairs (by equality).
    
    >>> object_has_all(Path('/a/b/c.txt'), name='c.txt', suffix='.txt')
    True
    >>> object_has_all(Path('/a/b/c.txt'), name='c.txt', age=112)
    False
    '''
    for name, value in attrs.items():
        if not hasattr(obj, name) or getattr(obj, name) != value:
            return False
    return True

def object_has_any(obj, **attrs):
    '''Test if an object has any of `attrs` name/value pairs (by equality).
    
    >>> object_has_any(Path('/a/b/c.txt'), name='c.txt', suffix='.txt')
    True
    >>> object_has_any(Path('/a/b/c.txt'), name='c.txt', age=112)
    True
    '''
    for name, value in attrs.items():
        if hasattr(obj, name) and getattr(obj, name) == value:
            return True
    return False

def has_all(obj, *args, **kwds):
    '''Routes: 
    
    1.  `collections.abc.Mapping`   -> `mapping_has_all()`
    2.  `collections.abc.Iterable`  -> `iterable_has_all()`
    3.  else                        -> `object_has_all()`
    
    Returns a boolean in all cases.
    '''
    if isinstance(obj, Mapping):
        return mapping_has_all(obj, *args, **kwds)
    elif isinstance(obj, Iterable):
        return iterable_has_all(obj, *args, **kwds)
    else:
        return object_has_all(obj, *args, **kwds)

def has_any(obj, *args, **kwds):
    '''Routes: 
    
    1.  `collections.abc.Mapping`   -> `mapping_has_any()`
    2.  `collections.abc.Iterable`  -> `iterable_has_any()`
    3.  else                        -> `object_has_any()`
    
    Returns a boolean in all cases.
    '''
    if isinstance(obj, Mapping):
        return mapping_has_any(obj, *args, **kwds)
    elif isinstance(obj, Iterable):
        return iterable_has_any(obj, *args, **kwds)
    else:
        return object_has_any(obj, *args, **kwds)

def find_has_all(itr, *args, **kwds):
    '''Find first item in `itr` that passes `has_all(item, *args, **kwds)`.
    
    >>> animals = (
    ...     {'name': 'Hudie', 'type': 'cat', 'cute': True},
    ...     {'name': 'Mr. Sloth', 'type': 'sloth', 'cute': True},
    ... )
    
    >>> find_has_all(animals, name='Hudie', cute=True)
    {'name': 'Hudie', 'type': 'cat', 'cute': True}
    
    >>> find_has_all(animals, name='Mr. Sloth', type='small bear') is None
    True
    '''
    return find(itr, lambda item: has_all(item, *args, **kwds))

def find_has_any(itr, *args, **kwds):
    '''Find first item in `itr` that passes `has_any(item, *args, **kwds)`.
    
    >>> animals = (
    ...     {'name': 'Hudie', 'type': 'cat', 'cute': True},
    ...     {'name': 'Mr. Sloth', 'type': 'sloth', 'cute': True},
    ... )
    
    >>> find_has_any(animals, name='Hudie', cute=True)
    {'name': 'Hudie', 'type': 'cat', 'cute': True}
    
    >>> find_has_any(animals, name='Mr. Sloth', type='small bear')
    {'name': 'Mr. Sloth', 'type': 'sloth', 'cute': True}
    '''
    return find(itr, lambda item: has_any(item, *args, **kwds))

class FilterModule:
    def filters(self):
        return dict(
            ini_enc_value=ini_enc_value,
            f=f,
            path=path_join,
            urljoin=urljoin,
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
            os_map_resolve=os_map_resolve,
            repo_pathspace=repo_pathspace,
        )


if __name__ == '__main__':
    import doctest
    doctest.testmod()
