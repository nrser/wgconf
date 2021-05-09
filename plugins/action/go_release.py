from __future__ import annotations
from os import path
from typing import Literal, Optional

from nansi.plugins.action.compose import ComposeAction
from nansi.plugins.action.args.all import Arg, ArgsBase, attr_formatter
from nansi.os_resolve import os_map_resolve

# pylint: disable=relative-beyond-top-level
from . import release

class Args(ArgsBase):
    version     = Arg( str )

    name        = Arg(  str, "go" )
    state       = Arg(  Literal['present', 'absent'], 'present' )
    url         = Arg(  str,
                        "https://dl.google.com/go/"
                        "go{version}.{system}-{go_arch}.tar.gz" )
    checksum    = Arg(  Optional[str] )

    manage_profile_env  = Arg(  bool, True )
    profile_dir         = Arg(  str, "/etc/profile.d" )
    profile_basename    = Arg(  str,
                                "{name}.sh",
                                cast=attr_formatter("name") )
    profile_path        = Arg(  str,
                                lambda self, _: path.join(
                                    self.profile_dir,
                                    self.profile_basename,
                                )
                            )

    @property
    def version_dest(self) -> str:
        return release.Args(
            dict(name=self.name, version=self.version, url=self.url),
            parent=self,
        ).version_dest

    @property
    def bin_path(self) -> str:
        return path.join(self.version_dest, "bin")

class ActionModule(ComposeAction):

    def os_system_linux(self):
        args = Args(self._task.args, self._task_vars)

        self.tasks["nrser.nansi.release"](
            name        = args.name,
            state       = args.state,
            version     = args.version,
            url         = args.url,
            checksum    = args.checksum,
        )

        if args.manage_profile_env:
            if args.state == 'absent':
                self.tasks.file(
                    path = args.profile_path,
                    state = "absent",
                )
            else:
                self.tasks.copy(
                    content = (
                        f'''export GOROOT={args.version_dest}\n'''
                        f'''export PATH="$PATH:{args.bin_path}"\n'''
                    ),
                    dest = args.profile_path,
                )


    def compose(self):
        os_map_resolve(
            self._task_vars['ansible_facts'],
            {
                'system': {
                    'linux': self.os_system_linux,
                },
            },
        )()
