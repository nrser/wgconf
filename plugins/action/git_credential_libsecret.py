from __future__ import annotations
from os import path
from collections import abc

from nansi.plugins.action.compose import ComposeAction
from nansi.plugins.action.defaults import APT_DEFAULTS
from nansi.os_resolve import os_map_resolve

class ActionModule(ComposeAction):

    def install_deps_apt(self):
        apt_args = {
            **APT_DEFAULTS,
            **self.prefixed_vars(prefix="apt_", omit=("name", "state")),
        }

        mod_args = self.collect_args(
            var_prefix=f"{self._task.action}_apt_",
            defaults = dict(
                name = ['libsecret-1-0', 'libsecret-1-dev'],
            ),
        )

        for name in ('name', 'state'):
            if name in mod_args and isinstance(mod_args[name], abc.Mapping):
                mod_args[name] = os_map_resolve(
                    self._task_vars['ansible_facts'],
                    mod_args[name]
                )

        self.tasks.apt(**{ **apt_args, **mod_args })

    def install_deps(self):
        os_map_resolve(
            self._task_vars['ansible_facts'],
            {
                'family': {
                    'debian': self.install_deps_apt,
                }
            }
        )()

    def compose(self):
        self.install_deps()

        args = self.collect_args(
            defaults = dict(
                git_contrib_path = self._var_values.get(
                    'git_contrib_path',
                    '/usr/share/doc/git/contrib',
                )
            )
        )

        git_libsecret_path = path.join(
            args['git_contrib_path'], 'credential', 'libsecret'
        )

        self.tasks.make( chdir = git_libsecret_path )

        self.tasks.git_config(
            scope   = 'system',
            name    = 'credential.helper',
            value   = path.join(
                        git_libsecret_path,
                        'git-credential-libsecret'
                    ),
        )
