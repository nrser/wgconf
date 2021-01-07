from typing import *

from nansi.utils.collections import csl

TKey        = TypeVar('TKey')
TValue      = TypeVar('TValue')
TAlias      = TypeVar('TAlias')

class AliasError(KeyError):
    pass

def de_aliased(
    aliases: Mapping[TKey, Iterable[TAlias]],
    src: Mapping[Union[TKey, TAlias], TValue]
) -> Dict[TKey, TValue]:
    '''
    Resolve aliases, checking that there are no conflicts.

    Takes a mapping between "destination" keys and their possible "source" key
    aliases, along with a second mapping from key or aliases to values, and
    produces a `dict` of only "destination" keys to values.

    Raises `AliasError` if a conflict or collision is found.

    ### Usage ###

    >>> de_aliased(
    ...     aliases=dict(
    ...         names=["name"],
    ...     ),
    ...     src=dict(
    ...         name="Blah",
    ...         version="1.2.3",
    ...     )
    ... )
    {'names': 'Blah', 'version': '1.2.3'}

    ### Error Detection ###

    1.  Catches aliases that point to other keys:

    >>> de_aliased(
    ...     aliases={
    ...         "x": ["ex"],
    ...         "ex": ["ample"],
    ...     },
    ...     src={
    ...         "name": "Blah",
    ...         "version": "1.2.3",
    ...     }
    ... )
    Traceback (most recent call last):
        ...
    AliasError: "'ex' given as both key and alias of 'x'"

    2.  Catches duplicate aliases across spearate keys:

    >>> de_aliased(
    ...     aliases={
    ...         "x": ["yo"],
    ...         "y": ["yo"],
    ...     },
    ...     src={
    ...         "name": "Blah",
    ...         "version": "1.2.3",
    ...     }
    ... )
    Traceback (most recent call last):
        ...
    AliasError: "'yo' given as alias for both 'x' and 'y'"

    3.  Catches duplicate aliases across spearate keys:

    >>> de_aliased(
    ...     aliases={
    ...         "ex": ["x"],
    ...         "why": ["y"],
    ...     },
    ...     src={
    ...         "x": 1,
    ...         "y": 2,
    ...         "ex": 3,
    ...     }
    ... )
    Traceback (most recent call last):
        ...
    AliasError: "`src` keys 'ex', 'x' all resolve to 'ex'"
    '''
    dest = {}
    table = {}
    for key, alts in aliases.items():
        if key in table:
            raise AliasError(
                f"{repr(key)} given as both key and alias of {repr(table[key])}"
            )
        table[key] = key
        for alt in alts:
            if alt in table:
                raise AliasError(
                    f"{repr(alt)} given as alias for both {repr(table[alt])} "
                    f"and {repr(key)}"
                )
            table[alt] = key
    for src_key, value in src.items():
        if src_key in table:
            dest_key = table[src_key]
            if dest_key in dest:
                dups = (k for k in (dest_key, *aliases[dest_key]) if k in src)
                raise AliasError(
                    f"`src` keys {csl(dups)} all resolve to {repr(dest_key)}"
                )
            dest[dest_key] = value
        else:
            dest[src_key] = value
    return dest

if __name__ == '__main__':
    import doctest
    doctest.testmod()
