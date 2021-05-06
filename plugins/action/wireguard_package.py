from __future__ import annotations
from typing import Literal, Optional
import logging

from nansi.plugins.action.os_resolve import OSResolveAction
from nansi.plugins.action.args.all import Arg, ArgsBase

LOG = logging.getLogger(__name__)


class Args(ArgsBase):
    state = Arg(Literal["present", "absent"], "present")
    version = Arg(Optional[str], None)


class DebianArgs(Args):
    name = Arg(str, "wireguard")

    @property
    def names(self):
        if self.version is None:
            return self.name
        return dict(name=self.name, version=self.version)


class ActionModule(OSResolveAction):
    @OSResolveAction.map(family="debian")
    def debian(self):
        args = DebianArgs(self._task.args, self._task_vars)
        self.tasks["nrser.nansi.apt_ext"](names=args.names, state=args.state)
