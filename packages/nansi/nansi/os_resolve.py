from typing import *
import re
import os
import logging

from nansi.util import dig, flatten

TAnsibleFacts = Mapping[str, Any]

LOG = log = logging.getLogger(__name__)

RESOLVE_FACT_KEYS = dict(
    distribution    = 'distribution',
    version         = 'distribution_version',
    release         = 'distribution_release',
    family          = 'os_family',
    system          = 'system',
    kernel          = 'kernel',
)

RESOLVE_ORDER = (
    ('distribution', 'version'),
    ('distribution', 'release'),
    ('distribution',),
    ('family',),
    ('system', 'kernel'),
    ('system',),
)

'''Simple Regexp that matches 1 to 4 sequences of digits, `.`-separated, at the
begining of a string. So it wont match just a leading sequence of digits, and it
will match `'1.2.3.4.5.6'` as `'1.2.3.4'`, in order to limit things reasonably.

Does not deal with pre-release versions or any of that other stuff no one can
really seem to agree upon (check out how much SemVer parsers vary regarding
corner cases across implementations for a fun time).
'''
VERSION_RE = re.compile(r'^\d+(?:\.\d+){1,3}')

class OSResolveError(RuntimeError):
    def __init__(self, message, tried):
        super().__init__(message)
        self.message = message
        self.tried = tried

def is_debug(log=LOG):
    return log.isEnabledFor(logging.DEBUG)

def split_version(version_str: str) -> Optional[List[str]]:
    match = VERSION_RE.search(version_str)
    
    if match is None:
        return None
    
    return match.group(0).split('.')   

def get_fact(
    ansible_facts: TAnsibleFacts,
    name: str,
    lower: bool = True,
) -> str:
    key = RESOLVE_FACT_KEYS[name]
    if key not in ansible_facts:
        raise KeyError(
            f"Required `ansible_facts` key `{key}` is " +
            "missing. Maybe `gather_facts` is subsetted?"
        )
    fact = ansible_facts[key]
    if not isinstance(fact, str):
        raise TypeError(
            f"Expected ansible_facts.{key} to be str, found a {type(fact)}: " +
            str(fact)
        )
    if lower:
        return fact.lower()
    return fact

def print_facts(
    ansible_facts: TAnsibleFacts,
    lower: bool = True,
    printer = log.debug,
) -> None:
    printer("Resolution facts:")
    
    for name, key in RESOLVE_FACT_KEYS.items():
        printer(
            f"  {name}".ljust(16) +
            f"= {get_fact(ansible_facts, name, lower=lower)}".ljust(24) +
            f"(ansible_facts.{key})"
        )

def get_segments(
    ansible_facts: TAnsibleFacts,
    lower: bool = True,
) -> List[List[Tuple[str, str]]]:
    if log.isEnabledFor(logging.DEBUG):
        print_facts(ansible_facts, lower=lower)
    
    # Returns a list...
    return [
        # ...of lists...
        [
            # ...of (name, fact) tuples!
            (name, get_fact(ansible_facts, name, lower=lower))
            # where each name comes from a "name list"
            for name in name_list
        # and each name list is an entry in RESOLVE_ORDER
        ] for name_list
        in RESOLVE_ORDER
    ]

def iter_os_key_paths(ansible_facts, fallback='any', lower=True):
    '''Iterate over "key paths" to resolve relative to Ansible os facts,
    from most to least specific. Can be used to find files, dictionary values,
    etc.
    
    >>> ansible_facts = dict(
    ...     distribution            = 'Ubuntu',
    ...     distribution_version    = '18.04',
    ...     distribution_release    = 'bionic',
    ...     os_family               = 'Debian',
    ...     system                  = 'Linux',
    ...     kernel                  = '4.15.0-106-generic',
    ... )
    >>> for i in iter_os_key_paths(ansible_facts):
    ...     print(i)
    ('distribution', 'ubuntu', 'version', '18.04')
    ('distribution', 'ubuntu', 'version', '18')
    ('distribution', 'ubuntu', 'release', 'bionic')
    ('distribution', 'ubuntu')
    ('family', 'debian')
    ('system', 'linux', 'kernel', '4.15.0')
    ('system', 'linux', 'kernel', '4.15')
    ('system', 'linux', 'kernel', '4')
    ('system', 'linux')
    ('any',)
    
    MacOS is weird 'cause we get the kernel version as the
    `distribution_release`, but shouldn't be too much of a problem in practice.
    
    >>> ansible_facts = dict(
    ...     distribution            = 'MacOSX',
    ...     distribution_version    = '10.14.6',
    ...     distribution_release    = '18.7.0',
    ...     os_family               = 'Darwin',
    ...     system                  = 'Darwin',
    ...     kernel                  = '18.7.0',
    ... )
    >>> for i in iter_os_key_paths(ansible_facts):
    ...     print(i)
    ('distribution', 'macosx', 'version', '10.14.6')
    ('distribution', 'macosx', 'version', '10.14')
    ('distribution', 'macosx', 'version', '10')
    ('distribution', 'macosx', 'release', '18.7.0')
    ('distribution', 'macosx')
    ('family', 'darwin')
    ('system', 'darwin', 'kernel', '18.7.0')
    ('system', 'darwin', 'kernel', '18.7')
    ('system', 'darwin', 'kernel', '18')
    ('system', 'darwin')
    ('any',)
    '''
    
    for segments in get_segments(ansible_facts, lower=lower):
        last_name, last_value = segments[-1]
        
        if (
            last_name in ('version', 'kernel') and
            (version_segments := split_version(last_value))
        ):
            base_segments = flatten(segments[0:-1])
            
            for end in range(len(version_segments), 0, -1):
                yield (
                    *base_segments,
                    last_name,
                    '.'.join(version_segments[0:end])
                )
        else:
            yield flatten(segments)
    
    if fallback is not None:
        yield (fallback,)

def os_map_resolve(ansible_facts: TAnsibleFacts, map: Mapping):
    '''
    >>> ubuntu_facts = dict(
    ...     distribution            = 'Ubuntu',
    ...     distribution_version    = '18.04',
    ...     distribution_release    = 'bionic',
    ...     os_family               = 'Debian',
    ...     system                  = 'Linux',
    ...     kernel                  = '4.15.0-106-generic',
    ... )
    >>> macos_facts = dict(
    ...     distribution            = 'MacOSX',
    ...     distribution_version    = '10.14.6',
    ...     distribution_release    = '18.7.0',
    ...     os_family               = 'Darwin',
    ...     system                  = 'Darwin',
    ...     kernel                  = '18.7.0',
    ... )
    
    >>> os_map_resolve(ubuntu_facts, {
    ...     'family': {
    ...         'debian': 'resolve Debian',
    ...         'darwin': 'resolve Darwin',
    ...     },
    ... })
    'resolve Debian'
    
    >>> os_map_resolve(macos_facts, {
    ...     'family': {
    ...         'debian': 'resolve Debian',
    ...         'darwin': 'resolve Darwin',
    ...     },
    ... })
    'resolve Darwin'
    
    >>> os_map_resolve(ubuntu_facts, {
    ...     'distribution': {
    ...         'ubuntu': 'resolve Ubuntu (any)',
    ...         'macosx': 'resolve macOS (any)',
    ...     },
    ... })
    'resolve Ubuntu (any)'
    
    >>> os_map_resolve(macos_facts, {
    ...     'distribution': {
    ...         'ubuntu': 'resolve Ubuntu (any)',
    ...         'macosx': 'resolve macOS (any)',
    ...     },
    ... })
    'resolve macOS (any)'
    
    >>> os_map_resolve(ubuntu_facts, {
    ...     'distribution': {
    ...         'ubuntu': {
    ...             'version': {
    ...                 '18.04': 'resolve Ubuntu 18.04',
    ...             },
    ...             'any': 'resolve Ubuntu (any)',
    ...         },
    ...     },
    ... })
    'resolve Ubuntu 18.04'
    
    >>> os_map_resolve(ubuntu_facts, {
    ...     'distribution': {
    ...         'ubuntu': {
    ...             'version': {
    ...                 '16.04': 'resolve Ubuntu 16.04',
    ...             },
    ...             'any': 'resolve Ubuntu (any)',
    ...         },
    ...     },
    ... })
    'resolve Ubuntu (any)'
    '''
    
    tried = []
    
    for key_path in iter_os_key_paths(ansible_facts):
        if value := dig(map, *key_path):
            if isinstance(value, Mapping) and len(key_path) == 2:
                if 'any' in value:
                    return value['any']
                else:
                    tried.append((*key_path, 'any'))
            else:
                return value
        else:
            tried.append(key_path)
        
    raise OSResolveError("Failed to resolve os value from mapping", tried)

def os_file_resolve(ansible_facts, base_dir, exts, lower=True):
    '''Resolve a file using Ansible os facts, starting at a base directory.
    
    Useful (and used!) for resolving tasks, templates... whatever.
    
    - `ansible_facts: Mapping` - Ansible's facts mapping.
    - `base_dir: str` - Directory to start from.
    - `exts: Sequence[str]` - Extensions to check (in order). 
    
    >>> ubuntu_facts = dict(
    ...     distribution            = 'Ubuntu',
    ...     distribution_version    = '18.04',
    ...     distribution_release    = 'bionic',
    ...     os_family               = 'Debian',
    ...     system                  = 'Linux',
    ...     kernel                  = '4.15.0-106-generic',
    ... )
    >>> macos_facts = dict(
    ...     distribution            = 'MacOSX',
    ...     distribution_version    = '10.14.6',
    ...     distribution_release    = '18.7.0',
    ...     os_family               = 'Darwin',
    ...     system                  = 'Darwin',
    ...     kernel                  = '18.7.0',
    ... )
    
    >>> handle, base_dir, rel = temp_paths(
    ...     'distribution/ubuntu/version/18.04.yaml',
    ...     'distribution/ubuntu.json',
    ...     'family/debian.yaml',
    ...     'family/darwin.json',
    ...     'any.yaml',
    ... )
    
    >>> rel( os_file_resolve(ubuntu_facts, base_dir, ['yaml', 'json']) )
    'distribution/ubuntu/version/18.04.yaml'
    
    >>> rel( os_file_resolve(macos_facts, base_dir, ['yaml', 'json']) )
    'family/darwin.json'
    
    >>> rel(
    ...     os_file_resolve(
    ...         {   **ubuntu_facts,
    ...             'distribution_version': '16.04',
    ...             'distribution_release': 'xenial' },
    ...         base_dir,
    ...         ['yaml', 'json']
    ...     )
    ... )
    'distribution/ubuntu.json'
    
    >>> rel(
    ...     os_file_resolve(
    ...         {   **ubuntu_facts,
    ...             'distribution_version': '16.04',
    ...             'distribution_release': 'xenial' },
    ...         base_dir,
    ...         ['yaml']
    ...     )
    ... )
    'family/debian.yaml'
    
    >>> handle.cleanup()
    '''
    if is_debug():
        log.debug(f"START {__name__}.os_file_resolve()")
        log.debug(f"  @see {__file__}")
        
        log.debug("Base directory:")
        log.debug(f"  {base_dir}")
    
    tried = []
    exts_glob_str = '{' + ','.join(exts) + '}'
    
    for key_path in iter_os_key_paths(ansible_facts, lower=lower):
        bare_rel_path = os.path.join(*key_path)
        
        for ext in exts:
            rel_path = f"{bare_rel_path}.{ext}"
            path = os.path.join(base_dir, rel_path)
            
            if os.path.exists(path):
                if os.path.isfile(path):
                    if is_debug():
                        log.debug('*' * 78)
                        log.debug(f"FOUND:     {rel_path}")
                        log.debug('*' * 78)
                        log.debug(
                            f"DONE {__name__}.os_file_resolve(), returning:"
                        )
                        log.debug(f"  {path}")
                    return path
                log.warn(f"Path exists but is not a file: {path}")
        
        rel_glob = f"{bare_rel_path}.{exts_glob_str}"
        tried.append(rel_glob)
        
        log.debug(f"Not found: {rel_glob}")
        
    raise OSResolveError(
        f"Failed to resolve os file starting from {base_dir}",
        tried
    )

if __name__ == '__main__':
    import doctest
    from nansi.utils.doctesting import temp_paths
    doctest.testmod()
