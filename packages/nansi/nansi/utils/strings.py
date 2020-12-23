import urllib.parse

from nansi.utils.collections import flat_map, iter_flat


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


if __name__ == "__main__":
    import doctest

    doctest.testmod()
