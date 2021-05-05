from urllib.parse import urlparse
import re

def repo_pathspace(origin_url: str) -> str:
    '''
    >>> repo_pathspace("https://github.com/nrser/ansible-roles.git")
    'github.com/nrser/ansible-roles'
    '''
    parse = urlparse(origin_url)
    if parse.scheme != 'https' and parse.scheme != 'http':
        raise ValueError(
            "Sorry, repo_pathspace() only handles http(s) urls, " +
            f"given {repr(origin_url)} (scheme={repr(parse.scheme)})"
        )
    return parse.hostname + re.sub(r'\.git$', '', parse.path)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
