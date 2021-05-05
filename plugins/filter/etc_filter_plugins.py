# Assorted filters that I haven't thought made sense to have their own home yet.

from typing import *

import nansi.support.git

def ini_enc_value(value):
    """Encode `value` for use in the `ini_file` module's `value:` parameter.
    """
    if value is True:
        return 'yes'
    elif value is False:
        return 'no'
    else:
        return value

class FilterModule:
    def filters(self):
        return dict(
            ini_enc_value   = ini_enc_value,
            repo_pathspace  = nansi.support.git.repo_pathspace,
        )

if __name__ == '__main__':
    import doctest
    from nansi.utils.doctesting import template_for_filters
    template = template_for_filters(FilterModule)
    doctest.testmod()
