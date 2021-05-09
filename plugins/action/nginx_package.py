from __future__ import annotations
from typing import Dict, Literal, Optional

from nansi.plugins.action.compose import ComposeAction
from nansi.os_resolve import os_map_resolve
from nansi.plugins.action.args.all import Arg, OpenArgsBase


class Args(OpenArgsBase):
    state = Arg(Literal["present", "absent"], "present")
    version = Arg(Optional[str])


class DebianArgs(Args):
    names = Arg.one_or_more(
        str, ["nginx", "nginx-common"], alias=("name", "pkg")
    )

    def apt_ext_args(self) -> Dict:
        # pylint: disable=not-an-iterable
        return dict(
            names=[
                name
                if self.version is None
                else dict(name=name, version=self.version)
                for name in self.names
            ],
            state=self.state,
            **self.extras()
        )


class ActionModule(ComposeAction):
    def os_family_debian(self):
        self.tasks["nrser.nansi.apt_ext"](
            **DebianArgs(self._task.args, self._task_vars).apt_ext_args()
        )

    def compose(self):
        os_map_resolve(
            self._task_vars["ansible_facts"],
            {
                "family": {
                    "debian": self.os_family_debian,
                }
            },
        )()
