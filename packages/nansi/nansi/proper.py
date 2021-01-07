"""
Typed properties, with optional defaults and cast functions.
"""

# pylint: disable=redefined-builtin,invalid-name,redefined-outer-name

from __future__ import annotations
from typing import *
import logging

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

    def _try_cast(self, instance, value):
        if self.cast is not None:
            # try:
            return self.cast(instance, value)
            #
            # This is hard as hell to track down if `cast` is being used as a
            # `T -> T` transform!?!?!
            #
            # pylint: disable=broad-except
            # except Exception:
            #     log.error(
            #         f"prop {self.__str__(instance)} raised casting value "
            #         + repr(value),
            #         exc_info=exc_info(),
            #     )
        return value

    def _get(self, instance):
        _name, attr_name = self._names(instance)

        # Need this to handle defaults that reference other defaults
        if not hasattr(instance, attr_name):
            self._set_to_default(instance, context="get")

        return getattr(instance, attr_name)

    def _set(self, instance, value) -> None:
        name, attr_name = self._names(instance)

        value = self._try_cast(instance, value)

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

        # Since if default behaves different than given value it's weird in
        # practice
        value = self._try_cast(instance, self._get_default(instance))

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
            props[name]._set(self, value)
            del props[name]

        for name, p in props.items():
            # Since setting a prop to it's default may cause other props to be
            # set to their default we check that the attribute is missing before
            # setting
            if not hasattr(self, f"_{name}"):
                p._set_to_default(self)

    def to_dict(self) -> Dict[str, Any]:
        return {
            name: getattr(self, name)
            for name in self.__class__.iter_prop_names()
        }
