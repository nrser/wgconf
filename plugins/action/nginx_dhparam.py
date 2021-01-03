from __future__ import annotations

from nansi.plugins.compose_action import ComposeAction

DEFAULTS = dict(
    path = '/etc/ssl/certs/dhparam.pem',
)

class ActionModule(ComposeAction):
    def compose(self):
        self.tasks.openssl_dhparam( **self.collect_args(defaults=DEFAULTS) )
