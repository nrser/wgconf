from typing import *

from nansi.utils.collections import iter_flat

TFileDataValue = Union[bool, str, int, float]
TFileDataSection = Mapping[str, Union[TFileDataValue, Iterable[TFileDataValue]]]
TFileData = Mapping[str, TFileDataSection]

def file_content_for(data: TFileData) -> str:
    lines = []

    for section_name, section_opts in data.items():
        lines.append(f"[{section_name}]")
        for name, value in section_opts.items():
            # pylint: disable=isinstance-second-argument-not-valid-type
            if isinstance(value, Iterable) and (
                not isinstance(value, (str, bytes))
            ):
                for item in iter_flat(value):
                    lines.append(f"{name}={item}")
            else:
                lines.append(f"{name}={value}")
        lines.append("")

    return "\n".join(lines)
