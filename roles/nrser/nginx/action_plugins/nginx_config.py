from __future__ import annotations
from collections.abc import Mapping
from typing import *
from os.path import join, realpath, dirname

from nansi.plugins.compose_action import ComposeAction

VAR_PREFIX          = "nginx_config_"
DEFAULTS_VAR_NAME   = "nginx_config_defaults"

def role_path(rel_path: str) -> str:
    return realpath(join(dirname(__file__), '..', rel_path))

class ActionModule(ComposeAction):
    def compose(self):
        defaults = {
            'src': role_path('templates/nginx.conf'),
            'dest': join(self.render(var='nginx_config_dir'), 'nginx.conf'),
            'backup': True,
            'vars': {
                'user': 'www-data',
                'run_dir': self._task_vars['nginx_run_dir'],
                'log_dir': self._task_vars['nginx_log_dir'],
                'proxy_websockets': self._task_vars['nginx_proxy_websockets'],
            },
        }
        
        prefixed_vars = self.prefixed_vars(
            omit=('nginx_config_dir', DEFAULTS_VAR_NAME)
        )
        
        template_task_args = {}
        template_task_vars = {}
        
        for params in (defaults, prefixed_vars, self._task.args):
            for name, value in params.items():
                if name == 'vars':
                    template_task_vars.update(value)
                else:
                    template_task_args[name] = value
        
        template_task_vars['dir'] = dirname(
            self.render(template_task_args['dest'])
        )
        
        self.tasks.template(
            _task_vars = { **self._task_vars, **template_task_vars },
            **template_task_args,
        )
        
