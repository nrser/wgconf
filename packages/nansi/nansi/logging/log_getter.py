"""Defines `LogGetter` class."""

from functools import wraps
import logging
from typing import Any, Callable
from inspect import isfunction, isclass, unwrap
from warnings import warn

def is_unbound_method_of(fn: Callable, obj: Any) -> bool:
    # We want to work with the original function, unwrapping any decorators
    unwrapped_fn = unwrap(fn)

    # The user can pass a class or an instance value, so figure out what the
    # class is
    cls = obj if isclass(obj) else obj.__class__

    # Source function gotta have a name for us to find it on the class
    if not hasattr(unwrapped_fn, "__name__"):
        return False
    attr_name = unwrapped_fn.__name__

    # If class doesn't have an attribute named the same as the function then it
    # sure can't have the function as it's value
    if not hasattr(cls, attr_name):
        return False
    attr_value = getattr(cls, attr_name)

    # If the attribute value is not a function, then it can't be our function
    # either
    if not isfunction(attr_value):
        return False

    # Finally, unwrap the value from got from the class and see if it's the same
    return unwrap(attr_value) is unwrapped_fn

class LogGetter:
    """\
    Proxy to `logging.Logger` instance that defers construction until use.

    This allows things like:

        LOG = logging.getLogger(__name__)

    at the top scope in files, where it is processed _before_ `setup()` is
    called to switch the logger class. Otherwise, those global definitions would
    end up being regular `logging.Logger` classes that would not support the
    "keyword" log method signature we prefer to use.

    See `KwdsLogger` and `getLogger`.
    """

    name: str

    def __init__(self, *name: str):
        self.name = ".".join(name)

        if (
            self.name.startswith("nrser.nansi.") or
            self.name.startswith("ansible_collections.nrser.nansi.")
        ):
            warn(f"Using weird name: {self.name}")

    @property
    def _logger(self) -> logging.Logger:
        return logging.getLogger(self.name)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._logger, name)

    def getChild(self, name):
        return LogGetter(f"{self.name}.{name}")

    def inject(self, fn):
        @wraps(fn)
        def log_inject_wrapper(*args, **kwds):
            if "log" in kwds:
                return fn(*args, **kwds)
            else:
                return fn(*args, log=self.getChild(fn.__name__), **kwds)

        return log_inject_wrapper
