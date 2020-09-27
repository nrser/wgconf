from pathlib import Path
from os import path
from typing import *

import nansi.utils.path

def to_path(frags) -> str:
    '''It's just `os.path.join`, man.
    
    >>> to_path(('a', 'b', 'c'))
    'a/b/c'
    
    Preferred usage style (Jinja2):
    
    >>> template("{{ ('a', 'b', 'c') | to_path }}")
    'a/b/c'
    '''
    return path.join(*frags)

class FilterModule:
    def filters(self):
        return dict(
            to_path         = to_path,
              path          = to_path,  # Old name
            rel             = nansi.utils.path.rel,
        )

if __name__ == '__main__':
    import doctest
    from nansi.utils.doctesting import template_for_filters
    template = template_for_filters(FilterModule)
    doctest.testmod()
