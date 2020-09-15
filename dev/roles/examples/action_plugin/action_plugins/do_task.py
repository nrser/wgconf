#!/usr/bin/python
# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pprint

from ansible.plugins.action import ActionBase
from ansible.utils.display import Display

D = Display()
PP = pprint.PrettyPrinter(indent=4)

def dump(name, v):
    D.v(f"# *** {name} ***")
    D.v(f"# type: {type(v)}")
    D.v(f"value = {PP.pformat(v)}")
    D.v(f"# *** /{name} ***")

class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        result = super(ActionModule, self).run(tmp, task_vars)
        
        dump('self._task', self._task)
        
        # module_name, module_args = tuple(self._task.args['task'].items())[0]
        task_name = self._task.args['name']
        task_args = self._task.args['args']
        
        del tmp  # tmp no longer has any effect

        # Shell module is implemented via command
        self._task.action = task_name
        self._task.args = task_args

        action = self._shared_loader_obj.action_loader.get(
            # 'ansible.legacy.command',
            self._task.action,
            task=self._task,
            connection=self._connection,
            play_context=self._play_context,
            loader=self._loader,
            templar=self._templar,
            shared_loader_obj=self._shared_loader_obj
        )
        
        dump('action', action)
        
        result.update(action.run(task_vars=task_vars))
        
        dump('result', result)
        
        return result
