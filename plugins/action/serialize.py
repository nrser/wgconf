from __future__ import annotations
import logging
import json
from typing import Any, Dict, Literal
import yaml
import base64
from collections import abc

from ansible.parsing.yaml.dumper import AnsibleDumper

from nansi.plugins.action.compose import ComposeAction
from nansi.plugins.action.args.all import Arg, OpenArgsBase
from nansi.utils.functions import get_fn

LOG = logging.getLogger(__name__)


class Args(OpenArgsBase):
    DEFAULT_ENV_OPTS = (("bytes_base", 16),)
    DEFAULT_JSON_OPTS = (("indent", 2),)

    # Same as Ansible's `to_nice_yaml` filter plugin
    #
    # https://github.com/ansible/ansible/blob/9ea56ff2925a2d6afe62333340570b44e59e50a1/lib/ansible/plugins/filter/core.py#L70
    #
    DEFAULT_YAML_OPTS = (
        ("indent", 2),
        ("allow_unicode", True),
        ("default_flow_style", False),
    )

    data = Arg(Any)
    format = Arg(Literal["env", "json", "yaml"])
    opts = Arg(Dict[str, Any], lambda *_: {})

    @property
    def env_opts(self) -> Dict[str, Any]:
        return {**self.opts, **dict(self.DEFAULT_ENV_OPTS)}

    @property
    def json_opts(self) -> Dict[str, Any]:
        return {**self.opts, **dict(self.DEFAULT_JSON_OPTS)}

    @property
    def yaml_opts(self) -> Dict[str, Any]:
        return {**self.opts, **dict(self.DEFAULT_YAML_OPTS)}


class ActionModule(ComposeAction):
    def encode_bytes(self, args, bytes) -> str:
        # pylint: disable=redefined-builtin
        fn_name = f"b{args.bytes_base}encode"
        fn = getattr(base64, fn_name)
        return fn(bytes)

    def env_serialize_value(self, args, value):
        if isinstance(value, bytes):
            return self.encode_bytes(args, value)
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            if '"' in value:
                return '"' + value.replace('"', '\\"') + '"'
            return value
        raise TypeError(f"Can't env serialize {type(value)}: {value}")

    def format_env(self, args):
        if not isinstance(args.data, abc.Mapping):
            raise TypeError(
                f"env serialized data must be Mapping, given "
                f"{type(args.data)}: {args.data}"
            )
        return "".join(
            (
                f"{name}={self.env_serialize_value(args, value)}\n"
                for name, value in args.data.items()
            )
        )

    def format_json(self, args):
        return json.dumps(args.data, **args.json_opts) + "\n"

    def format_yaml(self, args):
        """
        ## See

        1.  Ansible's `to_nice_yaml` filter plugin

            https://github.com/ansible/ansible/blob/9ea56ff2925a2d6afe62333340570b44e59e50a1/lib/ansible/plugins/filter/core.py#L70

        """
        return yaml.dump(args.data, Dumper=AnsibleDumper, **args.yaml_opts)

    def compose(self):
        args = Args(self._task.args, self._task_vars)
        content = get_fn(self, f"format_{args.format}")(args)

        self.tasks.copy(content=content, **args.extras())
