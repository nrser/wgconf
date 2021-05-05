from typing import *

from nansi.utils.collections import iter_flat


def connect(*parts, seperator: str = "/") -> str:
    """
    A generalized version of `os.path.join` that handles nested lists.

    >>> connect(
    ...     ('/etc', 'dir'),
    ...     'sir',
    ...     ('/projects', 'objects/'),
    ...     'file.ext',
    ... )
    '/etc/dir/sir/projects/objects/file.ext'

    >>> connect(
    ...     ('/etc/', '/dir'),
    ...     'sir',
    ...     ('/projects', 'objects/'),
    ...     'file.ext',
    ... )
    '/etc/dir/sir/projects/objects/file.ext'

    >>> connect('http://example.com', 'c')
    'http://example.com/c'

    >>> connect('a', '//', 'c')
    'a/c'

    >>> connect('/', 'a', 'b', 'c')
    '/a/b/c'
    """
    return seperator.join(
        (
            part
            for index, part in (
                (
                    index,
                    (
                        part.rstrip(seperator)
                        if index == 0
                        else part.strip(seperator)
                    ),
                )
                for index, part in enumerate(iter_flat(parts))
            )
            if index == 0 or part != ""
        )
    )


def coord(
    seq: Sequence,
    conjunction: str="and",
    *,
    to_s: Callable[[Any], str] = str,
    sep: str = ",",
) -> str:
    """\
    Examples:

    1.  Empty list

        >>> coord([])
        '[empty]'

    2.  List with a single item

        >>> coord([1])
        '1'

    3.  List with two items

        >>> coord([1, 2])
        '1 and 2'

    4.  List with more than two items

        >>> coord([1, 2, 3])
        '1, 2 and 3'

    5.  Defaults to `repr` to cast to string

        >>> coord(['a', 'b', 'c'], to_s=repr)
        "'a', 'b' and 'c'"

    6.  Providing an alternative cast function

        >>> coord(['a', 'b', 'c'], to_s=lambda x: f"`{x}`")
        '`a`, `b` and `c`'
    """
    length = len(seq)
    if length == 0:
        return "[empty]"
    if length == 1:
        return to_s(seq[0])
    return f" {conjunction} ".join(
        (f"{sep} ".join(map(to_s, seq[0:-1])), to_s(seq[-1]))
    )

if __name__ == "__main__":
    import doctest

    doctest.testmod()
