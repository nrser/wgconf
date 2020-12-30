from __future__ import annotations
from typing import *
import re
from collections import namedtuple

from typeguard import check_type

from .util import *
from .typing import (
    decode,
    is_list as is_list_typing,
    is_optional_list,
)
from .line import (
    Line,
    Blank,
    Comment,
    Option,
    SectionHead,
    DefaultSectionHead,
)

DUP_TYPE = Literal['first', 'list'] # pylint: disable=invalid-name
DEFAULT_DUP = 'first'

Meta = namedtuple('Meta', 'comment name value')

def meta_for(comment: Comment) -> Optional[Meta]:
    if match := Option.REGEXP.fullmatch(comment.value):
        return Meta(comment, match.group(1), match.group(2))
    return None

def encode_value(value: PropValue) -> Optional[str]:
    if value is None or value == '':
        return None
    if isinstance(value, str):
        return value
    if value is True:
        return 'true'
    if value is False:
        return 'false'
    if isinstance(value, (list, tuple)):
        return ', '.join(encode_value(v) for v in value)
    return str(value)

class Prop(property):
    # pylint: disable=redefined-builtin
    def __init__(self, option_name, type, meta: bool = False):
        super().__init__(self._get, self._set, self._del)

        required = False
        try:
            check_type(f"(required check for {option_name})", None, type)
        except TypeError:
            required = True

        self.option_name = option_name
        self.type = type
        self.required = required
        self.meta = meta

    def _get(self, section, encoded: bool = False):
        if self.meta:
            value = section.get_meta(self.option_name)
        else:
            value = section[self.option_name]
        if encoded:
            return value
        else:
            return decode(value, self.type)

    def _del(self, section):
        if self.required:
            check_type(f"prop for {self.option_name}", None, self.type)
            raise Exception("Should never happen")
        if self.meta:
            section.delete_meta(self.option_name)
        else:
            del section[self.option_name]

    def _set(self, section, value) -> None:
        if value is None or value == '':
            self._del(section)
            return
        value = self.cast(value)
        check_type(f"prop for {self.option_name}", value, self.type)
        if self.meta:
            section.set_meta(self.option_name, value)
        else:
            section[self.option_name] = value

    def is_set(self, section) -> bool:
        if self.meta:
            return section.has_meta(self.option_name)
        else:
            return self.option_name in section

    def is_change(self, section, new_value) -> bool:
        '''Would setting the Prop to `new_value` change the `section`?

        String-encodes `new_value` and compares that to the string-encoding in
        the relevant Option or Comment (in the case of meta props). The goal is
        to avoid any differences due to casting and test if the actual file
        contents would change in a material way.
        '''
        new_enc = encode_value(new_value)
        if new_enc is None:
            return self.is_set(section) # Delete option that is present?
        if self.is_set(section):
            # Change value?
            return new_enc != self._get(section, encoded=True)
        else:
            return True # Add option that is not present

    def cast(self, value):
        if (
            (is_list_typing(self.type) or is_optional_list(self.type)) and
            not isinstance(value, list)
        ):
            return [value]
        if isinstance(value, Path):
            return str(value)
        return value



class Section:
    # @classmethod
    # def from_string(self, string: str) -> Optional[Section]:
    #     if head := SectionHead.from_string(string):
    #         if head.value == self.__name__:
    #             return self(head)

    @classmethod
    def props(self) -> Dict[str, Prop]:
        return {
            name: getattr(self, name)
            for name
            in dir(self)
            if isinstance(getattr(self, name, None), Prop)
        }

    @classmethod
    def is_prop(self, name) -> bool:
        return isinstance(getattr(self, name, None))

    _head: Union[SectionHead, DefaultSectionHead]
    _dup: DUP_TYPE

    name = Prop('Name', Optional[str], meta=True)
    description = Prop('Description', Optional[str], meta=True)

    def __init__(
        self,
        head: Union[SectionHead, DefaultSectionHead],
        dup: DUP_TYPE=DEFAULT_DUP,
    ):
        check_type("Bad `dup` value", dup, DUP_TYPE)
        self._head = head
        self._dup = dup

    @property
    def head(self):
        return self._head

    @property
    def dup(self) -> DUP_TYPE:
        return self._dup

    @property
    def kind(self) -> Optional[str]:
        if not self.is_default:
            return self._head.value

    @property
    def is_default(self) -> bool:
        return isinstance(self._head, DefaultSectionHead)

    def meta(self) -> Iterator[Meta]:
        for comment in self.comments():
            if meta := meta_for(comment):
                yield meta

    def has_meta(self, name: str) -> bool:
        return self.get_meta(name) is not None

    def get_meta(self, name: str) -> Optional[str]:
        if meta := find(self.meta(), lambda m: m.name == name):
            return meta.value

    def set_meta(self, name: str, value: Any) -> None:
        string = encode_value(value)

        if string is None:
            self.delete_meta(name)
            return

        comment_value = f"{name} = {string}"

        # pylint: disable=too-many-function-args
        if meta := find(self.meta(), lambda m: m.name == name):
            meta.comment.value = comment_value
        else:
            comment = Comment(comment_value)
            if meta := last(self.meta()):
                line = meta.comment
            else:
                line = self._head
            line.insert_next(comment)

    def delete_meta(self, name: str) -> None:
        for meta in (c for c in self.meta() if c.name == name):
            meta.comment.remove()

    def comments(self) -> Iterator[Comment]:
        return (line for line in self if isinstance(line, Comment))

    def options(self) -> Iterator[Option]:
        return (line for line in self if isinstance(line, Option))

    def items(self, meta: bool = False) -> Iterator[Tuple[str, str]]:
        for line in self:
            if meta and isinstance(line, Comment):
                if meta := meta_for(line):
                    yield (meta.name, meta.value)
                continue
            if isinstance(line, Option):
                yield (line.name, line.value)

    def remove(self) -> None:
        if self.is_default:
            raise Exception("Can't remove the default section. #clear() it?")
        tail = last(self)
        if self.head.prev is not None:
            self.head.prev.next = tail.next
        if tail.next is not None:
            tail.next.prev = self.head.prev
        self.head.prev = tail.next = None

    def replace(self, replacement: Section) -> None:
        if self.is_default:
            raise Exception("Can't replace the default section. #clear() it?")
        if replacement.is_default:
            raise ValueError("Can't replace a section with a default section")

        if self.head.prev is None:
            replacement.head.prev = None
        else:
            self.head.prev.next = replacement.head
            replacement.head.prev = self.head.prev

        our_tail = last(self)
        replacement_tail = last(replacement)
        if our_tail.next is None:
            replacement_tail.next = None
        else:
            our_tail.next.prev = replacement_tail
            replacement_tail.next = our_tail.next
        self.head.prev = our_tail.next = None

    def clear(self) -> None:
        line = self.head.next
        while line is not None:
            line.remove()
            line = line.next

    def has_changes(self, **props) -> bool:
        return any((
            getattr(self.__class__, prop_name).is_change(self, new_value)
            for prop_name, new_value
            in props.items()
        ))

    def update(self, **props):
        for prop_name, prop_value in props.items():
            setattr(self, prop_name, prop_value)

    def __str__(self) -> str:
        return ''.join((f"{line}\n" for line in self))

    def __iter__(self, include_default_head: bool = False) -> Iterator[Line]:
        if include_default_head or (not self.is_default):
            yield self.head
        line = self.head.next
        while line is not None and not isinstance(line, SectionHead):
            yield line
            line = line.next

    def __contains__(self, name: str) -> bool:
        return bool(find(self.options(), lambda opt: opt.name == name))

    def __getitem__(self, name: str) -> Union[None, str, List[str]]:
        if self.dup == 'list':
            values = [opt.value for opt in self.options() if opt.name == name]
            if len(values) == 1:
                return values[0]
            elif len(values) > 1:
                return values
        elif option := find(self.options(), lambda opt: opt.name == name):
            return option.value
        return None

    def __setitem__(self, name: str, value: Any) -> None:
        if self.dup == 'list' and isinstance(value, (list, tuple)):
            strings = tuple(map(encode_value, value))

            if len(strings) == 0:
                self.__delitem__(name)
                return

            options = [opt for opt in self.options() if opt.name == name]

            if len(options) == 0:
                insert_after = last((
                    line for
                    line in
                    self.__iter__(include_default_head=True)
                    if not isinstance(line, Blank)
                ))
            else:
                insert_after = options[0].prev

            for option in options:
                option.remove()

            for string in strings:
                # pylint: disable=unexpected-keyword-arg
                insert_after.insert_next(Option(name=name, value=string))
                insert_after = insert_after.next

        else:
            string = encode_value(value)

            if string is None:
                self.__delitem__(name)
                return

            # pylint: disable=unexpected-keyword-arg
            if option := find(self.options(), lambda opt: opt.name == name):
                if option.value == string:
                    return
                option.value = string
            else:
                last_non_blank_line = last((
                    line for
                    line in
                    self.__iter__(include_default_head=True)
                    if not isinstance(line, Blank)
                ))
                last_non_blank_line.insert_next(Option(name=name, value=string))

    def __delitem__(self, name: str) -> None:
        for option in self.options():
            if option.name == name:
                option.remove()
