from typing import *

import nansi.os_resolve

class FilterModule:
    def filters(self):
        return dict(
            os_map_resolve = nansi.os_resolve.os_map_resolve,
        )

if __name__ == '__main__':
    import doctest
    from nansi.utils.doctesting import template_for_filters
    template = template_for_filters(FilterModule)
    doctest.testmod()
