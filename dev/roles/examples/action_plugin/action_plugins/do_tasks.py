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
        
        # dump('self._task', self._task)
        # dump('self._task.args', self._task.args)
        dump('task_vars', task_vars)
        
        # module_name, module_args = tuple(self._task.args['task'].items())[0]
        tasks = self._task.args['tasks']
        
        # dump('tasks', tasks)
        
        del tmp  # tmp no longer has any effect
        
        # result['result'] = []
        
        for task_dict in tasks:
            for action_name, action_args in task_dict.items():
                task = self._task.copy()
                # Shell module is implemented via command
                task.action = action_name
                task.args = action_args

                action = self._shared_loader_obj.action_loader.get(
                    task.action,
                    task=task,
                    connection=self._connection,
                    play_context=self._play_context,
                    loader=self._loader,
                    templar=self._templar,
                    shared_loader_obj=self._shared_loader_obj
                )
                
                action_result = action.run(task_vars=task_vars)
                
                if action_result['changed']:
                    result['changed'] = True
                # result['results'].append(action_result)
        
        # dump('result', result)
        
        return result
