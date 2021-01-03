from __future__ import annotations
from typing import *

from nansi.plugins.compose_action import ComposeAction
from nansi.proper import Proper, prop
from nansi.os_resolve import os_map_resolve

GO_ARCH_MAP = {
    "i386": "386",
    "x86_64": "amd64",
    "aarch64": "arm64",
    "armv7l": "armv7",
    "armv6l": "armv6",
}

class Args(Proper):
    state   = prop( Literal['present', 'absent'], 'present' )
    version = prop( str )

class DebianArgs(Args):
    name        = prop( str, 'esl-erlang' )
    key_url     = prop( str, "https://packages.erlang-solutions.com/ubuntu/erlang_solutions.asc" )
    key_id      = prop( str, "2C8B586B1FC61E31C836D7B450B12719341540CB" )
    repo        = prop( str, "deb https://packages.erlang-solutions.com/ubuntu {release} contrib" )

    def format_repo(self, task_vars) -> str:
        arch = task_vars["ansible_facts"]["architecture"]
        subs = {
            "arch": task_vars["ansible_facts"]["architecture"],
            "system": task_vars["ansible_facts"]["system"].lower(),
            "release": task_vars["ansible_facts"]["distribution_release"].lower(),
            "version": self.version,
        }
        if arch in GO_ARCH_MAP:
            subs["go_arch"] = GO_ARCH_MAP[arch]
        return self.repo.format(**subs)

class ActionModule(ComposeAction):
    def os_family_debian(self):
        args = DebianArgs(**self._task.args)

        # TODO  Can / should this use `apt_ext`? Some work/decisions required...
        self.tasks.apt_key(
            state   = args.state,
            id      = args.key_id.replace(' ', ''),
            url     = args.key_url,
        )

        self.tasks.apt_repository(
            state           = args.state,
            repo            = args.format_repo(self._task_vars),
            update_cache    = (args.state == 'present'),
        )

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
