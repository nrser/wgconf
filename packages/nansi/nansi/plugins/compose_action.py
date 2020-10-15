from __future__ import annotations
import logging
from abc import abstractmethod
from collections.abc import Mapping

from ansible.plugins.action import ActionBase
from ansible.utils.display import Display
from ansible.errors import AnsibleError
from ansible import constants as C

import nansi.logging
from nansi.logging.test import test_logger
from nansi.template.var_values import VarValues

LOG = log = logging.getLogger(__name__)

class ComposedActionFailedError(RuntimeError): #(AnsibleError):
    def __init__(self, msg, name, action, result):
        super().__init__(msg)
        self.name = name
        self.action = action
        self.result = result

class TaskRunner:
    '''Nicety wrapper of a `ComposeAction`, a task name, and optionally task
    variables, allowing you to run the named task through
    `ComposeAction#run_task`:
    
        class ActionModule(ComposeAction):
            def compose(self):
                self.tasks.file(
                    path    = 'where/ever',
                    state   = 'absent',
                )
    
    Nice, huh?
    
    Also, you can create instances with different task variables:
    
        class ActionModule(ComposeAction):
            def compose(self):
                self.tasks.template.with_vars(
                    **self._task_vars,
                    python  = 'headache',
                )(
                    src     = 'source.conf.j2',
                    dest    = 'destination.conf',
                )
    
    or, for short, just use:
    
        class ActionModule(ComposeAction):
            def compose(self):
                self.tasks.template.add_vars(
                    python  = 'headache',
                )(
                    src     = 'source.conf.j2',
                    dest    = 'destination.conf',
                )
    
    '''
    
    def __init__(self, compose_action, task_name, task_vars=None):
        self._compose_action = compose_action
        self._task_name = task_name
        self._task_vars = task_vars
    
    def run(self, **task_args):
        return self._compose_action.run_task(
            self._task_name,
            self._task_vars,
            **task_args
        )
    
    __call__ = run
    
    def with_vars(self, **task_vars):
        return self.__class__(
            self._compose_action,
            self._task_name,
            task_vars,
        )
    
    def add_vars(self, **new_task_vars):
        if self._task_vars is None:
            base_vars = self._compose_action._task_vars
        else:
            base_vars = self._task_vars
        
        return self.__class__(
            self._compose_action,
            self._task_name,
            { **base_vars, **new_task_vars },
        )

class Tasks:
    '''Nicety wrapper assigned to `ComposeAction#tasks`, allowing you to do:
    
        self.tasks.file(
            path = 'some/path',
            state = 'absent',
        )
    
    Attribute access returns `functools.partial( compose_action, name)`.
    '''
    
    def __init__(self, compose_action: ComposeAction):
        self.__compose_action = compose_action
    
    def __getattr__(self, task_name: str) -> TaskRunner:
        return TaskRunner(self.__compose_action, task_name)
    
    __getitem__ = __getattr__

class ComposeAction(ActionBase):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        
        # *Not* dependent on `run()`-time information, so this can be setup now
        self.tasks = Tasks(self)
        
        nansi.logging.setup_for_display()
        
        self.log = logging.getLogger(
            f"{ComposeAction.__module__}.{ComposeAction.__name__}" +
            f"( _task.action = {repr(self._task.action)} )"
        )
    
    # Helper Methods
    # ========================================================================
    
    def render(self, value):
        return self._templar.template(value)
    
    def prefixed_vars(self, prefix: Optional[str]=None, omit=tuple()):
        if prefix is None:
            prefix = self._task.action
        if not prefix.endswith('_'):
            prefix = prefix + '_'
        if isinstance(omit, str):
            omit = (omit,)
        omit = {
            (name if name.startswith(prefix) else f"{prefix}{name}")
            for name in omit
        }
        return {
            name.replace(prefix, '', 1): value
            for name, value
            in self._task_vars.items()
            if (name not in omit and name.startswith(prefix))
        }
    
    def collect_args(
        self,
        defaults={},
        omit_vars=tuple(),
        var_prefix=None
    ):
        return {
            **defaults,
            **self.prefixed_vars(prefix=var_prefix, omit=omit_vars),
            **self._task.args,
        }
    
    # Task Commposition Methods
    # =========================================================================
    
    @abstractmethod
    def compose(self) -> None:
        '''Responsible for executing composed sub-tasks by calling
        `#run_task()`, called automatically inside `#run()`.
        
        Abstract -- must be implemented by realizing classes.
        '''
        pass
    
    def run(self, tmp=None, task_vars=None):
        self.log.debug(f"Starting run()...")
        
        result = super().run(tmp, task_vars)
        result['changed'] = False
        result['results'] = []
        
        del tmp # Some Ansible legacy shit I guess
        
        if task_vars is None: # Hope not, not sure what that would mean..?
            task_vars = {}
        
        for attr_name in ('_task_vars', '_result', '_var_values'):
            if hasattr(self, attr_name):
                raise RuntimeError(
                    f"Already *has* self.{attr_name}: " +
                    repr(getattr(self, attr_name))
                )
        
        self._task_vars = task_vars
        self._result = result
        self._var_values = VarValues(self._templar, task_vars)
        
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
    
    def run_task(self, name, task_vars=None, /, **task_args):
        if task_vars is None:
            task_vars = self._task_vars
        # Since they're becoming args to tasks, any variables that may have 
        # ended up in here need to be template rendered before execution
        task_args = self.render(task_args)
        task = self._task.copy()
        task.action = name
        task.args = task_args
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
                module_args=task_args,
                task_vars=task_vars,
            )
        else:
            result = action.run(task_vars=task_vars)
        
        self._result['results'].append(result)
        
        if result.get('failed', False):
            self.log.debug(f"{name} FAILED RESULT", result)
            raise ComposedActionFailedError(
                result.get('msg', ''), name, action, result
            )
        
        if result['changed'] and not self._result['changed']:
            self._result['changed'] = True
        
        return result
        