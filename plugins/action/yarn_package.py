from __future__ import annotations
from typing import Literal, Optional

from nansi.plugins.action.compose import ComposeAction
from nansi.plugins.action.args.all import Arg, ArgsBase
from nansi.os_resolve import os_map_resolve

class Args(ArgsBase):
    state   = Arg( Literal['present', 'absent'], 'present' )
    version = Arg( Optional[str] )

class DebianArgs(Args):
    name        = Arg( str, "yarn" )
    key_url     = Arg( str, "https://dl.yarnpkg.com/debian/pubkey.gpg" )
    key_id      = Arg( str, "DE5786295D8C497E4D99124102820C39D50AF136" )
    repo        = Arg( str, "deb https://dl.yarnpkg.com/debian/ stable main" )

    @property
    def apt_ext_name(self):
        if self.version is None:
            return self.name
        return dict(name=self.name, version=self.version)

class ActionModule(ComposeAction):
    def os_family_debian(self):
        args = DebianArgs(self._task.args, self._task_vars)

        self.tasks["nrser.nansi.apt_ext"](
            name = args.apt_ext_name,
            state = args.state,
            key_url = args.key_url,
            key_id = args.key_id,
            repo = args.repo,
        )

    def compose(self):
        os_map_resolve(
            self._task_vars['ansible_facts'],
            {
                'family': {
                    'debian': self.os_family_debian,
                }
            }
        )()
