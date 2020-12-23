# pylint: disable=logging-too-many-args

from __future__ import annotations
from typing import *
import logging
import shlex

from nansi.plugins.compose_action import ComposeAction
from nansi.proper import Proper, prop
from nansi.utils.strings import connect
from nansi.utils.cmds import iter_opts, TOpts
from nansi.support.systemd import file_content_for

LOG = logging.getLogger(__name__)

class SystemdDockerService(Proper):

    docker_service  = prop(str, "docker.service")
    docker_exe      = prop(str, "/usr/bin/docker")
    file_dir        = prop(str, "/etc/systemd/system")

    state           = prop(Literal['present', 'absent'], 'present')
    name            = prop(str)
    description     = prop(str)
    tag             = prop(str)
    opts            = prop(Optional[TOpts])

    @property
    def exec_start(self) -> str:
        return shlex.join([
            self.docker_exe,
            "run",
            "--name", "%n",
            "--rm",
            *iter_opts(self.opts),
            self.tag,
        ])

    def volumes(self):
        if isinstance(self.opts, dict) and "volume" in self.opts:
            volumes = self.opts["volume"]
            if isinstance(volumes, str):
                volumes = [volumes]
            for volume in volumes:
                parts = volume.split(":")
                if len(parts) > 0 and not parts[0].startswith("/"):
                    yield parts[0]

    @property
    def file_data(self):
        return {
            "Unit": {
                "Description": self.description,
                "After": self.docker_service,
                "Requires": self.docker_service,
            },
            "Service": {
                "ExecStartPre": [
                    "-/usr/bin/docker stop %n",
                    "-/usr/bin/docker rm %n",
                    f"/usr/bin/docker pull {self.tag}",
                ],
                "ExecStart": self.exec_start,
                "Restart": "always",
                "TimeoutStartSec": 0,
            },
            "Install": {
                "WantedBy": "multi-user.target",
            }
        }

    @property
    def filename(self) -> str:
        return f"{self.name}.service"

    @property
    def file_content(self) -> str:
        return file_content_for(self.file_data)

    @property
    def file_path(self) -> str:
        return connect(self.file_dir, self.filename)

class ActionModule(ComposeAction):

    def append_result(self, task, action, result):
        if "results" not in self._result:
            self._result["results"] = []
        self._result["results"].append({
            'task': task.action,
            'args': task.args,
            'status': self.result_status(result),
        })

    def state_present(self, service: SystemdDockerService):
        unit_file = self.tasks.copy(
            dest    = service.file_path,
            content = service.file_content,
        )

        self.tasks.systemd(
            name        = service.filename,
            state       = ("restarted" if unit_file.get("changed", False)
                            else "started"),
            enabled     = True,
            daemon_reload   = unit_file.get("changed", False),
        )

    def state_absent(self, service: SystemdDockerService):
        self.tasks.systemd(
            name        = service.filename,
            state       = 'stopped',
            enabled     = False,
        )
        self.tasks.file(path=service.file_path, state='absent')

        for volume in service.volumes():
            self.tasks.command(argv=[
                service.docker_bin,
                "volume",
                "rm",
                volume,
            ])

    def compose(self):
        service = SystemdDockerService(**self._task.args)
        getattr(self, f"state_{service.state}")(service)
