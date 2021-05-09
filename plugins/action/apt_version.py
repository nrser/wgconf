from __future__ import annotations
from typing import Literal, Optional

from nansi.plugins.action.compose import ComposeAction
from nansi.plugins.action.args.all import Arg, ArgsBase

class PackageArgs(ArgsBase):
    name        = Arg( str )
    version     = Arg( Optional[str] )

class Args(ArgsBase):
    state       = Arg( Literal[ 'present', 'absent' ], 'present' )
    packages    = Arg.one_or_more( PackageArgs )

    def __init__(self, values, parent=None):
        if 'packages' not in values:
            values = dict(packages=values)
        super().__init__(values, parent=parent)

class ActionModule(ComposeAction):
    def compose(self):
        args = Args(self._task.args, self._task_vars)

        apt_versions = self.tasks['nrser.nansi.apt_version_resolve'](
            packages = [
                # pylint: disable=not-an-iterable
                dict(name=p.name, version=p.version) for p in args.packages
            ]
        )

        self.tasks.apt(
            state   = args.state,
            name    = apt_versions["names"],
        )
