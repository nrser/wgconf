from __future__ import annotations
from collections.abc import Mapping
from typing import *
from os.path import join, realpath, dirname

from nansi.plugins.compose_action import ComposeAction
from nansi.plugins.action.defaults import APT_DEFAULTS
from nansi.os_resolve import os_map_resolve, OSResolveError

def role_path(rel_path: str) -> str:
    return realpath(join(dirname(__file__), '..', rel_path))

class ActionModule(ComposeAction):
    
    def common_defaults(self):
        return dict( name = 'nginx' )
    
    def apt(self):
        '''Manage the package via the [apt][1] module.
        
        Arguments are merged from lowest (1) to highest (5) priority:
        
        1.  Nansi's build-in `APT_DEFAULTS`.
        2.  `apt_<name>` variables present, such as `apt_update_cache` becoming
            the `update_cache` argument **except** `apt_name` and `apt_state`,
            which are ignored (doesn't pick-up a default package `name` or
            `state` ).
        3.  Return value of the `common_defaults()` method.
        # 4.  Variables `nginx_package_name` and `nginx_package_state`, becoming
        #     `name` and `state`, respectively.
        5.  Arguments given directly to the `nginx_package` task.
        
        If arguments `name` or `state` end up being mappings after the merge,
        `nansi.os_resolve.os_map_resolve()` is run on them, allowing them to
        carry os-dependent values.
        
        [apt]: https://docs.ansible.com/ansible/latest/modules/apt_module.html
        '''
        
        apt_args = {
            **APT_DEFAULTS,
            **self.prefixed_vars(prefix="apt_", omit=("name", "state")),
        }
        
        mod_args = self.collect_args(
            defaults = {
                **self.common_defaults(),
                **dict(name = ['nginx', 'nginx-common']), # To rm everything
            },
        )
        
        for name in ('name', 'state'):
            if name in mod_args and isinstance(mod_args[name], Mapping):
                mod_args[name] = os_map_resolve(
                    self._task_vars['ansible_facts'],
                    mod_args[name]
                )
        
        args = { **apt_args, **mod_args }
        
        self.tasks.apt(**args)
    
    def compose(self):
        methods = {
            'family': {
                'debian': self.apt,
            }
        }
        os_map_resolve(self._task_vars['ansible_facts'], methods)()
        