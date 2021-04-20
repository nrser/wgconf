from typing import Callable, Dict, Optional

from nansi.os_resolve import RESOLVE_ORDER, os_map_resolve
from nansi.utils.collections import bury

from .compose import ComposeAction

class OSResolveAction(ComposeAction):
    class MatchMethod:
        def __init__(
            self,
            target: Callable,
            *,
            distribution: Optional[str]=None,
            version: Optional[str]=None,
            release: Optional[str]=None,
            family: Optional[str]=None,
            system: Optional[str]=None,
            kernel: Optional[str]=None,
            all: bool=False,
        ):
            # pylint: disable=redefined-builtin
            self.target = target
            self.distribution = distribution
            self.version = version
            self.release = release
            self.family = family
            self.system = system
            self.kernel = kernel
            self.all = all
            self.key_path = self._compute_key_path()

        def _compute_key_path(self):
            """
            >>> OSResolveAction.MatchMethod(
            ...     lambda x: f"x: {x}",
            ...     family="debian",
            ... ).key_path
            ['family', 'debian']

            >>> OSResolveAction.MatchMethod(
            ...     lambda x: f"x: {x}",
            ...     distribution="macos",
            ...     version="10.14",
            ... ).key_path
            ['distribution', 'macos', 'version', '10.14']

            >>> OSResolveAction.MatchMethod(
            ...     lambda x: f"x: {x}",
            ...     distribution="macos",
            ...     version="10.14",
            ... ).key_path
            ['distribution', 'macos', 'version', '10.14']
            """
            for names in RESOLVE_ORDER:
                key_path = []
                for name in names:
                    if value := getattr(self, name):
                        key_path.append(name)
                        key_path.append(value)
                if len(key_path) > 0:
                    return key_path
            if self.all:
                return ["all"]
            mapping = {k: v for k, v in self.__dict__ if v is not None}
            raise ValueError(
                f"Invalid valid OS resolve mapping: {mapping}"
            )

        def __call__(self, *args, **kwds):
            self.target(*args, **kwds)


    @classmethod
    def map(cls, **mapping: Dict[str, Optional[str]]):
        def decorator(target):
            return cls.MatchMethod(target, **mapping)
        return decorator

    @classmethod
    def mapping(cls):
        mapping = {}
        for name in dir(cls):
            value = getattr(cls, name)
            if isinstance(value, cls.MatchMethod):
                bury(mapping, value.key_path, value)
        return mapping

    def compose(self):
        os_map_resolve(
            self._task_vars["ansible_facts"],
            self.__class__.mapping()
        )(self)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
