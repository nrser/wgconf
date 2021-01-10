"""
Typed properties, with optional defaults and cast functions.
"""

# pylint: disable=redefined-builtin,invalid-name,redefined-outer-name

from __future__ import annotations
from typing import *
import logging

from typeguard import check_type


LOG = log = logging.getLogger(__name__)


class PropTypeError(TypeError):
    def __init__(
        self, message, value, owner, name, type, instance, context=None
    ):
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


class prop:
    """
    Extension of the built-in `property` that adds support for:

    1.  Typed values which are runtime checked during set.
    2.  Default values and callables that produce them.
    3.  Cast callables that convert values during set.

    Designed to be used with classes extending `Proper`.
    """

    def __init__(
        self,
        type,
        default=None,
        *,
        cast=None,
        default_value=None,
        get_default=None,
    ):
        self._type = type

        if default is not None:
            if callable(default):
                get_default = default
            else:
                default_value = default

        self._default_value = default_value
        self._get_default = get_default

        self._cast = cast

    def __set_name__(self, owner, name):
        # pylint: disable=attribute-defined-outside-init
        self._owner = owner
        self._name = name
        self._attr_name = "_" + name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

        # Need this to handle defaults that reference other defaults
        if not hasattr(instance, self.attr_name):
            self.set_to_default(instance, _context="get")

        return getattr(instance, self.attr_name)

    def __set__(self, instance, value) -> None:
        value = self.cast(instance, value)

        self.check_type(
            value,
            _instance=instance,
            _context="__set__",
            _message=("Failed to set {name}, given a {value_type}: {value}"),
        )

        setattr(instance, self.attr_name, value)

    def __delete__(self, instance) -> None:
        self.set_to_default(instance, _context="__delete__")

    @property
    def name(self):
        return self._name

    @property
    def attr_name(self):
        return self._attr_name

    @property
    def owner(self):
        return self._owner

    @property
    def full_name(self) -> str:
        return ".".join((self.owner.__module__, self.owner.__name__, self.name))

    @property
    def type(self):
        return self._type

    def check_type(
        self, value, *, _instance=None, _message=None, _context=None
    ):
        try:
            check_type("", value, self._type)
        except TypeError:
            if _message is None:
                _message = (
                    "`{name}` check failed for value of type "
                    "{value_type}: {value}"
                )
            message = _message.format(
                name=self.__str__(_instance),
                # type=self.type,
                value_type=type(value),
                value=repr(value),
            )
            # pylint: disable=raise-missing-from
            raise PropTypeError(
                message,
                value=value,
                owner=self.owner,
                name=self.name,
                type=self.type,
                instance=_instance,
                context=_context,
            )

    def default(self, instance):
        if self._get_default is not None:
            return self._get_default(instance, self.name)
        return self._default_value

    def set_to_default(self, instance, *, _context="set_to_default") -> None:
        default = self.default(instance)
        value = self.cast(instance, default)

        self.check_type(
            value,
            _instance=instance,
            _context=_context,
            _message=(
                "Failed to set {name} to default, got a {value_type}: {value}"
            ),
        )

        setattr(instance, self.attr_name, value)

    def cast(self, instance, value):
        if self._cast is not None:
            return self._cast(instance, self.name, value)
        return value

    def __str__(self, instance=None) -> str:
        if instance is None:
            name = self.full_name
        else:
            name = ".".join(
                (
                    instance.__class__.__module__,
                    instance.__class__.__name__,
                    self.name,
                )
            )
        return f"{name}: {self.type}"


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
                    f"No property {name} on {self.__class__}",
                    instance=self,
                    name=name,
                    value=value,
                )
            props[name].__set__(self, value)
            del props[name]

        for name, p in props.items():
            # Since setting a prop to it's default may cause other props to be
            # set to their default we check that the attribute is missing before
            # setting
            if not hasattr(self, p.attr_name):
                p.set_to_default(self)

    def to_dict(self) -> Dict[str, Any]:
        return {
            name: getattr(self, name)
            for name in self.__class__.iter_prop_names()
        }
