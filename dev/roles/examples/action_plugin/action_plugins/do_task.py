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
    D.vvvv(f"*** {name} ***")
    D.vvvv(f"value: {PP.pformat(v)}")
    D.vvvv(f"type: {type(v)}")
    D.vvvv(f"******")

class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        super(ActionModule, self).run(tmp, task_vars)
        
        # module_name, module_args = tuple(self._task.args['task'].items())[0]
        task_name = self._task.args['name']
        task_args = self._task.args['args']
        
        del tmp  # tmp no longer has any effect

        # Shell module is implemented via command
        self._task.action = task_name
        self._task.args = task_args

        command_action = self._shared_loader_obj.action_loader.get(
            # 'ansible.legacy.command',
            self._task.action,
            task=self._task,
            connection=self._connection,
            play_context=self._play_context,
            loader=self._loader,
            templar=self._templar,
            shared_loader_obj=self._shared_loader_obj
        )
        
        result = command_action.run(task_vars=task_vars)

        return result
