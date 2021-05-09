# pylint: disable=logging-too-many-args

from __future__ import annotations
import logging
from typing import Any, Dict, Literal, Union

from nansi.plugins.action.compose import ComposeAction
from nansi.plugins.action.args.all import Arg, ArgsBase
from nansi.utils.strings import connect
from nansi.support.systemd import file_content_for

LOG = logging.getLogger(__name__)

class SystemdUnit(ArgsBase):
    file_dir = Arg(str, "/etc/systemd/system")
    state = Arg(Literal["present", "absent"], "present")
    name = Arg(str)
    data = Arg(Dict[str, Any])
    mode = Arg(Union[str, int], 0o600)

    @property
    def filename(self) -> str:
        return f"{self.name}.service"

    @property
    def file_content(self) -> str:
        return file_content_for(self.data)

    @property
    def file_path(self) -> str:
        return connect(self.file_dir, self.filename)


class ActionModule(ComposeAction):

    def state_present(self, unit: SystemdUnit):
        unit_file = self.tasks.copy(
            dest=unit.file_path,
            content=unit.file_content,
            mode=unit.mode,
        )

        self.tasks.systemd(
            name=unit.filename,
            state=(
                "restarted" if self._result.get("changed", False) else "started"
            ),
            enabled=True,
            daemon_reload=unit_file.get("changed", False),
        )

    def state_absent(self, unit: SystemdUnit):
        self.tasks.systemd(
            name=unit.filename,
            state="stopped",
            enabled=False,
        )
        self.tasks.file(path=unit.file_path, state="absent")

    def compose(self):
        service = SystemdUnit(self._task.args, self)
        getattr(self, f"state_{service.state}")(service)
