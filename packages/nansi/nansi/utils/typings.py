# Adapted from the core of `typeguard` 2.9.1, specifically:
#
# https://github.com/agronholm/typeguard/blob/0c7d1e7df87e3cf8de6e407e2ee04df21691280d/typeguard/__init__.py
#
# Chopped down to just what is needed to type check option values in Python
# 3.8+, with ability to decode them from strings added on.
#

from inspect import isclass, isfunction
from typing import (
    Any,
    Dict,
    Generator,
    List,
    Mapping,
    Sequence,
    Tuple,
    Type,
    Union,
    get_origin as _get_origin,
    get_args as _get_args,
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


def each_union_member(t: Type) -> Generator[Type, None, None]:
    root_type = get_root_type(t)
    if root_type is Union:
        raise ValueError(
            "Expected root type of argument `t` to be `typing.Union`, "
            f"given {t} of type {type(t)} with root type {root_type}"
        )
    for member in map(get_root_type, get_args(t)):
        if member is Union:
            yield from each_union_member(member)
        else:
            yield member


def each_member_type(t: Type) -> Generator[Type, None, None]:
    if is_union(t):
        yield from each_union_member(t)
    else:
        yield get_root_type(t)


def cast_values(value: Any, expected_type: Type, cast_map):
    # If the value satisfies the expected type then we use it. This is meant to
    # help prevent unnecessary and unexpected casts
    if test_type(value, expected_type):
        return value

    # Otherwise we try to cast. Casting is first-come, first-serve over the
    # "member types":
    #
    # 1.  When `expected_type` is an alias to a <typing.Union>, the member types
    #     are the _arg types_ of the <typing.Union> (unwrapped).
    #
    # 2.  Otherwise, the single member type is the unwrapped, de-aliased type
    #     extracted from the `expected_type`.
    #
    for member_type in each_member_type(expected_type):
        # 1.  Collections — recursively map

        if member_type is dict:
            if not isinstance(value, Mapping):
                return value
            expected_key_type, expected_value_type = _get_args(member_type)
            return {
                cast_values(item_key, expected_key_type, cast_map):
                    cast_values(item_value, expected_value_type, cast_map)
                for item_key, item_value in value.items()
            }

        if member_type is list:
            if not isinstance(value, Sequence):
                return value
            expected_item_type, = _get_args(member_type)
            return [
                cast_values(item, expected_item_type, cast_map)
                for item in value
            ]

        # 2.  Scalars — apply `cast_map`

        for cast_type, cast_fn in cast_map.items():
            if (
                member_type is cast_type or
                (isclass(member_type) and issubclass(member_type, cast_type))
            ):
                cast_value = cast_fn(value, member_type)
                if test_type(cast_value, member_type):
                    return cast_value

        # 3.  Give up.

        return value


doctesting.testmod(__name__)
