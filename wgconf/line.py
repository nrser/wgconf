from __future__ import annotations
from typing import Optional
import re
from dataclasses import dataclass

# Pylint doesn't like `REGEXP` constant in dataclasses?
# pylint: disable=invalid-name


class Line:
    REGEXP = None  # For the linters in the crowd tonight!!

    prev: Optional[Line] = None
    next: Optional[Line] = None

    @classmethod
    def from_string(cls, string: str) -> Optional[Line]:
        if match := cls.match(string):
            return cls.from_match(match)
        return None

    @classmethod
    def match(cls, line: str) -> Optional[re.Match]:
        return cls.REGEXP.fullmatch(line)

    @classmethod
    def from_match(cls, match: re.Match) -> Line:
        return cls(*match.groups())

    def remove(self) -> None:
        if self.prev is not None:
            self.prev.next = self.next
        if self.next is not None:
            self.next.prev = self.prev
        self.prev = self.next = None

    def insert_next(self, line: Line) -> None:
        if self.next is not None:
            line.next = self.next
            self.next.prev = line
        line.prev = self
        self.next = line

    def insert_prev(self, line: Line) -> None:
        if self.prev is not None:
            self.prev.next = line
        line.next = self
        self.prev = line


@dataclass
class Blank(Line):
    REGEXP = re.compile(r"\s*")

    @classmethod
    def from_match(cls, match: re.Match) -> Blank:
        return Blank()

    def __str__(self) -> str:
        return ""


@dataclass
class Comment(Line):
    REGEXP = re.compile(r"#\ ?(.*)")

    value: str

    def __str__(self) -> str:
        return f"# {self.value}"


@dataclass
class OptBase(Line):
    name: str
    value: str

    @classmethod
    def from_match(cls, match: re.Match) -> OptBase:
        # pylint: disable=unexpected-keyword-arg
        return cls(name=match.group(1), value=match.group(2).rstrip())


@dataclass
class Option(OptBase):
    REGEXP = re.compile(r"([A-Za-z]+)\s*=\s*(.+)")

    def __str__(self) -> str:
        return f"{self.name} = {self.value}"


@dataclass
class SectionHead(Line):
    REGEXP = re.compile(r"\[([A-Za-z]+)\]\s*")

    value: str

    def __str__(self) -> str:
        return f"[{self.value}]"


class DefaultSectionHead(Line):
    @classmethod
    def match(cls, line: str) -> Optional[re.Match]:
        return None

    def remove(self) -> None:
        raise NotImplementedError("Can't remove DefaultSectionHead")

    def insert_prev(self, line: Line) -> None:
        raise NotImplementedError("Can't insert before DefaultSectionHead")
