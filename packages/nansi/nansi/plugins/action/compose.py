from __future__ import annotations
from abc import abstractmethod
from typing import Dict, Optional

from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleError
from ansible.playbook.task import Task

from nansi import logging
from nansi.logging.rich_handler import table
from nansi.template.var_values import VarValues


LOG = logging.getLogger(__name__)


class ComposedActionFailedError(RuntimeError):  # (AnsibleError):
    def __init__(self, msg, name, action, result):
        super().__init__(msg)
        self.name = name
        self.action = action
        self.result = result


class TaskRunner:
    """Nicety wrapper of a `ComposeAction`, a task name, and optionally task
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

    """

    def __init__(self, compose_action, task_name, task_vars=None):
        self._compose_action = compose_action
        self._task_name = task_name
        self._task_vars = task_vars

    def run(self, _raw_params: Optional[str] = None, **task_args):
        # Allow passing of "raw params" (the thing you're prob seen with
        # `command`, `shell`, `raw`, etc.) positionally, which feels nicer
        if _raw_params is not None:
            task_args["_raw_params"] = _raw_params

        return self._compose_action.run_task(
            self._task_name, self._task_vars, **task_args
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
            base_vars = self._compose_action.task_vars
        else:
            base_vars = self._task_vars

        return self.__class__(
            self._compose_action,
            self._task_name,
            {**base_vars, **new_task_vars},
        )


class Tasks:
    """Nicety wrapper assigned to `ComposeAction#tasks`, allowing you to do:

    self.tasks.file(
        path = 'some/path',
        state = 'absent',
    )
    """

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
        self._task_vars = None
        self._result = None
        self._var_values = None

        logging.setup_for_display()

        # self.log = logging.getLogger(
        #     f"{self.__class__.__module__}.{self.__class__.__name__}"
        # )

        self.log = logging.getLogger(
            f"nrser.nansi.{self.__class__.__module__.split('.')[-1]}"
        )

    # This is really just so that pylint shuts up about it's use in TaskRunner
    @property
    def task_vars(self):
        return self._task_vars

    @property
    def vars(self):
        return self._var_values

    # Helper Methods
    # ========================================================================

    def result_status(self, result):
        if result.get("failed", False):
            return "FAILED"
        if result.get("changed", False):
            return "CHANGED"
        return "OK"

    def append_result(self, task, action, result):
        if "composed" not in self._result:
            self._result["composed"] = []
        self._result["composed"].append(
            {
                "task": task.action,
                # "args": task.args,
                "status": self.result_status(result),
            }
        )

    def has_changed(
        self,
        task: Task,
        action: ActionBase,
        result: Dict,
    ) -> bool:
        # pylint: disable=no-self-use
        # Meant to be overridden to customize, so it makes sense to me as a
        # method, even though _this_ implementation doesn't need to be
        """
        Determins if something has "changed" given the result of a composed
        sub-task.

        Default implementation simply propagates the sub-result's `"changed"`
        value.

        :returns: `bool`_ indicating if the composed sub-task has changed
        things.
        """
        return result.get("changed", False)

    def handle_ok_result(
        self,
        task: Task,
        action: ActionBase,
        result: Dict,
    ) -> None:
        """What to do when a task succeeds. Default implementation:

        1.  Calls `append_result`_ to add the `result` to a `'results'` list in
            the master `self._result`.
        2.  Calls `has_changed`_ and updates the `'changed'` value in
            `self._result` if needed.
        """
        status = self.result_status(result)
        self.log.debug(
            f"Composed task `{task.action}` {status}", result=table(result)
        )
        self.append_result(task, action, result)
        if (
            self.has_changed(task, action, result)
            and not self._result["changed"]
        ):
            self._result["changed"] = True

    def handle_failed_result(
        self,
        task: Task,
        action: ActionBase,
        result: Dict,
    ) -> None:
        """
        What to do when a composed task fails. This implementation logs and
        raises a `ComposedActionFailedError`_.

        The relevant `Task`_, `ActionBase`_ and `result` `dict`_ are provided
        to allow realizing subclasses to make specific decisions.
        """
        self.log.error(
            f"Composed task `{task.action}` FAILED", result=table(result)
        )

        raise ComposedActionFailedError(
            result.get("msg", ""), task.action, action, result
        )

    def render(self, value):
        return self._templar.template(value)

    def prefixed_vars(self, prefix: Optional[str] = None, omit=tuple()):
        if prefix is None:
            prefix = self._task.action
        if not prefix.endswith("_"):
            prefix = prefix + "_"
        if isinstance(omit, str):
            omit = (omit,)
        omit = {
            (name if name.startswith(prefix) else f"{prefix}{name}")
            for name in omit
        }
        return {
            name.replace(prefix, "", 1): value
            for name, value in self._task_vars.items()
            if (name not in omit and name.startswith(prefix))
        }

    def collect_args(self, defaults={}, omit_vars=tuple(), var_prefix=None):
        # pylint: disable=dangerous-default-value
        return {
            **defaults,
            **self.prefixed_vars(prefix=var_prefix, omit=omit_vars),
            **self._task.args,
        }

    # Task Commposition Methods
    # =========================================================================

    @abstractmethod
    def compose(self) -> None:
        """Responsible for executing composed sub-tasks by calling
        `#run_task()`, called automatically inside `#run()`.

        Abstract -- must be implemented by realizing classes.
        """

    def run(self, tmp=None, task_vars=None):
        self.log.debug(
            "Starting task composition...",
            extra={"data": {"args": table(self._task.args)}}
        )

        self._result = super().run(tmp, task_vars)
        self._result["changed"] = False
        # result["results"] = [] Now handled dynamically in `append_result`_

        del tmp  # Some Ansible legacy shit I guess
        if task_vars is None:  # Hope not, not sure what that would mean..?
            task_vars = {}

        self._task_vars = task_vars
        self._var_values = VarValues(self._templar, task_vars)

        try:
            self.compose()
        except AnsibleError as error:
            self.log.debug(
                f"AnsibleError during `{self.__class__.__name__}.compose`",
                exc_info=True,
            )
            raise error
        except Exception as error:
            self.log.debug(
                f"NON-AnsibleError during `{self.__class__.__name__}.compose`",
                exc_info=True,
            )
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
            raise AnsibleError(error.args[0], orig_exc=error) from error

        self.log.debug("Task composition complete", result=table(self._result))

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
            shared_loader_obj=self._shared_loader_obj,
        )

        if action is None:
            self.log.debug(
                f"Composing task `{name}`",
                extra={"data": {"args": task_args}}
            )
            result = self._execute_module(
                name,
                module_args=task_args,
                task_vars=task_vars,
            )
        else:
            self.log.debug(
                f"Composing action `{name}`",
                extra={"data": {"args": task_args}}
            )
            result = action.run(task_vars=task_vars)

        if result.get("failed", False):
            self.handle_failed_result(task, action, result)
        else:
            self.handle_ok_result(task, action, result)

        return result
