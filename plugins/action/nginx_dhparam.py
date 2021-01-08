from __future__ import annotations

from nansi.plugins.action.compose import ComposeAction
from nansi.plugins.action.args import Arg, OpenArgsBase

class Args(OpenArgsBase):
    path = Arg(str, "/etc/ssl/certs/dhparam.pem")

class ActionModule(ComposeAction):
    def compose(self):
        self.tasks.openssl_dhparam(
            **Args(self._task.args, self._task_vars).to_dict()
        )