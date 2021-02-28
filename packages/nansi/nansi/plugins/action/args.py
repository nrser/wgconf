from typing import *
import logging
import collections.abc

from nansi.proper import Prop, Proper
from nansi.utils.aliases import de_aliased
from nansi.support.go import GO_ARCH_MAP

# pylint: disable=redefined-builtin,invalid-name,redefined-outer-name

LOG = logging.getLogger(__name__)


def os_fact_format(string: str, ansible_facts, **extras) -> str:
    os_facts = {
        "arch": ansible_facts["architecture"].lower(),
        "system": ansible_facts["system"].lower(),
        "release": ansible_facts["distribution_release"].lower(),
        **extras,
    }
    if os_facts["arch"] in GO_ARCH_MAP:
        os_facts["go_arch"] = GO_ARCH_MAP[os_facts["arch"]]
    return string.format(**os_facts)


def os_fact_formatter(*extra_attrs):
    def cast(args, _, string: str) -> str:
        return os_fact_format(
            string,
            args.task_vars["ansible_facts"],
            **{name: getattr(args, name) for name in extra_attrs},
        )

    return cast


def attr_formatter(*names):
    """
    >>> class Args(ArgsBase):
    ...     name = Arg( str )
    ...     path = Arg( str, "{name}.txt", cast=attr_formatter("name") )
    ...
    >>> Args({"name": "blah"}).path
    'blah.txt'
    """
    return lambda args, _, string: string.format(
        **{name: getattr(args, name) for name in names}
    )

class CastTypeError(TypeError):
    # def __init__(self, *args, **kwds):
    #     args_map = dict(zip(["message", "expected", "given"], args))
    #     dups = set(args_map).intersection(kwds)

    #     if len(dups) != 0:
    #         raise TypeError(
    #             f"CastError() got multiple values for arguments {dups}"
    #         )

    #     args_map.update(kwds)
    #     self.expected = args_map["expected"]
    #     self.given = args_map["given"]

    #     if "message" not in args_map:
    #         args_map["message"] = (
    #             f"Expected a {self.expected}, "
    #             f"given a {type(self.given)}: {self.given}"
    #         )

    #     super().__init__(args_map["message"])

    def __init__(self, message, arg, value):
        super().__init__(message)
        self.arg = arg
        self.value = value

class CastValueError(ValueError):
    def __init__(self, message, arg, value):
        super().__init__(message)
        self.arg = arg
        self.value = value

class Arg(Prop):
    # Don't complain about `typing.cast` override
    # pylint: disable=redefined-outer-name

    @staticmethod
    def auto_cast_args(arg_type, cast):
        if (
            cast is None
            and isinstance(arg_type, type)
            and issubclass(arg_type, ArgsBase)
        ):
            return lambda args, _, values: arg_type(values, args.task_vars)
        return cast

    def __init__(
        self,
        arg_type,
        default=None,
        *,
        cast=None,
        default_value=None,
        get_default=None,
        alias=None,
    ):
        super().__init__(
            arg_type,
            default,
            cast=Arg.auto_cast_args(arg_type, cast),
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
    def one_or_more(cls, item_type, default=None, item_cast=None, alias=None):
        item_cast = Arg.auto_cast_args(item_type, item_cast)

        def cast(instance, arg, value):
            if not isinstance(value, list):
                value = [value]
            if item_cast is None:
                return value
            return [item_cast(instance, arg, item) for item in value]

        return cls(List[item_type], default, cast=cast, alias=alias)

    @classmethod
    def zero_or_more(cls, item_type, default=None, item_cast=None, alias=None):
        item_cast = Arg.auto_cast_args(item_type, item_cast)

        def cast(instance, arg, value):
            if value is None:
                return []
            if not isinstance(value, list):
                value = [value]
            if item_cast is None:
                return value
            return [item_cast(instance, arg, item) for item in value]

        return cls(List[item_type], default, cast=cast, alias=alias)


class ArgsBase(Proper):
    """
    ### Aliases ###

    Aliases only operate in one direction: from task args to arg values. This
    works:

    >>> class Args(ArgsBase):
    ...     x = Arg(int, alias="ex")
    ...     y = Arg(int, alias=("hi", "why"))
    ...     z = Arg(int)
    ...
    >>> args = Args({'ex': 1, 'why': 2, 'z': 3}, {})
    >>> [args.x, args.y, args.z]
    [1, 2, 3]

    However, you can't *access* arg values using their aliases:

    >>> args.ex
    Traceback (most recent call last):
        ...
    AttributeError: 'Args' object has no attribute 'ex'
    """

    @classmethod
    def prop_aliases(cls):
        return {
            name: prop.iter_aliases()
            for name, prop in cls.iter_props()
            if prop.alias is not None
        }

    task_vars: Mapping

    def __init__(self, values, task_vars=None):
        self.task_vars = {} if task_vars is None else task_vars
        super().__init__(
            **de_aliased(
                aliases=self.__class__.prop_aliases(),
                src=values,
            )
        )


class OpenArgsBase(ArgsBase, collections.abc.Mapping):
    def __init__(self, values, task_vars=None):
        prop_values = {
            name: value
            for name, value in values.items()
            if self.__class__.is_prop(name)
        }

        ArgsBase.__init__(self, prop_values, task_vars)

        self.__extras__ = {
            name: value
            for name, value in values.items()
            if not self.__class__.is_prop(name)
        }

    def __len__(self):
        return len(self.__class__.iter_prop_names()) + len(self.__extras__)

    def __contains__(self, key: Any) -> bool:
        return isinstance(key, str) and (
            self.__class__.is_prop(key) or key in self.__extras__
        )

    def __getitem__(self, key: Any) -> Any:
        if not isinstance(key, str):
            raise KeyError(f"Keys must be str, given {type(key)}: {repr(key)}")
        if self.__class__.is_prop(key):
            return getattr(self, key)
        return self.__extras__[key]

    def __setitem__(self, key: str, value: Any) -> None:
        if not isinstance(key, str):
            raise TypeError(f"Keys must be str, given {type(key)}: {repr(key)}")
        if self.__class__.is_prop(key):
            setattr(self, key, value)
        else:
            self.__extras__[key] = value

    def __delitem__(self, key: str) -> None:
        if self.__class__.is_prop(key):
            delattr(self, key)
        else:
            del self.__extras__[key]

    def keys(self) -> Generator[str, None, None]:
        yield from self.__class__.iter_prop_names()
        yield from self.__extras__.keys()

    __iter__ = keys

    def values(self) -> Generator[Any, None, None]:
        for name in self.__class__.iter_prop_names():
            yield getattr(self, name)
        yield from self.__extras__.items()

    def items(self) -> Generator[Tuple[str, Any], None, None]:
        for name in self.__class__.iter_prop_names():
            yield (name, getattr(self, name))
        yield from self.__extras__.items()

    def get(self, key: Any, default: Any = None) -> Any:
        if key in self:
            return self[key]
        else:
            return default

    def extra_keys(self) -> collections.abc.KeysView:
        return self.__extras__.keys()

    def extra_values(self) -> collections.abc.ValuesView:
        return self.__extras__.values()

    def extra_items(self) -> collections.abc.ItemsView:
        return self.__extras__.items()

    def extras(self) -> Dict[str, Any]:
        return dict(self.extra_items())

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), **self.extras()}

    # def prop_keys(self) -> Generator[str, None, None]:
    #     return self.__class__.iter_prop_names()

    # def prop_values(self) -> Generator[Any, None, None]:
    #     for name in self.__class__.iter_prop_names():
    #         yield getattr(self, name)

    # def prop_items(self) -> Generator[Tuple[str, Any], None, None]:
    #     for name in self.__class__.iter_prop_names():
    #         yield (name, getattr(self, name))

    # Fucking-A, this breaks Proper.props()
    # def props(self) -> Dict[str, Any]:
    #     return dict(self.prop_items())


if __name__ == "__main__":
    import doctest

    doctest.testmod()
