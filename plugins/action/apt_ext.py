from __future__ import annotations
from collections.abc import Mapping
from typing import *

from nansi.plugins.compose_action import ComposeAction
from nansi.proper import Proper, prop

class AptExt(Proper):
    STATE_TYPE = Literal[ 'present', 'absent' ]

    state   = prop( STATE_TYPE, 'present' )
    key_url = prop( str )
    key_id  = prop( str )
    repo    = prop( str )
    name    = prop.one_or_more( str ) #, aliases=('pkg') )

class ActionModule(ComposeAction):
    def compose(self):
        apt_ext = AptExt(**self._task.args)

        self.tasks.apt_key(
            state   = apt_ext.state,
            id      = apt_ext.key_id.replace(' ', ''),
            url     = apt_ext.key_url,
        )

        self.tasks.apt_repository(
            state           = apt_ext.state,
            repo            = apt_ext.repo,
            update_cache    = (apt_ext.state == 'present'),
        )

        self.tasks.apt(
            name    = apt_ext.name,
            state   = apt_ext.state,
        )

