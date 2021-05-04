from __future__ import annotations
from typing import Generator, Protocol, Union, Iterable

from nansi.proper import Prop

TAlias = Union[None, str, Iterable[str]]

# class PArg(Prop, Protocol):
#     alias: TAlias

#     def iter_aliases(self: PArg) -> Generator[TAlias, None, None]:
#         ...


