from typing import *
from pathlib import Path
import re
import os
import itertools

K = TypeVar('K')
T = TypeVar('T')
V = TypeVar('V')

TItem       = TypeVar('TItem')
TNotFound   = TypeVar('TNotFound')
TResult     = TypeVar('TResult')
TKey        = TypeVar('TKey')
TValue      = TypeVar('TValue')

Nope = NewType('Nope', Union[None, Literal[False]])

class NotFoundError(Exception):
    pass

def is_nope(x: Any) -> bool:
    '''
    >>> is_nope(None)
    True
    
    >>> is_nope(False)
    True
    
    >>> any(is_nope(x) for x in ('', [], {}, 0, 0.0))
    False
    '''
    return x is None or x is False

def find(
    predicate: Callable[[TItem], Any],
    itr: Iterator[TItem],
    not_found: TNotFound=None
) -> Union[T, TNotFound]:
    '''Return the first item in an iterator `itr` for which `predicate`
    returns anything other than `False` or `None`.
    
    >>> find(lambda x: x % 2 == 0, (1, 2, 3, 4))
    2
    
    If `predicate` returns `False` or `None` for **all** items in `itr` then
    `not_found` is returned, which defaults to `None`.
    
    >>> find(lambda p: Path(p).exists(), ('./a/b', './c/d'), '/dev/null')
    '/dev/null'
    
    Notes that this diverges from Python's "truthy" behavior, where things like
    empty lists and the number zero are "false". That (obviously) got in the way
    of finding objects like those. I think this approach is a lot more clear,
    if a bit more work to explain.
    
    Allows this to work, for example:
    
    >>> find(lambda lst: len(lst) == 0, ([1, 2], [], [3, 4, 5]))
    []
    '''
    for item in itr:
        if not is_nope(predicate(item)):
            return item
    return not_found

def need(
    predicate: Callable[[TItem], Any],
    itr: Iterator[TItem],
) -> TItem:
    '''
    Like `find()`, but raises `NotFoundError` if `predicate` returns `False` or
    `None` for every item in `itr`.
    
    >>> need(lambda x: x > 2, [1, 2, 3])
    3
    
    >>> need(lambda x: x > 5, [1, 2, 3])
    Traceback (most recent call last):
        ...
    NotFoundError: Not found
    
    `need()` _can_ return `None`, if that's the value of the iterator entry it
    matched:
    
    >>> need(lambda x: x is None, [1, None, 2]) is None
    True
    '''
    # find() can return None when the item was found if the item it matched was
    # None, so need to repeat logic here.
    for item in itr:
        if not is_nope(predicate(item)):
            return item
    raise NotFoundError("Not found")

def find_map(
    fn: Callable[[TItem], Union[TResult, Nope]],
    itr: Iterator[TItem],
    not_found: TNotFound=None,
) -> Union[TResult, TNotFound]:
    '''
    Like `find()`, but returns first value returned by `predicate` that is not
    `False` or `None`.
    
    >>> find_map(
    ...     lambda dct: dct.get('z'),        
    ...     ({'x': 1}, {'y': 2}, {'z': 3}),
    ... )
    3
    '''
    for item in itr:
        result = fn(item)
        if not is_nope(result):
            return result
    return not_found
    
def need_map(
    fn: Callable[[TItem], Union[TResult, Nope]],
    itr: Iterator[TItem],
) -> TResult:
    # find_map() never returns None unless it's not found
    result = find_map(fn, itr)
    if result is not None:
        raise NotFoundError("Not found")
    return result

def find_is_a(
    cls: Type[T],
    itr: Iterator[Any],
    not_found: TNotFound=None,
) -> Union[T, TNotFound]:
    '''
    >>> find_is_a(str, (1, 2, 'three', 4))
    'three'
    '''
    return find(lambda x: isinstance(x, cls), itr, not_found)

def first(itr: Iterable[T]) -> Optional[T]:
    '''
    >>> first([1, 2, 3])
    1
    
    >>> first([]) is None
    True
    
    >>> def naturals():
    ...     i = 1
    ...     while True:
    ...         yield i
    ...         i += 1
    >>> first(naturals())
    1
    '''
    return next(iter(itr), None)

def last(itr: Iterable[T]) -> Optional[T]:
    '''
    Get the last item in an iterator `itr`, or `None` if it's empty.
    
    **WARNING** If `itr` goes on forever, so will this function.
    
    >>> last([1, 2, 3])
    3
    
    >>> last([]) is None
    True
    
    >>> last(range(1, 100))
    99
    '''
    if isinstance(itr, Sequence):
        itr_len = len(itr)
        if itr_len == 0:
            return None
        return itr[len(itr) - 1]
    last_item = None
    for item in itr:
        last_item = item
    return last_item

def pick(map: Mapping[K, V], keys: Container[K]) -> Dict[K, V]:
    return {key: value for key, value in map.items() if key in keys}

def dig(target: Union[Sequence, Mapping], *key_path: Sequence):
    '''Like Ruby - get the value at a key-path, or `None` if any keys in the
    path are missing.
    
    Will puke if an intermediate key's value is **not** a `dict`.
    
    >>> d = {'A': {'B': 'V'}}
    >>> dig(d, 'A', 'B')
    'V'
    >>> dig(d, 'A', 'C') is None
    True
    
    >>> dig(['a', 'b'], 0)
    'a'
    
    >>> mixed = {'a': [{'x': 1}, {'y': [2, 3]}], 'b': {'c': [4, 5]}}
    >>> dig(mixed, 'a', 0, 'x')
    1
    >>> dig(mixed, 'a', 1, 'y', 0)
    2
    >>> dig(mixed, 'a', 1, 'y', 1)
    3
    >>> dig(mixed, 'b', 'c', 0)
    4
    >>> dig(mixed, 'b', 'c', 1)
    5
    '''
    
    for key in key_path:
        if isinstance(target, Sequence):
            if isinstance(key, int) and key >= 0 and key < len(target):
                target = target[key]
            else:
                return None
        elif key in target:
            target = target[key]
        else:
            return None
    return target

def iter_flat(itr: Iterable, skip=(str, bytes)):
    for entry in itr:
        if (not isinstance(entry, Iterable)) or isinstance(entry, skip):
            yield entry
        else:
            yield from iter_flat(entry)

def flatten(itr: Iterable, skip=(str, bytes), into=tuple):
    '''
    >>> flatten(['abc', '123'])
    ('abc', '123')
    
    >>> flatten(['abc', ['123', 'ddd']])
    ('abc', '123', 'ddd')
    
    >>> flatten([1, [2, [3, [4, [5]]]]], into=list)
    [1, 2, 3, 4, 5]
    
    >>> flatten([{'a': 1, 'b': 2}, 'c', 3])
    ('a', 'b', 'c', 3)
    '''
    return into(iter_flat(itr, skip))

def filtered(fn, itr):
    return list(filter(fn, itr))

def smells_like_namedtuple(obj):
    # NOTE  `namedtuple` is nasty under there. Zen for thee, meta-spaghetti for
    #       me..?
    return (
        isinstance(obj, tuple)
        and hasattr(type(obj), '_fields')
    )

if __name__ == '__main__':
    import doctest
    doctest.testmod()
    