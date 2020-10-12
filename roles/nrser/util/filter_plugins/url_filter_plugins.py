from typing import *
import urllib.parse

from nansi.utils.collections import flatten
    
def to_url(frags) -> str:
    '''It's just `urllib.parse.urljoin()`. Don't use `join()`, it gets weird if
    any segments start with a `/`.
    
    >>> to_url(('http://example.com', '/a/b/c'))
    'http://example.com/a/b/c'
    
    Preferred usage style (Jinja2):
    
    >>> template("{{ ('http://example.com', '/a/b/c') | to_url }}")
    'http://example.com/a/b/c'
    
    '''
    return urllib.parse.urljoin(*flatten(frags))

class FilterModule:
    def filters(self):
        return dict(
            to_url          = to_url,
              urljoin       = to_url,   # I hate these smush-case names
        )

if __name__ == '__main__':
    import doctest
    from nansi.utils.doctesting import template_for_filters
    template = template_for_filters(FilterModule)
    doctest.testmod()
