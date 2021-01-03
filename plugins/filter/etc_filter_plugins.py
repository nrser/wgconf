# Assorted filters that I haven't thought made sense to have their own home yet.

from typing import *

from nansi.utils.path import rel
import nansi.utils.git

def ini_enc_value(value):
    """Encode `value` for use in the `ini_file` module's `value:` parameter.
    """
    if value is True:
        return 'yes'
    elif value is False:
        return 'no'
    else:
        return value

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

class FilterModule:
    def filters(self):
        return dict(
            ini_enc_value   = ini_enc_value,
            f               = f,
            repo_pathspace  = nansi.utils.git.repo_pathspace,
        )

if __name__ == '__main__':
    import doctest
    from nansi.utils.doctesting import template_for_filters
    template = template_for_filters(FilterModule)
    doctest.testmod()
