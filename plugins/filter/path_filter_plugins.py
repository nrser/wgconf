from pathlib import PurePosixPath, PureWindowsPath
import os.path

from nansi.utils import paths
from nansi.utils.collections import flatten
from nansi.os_resolve import os_map_resolve
from nansi.utils import doctesting

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

def is_file(path) -> bool:
    return os.path.isfile(path)

class FilterModule:
    def filters(self):
        return dict(
            to_path         = to_path,
              path          = to_path,  # Old name
            to_win_path     = to_win_path,
            rel             = paths.rel,
            is_file         = is_file,
        )

doctesting.testmod(__name__)
