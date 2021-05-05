from typing import *
from collections import abc

K = TypeVar('K')
T = TypeVar('T')
V = TypeVar('V')

TItem       = TypeVar('TItem')
TNotFound   = TypeVar('TNotFound')
TResult     = TypeVar('TResult')
TKey        = TypeVar('TKey')
TValue      = TypeVar('TValue')
TAlias      = TypeVar('TAlias')

Nope        = Union[None, Literal[False]]
Diggable    = Union[Sequence, Mapping]

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
    if isinstance(itr, abc.Sequence):
        itr_len = len(itr)
        if itr_len == 0:
            return None
        return itr[len(itr) - 1]
    last_item = None
    for item in itr:
        last_item = item
    return last_item

def pick(mapping: Mapping[K, V], keys: Container[K]) -> Dict[K, V]:
    return {key: value for key, value in mapping.items() if key in keys}

def omit(mapping: Mapping[K, V], keys: Container[K]) -> Dict[K, V]:
    return {key: value for key, value in mapping.items() if key not in keys}

def dig(target: Diggable, *key_path: Sequence):
    '''Like Ruby - get the value at a key-path, or `None` if any keys in the
    path are missing.

    Will puke if an intermediate key's value is **not** a `dict`.

    >>> d = {'A': {'B': 'V'}}
    >>> dig(d, 'A', 'B')
    'V'
    >>> dig(d, 'A', 'C') is None
    True
    >>> dig(d)
    {'A': {'B': 'V'}}

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
        if isinstance(target, abc.Sequence):
            if isinstance(key, int) and key >= 0 and key < len(target):
                target = target[key]
            else:
                return None
        elif isinstance(target, abc.Collection) and key in target:
            target = target[key]
        else:
            return None
    return target

def default_bury_create(
    target: Diggable,
    for_key: Sequence,
) -> Union[List, Dict]:
    # return [] if isinstance(for_key, int) else {}
    return {}

def bury(
    root: Diggable,
    key_path: Sequence,
    value: Any,
    *,
    create: Callable[[Diggable, Any], Diggable]=default_bury_create,
):
    """
    >>> bury({}, ["A", 1, "B", 2], "TREASURE")
    {'A': {1: {'B': {2: 'TREASURE'}}}}

    >>> bury({}, ["family", "debian"], "payload")
    {'family': {'debian': 'payload'}}
    """
    target = root
    while len(key_path) > 0:
        key = key_path.pop(0)
        if len(key_path) == 0:
            # Termination case — no more keys!
            target[key] = value
        else:
            # We now _know_ there are more keys on the path...
            if key in target:
                # Easy case — more the target down the path
                target = target[key]
            else:
                # Wonky case — need to create something, which depends on the
                # _next_ key (which — as mentioned above — we know exists)
                #
                target[key] = create(target, key_path[0])
                target = target[key]
    return root

def each(
    types: Union[Type[T], Iterable[Type[T]]],
    x: Union[None, T, Iterable[T]],
) -> Generator[T, None, None]:
    '''
    Iterate over "zero or more" of some type `T`, where:

    1.  An `x` of `None` represents no items (does not yield).
    2.  An `x` that is an instance of `T` represents a single item (yields
        once).
    3.  Anything else is assumed to be an <typing.Iterable> of `T` and yielded
        from. Items are _not_ checked to be instances of `T`.

    ## Examples

    1.  ### Looping over nothing ###

        >>> list(each(str, None))
        []

        >>> list(each(str, []))
        []

    2.  ### Looping over values of an <typing.Iterable> type ###

        <builtins.str> is _iterable_, but since `T=str` it is treated as a
        _value_:

        >>> list(each(str, 'blah'))
        ['blah']

        Since iterating <builtins.str> yields <builtins.str> items, the only way
        to iterate over each character is to provide `Any` as the `types`,
        which falls back to testing if `x` is <typing.Iterable>:

        >>> list(each(Any, 'blah'))
        ['b', 'l', 'a', 'h']

        These should hopefully be what you would expect:

        >>> list(each(str, ['blah', 'blah', 'blah me']))
        ['blah', 'blah', 'blah me']

        >>> list(each(tuple, (1, 2)))
        [(1, 2)]

        >>> list(each(dict, {'name': 'NRSER', 'version': '0.1.0'}))
        [{'name': 'NRSER', 'version': '0.1.0'}]

    3.  Absence of type checking when yielding from an <typing.Iterable>:

        This will work, even through the <typing.Iterable> provided does _not_
        contains elements of type `T` (in violation of the type contract):

        >>> list(each(str, [1, 2, 3]))
        [1, 2, 3]

    4.  Useful with types as well as values:

        >>> list(each(Type, str))
        [<class 'str'>]

        >>> list(each(Type, [str, bytes]))
        [<class 'str'>, <class 'bytes'>]

    '''
    if x is None:
        return
    if types is Any:
        if isinstance(x, Iterable):
            yield from x
        else:
            yield x
    else:
        if isinstance(x, types):
            yield x
        else:
            yield from x

def iter_flat(itr: Iterable, skip=(str, bytes)):
    for entry in itr:
        if (not isinstance(entry, abc.Iterable)) or isinstance(entry, skip):
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
    '''
    >>> filtered(lambda x: x % 2 == 0, range(1, 10))
    [2, 4, 6, 8]
    '''
    return list(filter(fn, itr))

def flat_map(
    fn: Callable[[TItem], TResult],
    itr, # : Iterable[T], Not right, can we even *do* recursive types?!?
    /,
    skip: Tuple[type] = (str, bytes),
) -> Iterable[TResult]:
    for item in iter_flat(itr):
        result = fn(item)
        if isinstance(result, abc.Iterable) and not isinstance(result, skip):
            yield from iter_flat(result)
        else:
            yield result


def smells_like_namedtuple(obj):
    # NOTE  `namedtuple` is nasty under there. Zen for thee, meta-spaghetti for
    #       me..?
    return (
        isinstance(obj, tuple)
        and hasattr(type(obj), '_fields')
    )

def only(collection: Collection[TItem]) -> TItem:
    '''Stupid, but surprisingly useful: you have an iterable that should only
    have one element, and you want that element, or to know if you were wrong
    for some reason.

    >>> only([1])
    1

    >>> only([1, 2])
    Traceback (most recent call last):
        ...
    AssertionError: Excpected collection to have only one element, found [1, 2]
    '''
    assert len(collection) == 1, (
        f"Excpected collection to have only one element, found {collection}"
    )
    return first(collection)

def csl(iterable: Iterable) -> str:
    '''
    Join an iterable into a comma-seperated list, using `repr` to convert
    entries to strings.

    A quick, crude solution used in error messages and such.

    >>> csl([1, 2, 3])
    '1, 2, 3'

    >>> csl(['1', '2', '3'])
    "'1', '2', '3'"
    '''
    return ", ".join(map(repr, iterable))

def map_add(map_1, map_2):
    common_keys = set(map_1).intersection(set(map_2))

    if len(common_keys) != 0:
        raise ValueError(
            f"Can not add maps with common keys; shared keys: {common_keys}"
        )

    return {**map_1, **map_2}

if __name__ == '__main__':
    from pathlib import Path # pylint: disable=unused-import
    import doctest
    doctest.testmod()
