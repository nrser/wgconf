from typing import Any, Iterable, Optional, Type
from pathlib import Path

from nansi.utils import doctesting
from nansi.utils.casting import CastError, map_cast
from nansi.utils import text
from nansi import logging
from nansi.utils.typings import is_optional

from .base import ArgsBase
from .arg import Arg


LOG = logging.getLogger(__name__)


def cast_path(value: Any, expected_type: Type, **context) -> Optional[Path]:
    if value is None and is_optional(expected_type):
        return None
    if isinstance(value, str):
        return Path(value)
    if isinstance(value, Path):
        return value
    if isinstance(value, Iterable):
        return Path(*value)
    raise CastError(
        f"Can't cast to Path, expected {text.one_of(str, Path, Iterable)}, "
        f"given {text.arg('value', value)}",
        value,
        Path,
    )


def cast_child_args(
    value: Any,
    expected_type: ArgsBase,
    instance: ArgsBase,
    **context
):
    return expected_type(value, parent=instance)


@LOG.inject
def autocast(
    value: Any,
    expected_type: Type,
    instance: ArgsBase,
    prop: Arg,
    *,
    log=LOG
):
    """
    ## Examples

    Scalar casts

    >>> class ArgsWithPath(ArgsBase):
    ...     path = Arg(Path)
    ...
    >>> ArgsWithPath({"path": ["/", "usr", "local", "bin"]}).path
    PosixPath('/usr/local/bin')

    >>> class SuperArgs(ArgsBase):
    ...     with_path = Arg(ArgsWithPath)
    ...
    >>> SuperArgs(
    ...     {"with_path": {"path": ["/", "usr", "local", "bin"]}}
    ... ).with_path.path
    PosixPath('/usr/local/bin')

    >>> class ArgsEx2(ArgsBase):
    ...     address = Arg.zero_or_more(str)
    ...
    >>> ArgsEx2({"address": "10.10.0.1"}).address
    ['10.10.0.1']
    """
    return map_cast(
        value=value,
        expected_type=expected_type,
        handlers={
            ArgsBase: cast_child_args,
            Path: cast_path,
        },
        instance=instance,
        prop=prop,
    )


doctesting.testmod(__name__)
