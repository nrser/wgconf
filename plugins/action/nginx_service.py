from __future__ import annotations
from typing import Literal

from nansi.plugins.action.compose import (
    ComposeAction,
    ComposedActionFailedError,
)
from nansi.plugins.action.args.all import Arg, OpenArgsBase

# pylint: disable=relative-beyond-top-level
from .nginx_config import CommonArgs


class Args(OpenArgsBase, CommonArgs):
    name = Arg(str, "nginx")
    state = Arg(
        Literal["reloaded", "restarted", "started", "stopped"], "started"
    )
    enabled = Arg(bool, True)
    validate = Arg(
        bool, lambda self, _: self.task_vars.get("nginx_service_validate", True)
    )


class ActionModule(ComposeAction):
    def handle_failed_result(self, task, action, result) -> None:
        if task.action == "command":
            self.log.error(
                "Nginx configuration validation FAILED\n\n>   %s\n",
                "\n>   ".join(result["stderr_lines"])
            )

            raise ComposedActionFailedError(
                "\n".join(result["stderr_lines"]), task.action, action, result
            )
        super().handle_failed_result(task, action, result)

    def compose(self):
        args = Args(self._task.args, self._var_values)

        if args.validate:
            self.tasks.command(argv=[args.exe, "-t"])

        self.tasks.service(
            name=args.name,
            state=args.state,
            enabled=args.enabled,
            **args.extras(),
        )
