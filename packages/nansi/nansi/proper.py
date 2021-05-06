"""
Typed properties, with optional defaults and cast functions.
"""

from __future__ import annotations
from typing import *
from abc import ABC, abstractmethod

from typeguard import check_type

from nansi import logging

# pylint: disable=redefined-builtin,invalid-name

LOG = logging.getLogger(__name__)

TValue = TypeVar("TValue")
TInput = TypeVar("TInput")

class PropTypeError(TypeError):
    def __init__(self, message, value, instance, prop, context=None):
        super().__init__(message)
        self.instance = instance
        self.prop = prop
        self.context = context


class PropInitError(ValueError):
    def __init__(self, message, instance, name, value):
        super().__init__(message)
        self.instance = instance
        self.name = name
        self.value = value


class Prop(Generic[TValue, TInput]):
    """
    Extension of the built-in `property` that adds support for:

    1.  Typed values which are runtime checked during set.
    2.  Default values and callables that produce them.
    3.  Cast callables that convert values during set.

    Designed to be used with classes extending `Proper`.
    """

    _type: Type[TValue]
    _default_value: Optional[TInput]
    _get_default: Optional[Callable[[Any, Prop, TInput], TValue]]
    _cast: Optional[Callable[[Any, Prop, TInput], TValue]]

    def __init__(
        self,
        type: Type[TValue],
        default: Union[None, TInput, Callable[[Any, Prop, TInput], TValue]]=None,
        *,
        cast: Optional[Callable[[Any, Prop, TInput], TValue]]=None,
        default_value: Optional[TInput]=None,
        get_default: Optional[Callable[[Any, Prop], TInput]]=None,
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
            self.set_to_default(instance, context="__get__")

        return getattr(instance, self.attr_name)

    def __set__(self, instance, value) -> None:
        value = self.cast(instance, value)

        self.check_type(
            value,
            instance=instance,
            context="__set__",
            message=("Failed to set {name}, given a {value_type}: {value}"),
        )

        setattr(instance, self.attr_name, value)

    def __delete__(self, instance) -> None:
        self.set_to_default(instance, context="__delete__")

    @property
    def name(self) -> str:
        return self._name

    @property
    def attr_name(self) -> str:
        return self._attr_name

    @property
    def owner(self) -> Type:
        return self._owner

    @property
    def full_name(self) -> str:
        return ".".join((self.owner.__module__, self.owner.__name__, self.name))

    @property
    def type(self) -> Type[TValue]:
        return self._type

    def test_type(self, value: Any) -> bool:
        try:
            check_type("", value, self._type)
        except TypeError:
            return False
        return True

    def check_type(
        self,
        value: Any,
        *,
        instance=None,
        message=None,
        context=None
    ):
        try:
            check_type("", value, self._type)
        except TypeError:
            if message is None:
                message = (
                    "`{name}` check failed for value of type "
                    "{value_type}: {value}"
                )
            # pylint: disable=raise-missing-from
            raise PropTypeError(
                message.format(
                    name=self.__str__(instance),
                    value_type=type(value),
                    value=repr(value),
                ),
                value=value,
                prop=self,
                instance=instance,
                context=context,
            )

    def default(self, instance):
        if self._get_default is not None:
            return self._get_default(instance, self)
        return self._default_value

    def set_to_default(self, instance, *, context="set_to_default") -> None:
        default = self.default(instance)
        value = self.cast(instance, default)

        self.check_type(
            value,
            instance=instance,
            context=context,
            message=(
                "Failed to set {name} to default, got a {value_type}: {value}"
            ),
        )

        setattr(instance, self.attr_name, value)

    def cast(self, instance, value):
        if self._cast is not None:
            return self._cast(
                value,
                self.type,
                instance=instance,
                prop=self,
            )
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


class Proper(ABC):
    @classmethod
    def is_prop(cls, name: str) -> bool:
        if not isinstance(name, str):
            raise TypeError(
                f"Names must be str, given {type(name)}: {repr(name)}"
            )
        return isinstance(getattr(cls, name, None), Prop)

    @classmethod
    def iter_props(cls) -> Generator[Tuple[str, Prop], None, None]:
        for name in dir(cls):
            if cls.is_prop(name):
                yield (name, getattr(cls, name))

    @classmethod
    def iter_prop_names(cls) -> Generator[str, None, None]:
        for name in dir(cls):
            if cls.is_prop(name):
                yield name

    @classmethod
    def props(cls) -> Dict[str, Prop]:
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

        for name, prop in props.items():
            # Since setting a prop to it's default may cause other props to be
            # set to their default we check that the attribute is missing before
            # setting
            if not hasattr(self, prop.attr_name):
                prop.set_to_default(self, context="Proper.__init__")

    def to_dict(self) -> Dict[str, Any]:
        return {
            name: getattr(self, name)
            for name in self.__class__.iter_prop_names()
        }
