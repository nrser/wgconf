from ansible.plugins.action import ActionBase
from ansible.utils.vars import merge_hash

_VER_KEYS = {"version", "state"}


def _state_for_versions_item(item):
    if isinstance(item, str):
        return dict(version=item, state="present")

    if isinstance(item, dict):
        keys = set(item.keys())
        if not (keys <= _VER_KEYS):
            unknown = keys - _VER_KEYS
            raise ValueError(
                f"Unknown keys {unknown} in `versions` arg item "
                + f"{item}, allowed: {_VER_KEYS}"
            )
        return dict(version=item["version"], state=item.get("state", "present"))

    raise TypeError(
        f"Bad item type {type(item)} in `versions` list, "
        + f"expected str or dict. Item: {item}"
    )


class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        # pylint: disable=broad-except
        if task_vars is None:
            task_vars = dict()
        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp
        try:
            result = merge_hash(
                result, self.work(task_vars, self._task.args.copy())
            )
        except Exception as error:
            result["failed"] = True
            result["msg"] = str(error)
        return result

    def work(self, task_vars, args):
        if "versions" not in args:
            raise ValueError("`versions` argument required")

        args["versions"] = list(map(_state_for_versions_item, args["versions"]))

        args["pyenv_root"] = self._templar.template(
            self._templar.available_variables["pyenv_root"]
        )

        return self._execute_module(
            module_args=args,
            task_vars=task_vars,
        )
