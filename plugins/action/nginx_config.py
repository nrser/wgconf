from __future__ import annotations
from typing import *
from pathlib import Path

from nansi.plugins.action.compose import ComposeAction

# TODO  Get rid of needed vars

def role_path(rel_path):
    return str(
        Path(__file__).parent.parent.parent / "roles" / "nginx" / rel_path
    )


class ActionModule(ComposeAction):
    def compose(self):
        defaults = {
            "src": role_path("templates/nginx.conf"),
            "dest": str(
                Path(self._var_values["nginx_config_dir"]) / "nginx.conf"
            ),
            "backup": True,
        }

        args = self.collect_args(
            omit_vars="nginx_config_dir",  # Not a `template` task arg
            defaults=defaults,
        )

        self.tasks.template.add_vars(
            dir=str(Path(self.render(args["dest"])).parent),
        )(**args)
