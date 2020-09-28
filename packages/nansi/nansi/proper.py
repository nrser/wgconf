from __future__ import annotations
from typing import *
from collections import namedtuple
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
        return (name, '_' + name)
    
    def _check_type(self, instance, name, value, context, message):
        try:
            check_type("", value, self.type)
        except TypeError:
            if callable(message):
                message = message()
            raise PropTypeError(
                message, instance=instance, name=name, type=self.type,
                value=value, context=context,
            )
    
    def _get_default(self, instance):
        default = self.default
        if callable(default):
            default = default(instance)
        return default
    
    def _test_default(self, instance):
        try:
            check_type("", self._get_default(instance), self.type)
        except TypeError:
            return False
        return True
    
    def _try_cast(self, value):
        if self.cast is not None:
            try:
                return self.cast(value)
            except StandardError as error:
                # TODO Issue warning
                pass
        return value
    
    def _get(self, instance):
        name, attr_name = self._names(instance)
        is_default = True
        
        if hasattr(instance, attr_name):
            value = getattr(instance, attr_name)
            is_default = False
        else:
            value = self._get_default(instance)
        
        self._check_type(instance, name, value, 'get', lambda: (
            f"Uh-oh! {'Default' if is_default else 'Stored'} value for prop " +
            f"{name} on {instance} is not typing {self.type}, got a " +
            f"{type(value)}: {repr(value)}"
        ))
        
        return value
    
    def _set(self, instance, value) -> None:
        name, attr_name = self._names(instance)
        
        value = self._try_cast(value)
        
        self._check_type(instance, name, value, 'set', lambda: (
            f"{instance.__class__.__name__}#{name} must be of typing " +
            f"{self.type}, given a {type(value)}: {repr(value)}"
        ))
        
        setattr(instance, attr_name, value)

class Proper:    
    @classmethod
    def is_prop(self, name) -> bool:
        return isinstance(getattr(self, name, None), prop)
    
    @classmethod
    def props(self) -> Dict[str, prop]:
        return {
            name: getattr(self, name)
            for name
            in dir(self)
            if self.is_prop(name)
        }
    
    def __init__(self, **values):
        props = self.__class__.props()
        for name, value in values.items():
            if name not in props:
                raise PropInitError(
                    f"No property {name} on {self.__class__.__name__}",
                    instance=self, name=name, value=value
                )
            prop = props[name]
            prop._set(self, value)
            del props[name]
        
        for name, prop in props.items():
            if prop._test_default(self) is False:
                raise PropInitError(
                    f"No value provided for prop `{name}` on " +
                    f"{self.__class__.__name__}, and default value " +
                    f"{ repr(prop._get_default(self)) } does not satisfy " +
                    f"prop typing {prop.type}",
                    instance=self, name=name, value=None
                )
    
    def is_prop_set(self, name: str) -> bool:
        return hasattr(self, '_' + name)