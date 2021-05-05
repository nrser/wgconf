from typing import Any, Dict, Generator, Tuple
import collections.abc

from .base import ArgsBase

class OpenArgsBase(ArgsBase, collections.abc.Mapping):
    def __init__(self, values, parent=None):
        prop_values = {
            name: value
            for name, value in values.items()
            if self.__class__.is_prop(name)
        }

        ArgsBase.__init__(self, prop_values, parent=parent)

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

