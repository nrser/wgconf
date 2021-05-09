from __future__ import annotations

from nansi.plugins.action.compose import ComposeAction


class ActionModule(ComposeAction):
    def has_changed(self, task, action, result):
        return (
            task.args["_raw_params"] == "yum update -y"
            and "No packages marked for update" not in result["stdout_lines"]
        ) or (
            task.args["_raw_params"] == "yum install -y python3"
            and "Nothing to do" not in result["stdout_lines"]
        )

    def compose(self):
        update_result = self.tasks.raw("yum update -y")
        install_result = self.tasks.raw("yum install -y python3")

        self._result["changed"] = not (
            "No packages marked for update" in update_result["stdout_lines"]
            and "Nothing to do" in install_result["stdout_lines"]
        )
