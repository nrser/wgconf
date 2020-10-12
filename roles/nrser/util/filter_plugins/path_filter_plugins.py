from pathlib import PurePosixPath, PureWindowsPath
from os import path
from typing import *

import nansi.utils.path
from nansi.utils.collections import flatten
from nansi.os_resolve import os_map_resolve

def to_posix_path(path_segments) -> str:
    return str(PurePosixPath(*flatten(path_segments)))

def to_win_path(path_segments) -> str:
    return str(PureWindowsPath(*flatten(path_segments)))

def to_os_path(path_segments, facts) -> str:
    return os_map_resolve(
        facts,
        {
            'family': {
                'windows': to_win_path,
            },
            'any': to_path,
        }
    )(path_segments)

def to_path(path_segments, facts=None) -> str:
    '''It's just `os.path.join`, man.
    
    >>> to_path(('a', 'b', 'c'))
    'a/b/c'
    
    Preferred usage style (Jinja2):
    
    >>> template("{{ ('a', 'b', 'c') | to_path }}")
    'a/b/c'
    '''
    if facts is None:
        return to_posix_path(path_segments)
    return to_os_path(path_segments, facts=facts)

class FilterModule:
    def filters(self):
        return dict(
            to_path         = to_path,
              path          = to_path,  # Old name
            to_win_path     = to_win_path,
            rel             = nansi.utils.path.rel,
        )

if __name__ == '__main__':
    import doctest
    from nansi.utils.doctesting import template_for_filters
    template = template_for_filters(FilterModule)
    doctest.testmod()
