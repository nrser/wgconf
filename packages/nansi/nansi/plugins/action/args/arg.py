from __future__ import annotations
from inspect import isclass
from typing import Any, Callable, Generic, Iterable, List, Optional, TypeVar, Union

from nansi.proper import Prop
from nansi.utils.typings import (
    each_union_member,
    unwrap,
    is_union,
)
from nansi.utils import doctesting

from .base import ArgsBase


TValue = TypeVar("TValue")
TInput = TypeVar("TInput")
TItem = TypeVar("TItem")
TAlias = Union[None, str, Iterable[str]]


def is_args_class(x: Any) -> bool:
    """
    Is a value a _proper_ subclass of [ArgsBase][]?

    Mostly used to test if a [Arg#type][] is an args substructure so it can be
    cast appropriately.

    ## Examples

    1.  Safe to use with values that are not classes.

        >>> is_args_class(123)
        False

    2.  Test for _proper_ subclasses — [ArgsBase][] itself does _not_ count!

        >>> is_args_class(ArgsBase)
        False

        This is because [ArgsBase][] is an _abstract_ class, and in the current
        use case we are looking for _concrete_ classes we can instantiate.

    3.  Ok, here's an actual positive case. Should look about as you'd expect.

        >>> class PointArgs(ArgsBase):
        ...     x = Arg(float)
        ...     y = Arg(float)
        ...
        >>> is_args_class(PointArgs)
        True

    4.  Of course, _instances_ of [ArgsBase][] subclasses don't count either.

        >>> is_args_class(PointArgs({"x": 1.23, "y": 3.45}))
        False

    [Arg#type]: nansi.plugins.action.args.arg.Arg.type
    [ArgsBase]: nansi.plugins.action.args.base.ArgsBase
    """
    return isclass(x) and issubclass(x, ArgsBase) and x is not ArgsBase


def autocast(args: ArgsBase, arg: Arg, value: Any):
    """
    >>> class PersonArgs(ArgsBase):
    ...     name = Arg(str)
    ...     fav_color = Arg(str)

    >>> class PeopleArgs(ArgsBase):
    ...     person = Arg(Optional[PersonArgs], cast=autocast)

    >>> PeopleArgs(
    ...     {"person": {"name": "Neil E.O.", "fav_color": "grey"}},
    ... ).person.name
    'Neil E.O.'

    >>> PeopleArgs(
    ...     {"person": {"name": "Neil E.O.", "fav_color": "grey"}},
    ... ).person.fav_color
    'grey'

    >>> PeopleArgs({}).person is None
    True
    """
    # We don't screw with any value that _already_ satisfies the arg type
    if arg.test_type(value):
        return value

    # Ok, into the meat of it...
    #
    # We want to "unwrap" any <typing.NewType> that may enclose the arg type
    t = unwrap(arg.type)

    # If the bare type is an <.base.ArgsBase> subclass then we try to
    # instantiate it.
    #
    # Note that we _do_ _not_ make any decisions based on what `value` is or
    # isn't... it's simply provided to the constructor, which could be
    # overridden to accept whatever-the-hell it wants.
    if is_args_class(t):
        return t(value, parent=args)

    # Now the fun part... composite types!
    #
    # We want to support <typing.Union>, particularly for <typing.Optional>
    # (which instantiates as `Union[None, T]`).
    if is_union(t):
        # Iterate through each <.base.ArgsBase> subclass in the `Union` trying
        # to instantate it. First to succeed wins.
        for args_class in filter(is_args_class, each_union_member(t)):
            # pylint: disable=broad-except
            try:
                # Return from the function on success
                return args_class(value, parent=args)
            except Exception:
                pass
        # None of them worked (if there even _were_ any), we're SOL. Return the
        # value and let <nansi.proper.Prop.check_type> puke on it...
        return value

    # SOMEDAY-MAYBE Process container classes... <typing.Dict>, <typing.List>,
    #               etc.

    # if is_dict(t) and isinstance(value, Mapping):
    #     _key_type, value_type = map(unwrap, need_args(t))

    #     if is_args_class(value_type):
    #         return {k: value_type(v, args) for k, v in value.items()}

    #     if is_union(value_type):
    #         args_classes = filtered(
    #             is_args_class, each_union_member(value_type)
    #         )

    #         if len(args_classes) == 0:
    #             return value

    #         cast_values = {}
    #         for k, v in value.items():
    #             for args_class in args_classes:
    #                 try:
    #                     cast_value = args_class(v, parent=args)
    #                 except Exception:
    #                     pass
    #                 else:

    # No dice. Return the value and let <nansi.proper.Prop.check_type> raise up
    return value


class Arg(Prop[TValue, TInput]):
    alias: TAlias

    def __init__(
        self,
        type,
        default=None,
        *,
        cast=autocast,
        default_value=None,
        get_default=None,
        alias: TAlias = None,
    ):
        # pylint: disable=redefined-builtin
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
        def cast(args, arg, value):
            if value is None:
                if allow_empty:
                    return []
                return value
            if not isinstance(value, list):
                value = [value]
            if item_cast is None:
                return value
            return [item_cast(args, arg, item) for item in value]

        return cls(List[item_type], default, cast=cast, alias=alias)

    @classmethod
    def one_or_more(
        cls, item_type, default=None, item_cast=autocast, alias=None
    ):
        return cls._x_or_more(item_type, default, item_cast, alias, False)

    @classmethod
    def zero_or_more(
        cls, item_type, default=None, item_cast=autocast, alias=None
    ):
        return cls._x_or_more(item_type, default, item_cast, alias, True)


doctesting.testmod(__name__)
