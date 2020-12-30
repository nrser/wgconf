"""
Typed properties, with optional defaults and cast functions.
"""

# pylint: disable=redefined-builtin,invalid-name,redefined-outer-name

from __future__ import annotations
from typing import *
import logging
from sys import exc_info
import collections.abc

from typeguard import check_type

from nansi.utils.collections import need

LOG = log = logging.getLogger(__name__)


class PropTypeError(TypeError):
    def __init__(self, message, instance, name, type, value, context=None):
        super().__init__(message)
        self.instance = instance
        self.type = type
        self.name = name
        self.value = value
        self.context = context


class PropInitError(ValueError):
    def __init__(self, message, instance, name, value):
        super().__init__(message)
        self.instance = instance
        self.name = name
        self.value = value


class prop(property):
    """
    Extension of the built-in `property` that adds support for:

    1.  Typed values which are runtime checked during set.
    2.  Default values and callables that produce them.
    3.  Cast callables that convert values during set.

    Designed to be used with classes extending `Proper`.
    """

    def __init__(self, type, default=None, cast=None):
        super().__init__(self._get, self._set)

        self.type = type
        self.default = default
        self.cast = cast

    def _name(self, instance) -> str:
        return need(
            lambda name: getattr(instance.__class__, name, None) is self,
            dir(instance.__class__),
        )

    def _names(self, instance) -> str:
        name = self._name(instance)
        return (name, "_" + name)

    def _check_type(self, instance, name, value, context, message):
        try:
            check_type("", value, self.type)
        except TypeError:
            if callable(message):
                message = message()
            # pylint: disable=raise-missing-from
            raise PropTypeError(
                message,
                instance=instance,
                name=name,
                type=self.type,
                value=value,
                context=context,
            )

    def _get_default(self, instance):
        default = self.default
        if callable(default):
            default = default(instance)
        return default

    def _try_cast(self, value, instance=None):
        if self.cast is not None:
            try:
                return self.cast(value)
            # pylint: disable=broad-except
            except Exception:
                log.error(
                    f"prop {self.__str__(instance)} raised casting value "
                    + repr(value),
                    exc_info=exc_info(),
                )
        return value

    def _get(self, instance):
        _name, attr_name = self._names(instance)

        # Need this to handle defaults that reference other defaults
        if not hasattr(instance, attr_name):
            self._set_to_default(instance, context="get")

        return getattr(instance, attr_name)

    def _set(self, instance, value) -> None:
        name, attr_name = self._names(instance)

        value = self._try_cast(value)

        self._check_type(
            instance,
            name,
            value,
            "set",
            lambda: (
                f"{instance.__class__.__name__}#{name} must be of typing "
                + f"{self.type}, given a {type(value)}: {repr(value)}"
            ),
        )

        setattr(instance, attr_name, value)

    def _set_to_default(
        self, instance, context: str = "set_to_default"
    ) -> None:
        name, attr_name = self._names(instance)

        value = self._get_default(instance)

        self._check_type(
            instance,
            name,
            value,
            context,
            lambda: (
                f"{instance.__class__.__name__}#{name} default does not "
                f"satisfy type {self.type}, given a "
                f"{type(value)}: {repr(value)}"
            ),
        )

        setattr(instance, attr_name, value)

    def _del(self, instance) -> None:
        self._set_to_default(instance, "del")

    def __str__(self, instance=None) -> str:
        if instance is None:
            return f"???.???: {self.type}"
        else:
            return f"{instance.__class__}.{self._name(instance)}: {self.type}"

    @classmethod
    def one_or_more(cls, item_type, default=None, item_cast=None):
        def cast(value):
            if not isinstance(value, list):
                value = [value]
            if item_cast is None:
                return value
            return [item_cast(item) for item in value]

        return cls(List[item_type], default=default, cast=cast)

    @classmethod
    def zero_or_more(cls, item_type, default=lambda _: [], item_cast=None):
        def cast(value):
            if value is None:
                return []
            if not isinstance(value, list):
                value = [value]
            if item_cast is None:
                return value
            return [item_cast(item) for item in value]

        return cls(List[item_type], default=default, cast=cast)


class Proper:
    @classmethod
    def is_prop(cls, name: str) -> bool:
        if not isinstance(name, str):
            raise TypeError(
                f"Names must be str, given {type(name)}: {repr(name)}"
            )
        return isinstance(getattr(cls, name, None), prop)

    @classmethod
    def iter_props(cls) -> Generator[Tuple[str, prop], None, None]:
        for name in dir(cls):
            if cls.is_prop(name):
                yield (name, getattr(cls, name))

    @classmethod
    def iter_prop_names(cls) -> Generator[str, None, None]:
        for name in dir(cls):
            if cls.is_prop(name):
                yield name

    @classmethod
    def props(cls) -> Dict[str, prop]:
        return dict(cls.iter_props())

    def __init__(self, **values):
        props = self.__class__.props()
        for name, value in values.items():
            if name not in props:
                raise PropInitError(
                    f"No property {name} on {self.__class__.__name__}",
                    instance=self,
                    name=name,
                    value=value,
                )
            props[name]._set(self, value)
            del props[name]

        for name, p in props.items():
            # Since setting a prop to it's default may cause other props to be
            # set to their default we check that the attribute is missing before
            # setting
            if not hasattr(self, f"_{name}"):
                p._set_to_default(self)

class Improper(Proper, collections.abc.Mapping):
    def __init__(self, **values):
        prop_values = {
            name: value
            for name, value in values.items()
            if self.__class__.is_prop(name)
        }

        Proper.__init__(self, **prop_values)

        self.__extras__ = {
            name: value
            for name, value in values.items()
            if not self.__class__.is_prop(name)
        }

    def __len__(self):
        return len(self.__class__.iter_prop_names()) + len(self.__extras__)

    def __contains__(self, key: Any) -> bool:
        return (
            isinstance(key, str) and
            (self.__class__.is_prop(key) or key in self.__extras__)
        )

    def __getitem__(self, key: Any) -> Any:
        if not isinstance(key, str):
            raise KeyError(
                f"Keys must be str, given {type(key)}: {repr(key)}"
            )
        if self.__class__.is_prop(key):
            return getattr(self, key)
        return self.__extras__[key]

    def __setitem__(self, key: str, value: Any) -> None:
        if not isinstance(key, str):
            raise TypeError(
                f"Keys must be str, given {type(key)}: {repr(key)}"
            )
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
