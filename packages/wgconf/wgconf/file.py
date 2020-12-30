from __future__ import annotations
from typing import *
from pathlib import Path

from typeguard import check_type

from .util import *
from .line import (
    Line,
    Blank,
    Comment,
    Option,
    SectionHead,
    DefaultSectionHead,
)
from .section import Section, DUP_TYPE, DEFAULT_DUP

class File:
    path: Optional[Path]
    _default_section_head: DefaultSectionHead
    dup: DUP_TYPE

    def __init__(
        self,
        path: Optional[Union[Path, str]] = None,
        dup: DUP_TYPE = DEFAULT_DUP,
    ):
        check_type("Bad `dup` value", dup, DUP_TYPE)

        if path is not None and not isinstance(path, Path):
            path = Path(path)

        self.path = path

        self._default_section_head = DefaultSectionHead()

        self.dup = dup

        if self.path is not None and self.path.exists():
            self.__init_load()

    def __init_load(self):
        with open(self.path) as fp:
            strings = fp.read().splitlines()

        tail = self._default_section_head

        for index, string in enumerate(strings):
            line_num = index + 1

            # pylint: disable=cell-var-from-loop
            line = find_map(
                (Blank, Comment, SectionHead, Option),
                lambda c: c.from_string(string)
            )

            if line is None:
                raise Exception(
                    f"{self.path}:{line_num} Bad line: {string}"
                )

            tail.next = line
            line.prev = tail

            tail = line

    @property
    def first_line(self) -> Optional[Line]:
        return self._default_section_head.next

    @property
    def is_empty(self) -> bool:
        return self.first_line is None

    @property
    def default_section(self) -> Section:
        return Section(self._default_section_head, dup=self.dup)

    def lines(self) -> Iterator[Line]:
        line = self.first_line
        while line is not None:
            yield line
            line = line.next

    def sections(self) -> Iterator[Section]:
        yield self.default_section
        line = self.first_line
        while line is not None:
            if isinstance(line, SectionHead):
                yield Section(line, dup=self.dup)
            line = line.next

    def add_section(self, section: Section, newline: bool = True):
        if self.is_empty:
            self._default_section_head.insert_next(section.head)
        else:
            last_line = last(self.lines())
            if newline and not isinstance(last_line, Blank):
                last_line.insert_next(Blank())
                last_line = last_line.next
            last_line.insert_next(section.head)

        if newline:
            new_last_line = last(section)
            if not isinstance(new_last_line, Blank):
                new_last_line.insert_next(Blank())

    def __str__(self) -> str:
        return ''.join((f"{line}\n" for line in self.lines()))

    def __getitem__(self, key: Union[None, str]) -> Union[None, Line, Section]:
        if key is None or key == '':
            return self.default_section
        if section := find(self.sections(), lambda sect: sect.kind == key):
            return section
        return self.default_section[key]
