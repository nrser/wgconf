from __future__ import annotations
import pprint
import logging

from ansible.plugins.action import ActionBase
from ansible.utils.display import Display
from ansible.errors import AnsibleError

LOG = log = logging.getLogger(__name__)
D = Display()
PP = pprint.PrettyPrinter(indent=4)

class ComposedActionFailedError(RuntimeError): #(AnsibleError):
    def __init__(self, msg, name, action, result):
        super().__init__(msg)
        self.name = name
        self.action = action
        self.result = result

class NansiActionBase(ActionBase):
    
    def dump(self, name, value, method='v'):
        f = getattr(D, method)
        f(" ")
        f(f"# *** {name} ***")
        f(f"# type: {type(value)}")
        f(f"value = {PP.pformat(value)}")
        f(f"# *** /{name} ***")
    
    def run(self, tmp=None, task_vars=None):
        result = super(NansiActionBase, self).run(tmp, task_vars)
        
        del tmp # Some Ansible legacy shit I guess
        
        if task_vars is None: # Hope not, not sure what that would mean..?
            task_vars = {}
        
        for attr_name in ('_task_vars', '_result'):
            if hasattr(self, attr_name):
                raise RuntimeError(
                    f"Already *has* self.{attr_name}: " +
                    repr(getattr(self, attr_name))
                )
        
        self._task_vars = task_vars
        self._result = result
        
        try:
            self.run_actions()
        except AnsibleError as error:
            raise error
        except Exception as error:
            # `AnsibleError(Exception)` sig is (types as best as I can infer):
            # 
            #   __init__(
            #       self,
            #       message: str ="",
            #       obj: ansible.parsing.yaml.objects.AnsibleBaseYAMLObject? = None,
            #       show_content: bool = True,
            #       suppress_extended_error: bool = False,
            #       orig_exc: Exception? = None
            #   )
            # 
            # passes only `message` up to `Exception`.
            # 
            raise error
            raise AnsibleError(error.args[0], orig_exc=error)
        
        return self._result
    
    def run_action(self, name, _task_vars=None, **args):
        if _task_vars is None:
            _task_vars = self._task_vars
        task = self._task.copy()
        task.action = name
        task.args = args
        action = self._shared_loader_obj.action_loader.get(
            task.action,
            task=task,
            connection=self._connection,
            play_context=self._play_context,
            loader=self._loader,
            templar=self._templar,
            shared_loader_obj=self._shared_loader_obj
        )
        result = action.run(task_vars=_task_vars)
        
        if result.get('failed', False):
            self.dump(f"{name} FAILED RESULT", result)
            raise ComposedActionFailedError(
                result.get('msg', ''), name, action, result
            )
        
        if result['changed'] and not self._result['changed']:
            self._result['changed'] = True
        
        return result
        