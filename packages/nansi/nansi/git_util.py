from urllib.parse import urlparse, urljoin
import re

def repo_pathspace(origin_url: str) -> str:
    '''
    >>> repo_pathspace("https://github.com/nrser/ansible-roles.git")
    'github.com/nrser/ansible-roles'
    '''
    parse = urlparse(origin_url)
    if parse.scheme != 'https' and parse.scheme != 'http':
        raise ValueError(
            "Sorry, repo_rel_path() only handles http(s) urls, " +
            f"given {repr(origin_url)} (scheme={repr(parse.scheme)})"
        )
    return parse.hostname + re.sub(r'\.git$', '', parse.path)
