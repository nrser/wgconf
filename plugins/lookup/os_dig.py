import re
from typing import Optional, List, Dict, Any
import pprint
import logging
from collections.abc import Mapping

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.plugins.lookup import LookupBase
from ansible.utils.display import Display

from nansi.logging.display_handler import DisplayHandler

display = Display()

nansi_log = logging.getLogger('nansi')
nansi_log.setLevel(logging.DEBUG)
nansi_log.addHandler(DisplayHandler(display))

from nansi.os_resolve import os_map_resolve, OSResolveError

NAME = 'os_dig'
TITLE = f"[[{NAME} Lookup Plugin]]"
SEE = f"  @see {__file__}"

def display_error(error, ansible_facts, mapping):
    display.error(TITLE)
    display.error(error.message)
    display.error("Mapping:")
    display.error(f"  {mapping}")
    display.error("Searched key paths:")
    for path in error.tried:
        display.error(f"  {path}")

class LookupModule(LookupBase):

    def run(self, terms, variables: Optional[Dict[str, Any]]=None, **kwargs):
        display.vv(TITLE)
        display.vv(SEE)
        
        if variables is None:
            raise AnsibleError("received `variables=None`")
        
        if (ansible_facts := variables.get('ansible_facts')) is None:
            raise AnsibleError(
                "Required `ansible_facts` variable is missing, " +
                "maybe `gather_facts` is false?"
            )
        
        if len(terms) != 1:
            raise AnsibleError(
                "Must give exactly one arg (mapping for resolution), " +
                f"given {terms}"
            )
        
        mapping = terms[0]
        
        if not isinstance(mapping, Mapping):
            raise AnsibleError(
                f"Arg must be a Mapping, given {type(mapping)}: {mapping}"
            )
        
        display.vv(f"Search map:")
        display.vv(f" {mapping}")
        
        try:
            value = os_map_resolve(ansible_facts, mapping)
        except KeyError as error:
            raise AnsibleError(*error.args)
        except OSResolveError as error:
            display_error(error, ansible_facts, mapping)
            raise AnsibleError(error.message)
        
        result = [value]
        
        display.vv(f"Returning {result}")
        
        display.vv("Completed os_tasks lookup.")
        
        return result
