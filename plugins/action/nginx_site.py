from __future__ import annotations
from os.path import join
from collections import namedtuple
from typing import *
from operator import methodcaller

from nansi.plugins.action.compose import ComposeAction
from nansi.proper import Proper, prop

from ansible_collections.nrser.nansi.plugins.action.nginx_config import role_path # pylint: disable=import-error,no-name-in-module

# TODO  Needs work!

def from_var(name, *args):
    args_len = len(args)
    if args_len == 0:
        return lambda self: self.vars[name]
    elif args_len == 1:
        return lambda self: self.vars.get(name, args[0])
    else:
        raise TypeError(
            "from_var() takes 1-2 positional arguments but was given " +
            str(args_len)
        )

def cast_server_names(value: T) -> Union[List[str], T]:
    '''
    If `value` is a `str`, splits it into a list of `str`. All other `value`
    are returned as-is.

    >>> cast_server_names('example.com www.example.com')
    ['example.com', 'www.example.com']
    '''
    if isinstance(value, str):
        return str.split()
    return value

class NginxSite(Proper):
    # 'available' and 'disabled' are the same thing -- 'available' is the Nginx
    # term, as it ends up in the 'sites-available' directory, and 'disabled'
    # makes more sense next to 'enabled'.
    STATE_TYPE = Literal[ 'enabled', 'available', 'disabled', 'absent' ]

    Config = namedtuple('Config', (
        'scheme',
        'available',
        'enabled',
        'conf_template',
        'conf_path',
        'link_path',
    ))

    # Props
    # ========================================================================

    ### Required ###

    name = prop( str )

    ### Optional ###

    # Direcotry locations, pulled from global `nginx_` vars, with fallbacks
    config_dir  = prop( str, from_var('nginx_config_dir') )
    run_dir     = prop( str, from_var('nginx_run_dir') )
    log_dir     = prop( str, from_var('nginx_log_dir') )

    state               = prop( STATE_TYPE, 'enabled' )
    # server_name         = prop( str, methodcaller('_default_server_name') )
    server_names        = prop( List[str],
                                default = methodcaller('_default_server_name'),
                                cast    = cast_server_names )

    root                = prop( str, from_var("nginx_site_root", "/var/www/html") )

    http                = prop( Union[ bool, STATE_TYPE, Literal['redirect'] ],
                                True )
    https               = prop( Union[ bool, STATE_TYPE ],
                                True )

    http_template       = prop( str, role_path('templates/http.conf') )
    https_template      = prop( str, role_path('templates/https.conf') )

    lets_encrypt        = prop( bool, from_var('nginx_lets_encrypt') )

    proxy               = prop( bool, False )

    proxy_location      = prop( str, '/' )
    proxy_path          = prop( str, '/' )
    proxy_scheme        = prop( str, 'http' )
    proxy_host          = prop( str, 'localhost' )
    proxy_port          = prop( Union[ None, int, str ],
                                methodcaller('_default_proxy_port') )

    proxy_dest          = prop( str,
                                methodcaller('_default_proxy_dest') )
    proxy_websockets    = prop( bool,
                                from_var('nginx_proxy_websockets') )

    client_max_body_size    = prop( str, '1m' )

    # pylint: disable=redefined-builtin
    def __init__(self, args, vars):
        self.vars = vars
        super().__init__(**args)

    @property
    def sites_available_dir(self):
        return join( self.config_dir, 'sites-available' )

    @property
    def sites_enabled_dir(self):
        return join( self.config_dir, 'sites-enabled' )

    @property
    def server_name(self) -> str:
        return " ".join(self.server_names)

    def _default_server_names(self) -> List[str]:
        return [f"{self.name}.{self.vars['inventory_hostname']}"]

    def _default_proxy_port(self) -> Optional[int]:
        return 8888 if self.proxy_host == 'localhost' else None

    def _default_proxy_dest(self) -> str:
        netloc = (
            self.proxy_host if self.proxy_port is None
            else f"{self.proxy_host}:{self.proxy_port}"
        )
        return f"{self.proxy_scheme}://{netloc}{self.proxy_path}"

    def _config_for(
        self,
        scheme: Literal['http', 'https']
    ) -> NginxSite.Config:
        '''`NginxSite.Config` instances for each of the HTTP and HTTPS schemes
        supported -- packages up state and path information for convenient use.

        Access via `self.configs`.
        '''
        # Get the state property for this `scheme` -- value of `self.http` or
        # `self.https`.
        scheme_state = getattr(self, scheme)

        # Config is available when the site is not absent (prevents *any*
        # configs from being present) and the scheme wasn't set to be 'absent'
        # or `False`.
        available   = ( self.state != 'absent' and
                        scheme_state not in ('absent', False) )

        # Config is enabled when the site is enabled (necessary for *any*
        # configs to be enabled) and the scheme is 'enabled', 'redirect'
        # (HTTP-only, redirecting to HTTPS) or `True` (default).
        enabled     = ( self.state == 'enabled' and
                        scheme_state in ('enabled', 'redirect', True) )

        filename = f"{self.name}.{scheme}.conf"
        return NginxSite.Config(
            scheme          = scheme,
            available       = available,
            enabled         = enabled,
            conf_template   = getattr(self, f"{scheme}_template"),
            conf_path       = join(self.sites_available_dir, filename),
            link_path       = join(self.sites_enabled_dir, filename),
        )

    @property
    def configs(self):
        return (self._config_for(scheme) for scheme in ('http', 'https'))

class ActionModule(ComposeAction):
    def compose(self):
        site = NginxSite(self.collect_args(), self._var_values)

        for config in site.configs:
            if config.available:
                self.tasks.template.add_vars(
                    site        = site,
                    config      = config,
                )(
                    src         = self._loader.get_real_file(
                                    config.conf_template
                                ),
                    dest        = config.conf_path,
                    backup      = True,
                )
                if config.enabled:
                    self.tasks.file(
                        src     = config.conf_path,
                        dest    = config.link_path,
                        state   = 'link',
                    )
                else:
                    self.tasks.file(
                        path    = config.link_path,
                        state   = 'absent',
                    )
            else:
                for path in (config.link_path, config.conf_path):
                    self.tasks.file(
                        path    = path,
                        state   = 'absent',
                    )
