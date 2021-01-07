from __future__ import annotations

from nansi.plugins.action.compose import ComposeAction

# TODO  args conversion needs an improper..?

DEFAULTS = dict(
    path = '/etc/ssl/certs/dhparam.pem',
)

class ActionModule(ComposeAction):
    def compose(self):
        self.tasks.openssl_dhparam( **self.collect_args(defaults=DEFAULTS) )
