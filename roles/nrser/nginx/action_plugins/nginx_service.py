from __future__ import annotations

from nansi.plugins.compose_action import ComposeAction

DEFAULTS = dict(
    name        = 'nginx',
    enabled     = True,
    state       = 'started',
)

class ActionModule(ComposeAction):
    def compose(self):
        self.tasks.service( **self.collect_args(defaults=DEFAULTS) )
