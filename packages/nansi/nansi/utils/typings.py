# Adapted from the core of `typeguard` 2.9.1, specifically:
#
# https://github.com/agronholm/typeguard/blob/0c7d1e7df87e3cf8de6e407e2ee04df21691280d/typeguard/__init__.py
#
# Chopped down to just what is needed to type check option values in Python
# 3.8+, with ability to decode them from strings added on.
#

from inspect import isfunction
from typing import (
    Any,
    Dict,
    List,
    Tuple,
    Union,
)

from typeguard import check_type

from nansi.utils import doctesting

NoneType = type(None)

# SEE https://docs.python.org/3.8/library/json.html#json.JSONEncoder
JSONEncType = Union[
    Dict[Any, "JSONEncType"],
    List["JSONEncType"],
    Tuple["JSONEncType", ...],
    str,
    int,
    float,
    bool,
    None,
]  # type: ignore


def is_json_enc_type(x: Any) -> bool:
    """
    >>> is_json_enc_type(None)
    True

    >>> is_json_enc_type({"x": [1, 2, 3]})
    True

    [set][] can _not_ be encoded by the standard JSON encoder. Even
    though it's nestled inside a [dict][] (good job [typeguard][]!).

    >>> is_json_enc_type({"x": {1, 2, 3}})
    False

    [set]: builtins.set
    [dict]: builtins.dict
    [typeguard]: https://pypi.org/project/typeguard/
    """
    try:
        check_type("JSONEncType", x, JSONEncType)
    except TypeError:
        return False
    return True


def is_new_type(expected_type) -> bool:
    return (
        isfunction(expected_type)
        and getattr(expected_type, "__module__", None) == "typing"
        and getattr(expected_type, "__qualname__", None).startswith("NewType.")
        and hasattr(expected_type, "__supertype__")
    )


def get_origin(t):
    return getattr(unwrap(t), "__origin__", None)


def get_args(t):
    return getattr(unwrap(t), "__args__", None)


def need_args(t):
    return getattr(unwrap(t), "__args__")


def unwrap(t):
    while is_new_type(t):
        t = t.__supertype__
    return t


def reduces_to(t, typing) -> bool:
    return get_origin(t) is typing


def is_union(t) -> bool:
    return reduces_to(t, Union)


def is_list(t) -> bool:
    return reduces_to(t, list)


def is_dict(t) -> bool:
    return reduces_to(t, dict)


def is_optional(t) -> bool:
    return is_union(t) and NoneType in need_args(t)


def each_union_member(t):
    t = unwrap(t)
    if not is_union(t):
        raise ValueError(
            "Expected argument `t` to reduce to `typing.Union`, "
            f"given {type(t)} value {t}"
        )
    for member in map(unwrap, need_args(t)):
        if is_union(member):
            yield from each_union_member(member)
        else:
            yield member


doctesting.testmod(__name__)
