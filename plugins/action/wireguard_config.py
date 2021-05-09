from __future__ import annotations
from typing import Dict, List, Literal, Mapping, Optional, Union
from subprocess import run
from pathlib import Path
import shlex

from nansi import logging
from nansi.plugins.action.args.arg import Arg
from nansi.plugins.action.args.base import ArgsBase
from nansi.plugins.action.args.casts import autocast
from nansi.plugins.action.args.jsos import JSOSType
from nansi.plugins.action.compose import ComposeAction
from nansi.constants import REPO_ROOT
from nansi.utils.decorators import lazy_property
from nansi.utils.collections import pick

LOG = logging.getLogger(__name__)
WGCONF_ROOT = REPO_ROOT / "packages" / "wgconf"
WGCONF_NAME = "wgconf"

ROLE_DIR = REPO_ROOT / "roles" / "wireguard" / "config"


def from_var(name):
    return lambda args, _arg: args.vars[name]


def default_property(args, arg):
    return getattr(args, f"default_{arg.name}")


class HookScript(ArgsBase):
    hooks_dir = Arg(Path)
    src = Arg(Path)
    dest = Arg(Optional[Path])

    @property
    def is_template(self) -> bool:
        # pylint: disable=no-member
        return self.src.suffix == ".j2"

    @property
    def copy_task_name(self) -> str:
        return "template" if self.is_template else "copy"

    @lazy_property
    def full_dest(self) -> Path:
        # pylint: disable=no-member

        # If no dest is provided, form one from the `hooks_dir` and the filename
        # of the `src`, omitting any `.j2` suffix
        if self.dest is None:
            if self.is_template:
                dest_name = self.src.stem
            else:
                dest_name = self.src.name
            return self.hooks_dir / dest_name

        # Absolute paths are good-to-go, ignoring `hooks_dir`
        if self.dest.is_absolute():
            return self.dest

        # Relative paths are relative to `hooks_dir`
        return self.hooks_dir / self.dest

    @property
    def dest_dir(self) -> Path:
        return self.full_dest.parent

    @property
    def invocation(self) -> str:
        # pylint: disable=no-member
        return shlex.join(
            (
                str(self.full_dest),
                self.parent.parent.name,
                self.parent.parent.network_interface,
            )
        )

    def to_jsos(self) -> str:
        return self.invocation


class HookArg(Arg):
    def __init__(
        self, default=None, *, default_value=None, get_default=None, alias=None
    ):
        super().__init__(
            Union[None, str, HookScript],
            default,
            default_value=default_value,
            get_default=get_default,
            alias=alias,
        )

    def cast(self, instance, value):
        if isinstance(value, Mapping):
            return HookScript(
                values={**value, "hooks_dir": instance.parent.hooks_dir},
                parent=instance,
            )
        return value


class InterfaceUpdate(ArgsBase):
    name = Arg(Optional[str])
    description = Arg(Optional[str])
    address = Arg.zero_or_more(str)
    private_key = Arg(Optional[str])
    listen_port = Arg(Optional[int])
    dns = Arg.zero_or_more(str)
    table = Arg(Union[None, int, str])
    mtu = Arg(Optional[int])
    pre_up = HookArg()
    post_up = HookArg(default=dict(src=(ROLE_DIR / "files" / "post_up.sh")))
    pre_down = HookArg()
    post_down = HookArg(default=dict(src=(ROLE_DIR / "files" / "post_down.sh")))
    save_config = Arg(Optional[bool])

    @property
    def hook_scripts(self) -> List[HookScript]:
        return [
            hook
            for hook in (
                self.pre_up,
                self.post_up,
                self.pre_down,
                self.post_down,
            )
            if isinstance(hook, HookScript)
        ]


class PeerDefaults(ArgsBase):
    allowed_ips = Arg.zero_or_more(str)
    persistent_keepalive = Arg(Optional[int])


class PeerUpdate(PeerDefaults):
    description = Arg(Optional[str])
    public_key = Arg(Optional[str])
    endpoint = Arg(Optional[str])
    preshared_key = Arg(Optional[str])


class ClientBase(ArgsBase):
    allowed_ips = Arg.zero_or_more(str)
    dns = Arg.zero_or_more(str)
    persistent_keepalive = Arg(Optional[int])


class ClientDefaults(ClientBase):
    # You can't provide a _value_ for the pre-shared key by default of course,
    # but you can provide a boolean controlling generation of pre-shared keys.
    #
    # `True` enables pre-shared key generation (when no _value_ is provided),
    # `False` disables it.
    #
    preshared_key = Arg(Union[None, bool])


class ClientUpdate(ClientBase):
    owner = Arg(Optional[str])
    private_address = Arg(str)
    description = Arg(Optional[str])
    preshared_key = Arg(Union[None, str, bool], True)
    private_key = Arg(Optional[str])
    public_key = Arg(Optional[str])


class Args(ArgsBase):
    def cast_hooks_dir(self, arg, value):
        if isinstance(value, str):
            return Path(value.format(self=self))
        return value

    state = Arg(Literal["present", "absent"], "present")

    name = Arg(str, "wg0")
    hostname = Arg(str, from_var("inventory_hostname"))
    dir = Arg(Path, "/etc/wireguard")
    public_address = Arg(Optional[str])
    wg_bin_path = Arg(Optional[Path])
    network_interface = Arg(str, "eth0")

    interface = Arg(InterfaceUpdate)

    peers = Arg(Dict[str, PeerUpdate], {}, cast=autocast)
    peer_defaults = Arg(PeerDefaults, {}, cast=autocast)

    clients = Arg(Dict[str, ClientUpdate], {}, cast=autocast)
    client_defaults = Arg(ClientDefaults, {}, cast=autocast)

    fetch_clients_to = Arg(Optional[Path])
    copy_build_to = Arg(Path, "/tmp")
    force_build = Arg(bool, False)

    python_version = Arg(str, "3.8.5")
    python_bin_dir = Arg(Path, default_property)
    python_executable = Arg(Path, default_property)
    pip_executable = Arg(Path, default_property)

    hooks_dir = Arg(Path, default_property)
    clients_dir = Arg(Optional[Path])

    @property
    def pyenv_root(self) -> Path:
        return Path(self.vars.get("pyenv_root", "/opt/pyenv"))

    @property
    def default_python_bin_dir(self) -> Path:
        return self.pyenv_root / "versions" / self.python_version / "bin"

    @property
    def default_python_executable(self) -> Path:
        return self.python_bin_dir / "python"

    @property
    def default_pip_executable(self) -> Path:
        return self.python_bin_dir / "pip"

    @property
    def default_hooks_dir(self) -> Path:
        return self.dir / "hooks"

    @property
    def default_clients_dir(self) -> Path:
        return self.dir / "clients"

    @property
    def for_wg_cfg_update(self) -> Dict[str, JSOSType]:
        return pick(
            self.to_jsos(),
            {
                "name",
                "hostname",
                "dir",
                "public_address",
                "wg_bin_path",
                "clients_dir",
                "interface",
                "peers",
                "clients",
                "peer_defaults",
                "client_defaults",
            },
        )


class ActionModule(ComposeAction):

    args: Optional[Args] = None

    # Tracks if the build happen or not
    did_build: bool = False

    # Computed Properties
    # ========================================================================

    @lazy_property # Expensive, so only do it once
    def wgconf_version(self) -> str:
        with (WGCONF_ROOT / "VERSION").open("r") as file:
            return file.read().strip()

    @property
    def wgconf_wheel_filename(self) -> str:
        return f"{WGCONF_NAME}-{self.wgconf_version}-py3-none-any.whl"

    @property
    def wgconf_wheel_path(self) -> Path:
        return WGCONF_ROOT / "dist" / self.wgconf_wheel_filename

    @property
    def wgconf_wheel_dest(self) -> Path:
        return self.args.copy_build_to / self.wgconf_wheel_filename

    # Entry Point
    # ========================================================================

    def compose(self):
        """
        Hands off to the _state method_ identified by [Args#state][], either
        of:

        1.  [#present](ActionModule.present)
        1.  [#absent](ActionModule.absent) (TODO — just raises right now)

        [Args#state]: .Args.state
        """
        self.args = Args(self._task.args, self)
        getattr(self, self.args.state)()

    # State Methods
    # ========================================================================
    #
    # Called depending on the <Args.state>; responsible for invoking the steps.
    #

    def present(self):
        self.build_wgconf_wheel()
        self.copy_wgconf_wheel()
        self.install_wgconf()
        self.copy_hook_scripts()
        self.configure()

    def absent(self):
        raise NotImplementedError("TODO")

    # Composition Steps
    # ========================================================================
    #
    # Broken out into individual methods to make grasping pieces a bit easier.
    #

    def build_wgconf_wheel(self):
        if self.args.force_build or not self.wgconf_wheel_path.exists():
            self.log.debug(
                f"Building {WGCONF_NAME} wheel...",
                version=self.wgconf_version,
                force_build=self.args.force_build,
            )
            run(
                ["python", "setup.py", "bdist_wheel"],
                cwd=WGCONF_ROOT,
                capture_output=True,
                check=True,
            )
            self.log.debug(f"{WGCONF_NAME} wheel built.")
            self.did_build = True
        else:
            self.log.debug(
                f"{WGCONF_NAME} already built.",
                version=self.wgconf_version,
                path=self.wgconf_wheel_path,
            )

    def copy_wgconf_wheel(self):
        self.tasks.copy(
            src=str(self.wgconf_wheel_path),
            dest=str(self.wgconf_wheel_dest),
            force=self.did_build,
        )

    def install_wgconf(self):
        self.tasks.pip.add_vars(
            ansible_python_interpreter=str(self.args.python_executable),
        )(
            name=f"file://{self.wgconf_wheel_dest}",
            state="present",
            executable=str(self.args.pip_executable),
        )

    def copy_hook_scripts(self):
        # pylint: disable=no-member

        # First form a set of all the destination directories for hook scripts
        # (de-duping the paths)
        hook_dirs = {h.dest_dir for h in self.args.interface.hook_scripts}

        # Ensure those directories exist
        for hook_dir in hook_dirs:
            self.tasks.file(
                path=str(hook_dir),
                state="directory",
                mode="0700",
            )

        # Copy the scripts, using `template` if the `src` ends with `.j2`
        for hook_script in self.args.interface.hook_scripts:
            self.tasks[hook_script.copy_task_name](
                src=str(hook_script.src),
                dest=str(hook_script.dest),
                mode="0700",
            )

    def configure(self):
        self.tasks["nrser.nansi.wg_cfg_update"].add_vars(
            ansible_python_interpreter=str(self.args.python_executable),
        )(**self.args.for_wg_cfg_update)

