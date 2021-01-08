from __future__ import annotations
from typing import *
from pathlib import Path
import os.path
from operator import methodcaller

from nansi.plugins.action.compose import ComposeAction
from nansi.plugins.action.args import Arg, OpenArgsBase


def role_path(rel_path):
    return str(
        Path(__file__).parent.parent.parent / "roles" / "nginx" / rel_path
    )


class CommonArgs:
    config_dir = Arg(str, "/etc/nginx")
    run_dir = Arg(str, "/run")
    log_dir = Arg(str, "/var/log/nginx")
    user = Arg(str, "www-data")
    proxy_websockets = Arg(bool, False)

class Args(OpenArgsBase, CommonArgs):
    src = Arg(str, role_path("templates/nginx.conf"))
    dest = Arg(str, methodcaller("default_dest"))

    def default_dest(self):
        return os.path.join(self.config_dir, "nginx.conf")


class ActionModule(ComposeAction):
    def compose(self):
        args = Args(self._task.args, self._task_vars)
        self.tasks.template.add_vars(
            dir=str(Path(args.dest).parent),
            run_dir=args.run_dir,
            log_dir=args.log_dir,
            user=args.user,
            proxy_websockets=args.proxy_websockets,
        )(src=args.src, dest=args.dest, **args.extras())
