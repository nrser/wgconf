
from typing import Any, Type
from inspect import isclass

from nansi.utils import doctesting
from nansi.utils.strings import coord

def tick(x: Any) -> str:
    return f"`{x}`"

def typ(t: Type) -> str:
    return f"<{t.__module__}.{t.__name__}>"

def val(value: Any) -> str:
    return f"{typ(type(value))} {repr(value)}"

def any(x: Any) -> str:
    if isclass(x):
        return typ(x)
    return val(x)

def arg(name: str, value: Any) -> str:
    """
    >>> arg("x", 1)
    '`x`: <builtins.int> 1'
    """
    return f"{tick(name)}: {val(value)}"

def one_of(*items) -> str:
    return coord(items, "or", to_s=any)

doctesting.testmod(__name__)
