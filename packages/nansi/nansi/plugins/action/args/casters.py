from typing import Any, Iterable
from pathlib import Path
from nansi.plugins.action.args.errors import CastTypeError

from nansi.utils import doctesting
from nansi.utils.typings import cast_values

from .base import ArgsBase
from .arg import Arg


def cast_path(args: ArgsBase, arg: Arg, value: Any) -> Path:
    if value is None:
        return None
    if isinstance(value, str):
        return Path(value)
    if isinstance(value, Path):
        return value
    if isinstance(value, Iterable):
        return Path(*value)
    raise CastTypeError.create(arg, Path, value)


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
    return cast_values(
        value,
        arg.type,
        {
            ArgsBase: lambda v, t: t(v, parent=args),
            Path: lambda v, t: cast_path(args, arg, v),
        }
    )

doctesting.testmod(__name__)
