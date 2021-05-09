from __future__ import annotations
from typing import Literal

from nansi.plugins.action.compose import ComposeAction
from nansi.plugins.action.args.all import Arg, ArgsBase
from nansi.os_resolve import os_map_resolve

class Args(ArgsBase):
    name            = Arg( str, 'elixir' )
    state           = Arg( Literal['present', 'absent'], 'present' )
    version         = Arg( str )

class ActionModule(ComposeAction):
    def os_family_debian(self):
        args = Args(self._task.args, parent=self)

        self.tasks["nrser.nansi.apt_version"](
            packages = dict(
                name = args.name,
                version = args.version,
            ),
        )

    def compose(self):
        methods = {
            'family': {
                'debian': self.os_family_debian,
            }
        }
        os_map_resolve(self._task_vars['ansible_facts'], methods)()
