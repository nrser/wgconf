from __future__ import annotations
import logging
from typing import Literal

from nansi.plugins.action.compose import ComposeAction
from nansi.plugins.action.args.all import Arg, ArgsBase, os_fact_formatter
from nansi.os_resolve import os_map_resolve

LOG = logging.getLogger(__name__)


class Args(ArgsBase):
    state = Arg(Literal["present", "absent"], "present")
    version = Arg(str)

    @property
    def major_version(self) -> str:
        return self.version.split(".", 1)[0]  # pylint: disable=no-member


class DebianArgs(Args):
    name = Arg(str, "nodejs")
    key_url = Arg(str, "https://deb.nodesource.com/gpgkey/nodesource.gpg.key")
    key_id = Arg(str, "302755F9E22EDC1ABB62E9B56C5CDECAAA01DA2C")
    repo = Arg(
        str,
        "deb https://deb.nodesource.com"
        "/node_{major_version}.x {release} main",
        cast=os_fact_formatter("version", "major_version"),
    )

    @property
    def apt_ext_names(self):
        if self.version is None:
            return self.name
        return dict(name=self.name, version=self.version)


class ActionModule(ComposeAction):
    def os_family_debian(self):
        args = DebianArgs(self._task.args, self._task_vars)

        self.tasks["nrser.nansi.apt_ext"](
            names=args.apt_ext_names,
            state=args.state,
            key_url=args.key_url,
            key_id=args.key_id,
            repo=args.repo,
        )

    def compose(self):
        os_map_resolve(
            self._task_vars["ansible_facts"],
            {
                "family": {
                    "debian": self.os_family_debian,
                }
            }
        )()
