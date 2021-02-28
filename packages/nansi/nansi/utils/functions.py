from typing import *
from inspect import signature, Parameter


def named_arity(fn: Callable) -> int:
    """
    >>> named_arity(lambda x: x)
    1

    >>> def f1(a, b, *, c=3):
    ...     pass
    >>> named_arity(f1)
    2

    >>> def f2(a, b, *args, c=3):
    ...     pass
    >>> named_arity(f2)
    2

    >>> def f3(a, b=2, *args, c=3):
    ...     pass
    >>> named_arity(f3)
    2

    >>> def f4(a, b, c=3):
    ...     pass
    >>> named_arity(f4)
    3

    >>> def f5(*args, **kwds):
    ...     pass
    >>> named_arity(f5)
    0

    >>> class C1:
    ...     @staticmethod
    ...     def f(a, b, c=3):
    ...         pass
    ...
    ...     @classmethod
    ...     def g(cls):
    ...         pass
    ...
    ...     def __init__(self, a, b):
    ...         pass
    ...
    >>> named_arity(C1.f)
    3
    >>> named_arity(C1.g)
    0
    >>> named_arity(C1)
    2

    >>> named_arity(dict)
    0

    >>> get_x = methodcaller("__getitem__", "x")
    >>> get_x({"x": "ex"})
    'ex'
    >>> named_arity(get_x)
    1
    """
    if isinstance(fn, type):
        return named_arity(fn.__init__) - 1

    try:
        sig = signature(fn)
    except ValueError:
        sig = signature(fn.__call__)

    return sum(
        (
            1
            for name, param in sig.parameters.items()
            if param.kind is Parameter.POSITIONAL_ONLY
            or param.kind is Parameter.POSITIONAL_OR_KEYWORD
        )
    )

def get_fn(receiver, name):
    fn = getattr(receiver, name)
    if not callable(fn):
        raise TypeError(
            f"Expected {receiver}.{name} to be function, found "
            f"{type(fn)}: {fn}"
        )
    return fn

if __name__ == "__main__":
    import doctest
    from operator import methodcaller # pylint: disable=unused-import

    doctest.testmod()
