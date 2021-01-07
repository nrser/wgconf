from typing import *
from abc import abstractmethod
import sys
# from types import ModuleType
# from os.path import basename

import yaml
from ansible.module_utils.basic import AnsibleModule
# from ansible.module_utils.common.warnings import warn

from .errors import FailError

SPEC_ATTR = "ARGUMENT_SPEC"
DOC_ATTR = "DOCUMENTATION"
OPT_KEY = "options"

class ArgumentSpecError(Exception):
    @staticmethod
    def src_str_for(x: Any) -> str:
        # if isinstance(x, ModuleType):
        #     if x.__name__ == "__main__" and hasattr(x, "__file__"):
        #         return f"__main__({basename(x.__file__)})"
        #     return x.__name__
        if hasattr(x, "__name__"):
            x = getattr(x, "__name__")
        return str(x)

    def __init__(self, msg, *src_path):
        if src_path:
            src_str = ".".join(map(self.src_str_for, src_path))
            msg = f"Failed to get argument spec from `{src_str}` -- {msg}"
        super().__init__(msg)
        self.msg = msg

class FancyModule:
    changed: bool = False
    module: AnsibleModule

    @classmethod
    def get_argument_spec(cls):
        if hasattr(cls, SPEC_ATTR):
            spec = getattr(cls, SPEC_ATTR)
            if isinstance(spec, str):
                try:
                    spec = yaml.safe_load(spec)
                except Exception as parse_error:
                    raise ArgumentSpecError(
                        "received string and `yaml.safe_load` failed",
                        cls, SPEC_ATTR
                    ) from parse_error
            return spec

        mod_name = cls.__module__
        if mod_name not in sys.modules:
            raise ArgumentSpecError(
                f"{repr(mod_name)} not in `sys.modules`", mod_name, DOC_ATTR
            )

        mod = sys.modules[cls.__module__]
        if not hasattr(mod, "DOCUMENTATION"):
            raise ArgumentSpecError(
                "module has no `DOCUMENTATION` attribute", mod, DOC_ATTR
            )

        doc_yaml = getattr(mod, "DOCUMENTATION")
        try:
            doc = yaml.safe_load(doc_yaml)
        except Exception as parse_error:
            raise ArgumentSpecError(
                "`yaml.safe_load` failed", mod, DOC_ATTR
            ) from parse_error

        if not "options" in doc:
            raise ArgumentSpecError(
                f"has no {repr(OPT_KEY)} key", mod, DOC_ATTR
            )

        return doc["options"]

    def __init__(self):
        self.module = AnsibleModule(
            argument_spec=self.__class__.get_argument_spec(),
        )

    def __getitem__(self, key):
        return self.module.params[key]

    def get(self, key, default=None):
        return self.module.params.get(key, default)

    def fail(self, msg, **kwds):
        raise FailError(msg=msg, **kwds)

    @abstractmethod
    def main(self):
        raise NotImplementedError

    def run(self):
        # pylint: disable=broad-except
        try:
            result = self.main()
        except FailError as error:
            self.module.fail_json(**error.fail_kwds())
            return
        except Exception as error:
            self.module.fail_json(msg=str(error))
            return
        if result is None:
            result = {}
        self.module.exit_json(changed=self.changed, **result)
