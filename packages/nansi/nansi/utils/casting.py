# from inspect import isclass
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Sequence,
    Tuple,
    Type,
)

from nansi.utils.typings import (
    each_member_type,
    get_root_type,
    test_type,
    get_args,
)
from nansi.utils.strings import coord
from nansi import logging
from nansi.utils import doctesting


LOG = logging.getLogger(__name__)

THandlers = Mapping[Type, Callable[[Any, Type], Any]]


class CastError(TypeError):
    def __init__(self, message, value, expected_type):
        super().__init__(message)
        self.value = value
        self.expected_type = expected_type


def _cast_dict(
    value: Any,
    expected_types: Tuple[Type, Type],
    handlers: THandlers,
    **context,
) -> Dict:
    if not isinstance(value, Mapping):
        raise CastError(
            (
                "Value must be <typing.Mapping> to cast to <builtins.dict>, "
                f"given {type(value)} of {value}"
            ),
            value,
            Mapping,
        )

    expected_key_type, expected_value_type = expected_types
    return {
        map_cast(item_key, expected_key_type, handlers, **context): map_cast(
            item_value, expected_value_type, handlers, **context
        )
        for item_key, item_value in value.items()
    }


def _cast_list(
    value: Any, expected_item_type: Type, handlers: THandlers, **context
) -> List:
    if not isinstance(value, Sequence):
        raise CastError(
            (
                "Value must be <typing.Sequence> to cast to <builtins.list>, "
                f"given {type(value)} of {value}"
            ),
            value,
            Sequence,
        )

    return [
        map_cast(item, expected_item_type, handlers, **context)
        for item in value
    ]


def map_cast(
    value: Any, expected_type: Type, handlers: THandlers, **context
) -> Any:
    """
    Cast values using a mapping of type → cast function.

    Descends into <builtins.list> and <builtins.dict> collections, mapping
    items, keys and values according to their expected types.

    Before any casting, tests if the value satisfies the expected type — see
    <nansi.utils.typings.test_type>, which wraps <typeguard.check_type>. If the
    test passes, the value is simply returned. This is meant to help avoid
    unnecessary and unexpected casts.

    When more than one type are acceptable (<typing.Union>), the acceptable
    types are tried in iteration order; first cast to succeed wins.

    Examples
    --------------------------------------------------------------------------

    ### Basics ###

    Casting a <builtins.str> to a <builtins.int>:

    >>> map_cast(
    ...     value           = "123",
    ...     expected_type   = int,
    ...     handlers        = {
    ...                         int: lambda value, expected_type: int(value),
    ...                     }
    ... )
    123

    ### Unions ###

    The value is tested against the expected type _first_, and no casting is
    performed if it passes.

    Because the <builtins.str> `"123"` satisfies the expected type
    `Union[int, str]` the value is returned directly:

    >>> from typing import Union
    >>> map_cast(
    ...     value           = "123",
    ...     expected_type   = Union[int, str],
    ...     handlers        = {
    ...                         int: lambda value, expected_type: int(value),
    ...                     }
    ... )
    '123'

    When a cast does need to be performed against an expected <typing.Union>
    the first member type that succeeds wins.

    <builtins.int> comes first, so it wins here:

    >>> map_cast(
    ...     value           = "123",
    ...     expected_type   = Union[int, float],
    ...     handlers        = {
    ...                         int:    lambda v, t: int(v),
    ...                         float:  lambda v, t: float(v),
    ...                     }
    ... )
    123

    Reverse the order in the union to `float, int` and <builtins.float> will
    win:

    >>> map_cast(
    ...     value           = "123",
    ...     expected_type   = Union[float, int],
    ...     handlers        = {
    ...                         int:    lambda v, t: int(v),
    ...                         float:  lambda v, t: float(v),
    ...                     }
    ... )
    123.0

    ### Collections ###

    Walks into <typing.List> and <typing.Dict> collections:

    >>> from pathlib import Path
    >>> map_cast(
    ...     value           = {"PATH": ["/usr/local/bin", "/usr/bin", "/bin"]},
    ...     expected_type   = Dict[str, List[Path]],
    ...     handlers        = {
    ...                         Path: lambda v, t: Path(v),
    ...                     }
    ... )
    {'PATH': [PosixPath('/usr/local/bin'), PosixPath('/usr/bin'), PosixPath('/bin')]}

    """
    # If the value satisfies the expected type then we use it. This is meant to
    # help prevent unnecessary and unexpected casts
    if test_type(value, expected_type):
        return value

    # Otherwise we try to cast. Casting is first-come, first-serve over the
    # "member types":
    #
    # 1.  When `expected_type` is an alias to a <typing.Union>, the member types
    #     are the _arg types_ of the <typing.Union> (unwrapped).
    #
    # 2.  Otherwise, the single member type is the unwrapped, de-aliased type
    #     extracted from the `expected_type`.
    #
    for member_type in each_member_type(expected_type):
        root_type = get_root_type(member_type)

        # 1.  Collections — recursively map

        if root_type is dict:
            try:
                return _cast_dict(
                    value, get_args(member_type), handlers, **context
                )
            except CastError:
                continue

        if root_type is list:
            try:
                return _cast_list(
                    value, get_args(member_type)[0], handlers, **context
                )
            except CastError:
                continue

        # 2.  Scalars — apply `handlers`

        for cast_type, cast_fn in handlers.items():
            if issubclass(root_type, cast_type):
                try:
                    cast_value = cast_fn(value, member_type, **context)
                except CastError:
                    continue

                if test_type(cast_value, member_type):
                    return cast_value
                else:
                    LOG.warning(
                        "Cast function returned a value, but it failed to "
                        "type check against the expected type",
                        input_value=value,
                        return_value=cast_value,
                        expected_type=member_type,
                        cast_function=cast_fn,
                        cast_function_key=cast_type,
                        context=context,
                    )

    # END for member_type in ...

    # Failed to cast, raise an error

    member_types = tuple(each_member_type(expected_type))
    types_s = coord(member_types, "or")

    raise CastError(
        f"Expected {types_s}, given {type(value)} of {value}",
        value,
        member_types,
    )


doctesting.testmod(__name__)
