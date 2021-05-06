from __future__ import annotations
from typing import (
    Any,
    Callable,
    Iterable,
    List,
    Optional,
    TypeVar,
    Union,
)

from nansi.proper import Prop
from nansi.utils import doctesting
from nansi import logging

from .base import ArgsBase


LOG = logging.getLogger(__name__)

TValue = TypeVar("TValue")
TInput = TypeVar("TInput")
TItem = TypeVar("TItem")
TAlias = Union[None, str, Iterable[str]]


class Arg(Prop[TValue, TInput]):
    alias: TAlias

    def __init__(
        self,
        type,
        default=None,
        *,
        cast='autocast',
        default_value=None,
        get_default=None,
        alias: TAlias = None,
    ):
        # pylint: disable=redefined-builtin
        if cast == 'autocast':
            # pylint: disable=import-outside-toplevel
            from .casts import autocast
            cast = autocast
        super().__init__(
            type,
            default,
            cast=cast,
            default_value=default_value,
            get_default=get_default,
        )
        self.alias = alias

    def iter_aliases(self):
        if self.alias is not None:
            if isinstance(self.alias, str):
                yield self.alias
            else:
                yield from self.alias

    @classmethod
    def _x_or_more(
        cls,
        item_type: TItem,
        default: Any,
        item_cast: Optional[Callable[[ArgsBase, Arg, Any], Any]],
        alias: TAlias,
        allow_empty: bool,
    ):
        if item_cast == 'autocast':
            # pylint: disable=import-outside-toplevel
            from .casts import autocast
            item_cast = autocast
        def cast(value, expected_type, instance, prop):
            if value is None:
                if allow_empty:
                    return []
                return value
            if not isinstance(value, list):
                value = [value]
            if item_cast is None:
                return value
            return [
                item_cast(item, item_type, instance=item, prop=prop)
                for item
                in value
            ]

        return cls(List[item_type], default, cast=cast, alias=alias)

    @classmethod
    def one_or_more(
        cls, item_type, default=None, item_cast='autocast', alias=None
    ):
        return cls._x_or_more(item_type, default, item_cast, alias, False)

    @classmethod
    def zero_or_more(
        cls, item_type, default=None, item_cast='autocast', alias=None
    ):
        return cls._x_or_more(item_type, default, item_cast, alias, True)


doctesting.testmod(__name__)
