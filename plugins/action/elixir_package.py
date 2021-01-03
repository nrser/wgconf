from __future__ import annotations
from typing import *

from nansi.plugins.compose_action import ComposeAction
from nansi.proper import Proper, prop
from nansi.os_resolve import os_map_resolve

class Args(Proper):
    name            = prop( str, 'elixir' )
    state           = prop( Literal['present', 'absent'], 'present' )
    version         = prop( str )

class ActionModule(ComposeAction):
    def os_family_debian(self):
        args = Args(**self._task.args)

        self.tasks["nrser.nansi.apt_version"](
            state = args.state,
            name = args.name,
            version = args.version,
        )

    def compose(self):
        # TODO Implement this..?
        # os_method_resolve(self._task_vars["ansible_facts"], self)()
        methods = {
            'family': {
                'debian': self.os_family_debian,
            }
        }
        os_map_resolve(self._task_vars['ansible_facts'], methods)()
