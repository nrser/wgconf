# python 3 headers, required if submitting to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
    lookup: platform_tasks
    author: NRSER <neil@neilsouza.com>
    version_added: "2.9.10"
    short_description: select most specific tasks file from a direcotry tree
    description:
        - >-
            Iterates over combinations of
            
            1.  `ansible_distribution`
                1.  `ansible_distribution_version`
                2.  `ansible_distribution_release`
            2.  `ansible_os_family`
            3.  `ansible_system`
                1.  `ansible_kernel`

            "depth-first" from (1), indented to generally be most specific to 
            least.

        - >-
            For a target directory `DIR`, and host with:

            ```YAML
            ansible_distribution: Ubuntu
            ansible_distribution_version: 18.04
            ansible_os_family: Debian
            ansible_system: Linux
            ansible_kernel: 4.15.0-106-generic
            ```
            
            The path search order will be:
            
            1.  $DIR/distribution/ubuntu/version/18.04.yaml
            2.  $DIR/distribution/ubuntu/version/18.yaml
            3.  $DIR/distribution/ubuntu/release/bionic.yaml
            4.  $DIR/distribution/ubuntu.yaml
            5.  $DIR/family/debian.yaml
            6.  $DIR/system/linux/kernel/4.15.0.yaml
            7.  $DIR/system/linux/kernel/4.15.yaml
            8.  $DIR/system/linux/kernel/4.yaml
            9.  $DIR/system/linux.yaml
            10. $DIR/any.yaml
            
            `.yml` extension is supported as well, but `.yaml` takes priority.
            
        - >-
            First file found wins. If none are found, an error is raised.


    options:
      _terms:
        description: Directory path to search.
        required: True
"""

import os
from functools import reduce
import re
from typing import Optional, List, Dict, Any
import pprint

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.plugins.lookup import LookupBase
from ansible.utils.display import Display

'''Task file extensions we look for, in order.'''
TASK_FILE_EXTS = ('.yaml', '.yml')

'''Simple Regexp that matches 1 to 4 sequences of digits, `.`-separated, at the
begining of a string. So it wont match just a leading sequence of digits, and it
will match `'1.2.3.4.5.6'` as `'1.2.3.4'`, in order to limit things reasonably.

Does not deal with pre-release versions or any of that other stuff no one can
really seem to agree upon (check out how much SemVer parsers vary regarding
corner cases across languages for a fun time).
'''
VERSION_RE = re.compile(r'^\d+(?:\.\d+){1,3}')

'''File basename to use if no os-variable-specific paths exist.
'''
FALLBACK_BASENAME = 'any'

FACT_KEYS = (
    'distribution',
    'distribution_version',
    'distribution_release',
    'os_family',
    'system',
    'kernel',
)

display = Display()

def split_version(version_str: str) -> Optional[List[str]]:
    match = VERSION_RE.search(version_str)
    
    if match is None:
        return None
    
    return match.group(0).split('.')   

def path_for_segments(segments):
    return os.path.join(
        *(
            str(name).lower()
            for name
            in reduce(lambda a, b: a + b, segments)
        )
    )

def get_vars(vars):
    facts = vars.get('ansible_facts')
    
    if vars is None:
        raise AnsibleError(
            f"[os_tasks] `ansible_facts` variable is None - " +
            "maybe `gather_facts` is false?"
        )
    
    values = []
    
    for key in FACT_KEYS:
        value = facts.get(key)
        
        if value is None:
            raise AnsibleError(
                f"[os_tasks] Required `ansible_facts` value {key} is `None`. " +
                "Maybe `gather_facts` is false or subsetted?"
            )
        
        values.append(value)
    
    return values

class LookupModule(LookupBase):
    
    def _os_tasks_find_path(
        self,
        dir: str,
        bare_rel_path: str,
    ) -> Optional[str]:
        self._os_tasks_searched_brps.append(bare_rel_path)
    
        for ext in TASK_FILE_EXTS:
            rel_path = bare_rel_path + ext
            path = os.path.join(dir, rel_path)
            
            if os.path.exists(path):
                if os.path.isfile(path):
                    display.vvvv(f"*** Found: {{dir}}/{rel_path} ***")
                    return path
                
                display.warning(
                    f"Path exists but is not a file: {{dir}}/{rel_path}"
                )
            
        display.vvvv(f"Not found: {{dir}}/{bare_rel_path}.{{yaml,yml}}")
        
        return None 
    
    def _os_tasks_search(
        self,
        dir: str,
        distribution,
        version,
        release,
        family,
        system,
        kernel,
    ) -> Optional[str]:
        self._os_tasks_searched_brps = []
    
        dist = ('distribution', distribution)
        ver = ('version', version)
        rel = ('release', release)
        fam = ('family', family)
        sys = ('system', system)
        kern = ('kernel', kernel)
        
        order = (
            (dist, ver),
            (dist, rel),
            (dist,),
            (fam,),
            (sys, kern),
            (sys,),
        )
        
        for segments in order:
            bare_rel_paths = []
            last_name, last_value = segments[-1]
            
            if (
                last_name in ('version', 'kernel') and
                (version_segments := split_version(last_value))
            ):
                base_segments = segments[0:-1]
                
                base_path = path_for_segments(base_segments)
                
                for end in range(len(version_segments) - 1, 0, -1):
                    bare_rel_paths.append(
                        os.path.join(
                            base_path,
                            '.'.join(version_segments[0:end]),
                        )
                    )
            else:
                bare_rel_paths.append(path_for_segments(segments))
            
            for bare_rel_path in bare_rel_paths:
                if path := self._os_tasks_find_path(dir, bare_rel_path):
                    return path
        
        if fallback_path := self._os_tasks_find_path(dir, FALLBACK_BASENAME):
            return fallback_path
        
        return None

    def run(self, terms, variables: Optional[Dict[str, Any]]=None, **kwargs):
        
        if variables is None:
            raise AnsibleError("received `variables=None`")
        
        if len(terms) == 0:
            raise AnsibleError("must provide os tasks directory as only term")
        elif len(terms) > 1:
            raise AnsibleError(f"Too many terms given (expects 1): {terms}")
        
        dir = terms[0]
        
        if not os.path.exists(dir):
            raise AnsibleError(f"os tasks path {dir} does not exist")
        
        if not os.path.isdir(dir):
            raise AnsibleError(f"os tasks path {dir} is not a directory")
        
        var_keys = (
            # 'ansible_distribution',
            # 'ansible_distribution_version',
            # 'ansible_distribution_release',
            # 'ansible_os_family',
            # 'ansible_system',
            # 'ansible_kernel',
            'distribution',
            'distribution_version',
            'distribution_release',
            'os_family',
            'system',
            'kernel',
        )
        
        distribution, version, release, family, system, kernel = get_vars(
            variables,
        )
        
        display.vvvv("Starting os_tasks lookup...")
        
        display.vvvv(f"distribution = {distribution}")
        display.vvvv(f"version      = {version}")
        display.vvvv(f"release      = {release}")
        display.vvvv(f"family       = {family}")
        display.vvvv(f"system       = {system}")
        display.vvvv(f"kernel       = {kernel}")
        display.vvvv(f"dir          = {dir}")
        
        display.vvvv("Starting path search...")
        
        path = self._os_tasks_search(
            dir=dir,
            distribution=distribution,
            version=version,
            release=release,
            family=family,
            system=system,
            kernel=kernel,
        )
        
        if path is None:
            display.error(
                "[[os_tasks Lookup Plugin " +
                "(nrser/util/lookup_plugins/os_tasks.py)]]"
            )
            
            display.error("FAILED: No os tasks found!")
            
            display.error("Search values (Ansible facts):")
            
            display.error(f"distribution = {distribution}")
            display.error(f"version      = {version}")
            display.error(f"release      = {release}")
            display.error(f"family       = {family}")
            display.error(f"system       = {system}")
            display.error(f"kernel       = {kernel}")
            
            display.error(f"Search directory ({{dir}}:")
            display.error(dir)
            
            display.error("Searched paths:")
            
            for bare_rel_path in self._os_tasks_searched_brps:
                display.error(f"{{dir}}/{bare_rel_path}.{{yaml,yml}}")
            
            raise AnsibleError(f"No os tasks found, see error messages")
        
        result = [path]
        
        display.vvvv(f"Returning {result}")
        
        display.vvvv("Completed os_tasks lookup.")
        
        return result
