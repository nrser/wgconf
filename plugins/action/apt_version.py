from __future__ import annotations
from collections.abc import Mapping
from typing import *

from nansi.plugins.compose_action import ComposeAction
from nansi.proper import Proper, prop

STATE_TYPE = Literal[ 'present', 'absent' ]

class PackageArgs(Proper):

    @classmethod
    def cast(cls, value):
        return cls(**value)

    state       = prop( Optional[STATE_TYPE] )
    name        = prop( str )
    version     = prop( Optional[str] )

class Args(Proper):
    state       = prop( STATE_TYPE, 'present' )
    packages    = prop.one_or_more( PackageArgs, item_cast=PackageArgs.cast )

    def __init__(self, **values):
        if 'packages' not in values:
            values = dict(packages=values)
        super().__init__(**values)


class ActionModule(ComposeAction):
    def compose(self):
        args = Args(**self._task.args)

        apt_versions = self.tasks['nrser.nansi.apt_version_resolve'](
            packages = [
                dict(name=p.name, version=p.version) for p in args.packages
            ]
        )

        by_state = {}
        for pkg_args, name in zip(args.packages, apt_versions["names"]):
            if pkg_args.state is None:
                state = args.state
            else:
                state = pkg_args.state
            if state not in by_state:
                by_state[state] = []
            by_state[state].append(name)

        for state, names in by_state.items():
            self.tasks.apt(
                state   = state,
                name    = names,
            )
