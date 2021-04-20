# Adapted from the core of `typeguard` 2.9.1, specifically:
#
# https://github.com/agronholm/typeguard/blob/0c7d1e7df87e3cf8de6e407e2ee04df21691280d/typeguard/__init__.py
#
# Chopped down to just what is needed to type check option values in Python
# 3.8+, with ability to decode them from strings added on.
#

from inspect import isfunction
from typing import (
    Optional,
    Sequence,
    TypeVar,
    Union,
)

def is_new_type(expected_type) -> bool:
    return (
        isfunction(expected_type) and
        getattr(expected_type, "__module__", None) == "typing" and
        getattr(expected_type, "__qualname__", None).startswith("NewType.") and
        hasattr(expected_type, "__supertype__")
    )

def get_origin(t):
    return getattr(unwrap(t), '__origin__', None)

def get_args(t):
    return getattr(t, '__args__', None)

def need_args(t):
    return getattr(t, '__args__')

def unwrap(t):
    while is_new_type(t):
        t = t.__supertype__
    return t

def is_union(t) -> bool:
    return get_origin(unwrap(t)) is Union

def is_list(t) -> bool:
    return get_origin(t) is list

def is_optional_list(t) -> bool:
    t = unwrap(t)
    if get_origin(t) is not Union:
        return False
    if args := get_args(t):
        if len(args) != 2 or NoneType not in args:
            return False
        return is_list(args[0])
    return False

def is_optional(t) -> bool:
    t = unwrap(t)
    if get_origin(t) is not Union:
        return False
    if args := get_args(t):
        return NoneType in args(t)
    return False

NoneType = type(None)

SCALAR_TYPES = (str, int, bool)

def decode_scalar(raw: str, type_):
    if type_ is str:
        return raw
    if type_ is int:
        return int(raw)
    if type_ is bool:
        if raw == 'true':
            return True
        if raw == 'false':
            return False
        raise ValueError(
            f"Expected 'true' or 'false' when decoding bool, found {repr(type_)}"
        )
    raise TypeError(
        f"Can only decode str, int and bool scalars, not {repr(type_)}"
    )

def decode_list_of_union_item(raw: str, member_types):
    for member_type in member_types:
        try:
            return decode_scalar(raw, member_type)
        except ValueError:
            pass
    raise ValueError(
        f"Unable to decode {repr(raw)} as any of {member_types}"
    )

def decode_list_of_union(raws: Sequence[str], union_type):
    member_types = (unwrap(t) for t in need_args(union_type))
    return [
        decode_list_of_union_item(raw, member_types)
        for raw in raws
    ]

def decode_list(raw: str, item_type):
    raws = (s.lstrip() for s in raw.split(','))

    if is_union(item_type):
        return decode_list_of_union(raws, item_type)

    return [
        decode_scalar(raw_item, item_type)
        for raw_item in raws
    ]

def decode_union(raw: str, union_type):
    member_types = (
        member_type for
        member_type in
        (unwrap(t) for t in need_args(union_type))
        if member_type is not NoneType
    )

    for member_type in member_types:
        try:
            return decode(raw, member_type)
        except ValueError:
            pass
    raise ValueError(
        f"Unable to decode {repr(raw)} as any of {member_types}"
    )

def decode(raw: Optional[str], type_):
    if raw is None:
        return None

    type_ = unwrap(type_)

    if is_union(type_):
        return decode_union(raw, type_)

    if is_list(type_):
        item_type = unwrap(need_args(type_)[0])

        if type(item_type) is TypeVar:
            # Untyped list, which we assume is `str`
            item_type = str

        return decode_list(raw, item_type)

    return decode_scalar(raw, type_)
