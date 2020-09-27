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

No = NewType('No', Union[None, Literal[False]])

class NotFoundError(RuntimeError):
    pass

def is_no(x: Any) -> bool:
    '''
    >>> is_no(None)
    True
    
    >>> is_no(False)
    True
    
    >>> any(is_no(x) for x in ('', [], {}, 0, 0.0))
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
        if not is_no(predicate(item)):
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
        if not is_no(predicate(item)):
            return item
    raise NotFoundError("Not found")

def find_map(
    fn: Callable[[TItem], Union[TResult, No]],
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
        if not is_no(result):
            return result
    return not_found
    
def need_map(
    fn: Callable[[TItem], Union[TResult, No]],
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

def join_lines(lines: Iterable[str]) -> str:
    return ''.join((f"{line}\n" for line in lines))

def dig(target: Mapping, *key_path: Sequence):
    '''Like Ruby - get the value at a key-path, or `None` if any keys in the
    path are missing.
    
    Will puke if an intermediate key's value is **not** a `dict`.
    
    >>> d = {'A': {'B': 'V'}}
    >>> dig(d, 'A', 'B')
    'V'
    >>> dig(d, 'A', 'C') is None
    True
    '''
    
    for key in key_path:
        if key in target:
            target = target[key]
        else:
            return None
    return target

def flatten(seq):
    return tuple(itertools.chain(*seq))


if __name__ == '__main__':
    import doctest
    doctest.testmod()
    