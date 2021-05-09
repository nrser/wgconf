# pylint: disable=logging-too-many-args

from __future__ import annotations
from os.path import basename, isabs
from typing import Any, Dict, List, Literal, Optional, Type
from urllib.parse import urlparse
import logging
import shlex
from collections import abc

from ansible.errors import AnsibleError

from nansi.plugins.action.compose import ComposeAction
from nansi.plugins.action.args.all import Arg, ArgsBase, os_fact_format
from nansi.utils.strings import connect
from nansi.support.systemd import file_content_for


LOG = logging.getLogger(__name__)


def cast_url(value: Any, expected_type: Type, instance: ArgsBase, **context):
    if isinstance(value, list):
        value = connect(*value)
    return os_fact_format(
        value,
        instance.vars.raw["ansible_facts"],
        version=instance.version,
    )

class Exe(ArgsBase):
    @classmethod
    def cast(cls, args, _, value):
        if isinstance(value, str):
            return cls(
                dict(filename=basename(value), src=value),
                args.task_vars
            )
        if isinstance(value, abc.Mapping):
            return cls(value, args.task_vars)
        return value

    filename    = Arg(str)
    src         = Arg(str)

    def __init__(self, values, task_vars):
        super().__init__(values, task_vars)
        if isabs(self.src):
            raise ValueError(
                f"`{self.__class__.__name__}.src` may *not* be an " +
                f"absolute path, given `{self.src}`"
            )

class Args(ArgsBase):
    state       = Arg(Literal['present', 'absent'], 'present')

    release_dir = Arg(str, "/usr/local/release")
    bin_dir     = Arg(str, "/usr/local/bin")
    tmp_dir     = Arg(str, "/tmp/release")
    etc_dir     = Arg(str, "/usr/local/etc")
    systemd_dir = Arg(str, "/etc/systemd/system")

    name        = Arg(str)
    description = Arg(str, lambda self, *_: self.default_description)
    version     = Arg(str)
    service     = Arg(bool, False)
    user        = Arg(Optional[str])
    url         = Arg(str, cast=cast_url)
    checksum    = Arg(Optional[str])
    exe         = Arg.zero_or_more(Exe, item_cast=Exe.cast)
    args        = Arg(Optional[List[str]])
    systemd     = Arg(Dict[str, Dict[str, str]], lambda *_: {})

    def __init__(self, task_args, task_vars):
        super().__init__(task_args, task_vars)

        # Sanity checks...

        for name in ('name', 'version', 'url', 'user'):
            if getattr(self, name) == '':
                raise Exception(f"{repr(name)} arg can not be empty")

        for name in ('name', 'version'):
            value = getattr(self, name)
            if '/' in value: # pylint: disable=unsupported-membership-test
                raise Exception(
                    f"No / allowed in `{name}` arg! Given {repr(value)}"
                )

    @property
    def default_description(self):
        return f"{self.name} {self.version} release from {self.url}"

    @property
    def archive_filename(self):
        return basename(urlparse(self.url).path)

    @property
    def archive_dir(self):
        return connect(self.tmp_dir, 'archive', self.name, self.version)

    @property
    def extract_dir(self):
        return connect(self.tmp_dir, 'extract', self.name, self.version)

    @property
    def versions_dir(self):
        return connect(self.release_dir, self.name)

    def dirs(self):
        yield self.archive_dir
        yield self.extract_dir
        yield self.versions_dir

    @property
    def archive_dest(self):
        return connect(self.archive_dir, self.archive_filename)

    @property
    def version_dest(self):
        return connect(self.versions_dir, self.version)

    @property
    def default_exe_path(self):
        if len(self.exe) == 0:
            return None
        # pylint: disable=unsubscriptable-object
        return connect(self.bin_dir, self.exe[0].filename)

    @property
    def default_exec_start(self) -> Optional[str]:
        exe_path = self.default_exe_path
        if exe_path is None:
            return None
        if self.args is None or len(self.args) == 0:
            return exe_path
        return shlex.join((exe_path, *self.args))

    @property
    def service_name(self) -> str:
        return f"{self.name}.service"

    @property
    def service_dest(self) -> str:
        return connect(self.systemd_dir, self.service_name)

    @property
    def systemd_data(self) -> Dict[str, Dict[str, str]]:
        # pylint: disable=no-member
        return {
            "Unit": {
                "Description": self.description,
                **self.systemd.get("Unit", {}),
            },
            "Service": {
                "Type": "simple",
                "ExecStart": self.default_exec_start,
                "Restart": "always",
                "WorkingDirectory": self.version_dest,
                "User": self.user,
                "Group": self.user,
                **self.systemd.get("Service", {}),
            },
            "Install": {
                "WantedBy": "multi-user.target",
                **self.systemd.get("Install", {}),
            }
        }

    @property
    def systemd_content(self) -> str:
        return file_content_for(self.systemd_data)

class ActionModule(ComposeAction):

    # Start putting these things in super... somehow?
    def exists(self, path: str) -> bool:
        return self.tasks.stat(path=path)["stat"]["exists"]

    def compose(self):
        args = Args(self._task.args, self._task_vars)

        if args.state == 'present':
            self.present(args)
        elif args.state == 'absent':
            self.absent(args)
        else:
            raise AnsibleError(
                f"WTF `Release.state` is this? {repr(args.state)}"
            )

    def absent(self, release):
        if release.service:
            self.tasks.systemd(
                name        = release.service_name,
                state       = 'stopped',
                enabled     = False,
            )
            self.tasks.file(path=release.service_dest, state='absent')

            if release.user:
                self.tasks.user(name=release.user, state='absent')
                self.tasks.group(name=release.user, state='absent')

        for exe in release.exe:
            self.tasks.file(
                path    = connect(release.bin_dir, exe.filename),
                state   = 'absent',
            )

        for path in release.dirs():
            self.tasks.file(path=path, state='absent')

    def present(self, release):
        if not self.exists(release.version_dest):
            for path in release.dirs():
                self.tasks.file(
                    path    = path,
                    state   = 'directory',
                )

            self.tasks.get_url(
                url         = release.formatted_url,
                dest        = release.archive_dest,
                checksum    = release.checksum,
            )

            self.tasks.unarchive(
                src         = release.archive_dest,
                dest        = release.extract_dir,
                copy        = False,
            )

            self.tasks.command(
                argv = [
                    '/bin/mv',
                    self._get_mv_src(release),
                    release.version_dest,
                ]
            )

        for exe in release.exe:
            self.tasks.file(
                state   = 'link',
                src     = connect(release.version_dest, exe.src),
                dest    = connect(release.bin_dir, exe.filename),
                mode    = '775',
            )

        if release.service:
            if release.user:
                self.tasks.group(
                    name    = release.user,
                    system  = True,
                )

                self.tasks.user(
                    name        = release.user,
                    group       = release.user,
                    append      = True,
                    shell       = "/usr/sbin/nologin",
                    system      = True,
                    create_home = False,
                    home        = '/',
                )

            systemd_file = self.tasks.copy(
                dest    = release.service_dest,
                content = release.systemd_content,
            )

            self.tasks.systemd(
                name        = release.service_name,
                state       = ("restarted" if self._result["changed"]
                                else "started"),
                enabled     = True,
                daemon_reload   = systemd_file.get("changed", False),
            )


    def _get_mv_src(self, release: Args) -> str:
        '''Helper -- need to figure out what-the-hell came out of the archive.
        This seems so stupid, prob a good candidate to be replaced with a module
        at some point (never)'''

        stats = self.tasks.find(
            paths       = release.extract_dir,
            file_type   = 'any',
        )['files']

        if len(stats) == 0:
            raise AnsibleError(
                "Seem to have... not extracted anything? Looked at path "
                f"`{release.extract_dir}`"
            )
        elif len(stats) == 1:
            stat = stats[0]

            if stat['isdir']:
                copy_src = stat['path']

                self.log.debug(
                    "A single directory was extracted; that will be coppied",
                    dict(
                        copy_src = copy_src,
                        copy_dest = release.version_dest,
                    )
                )
            else:
                copy_src = release.extract_dir

                self.log.debug(
                    "A single *non-directory file* was extracted; the parent "
                    "directory will be coppied.",
                    dict(
                        extracted_file = stat["path"],
                        copy_src = copy_src,
                        copy_dest = release.version_dest,
                    )
                )
        else:
            copy_src = release.extract_dir

            self.log.debug(
                "Multiple files were extracted; the parent directory "
                "will be coppied.",
                dict(
                    extracted_files = [f["path"] for f in stats],
                    copy_src = copy_src,
                    copy_dest = release.version_dest,
                )
            )

        return copy_src
