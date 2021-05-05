# Originally adapted from the core of `typeguard` 2.9.1, specifically:
#
# https://github.com/agronholm/typeguard/blob/0c7d1e7df87e3cf8de6e407e2ee04df21691280d/typeguard/__init__.py
#
# Augmented with collection-recursive casting.
#

from inspect import isfunction
from typing import (
    Any,
    Dict,
    Generator,
    List,
    Tuple,
    Type,
    Union,
    get_args as _get_args,
    get_origin as _get_origin,
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


def test_type(value: Any, expected_type: Type) -> bool:
    try:
        check_type("", value, expected_type)
    except TypeError:
        return False
    return True


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


def get_args(t):
    return _get_args(unwrap(t))


def need_args(t):
    args = get_args(t)
    if len(args) == 0:
        raise RuntimeError(f"No typing args on {type(t)}: {t}")
    return args


def unwrap(t):
    while is_new_type(t):
        t = t.__supertype__
    return t


def get_origin(t: Type) -> Type:
    return _get_origin(unwrap(t))


def de_alias(t: Type) -> Type:
    if origin := get_origin(t):
        return origin
    return t


def get_root_type(t: Type) -> Type:
    return unwrap(de_alias(t))


def is_union(t) -> bool:
    """
    >>> is_union(Union[int, str])
    True

    >>> from typing import NewType
    >>> is_union(NewType("NewUnion", Union[int, str]))
    True
    """
    return get_root_type(t) is Union


def is_list(t) -> bool:
    return get_root_type(t) is list


def is_dict(t) -> bool:
    return get_root_type(t) is dict


def is_optional(t) -> bool:
    root_type = get_root_type(t)
    return t is Union and NoneType in _get_args(root_type)


def each_member_type(t: Type) -> Generator[Type, None, None]:
    if get_root_type(t) is Union:
        yield from get_args(t)
    else:
        yield t


doctesting.testmod(__name__)
