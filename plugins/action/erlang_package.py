from __future__ import annotations
from typing import Literal

from nansi.plugins.action.compose import ComposeAction
from nansi.plugins.action.args.all import Arg, ArgsBase, os_fact_formatter
from nansi.os_resolve import os_map_resolve

class Args(ArgsBase):
    state   = Arg( Literal['present', 'absent'], 'present' )
    version = Arg( str )

class DebianArgs(Args):
    name        = Arg(  str,
                        "esl-erlang" )
    key_url     = Arg(  str,
                        "https://packages.erlang-solutions.com"
                        "/ubuntu/erlang_solutions.asc" )
    key_id      = Arg(  str,
                        "2C8B586B1FC61E31C836D7B450B12719341540CB" )
    repo        = Arg(  str,
                        "deb https://packages.erlang-solutions.com/ubuntu "
                        "{release} contrib",
                        cast=os_fact_formatter() )

    @property
    def apt_ext_names(self):
        if self.version is None:
            return self.name
        return dict(name=self.name, version=self.version)

class ActionModule(ComposeAction):
    def os_family_debian(self):
        args = DebianArgs(self._task.args, self._task_vars)

        self.tasks["nrser.nansi.apt_ext"](
            names = args.apt_ext_names,
            state = args.state,
            key_url = args.key_url,
            key_id = args.key_id,
            repository_repo = args.repo,
        )

    def compose(self):
        methods = {
            'family': {
                'debian': self.os_family_debian,
            }
        }
        os_map_resolve(self._task_vars['ansible_facts'], methods)()
