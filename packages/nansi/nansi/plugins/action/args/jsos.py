from typing import Any, Collection, Dict, List, Mapping, Union
from pathlib import Path

from typeguard import check_type

from nansi.utils import doctesting

JSOSType = Union[
    Dict[str, "JSOSType"],
    List["JSOSType"],
    str,
    int,
    float,
    bool,
    None,
]


def is_jsos_type(x: Any) -> bool:
    """
    >>> is_jsos_type(None)
    True

    >>> is_jsos_type({"x": [1, 2, 3]})
    True

    >>> is_jsos_type({"x": (1, 2, 3)})
    False
    """
    try:
        check_type("JSOSType", x, JSOSType)
    except TypeError:
        return False
    return True


def jsos_for(value):
    if hasattr(value, "to_jsos"):
        to_jsos_value = getattr(value, "to_jsos")
        if callable(to_jsos_value):
            return to_jsos_value()

    if is_jsos_type(value):
        # This clears <builtins.str> out for us
        return value

    if isinstance(value, Path):
        # Obviously, <pathlib.Path> become <builtins.str>
        return str(value)

    if isinstance(value, bytes):
        # Hell, try UTF-8. Will barf a <builtins.UnicodeDecodeError> if
        # it fails. Cool, that get ever-annoying <builtins.bytes> out of
        # the way.
        return value.decode("utf-8")

    # With <builtins.str> and <builtins.bytes> taken care of we can start to
    # think about collections

    if isinstance(value, Mapping):
        # <typing.Mapping> become `Dict[str, JSOSType]` (or raise)
        return {str(k): jsos_for(v) for k, v in value.items()}

    if isinstance(value, Collection):
        # Other collections become `List[JSOSType]` (or fail)
        return [jsos_for(v) for v in value]

    return value


doctesting.testmod(__name__)
