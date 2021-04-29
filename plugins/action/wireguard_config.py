from __future__ import annotations
from typing import Dict, Iterable, List, Literal, Mapping, Optional, Union
from subprocess import run
from pathlib import Path
import shlex

from nansi import logging
from nansi.plugins.action.args.jsos import jsos_for
from nansi.plugins.action.compose import ComposeAction
from nansi.plugins.action.args import Arg, ArgsBase
from nansi.constants import REPO_ROOT
from nansi.utils.decorators import lazy_property

LOG = logging.getLogger(__name__)
WGCONF_ROOT = REPO_ROOT / "packages" / "wgconf"
WGCONF_NAME = "wgconf"


def from_var(name):
    return lambda args, _arg: args.vars[name]


def dict_of(args_class):
    def _dict_of(args, _arg, value):
        return {k: args_class(v, args) for k, v in value.items()}

    return _dict_of


def opt_of(args_class):
    def _opt_of(args, _arg, value):
        if value is None:
            return None
        return args_class(value, args)

    return _opt_of


def cast_path(_args, _arg, value):
    if value is None:
        return None
    if isinstance(value, str):
        return Path(value)
    if isinstance(value, Path):
        return value
    if isinstance(value, Iterable):
        return Path(*value)
    return value


def default_property(args, arg):
    return getattr(args, f"default_{arg.name}")


class HookScript(ArgsBase):
    hooks_dir = Arg(Path)
    src = Arg(Path, cast=cast_path)
    dest = Arg(Optional[Path], cast=cast_path)

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

    @lazy_property
    def dest_dir(self) -> Path:
        return self.full_dest.parent

    @lazy_property
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
                values={**value, "hooks_dir": instance.hooks_dir},
                parent=instance,
            )
        return value


class InterfaceUpdate(ArgsBase):
    def cast_hooks_dir(self, arg, value):
        if isinstance(value, str):
            return Path(value.format(self=self))
        return value

    name = Arg(Optional[str])
    description = Arg(Optional[str])
    address = Arg.zero_or_more(str)
    private_key = Arg(Optional[str])
    listen_port = Arg(Optional[int])
    dns = Arg.zero_or_more(str)
    table = Arg(Union[None, int, str])
    mtu = Arg(Optional[int])
    pre_up = HookArg()
    post_up = HookArg(default=dict(src="post_up.sh"))
    pre_down = HookArg()
    post_down = HookArg(default=dict(src="post_down.sh"))
    save_config = Arg(Optional[bool])

    hooks_dir = Arg(
        type=Path,
        default="{self.parent.dir}/hooks",
        cast=cast_hooks_dir,
    )

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
    state = Arg(Literal["present", "absent"], "present")

    name = Arg(str, "wg0")
    hostname = Arg(str, from_var("inventory_hostname"))
    dir = Arg(str, "/etc/wireguard")
    public_address = Arg(Optional[str])
    wg_bin_path = Arg(Optional[str])
    network_interface = Arg(str, "eth0")

    interface = Arg(InterfaceUpdate)

    peers = Arg(Dict[str, PeerUpdate], {}, cast=dict_of(PeerUpdate))
    peer_defaults = Arg(Optional[PeerDefaults], cast=opt_of(PeerDefaults))

    clients = Arg(Dict[str, ClientUpdate], {}, cast=dict_of(ClientUpdate))
    client_defaults = Arg(Optional[ClientDefaults], cast=opt_of(ClientDefaults))

    fetch_clients_to = Arg(Optional[str])
    copy_build_to = Arg(str, "/tmp")
    force_build = Arg(bool, False)

    python_version = Arg(str, "3.8.5")
    python_bin_dir = Arg(Path, default_property, cast=cast_path)
    python_executable = Arg(Path, default_property, cast=cast_path)
    pip_executable = Arg(Path, default_property, cast=cast_path)

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


class ActionModule(ComposeAction):

    args: Optional[Args] = None

    # Tracks if the build happen or not
    did_build: bool = False

    @lazy_property
    def wgconf_version(self) -> str:
        with (WGCONF_ROOT / "VERSION").open("r") as file:
            return file.read().strip()

    @lazy_property
    def wgconf_wheel_filename(self) -> str:
        return f"{WGCONF_NAME}-{self.wgconf_version}-py3-none-any.whl"

    @lazy_property
    def wgconf_wheel_path(self) -> Path:
        return WGCONF_ROOT / "dist" / self.wgconf_wheel_filename

    @lazy_property
    def wgconf_wheel_dest(self) -> Path:
        return Path(self.args.copy_build_to) / self.wgconf_wheel_filename

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
        self.tasks.wg_cfg_update(
            name=self.args.name,
            hostname=self.args.hostname,
            dir=self.args.dir,
            public_address=self.args.public_address,
            wg_bin_path=self.args.wg_bin_path,
            interface=jsos_for(self.args.interface),
            peers=jsos_for(self.args.peers),
            peer_defaults=jsos_for(self.args.peer_defaults),
            clients=jsos_for(self.args.clients),
            client_defaults=jsos_for(self.args.client_defaults),
        )

    def present(self):
        self.build_wgconf_wheel()
        self.copy_wgconf_wheel()
        self.install_wgconf()
        self.copy_hook_scripts()
        self.configure()

    def absent(self):
        raise NotImplementedError("TODO")

    def compose(self):
        self.args = Args(self._task.args, self)
        getattr(self, self.args.state)()
