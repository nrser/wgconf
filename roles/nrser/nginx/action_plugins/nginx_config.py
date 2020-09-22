from __future__ import annotations
from collections.abc import Mapping
from typing import *
from os.path import join, realpath, dirname

from nansi.plugins.compose_action import ComposeAction

def role_path(rel_path: str) -> str:
    return realpath(join(dirname(__file__), '..', rel_path))

class ActionModule(ComposeAction):
    def compose(self):
        defaults = {
            'src': role_path('templates/nginx.conf'),
            'dest': join(self._var_values['nginx_config_dir'], 'nginx.conf'),
            'backup': True,
        }
        
        args = self.collect_args(
            omit_vars   = 'nginx_config_dir', # Not a `template` task arg
            defaults    = defaults,
        )
        
        self.tasks.template.add_vars(
            dir = dirname(self.render(args['dest'])),
        )( **args )
        
