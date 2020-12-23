from nansi.plugins.compose_action import ComposeAction

class ActionModule(ComposeAction):
    def compose(self):
        self.log.debug(f"HERE {repr(self._task._become)} {repr(self._task._become_user)}")

        task = self._task.copy()
        task.action = 'command'
        task.args = {
            'argv': ['whoami'],
        }
        task._become = True
        task._become_user = 'root'

        action = self._shared_loader_obj.action_loader.get(
            task.action,
            task=task,
            connection=self._connection,
            play_context=self._play_context,
            loader=self._loader,
            templar=self._templar,
            shared_loader_obj=self._shared_loader_obj,
        )

        result = action.run(task_vars=self._task_vars)

        if result.get("failed", False):
            self.handle_failed_result(task, action, result)
        else:
            self.handle_ok_result(task, action, result)

        return result
