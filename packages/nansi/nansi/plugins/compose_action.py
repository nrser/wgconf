from __future__ import annotations
import pprint
import logging
from abc import abstractmethod
from collections.abc import Mapping

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

class ComposeAction(ActionBase):
    
    def dump(self, name, value, method='v'):
        try:
            value_str = PP.pformat(value)
        except Exception as e:
            value_str = f"!ERROR {e}"
        
        f = getattr(D, method)
        f(" ")
        f(f"# *** {name} ***")
        f(f"# type: {type(value)}")
        f(f"value = {value_str}")
        f(f"# *** /{name} ***")
    
    def render(self, value=None, var: Optional[str]=None):
        if var is not None:
            value = self._task_vars[var]
        return self._templar.template(value)
    
    def prefixed_vars(self, prefix: str=None, omit=tuple()):
        if prefix is None:
            prefix = self._task.action
        if not prefix.endswith('_'):
            prefix = prefix + '-'
        if isinstance(omit, str):
            omit = tuple(omit)
        return {
            name.replace(prefix, '', 1): value
            for name, value
            in self._task_vars.items()
            if (name not in omit and name.startswith(prefix))
        }
    
    def compose_args(self, defaults={}):
        var_prefix = f"{self._task.action}_"
        defaults_var_name = f"{self._task.action}_defaults"
        return {
            **defaults,
            **self._task_vars.get(defaults_var_name, {}),
            **self.prefixed_vars(var_prefix, omit=defaults_var_name),
            **self._task.args,
        }
    
    @abstractmethod
    def compose(self):
        '''Responsible for executing composed sub-tasks by calling
        `#run_task()`, called automatically inside `#run()`.
        
        Abstract -- must be implemented by realizing classes.
        '''
        pass
    
    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        result['changed'] = False
        
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
            self.compose()
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
    
    def run_task(self, name, _task_vars=None, **raw_args):
        if _task_vars is None:
            _task_vars = self._task_vars
        # Since they're becoming args to tasks, any variables that may have 
        # ended up in here need to be template rendered before execution
        args = self.render(raw_args)
        task = self._task.copy()
        task.action = name
        task.args = self.render(args)
        action = self._shared_loader_obj.action_loader.get(
            task.action,
            task=task,
            connection=self._connection,
            play_context=self._play_context,
            loader=self._loader,
            templar=self._templar,
            shared_loader_obj=self._shared_loader_obj
        )
        
        if action is None:
            # raise RuntimeError(f"Action {repr(name)} not found")
            result = self._execute_module(
                name,
                module_args = args,
                task_vars = _task_vars,
            )
        else:
            result = action.run(task_vars=_task_vars)
        
        if result.get('failed', False):
            self.dump(f"{name} FAILED RESULT", result)
            raise ComposedActionFailedError(
                result.get('msg', ''), name, action, result
            )
        
        if result['changed'] and not self._result['changed']:
            self._result['changed'] = True
        
        return result
        