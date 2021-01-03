# pylint: disable=logging-too-many-args

from __future__ import annotations
from typing import *
from os.path import basename, isabs, join
from urllib.parse import urlparse
from operator import attrgetter
import logging
import shlex

from ansible.errors import AnsibleError

from nansi.plugins.compose_action import ComposeAction
from nansi.proper import Proper, prop
from nansi.utils.strings import connect
from nansi.support.systemd import file_content_for

GO_ARCH_MAP = {
    "i386": "386",
    "x86_64": "amd64",
    "aarch64": "arm64",
    "armv7l": "armv7",
    "armv6l": "armv6",
}

LOG = logging.getLogger(__name__)


def cast_url(value):
    if isinstance(value, list):
        return connect(*value)
    return value


class Exe(Proper):
    @classmethod
    def cast(cls, value):
        if isinstance(value, str):
            return cls(filename=basename(value), src=value)
        elif isinstance(value, Mapping):
            return cls(**value)
        LOG.warning(f"Bad type! {type(value)}", dict(value=value))
        return value

    filename    = prop(str)
    src         = prop(str)

    def __init__(self, **values):
        super().__init__(**values)
        if isabs(self.src):
            raise ValueError(
                f"`{self.__class__.__name__}.src` may *not* be an " +
                f"absolute path, given `{self.src}`"
            )

class Release(Proper):
    state       = prop(Literal['present', 'absent'], 'present')

    release_dir = prop(str, "/usr/local/release")
    bin_dir     = prop(str, "/usr/local/bin")
    tmp_dir     = prop(str, "/tmp/release")
    etc_dir     = prop(str, "/usr/local/etc")
    systemd_dir = prop(str, "/etc/systemd/system")

    name        = prop(str)
    description = prop(str, attrgetter('_default_description'))
    version     = prop(str)
    service     = prop(bool, False)
    user        = prop(Optional[str])
    url         = prop(str, cast=cast_url)
    checksum    = prop(Optional[str])
    exe         = prop.zero_or_more(Exe, item_cast=Exe.cast)
    args        = prop(Optional[List[str]])
    systemd     = prop(Dict[str, Dict[str, str]], lambda _: {})

    def __init__(self, task_args, task_vars):
        self._task_vars = task_vars
        super().__init__(**task_args)

        # Sanity checks...

        for name in ('name', 'version', 'url', 'user'):
            if getattr(self, name) == '':
                raise Exception(f"{repr(name)} arg can not be empty")

        for name in ('name', 'version'):
            value = getattr(self, name)
            if '/' in value:
                raise Exception(
                    f"No / allowed in `{name}` arg! Given {repr(value)}"
                )

    @property
    def _default_description(self):
        return f"{self.name} {self.version} release from {self.formatted_url}"

    @property
    def formatted_url(self):
        arch = self._task_vars["ansible_facts"]["architecture"]
        subs = {
            "arch": self._task_vars["ansible_facts"]["architecture"],
            "system": self._task_vars["ansible_facts"]["system"].lower(),
            "version": self.version,
        }
        if arch in GO_ARCH_MAP:
            subs["go_arch"] = GO_ARCH_MAP[arch]
        return self.url.format(**subs)

    @property
    def archive_filename(self):
        return basename(urlparse(self.formatted_url).path)

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

    def append_result(self, task, action, result):
        if "results" not in self._result:
            self._result["results"] = []
        self._result["results"].append({
            'task': task.action,
            'args': task.args,
            'status': self.result_status(result),
        })

    # TODO  Start putting these things in super... somehow?
    def exists(self, path: str) -> bool:
        return self.tasks.stat(path=path)["stat"]["exists"]

    def compose(self):
        release = Release(self._task.args, self._task_vars)

        if release.state == 'present':
            self.present(release)
        elif release.state == 'absent':
            self.absent(release)
        else:
            raise AnsibleError(
                f"WTF `Release.state` is this? {repr(release.state)}"
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


    def _get_mv_src(self, release: Release) -> str:
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
