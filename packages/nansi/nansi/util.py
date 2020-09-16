from typing import *
from pathlib import Path
import re
import os
import itertools

K = TypeVar('K')
T = TypeVar('T')
V = TypeVar('V')

No = NewType('UserId', Union[None, Literal[False]])

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

def find(itr: Iterator[T], predicate: Callable[[T], No]) -> Optional[T]:
    '''
    >>> find([1, None, 2], lambda x: x is None) is None
    True
    '''
    for item in itr:
        if not is_no(predicate(item)):
            return item
    return None

def need(itr: Iterator[T], predicate: Callable[[T], No]) -> T:
    '''
    >>> need([1, 2, 3], lambda x: x > 2)
    3
    
    >>> need([1, 2, 3], lambda x: x > 5)
    Traceback (most recent call last):
        ...
    NotFoundError: Not found
    
    `need()` _can_ return `None`, if that's the value of the iterator entry it
    matched:
    
    >>> need([1, None, 2], lambda x: x is None) is None
    True
    '''
    
    # find() can return None when the item was found if the item it matched was
    # None, so need to repeat logic here.
    for item in itr:
        if not is_no(predicate(item)):
            return item
    raise NotFoundError("Not found")

def find_map(itr: Iterator[T], fn: Callable[[T], Union[V, No]]) -> Optional[V]:
    for item in itr:
        if not is_no((result := fn(item))):
            return result
    return None
    
def need_map(itr: Iterator[T], fn: Callable[[T], Union[V, No]]) -> Optional[V]:
    # find_map() never returns None unless it's not found
    if (result := find_map(itr, fn)) is not None:
        return result
    raise NotFoundError("Not found")

def find_is_a(itr: Iterator[Any], cls: Type[T]) -> Optional[T]:
    for item in itr:
        if isinstance(item, cls):
            return item

def first(iterable: Iterable[T]) -> Optional[T]:
    return next(iter(iterable), None)

def last(itr: Iterable[T]) -> Optional[T]:
    if isinstance(itr, Sequence):
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
