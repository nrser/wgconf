from __future__ import annotations
from typing import Any, Iterable, Type, Union

from nansi.proper import Prop
from nansi.utils.collections import each
from nansi.utils.strings import coord

class CastTypeError(TypeError):
    @classmethod
    def create(
        cls,
        prop: Prop,
        value: Any,
        expected_type: Union[Type, Iterable[Type]],
    ) -> CastTypeError:
        types_s = coord(each(Type, expected_type), "or")
        message = f"Expected {types_s}; given type {type(value)}: {value}"
        return cls(message, prop, value)

    def __init__(self, message, arg, value):
        super().__init__(message)
        self.arg = arg
        self.value = value

class CastValueError(ValueError):
    def __init__(self, message, arg, value):
        super().__init__(message)
        self.arg = arg
        self.value = value
