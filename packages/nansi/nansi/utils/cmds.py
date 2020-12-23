from typing import *

TOptValue = Union[bool, str, int, float]
TOpts = Dict[str, Union[TOptValue, List[TOptValue]]]


def iter_opts(
    opts: Optional[TOpts],
    *,
    long_style: Literal["=", " "] = " ",
    sort: bool = True,
):
    if opts is None:
        return
    if sort:
        items = sorted(opts.items())
    else:
        items = opts.items()
    for name, value in items:
        if value is None:
            continue
        is_short = len(name) == 1
        if is_short:
            flag = f"-{name}"
        else:
            flag = f"--{name}"
        if isinstance(value, list):
            for item in value:
                if is_short or long_style == " ":
                    yield flag
                    yield str(item)
                else:
                    yield f"{flag}={item}"
        elif isinstance(value, bool):
            if value is True:
                yield flag
        else:
            if is_short or long_style == " ":
                yield flag
                yield str(value)
            else:
                yield f"{flag}={value}"
