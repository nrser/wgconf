from __future__ import annotations
from pathlib import Path
import os.path

import yaml

from nansi.plugins.action.compose import ComposeAction
from nansi.plugins.action.args.all import Arg, OpenArgsBase


def role_path(rel_path):
    return Path(__file__).parent.parent.parent / "roles" / "nginx" / rel_path

# *&$%^&^ do I really have to do this to make it clean..?
class Defaults:
    @staticmethod
    def all():
        if hasattr(Defaults, "_all"):
            return getattr(Defaults, "_all")
        with role_path("defaults/main.yaml").open("r") as file:
            defaults = yaml.safe_load(file)
        setattr(Defaults, "_all", defaults)
        return defaults

    @staticmethod
    def get(name: str):
        return Defaults.all()[f"nginx_{name}"]


def role_default(args, arg):
    return Defaults.get(arg.name)

class CommonArgs:
    config_dir = Arg(str, role_default)
    run_dir = Arg(str, role_default)
    log_dir = Arg(str, role_default)
    exe = Arg(str, role_default)
    user = Arg(str, role_default)
    proxy_websockets = Arg(bool, role_default)

class Args(OpenArgsBase, CommonArgs):
    src = Arg(str, str(role_path("templates/nginx.conf")))
    dest = Arg(str, lambda self, _: self.default_dest())

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
