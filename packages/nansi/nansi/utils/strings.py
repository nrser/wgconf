from nansi.utils.collections import flat_map

def connect(*parts, seperator: str = "/") -> str:
    '''
    >>> connect(
    ...     ('/etc', 'dir'),
    ...     'sir',
    ...     ('/projects', 'objects/'),
    ...     'file.ext',
    ... )
    '/etc/dir/sir/projects/objects/file.ext'
    '''
    return seperator.join((
        part for
        index, part in
        enumerate(flat_map(lambda part: str(part).split(seperator), parts))
        if len(part) > 0 or index == 0
    ))
    
if __name__ == '__main__':
    import doctest
    doctest.testmod()  
    