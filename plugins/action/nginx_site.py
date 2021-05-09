from __future__ import annotations
from os.path import join
from collections import namedtuple
from typing import List, Literal, Optional, Type, TypeVar, Union

from nansi.plugins.action.compose import ComposeAction
from nansi.plugins.action.args.all import Arg, ArgsBase

# pylint: disable=relative-beyond-top-level
from .nginx_config import role_path, CommonArgs


T = TypeVar("T")


def cast_server_names(
    value: T, expected_type: Type, **context
) -> Union[List[str], T]:
    """
    If `value` is a `str`, splits it into a list of `str`. All other `value`
    are returned as-is.

    >>> cast_server_names('example.com www.example.com')
    ['example.com', 'www.example.com']
    """
    if isinstance(value, str):
        return str.split()
    return value


class Args(ArgsBase, CommonArgs):
    # 'available' and 'disabled' are the same thing -- 'available' is the Nginx
    # term, as it ends up in the 'sites-available' directory, and 'disabled'
    # makes more sense next to 'enabled'.
    STATE_TYPE = Literal["enabled", "available", "disabled", "absent"]

    Config = namedtuple(
        "Config",
        (
            "scheme",
            "available",
            "enabled",
            "conf_template",
            "conf_path",
            "link_path",
        ),
    )

    # Props
    # ========================================================================

    ### Required ###

    name = Arg(str)

    ### Optional ###

    state = Arg(STATE_TYPE, "enabled")
    server_names = Arg(
        List[str],
        lambda self, _: self.default_server_names(),
        cast=cast_server_names,
    )

    root = Arg(str, "/var/www/html")

    http = Arg(Union[bool, STATE_TYPE, Literal["redirect"]], True)
    https = Arg(Union[bool, STATE_TYPE], True)

    http_template = Arg(str, str(role_path("templates/http.conf")))
    https_template = Arg(str, str(role_path("templates/https.conf")))

    lets_encrypt = Arg(bool, False)

    proxy = Arg(bool, False)

    proxy_location = Arg(str, "/")
    proxy_path = Arg(str, "/")
    proxy_scheme = Arg(str, "http")
    proxy_host = Arg(str, "localhost")
    proxy_port = Arg(
        Union[None, int, str], lambda self, _: self.default_proxy_port()
    )
    proxy_dest = Arg(str, lambda self, _: self.default_proxy_dest())

    client_max_body_size = Arg(str, "1m")

    @property
    def sites_available_dir(self):
        return join(self.config_dir, "sites-available")

    @property
    def sites_enabled_dir(self):
        return join(self.config_dir, "sites-enabled")

    @property
    def server_name(self) -> str:
        return " ".join(self.server_names)

    def default_server_names(self) -> List[str]:
        return [f"{self.name}.{self.task_vars['inventory_hostname']}"]

    def default_proxy_port(self) -> Optional[int]:
        return 8888 if self.proxy_host == "localhost" else None

    def default_proxy_dest(self) -> str:
        netloc = (
            self.proxy_host
            if self.proxy_port is None
            else f"{self.proxy_host}:{self.proxy_port}"
        )
        return f"{self.proxy_scheme}://{netloc}{self.proxy_path}"

    def _config_for(self, scheme: Literal["http", "https"]) -> Args.Config:
        """`NginxSite.Config` instances for each of the HTTP and HTTPS schemes
        supported -- packages up state and path information for convenient use.

        Access via `self.configs`.
        """
        # Get the state property for this `scheme` -- value of `self.http` or
        # `self.https`.
        scheme_state = getattr(self, scheme)

        # Config is available when the site is not absent (prevents *any*
        # configs from being present) and the scheme wasn't set to be 'absent'
        # or `False`.
        available = self.state != "absent" and scheme_state not in (
            "absent",
            False,
        )

        # Config is enabled when the site is enabled (necessary for *any*
        # configs to be enabled) and the scheme is 'enabled', 'redirect'
        # (HTTP-only, redirecting to HTTPS) or `True` (default).
        enabled = self.state == "enabled" and scheme_state in (
            "enabled",
            "redirect",
            True,
        )

        filename = f"{self.name}.{scheme}.conf"
        return Args.Config(
            scheme=scheme,
            available=available,
            enabled=enabled,
            conf_template=getattr(self, f"{scheme}_template"),
            conf_path=join(self.sites_available_dir, filename),
            link_path=join(self.sites_enabled_dir, filename),
        )

    @property
    def configs(self):
        return (self._config_for(scheme) for scheme in ("http", "https"))


class ActionModule(ComposeAction):
    def compose(self):
        args = Args(self._task.args, self._var_values)

        for config in args.configs:
            if config.available:
                self.tasks.template.add_vars(site=args, config=config)(
                    src=self._loader.get_real_file(config.conf_template),
                    dest=config.conf_path,
                    # backup=True,
                )
                if config.enabled:
                    self.tasks.file(
                        src=config.conf_path,
                        dest=config.link_path,
                        state="link",
                    )
                else:
                    self.tasks.file(
                        path=config.link_path,
                        state="absent",
                    )
            else:
                for path in (config.link_path, config.conf_path):
                    self.tasks.file(
                        path=path,
                        state="absent",
                    )
