from __future__ import annotations
import os
from collections import namedtuple
from typing import *
import logging

from ansible.utils.display import Display

import os
import sys
LIB_DIR = os.path.realpath(
    os.path.join(
        os.path.dirname(__file__),
        '..', '..', '..', '..', 'lib'
    )
)
sys.path.insert(0, LIB_DIR)

from nansi.plugins.nansi_action_base import NansiActionBase
from nansi.proper import Proper, prop

from nansi.display_handler import DisplayHandler

D = Display()

nansi_log = logging.getLogger('nansi')
nansi_log.setLevel(logging.DEBUG)
nansi_log.addHandler(DisplayHandler(D))

# Invocation looks like:
# 
#   tasks:
#     - nginx_site:
#         name: mica.dev.outcut
#         https: no
#         proxy:
#           port: 4001
# 

NginxSiteScheme = namedtuple(
    'NginxSiteScheme',
    'scheme available enabled conf_template conf_path link_path'
)

def from_vars(name, default=None):
    return lambda self: self.vars.get(name, default)

def from_call(name):
    return lambda self: getattr(self, name)()

def from_attr(name):
    return lambda self: getattr(self, name)

def role_path(rel_path):
    return os.path.realpath(
        os.path.join(os.path.dirname(__file__), '..', rel_path)
    )

class NginxSite(Proper):
    STATE_TYPE = Literal['enabled', 'available', 'disabled', 'absent']
    
    config_dir          = prop( str, '/etc/nginx' )
    run_dir             = prop( str, '/run' )
    log_dir             = prop( str, '/var/log/nginx' )
    
    name                = prop( str )
    state               = prop( STATE_TYPE, 'enabled' )
    server_name         = prop( str, from_attr('name') )
    http                = prop( Union[bool, STATE_TYPE, Literal['redirect']],
                                True )
    https               = prop( Union[bool, STATE_TYPE], True )
    http_template       = prop( str, role_path('templates/http.conf') )
    https_template      = prop( str, role_path('templates/https.conf') )
    lets_encrypt        = prop( bool, False )
    proxy               = prop( bool, False )
    proxy_location      = prop( str, '/' )
    proxy_path          = prop( str, '/' )
    proxy_scheme        = prop( str, 'http' )
    proxy_host          = prop( str, 'localhost' )
    proxy_port          = prop( Union[None, int, str],
                                from_call('default_proxy_port') )
    proxy_dest          = prop( str,
                                from_call('default_proxy_dest') )
    proxy_websockets    = prop( bool,
                                from_vars('nginx_websockets', False) )
    
    def __init__(self, args, vars):
        self.vars = vars
        super().__init__(**{
            **vars.get('nginx_site_defaults', {}),
            **args
        })
    
    def default_proxy_port(self) -> Optional[int]:
        return (8888 if self.proxy_host == 'localhost' else None)
    
    def default_proxy_dest(self) -> str:
        netloc = (
            self.proxy_host if self.proxy_port is None
            else f"{self.proxy_host}:{self.proxy_port}"
        )
        return f"{self.proxy_scheme}://{netloc}{self.proxy_path}"
    
    def _scheme(self, scheme):
        state = getattr(self, scheme)
        if state is True:
            available = (self.state != 'absent')
            enabled = (self.state == 'enabled')
        elif state is False:
            available = False
            enabled = False
        else:
            available = (state != 'absent')
            enabled = (state == 'enabled' or state == 'redirect')
        filename = f"{self.name}.{scheme}.conf"
        conf_path = os.path.join(self.sites_available_dir, filename)
        link_path = os.path.join(self.sites_enabled_dir, filename)
        conf_template = getattr(self, f"{scheme}_template")
        return NginxSiteScheme(
            scheme=scheme, available=available, enabled=enabled,
            conf_template=conf_template, conf_path=conf_path,
            link_path=link_path
        )
        
    def schemes(self):
        return (self._scheme(scheme) for scheme in ('http', 'https'))
    
    @property
    def sites_available_dir(self):
        return os.path.join( self.config_dir, 'sites-available' )
    
    @property
    def sites_enabled_dir(self):
        return os.path.join( self.config_dir, 'sites-enabled' )

class ActionModule(NansiActionBase):
    def run_actions(self):
        site = NginxSite(self._task.args, self._task_vars)
        
        self.dump('site', site)
        for name in NginxSite.props().keys():
            self.dump(f"site.{name}", getattr(site, name))
                
        for scheme in site.schemes():
            if scheme.available:
                self.compose_task(
                    'template',
                    _task_vars = {
                        **self._task_vars,
                        'site': site,
                    },
                    src     = scheme.conf_template,
                    dest    = scheme.conf_path,
                    backup  = True,
                )
                if scheme.enabled:
                    self.compose_task(
                        'file',
                        src     = scheme.conf_path,
                        dest    = scheme.link_path,
                        state   = 'link',
                    )
                else:
                    self.compose_task(
                        'file',
                        path    = scheme.link_path,
                        state   = 'absent',
                    )
            else:
                for path in (scheme.link_path, scheme.conf_path):
                    self.compose_task(
                        'file',
                        path    = path,
                        state   = 'absent',
                    )

        
        
        

