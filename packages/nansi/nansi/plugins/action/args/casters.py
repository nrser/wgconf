from typing import Any, Iterable, Optional
from pathlib import Path

from nansi.utils import doctesting
from nansi.utils.casting import CastError, map_cast
from nansi.utils import text

from .base import ArgsBase
from .arg import Arg


def cast_path(args: ArgsBase, arg: Arg, value: Any) -> Optional[Path]:
    if value is None:
        return None
    return _cast_path(value)


def _cast_path(value: Any) -> Path:
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


def autocast(args: ArgsBase, arg: Arg, value: Any):
    """
    ## Examples

    1.  Scalar casts

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

    """
    return map_cast(
        value=value,
        expected_type=arg.type,
        handlers={
            ArgsBase: lambda v, t: t(v, parent=args),
            Path: lambda v, t: _cast_path(v),
        },
    )


doctesting.testmod(__name__)
