import logging

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

import nansi.logging

LOG = logging.getLogger(__name__)

class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        nansi.logging.setup_for_display()

        if variables is None:
            raise AnsibleError(
                "Received `variables=None`, not nothin' to be done!"
            )

        omit = kwargs.get('omit', tuple())
        values = {}

        for name, raw_value in variables.items():
            if name not in omit:
                for prefix in terms:
                    if name.startswith(prefix):
                        value = self._templar.template(raw_value)
                        new_name = name.replace(prefix, "", 1)
                        if new_name in values:
                            LOG.warning(
                                f"Duplicate entry for {repr(new_name)} when " +
                                f"de-fixing {name}, overwriting",
                                current_prefix=prefix,
                                var_name=new_name,
                                prev_value=values[new_name],
                                new_value=value,
                            )
                        values[new_name] = value

        return [values]
