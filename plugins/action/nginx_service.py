from __future__ import annotations

from nansi.plugins.action.compose import ComposeAction

# TODO  Is this even needed..?

DEFAULTS = dict(
    name        = 'nginx',
    enabled     = True,
    state       = 'started',
)

class ActionModule(ComposeAction):
    def compose(self):
        self.tasks.service( **self.collect_args(defaults=DEFAULTS) )
