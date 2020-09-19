from __future__ import annotations
from collections.abc import Mapping

from nansi.plugins.compose_action import ComposeAction

DEFAULTS = dict(
    path = '/etc/ssl/certs/dhparam.pem',
)

class ActionModule(ComposeAction):
    def compose(self):
        self.run_task(
            'openssl_dhparam',
            **self.compose_args(defaults=DEFAULTS)
        )
