from __future__ import annotations
from os.path import join, realpath, dirname
from collections import namedtuple
from typing import *
import logging

from ansible.utils.display import Display

from nansi.plugins.compose_action import ComposeAction
from nansi.proper import Proper, prop

from nansi.display_handler import DisplayHandler

D = Display()

nansi_log = logging.getLogger('nansi')
nansi_log.setLevel(logging.DEBUG)
nansi_log.addHandler(DisplayHandler(D))

def from_var(name, default=None):
    return lambda self: self.vars.get(name, default)

def from_method(name):
    return lambda self: getattr(self, name)()

def from_attr(name):
    return lambda self: getattr(self, name)

def role_path(rel_path):
    return realpath(join(dirname(__file__), '..', rel_path))

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
    config_dir  = prop( str, from_var('nginx_config_dir', '/etc/nginx') )
    run_dir     = prop( str, from_var('nginx_run_dir', '/run') )
    log_dir     = prop( str, from_var('nginx_log_dir', '/var/log/nginx') )
    
    state               = prop( STATE_TYPE, 'enabled' )
    server_name         = prop( str, from_method('_default_server_name') )
    
    http                = prop( Union[ bool, STATE_TYPE, Literal['redirect'] ],
                                True )
    https               = prop( Union[ bool, STATE_TYPE ],
                                True )
    
    http_template       = prop( str, role_path('templates/http.conf') )
    https_template      = prop( str, role_path('templates/https.conf') )
    
    lets_encrypt        = prop( bool, from_var('nginx_lets_encrypt', False) )
    
    proxy               = prop( bool, False )
    
    proxy_location      = prop( str, '/' )
    proxy_path          = prop( str, '/' )
    proxy_scheme        = prop( str, 'http' )
    proxy_host          = prop( str, 'localhost' )
    proxy_port          = prop( Union[ None, int, str ],
                                from_method('_default_proxy_port') )
    
    proxy_dest          = prop( str,
                                from_method('_default_proxy_dest') )
    proxy_websockets    = prop( bool,
                                from_var('nginx_websockets', False) )
    
    def __init__(self, args, vars):
        self.vars = vars
        super().__init__(**{
            **vars.get('nginx_site_defaults', {}),
            **args
        })

    @property
    def sites_available_dir(self):
        return join( self.config_dir, 'sites-available' )
    
    @property
    def sites_enabled_dir(self):
        return join( self.config_dir, 'sites-enabled' )
    
    def _default_server_name(self) -> str:
        return f"{self.name}.{self.vars['inventory_hostname']}"
    
    def _default_proxy_port(self) -> Optional[int]:
        return (8888 if self.proxy_host == 'localhost' else None)
    
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
        site = NginxSite(self._task.args, self._task_vars)
                
        for config in site.configs:            
            if config.available:
                self.run_task(
                    'template',
                    { **self._task_vars, 'site': site },
                    src     = config.conf_template,
                    dest    = config.conf_path,
                    backup  = True,
                )
                if config.enabled:
                    self.run_task(
                        'file',
                        src     = config.conf_path,
                        dest    = config.link_path,
                        state   = 'link',
                    )
                else:
                    self.run_task(
                        'file',
                        path    = config.link_path,
                        state   = 'absent',
                    )
            else:
                for path in (config.link_path, config.conf_path):
                    self.run_task(
                        'file',
                        path    = path,
                        state   = 'absent',
                    )
