from typing import *

from nansi.utils.strings import connect

def to_url(args,  allow_fragments=True) -> str:
    '''It's just `urllib.parse.urljoin()`. Don't use `join()`, it gets weird if
    any segments start with a `/`.

    >>> to_url(('http://example.com', '/a/b/c'))
    'http://example.com/a/b/c'

    Preferred usage style (Jinja2):

    >>> template("{{ ('http://example.com', '/a/b/c') | to_url }}")
    'http://example.com/a/b/c'

    >>> to_url(('https://some.example.com', 'projects', 'blah.tar.gz'))
    'https://some.example.com/projects/blah.tar.gz'

    >>> template("""{{
    ...     ('https://some.example.com', '/projects/', '/blah.tar.gz')
    ...     | to_url
    ... }}""")
    'https://some.example.com/projects/blah.tar.gz'

    '''
    # return url_join(*args, allow_fragments=allow_fragments)
    return connect(*args)

class FilterModule:
    def filters(self):
        return dict(
            to_url          = to_url,
              urljoin       = to_url,   # I hate these smush-case names
        )

from nansi.utils import doctesting
doctesting.testmod(__name__)
