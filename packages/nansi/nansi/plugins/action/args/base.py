from __future__ import annotations
from typing import Any, Dict, Generator, Tuple, Union
from abc import ABC

from typeguard import check_type

from nansi.proper import Proper, Prop
from nansi.utils.aliases import de_aliased
from nansi.template.var_values import VarValues
from nansi.plugins.action.compose import ComposeAction

from .jsos import JSOSType, jsos_for


class ArgsBase(Proper, ABC):
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

    @classmethod
    def each_prop_item(
        cls, instance
    ) -> Generator[Tuple[Prop, Any], None, None]:
        for name, prop in cls.iter_props():
            yield (prop, getattr(instance, name))

    # task_vars: Mapping
    parent: Union[None, ComposeAction, ArgsBase]

    def __init__(self, values, parent=None):
        check_type("parent", parent, Union[None, ComposeAction, ArgsBase])
        self.parent = parent
        super().__init__(
            **de_aliased(
                aliases=self.__class__.prop_aliases(),
                src=values,
            )
        )

    @property
    def vars(self) -> VarValues:
        """
        Reach up through the parent chain to get Ansible variable values.

        Returns a [VarValues][], which is a [Mapping][] that renders raw task
        variables into values on-demand.

        The raw vars [dict][] is accessible as [VarValues#raw][].

        If this [ArgsBase][] does not have a [ArgsBase#parent][] (e.g. it is
        `None`), then there is no way to reach the task vars, and a
        [RuntimeError][] will be raised.

        [ArgsBase]: nansi.plugins.action.args.base.ArgsBase
        [dict]: builtins.dict
        [Mapping]: collections.abc.Mapping
        [RuntimeError]: builtins.RuntimeError
        [VarValues]: nansi.template.var_values.VarValues
        [VarValues#raw]: nansi.template.var_values.VarValues.raw
        """
        if self.parent is None:
            raise RuntimeError(f"{self} has no parent, can't get vars")
        return self.parent.vars

    def to_jsos(self) -> Dict[str, JSOSType]:
        return {
            prop.name: jsos_for(value)
            for prop, value in self.__class__.each_prop_item(self)
            if value is not None
        }
