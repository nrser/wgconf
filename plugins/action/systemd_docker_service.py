# pylint: disable=logging-too-many-args

from __future__ import annotations
from typing import *
import logging
import shlex
from os.path import basename, isabs, join
from collections import abc

from nansi.plugins.action.compose import ComposeAction
from nansi.plugins.action.args import Arg, ArgsBase, OpenArgsBase
from nansi.utils.strings import connect
from nansi.utils.cmds import iter_opts, TOpts
from nansi.support.systemd import file_content_for

LOG = logging.getLogger(__name__)

class Config(OpenArgsBase):
    @classmethod
    def cast(cls, parent, value):
        if isinstance(value, abc.Mapping):
            if "copy" in value:
                return CopyConfig.cast(parent, value["copy"])
            elif "template" in value:
                return TemplateConfig.cast(parent, value["template"])
        return value

class FileConfig(Config):
    @classmethod
    def cast(cls, parent, value):
        if isinstance(value, str):
            return cls(dict(src=value), parent.task_vars)
        elif isinstance(value, abc.Mapping):
            return cls(value, parent.task_vars)
        return value

    src     = Arg(Optional[str])
    dest    = Arg(Optional[str])

    def task_args(self, config_dir: str) -> Dict[str, Any]:
        dest = self.dest
        if dest is None:
            dest = basename(self.src)
        if not isabs(dest):
            dest = join(config_dir, dest)
        return {
            k: v for k, v in
            dict(
                src     = self.src,
                dest    = dest,
                **self.extras(),
            ).items()
            if v is not None
        }

class CopyConfig(FileConfig):
    action = "copy"

class TemplateConfig(FileConfig):
    action = "template"

class SystemdDockerService(ArgsBase):

    docker_service  = Arg(str, "docker.service")
    docker_exe      = Arg(str, "/usr/bin/docker")
    file_dir        = Arg(str, "/etc/systemd/system")
    configs_dir     = Arg(str, "/usr/local/etc")

    state           = Arg(Literal['present', 'absent'], 'present')
    name            = Arg(str)
    description     = Arg(str)
    tag             = Arg(str)
    opts            = Arg(Optional[TOpts])
    config          = Arg.zero_or_more(Config, item_cast=Config.cast)

    @property
    def exec_start(self) -> str:
        return shlex.join([
            self.docker_exe,
            "run",
            "--name", "%n",
            "--rm",
            *iter_opts(self.opts, subs=dict(config=self.config_dir)),
            self.tag,
        ])

    def volumes(self):
        # pylint: disable=unsupported-membership-test,unsubscriptable-object
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

    @property
    def config_dir(self) -> str:
        return connect(self.configs_dir, self.name)

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
        if len(service.config) > 0:
            self.tasks.file(
                path    = service.config_dir,
                state   = "directory",
            )

            for config in service.config:
                self.tasks[config.__class__.action](
                    **config.task_args(service.config_dir)
                )

        unit_file = self.tasks.copy(
            dest    = service.file_path,
            content = service.file_content,
        )

        self.tasks.systemd(
            name        = service.filename,
            state       = ("restarted" if self._result.get("changed", False)
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

        # NOTE  Persue independent files? Require they're all under config?
        #       That's probably better...
        self.tasks.file(
            path    = service.config_dir,
            state   = "absent",
        )

    def compose(self):
        service = SystemdDockerService(self._task.args, self._task_vars)
        getattr(self, f"state_{service.state}")(service)
