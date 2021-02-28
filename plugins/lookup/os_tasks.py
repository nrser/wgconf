# python 3 headers, required if submitting to Ansible
# from __future__ import (absolute_import, division, print_function)
# __metaclass__ = type

DOCUMENTATION = """
    lookup: platform_tasks
    author: NRSER <neil@neilsouza.com>
    version_added: "2.9.10"
    short_description: select most specific tasks file from a direcotry tree
    description:
        - >-
            Iterates over combinations of

            1.  `ansible_facts.distribution`
                1.  `ansible_facts.distribution_version`
                2.  `ansible_facts.distribution_release`
            2.  `ansible_facts.os_family`
            3.  `ansible_facts.system`
                1.  `ansible_facts.kernel`

            "depth-first" from (1), indented to generally be most specific to
            least.

        - >-
            For a target directory `DIR`, and host with:

            ```YAML
            ansible_facts.distribution: Ubuntu
            ansible_facts.distribution_version: 18.04
            ansible_facts.distribution_release: bionic
            ansible_facts.os_family: Debian
            ansible_facts.system: Linux
            ansible_facts.kernel: 4.15.0-106-generic
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
            macOS looks a bit weirder, as the process was designed with Linux in
            mind, but should still work fine due to there only being one major
            distribution (at this time, at least).

            Assuming:

            ```YAML
            ansible_facts.distribution: MacOSX
            ansible_facts.distribution_version: 10.14.6
            ansible_facts.distribution_release: 18.7.0
            ansible_facts.os_family: Darwin
            ansible_facts.system: Darwin
            ansible_facts.kernel: 18.7.0
            ```

            The path search order will be:

            1.  $DIR/distribution/macosx/version/10.14.6.yaml
            2.  $DIR/distribution/macosx/version/10.14.yaml
            3.  $DIR/distribution/macosx/version/10.yaml
            4.  $DIR/distribution/macosx/release/18.7.0.yaml
            5.  $DIR/distribution/macosx.yaml
            6.  $DIR/family/darwin.yaml
            7.  $DIR/system/darwin/kernel/18.7.0.yaml
            8.  $DIR/system/darwin/kernel/18.7.yaml
            9.  $DIR/system/darwin/kernel/18.yaml
            10. $DIR/system/darwin.yaml
            11. $DIR/any.yaml

            Again, `.yml` extension is supported as well, but `.yaml` takes
            priority.

        - >-
            First file found wins. If none are found, an error is raised.


    options:
      _terms:
        description: Directory path to search.
        required: True
"""

# pylint: disable=wrong-import-position

from typing import *
import os
import logging

import nansi.logging

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.plugins.lookup import LookupBase

from nansi.os_resolve import os_file_resolve, OSResolveError

LOG = logging.getLogger(__name__)

# Task file extensions we look for, in order.
TASK_FILE_EXTS = ('yaml', 'yml')

class LookupModule(LookupBase):

    def run(self, terms, variables: Optional[Dict[str, Any]]=None, **kwargs):
        if variables is None:
            raise AnsibleError("Received `variables=None`")

        if (ansible_facts := variables.get('ansible_facts')) is None:
            raise AnsibleError(
                "Required `ansible_facts` variable is missing, " +
                "maybe `gather_facts` is false?"
            )

        if len(terms) != 1:
            raise AnsibleError(
                "Must give exactly one arg (base directory for resolution), " +
                f"given {terms}"
            )

        base_dir = terms[0]

        if not os.path.exists(base_dir):
            raise AnsibleError(f"Base directory does not exist: {base_dir}")

        if not os.path.isdir(base_dir):
            raise AnsibleError(f"Base directory is not a directory: {base_dir}")

        try:
            path = os_file_resolve(
                variables.get('ansible_facts'),
                base_dir,
                ('yaml', 'yml')
            )
        except KeyError as error:
            raise AnsibleError(*error.args)
        except OSResolveError as error:
            LOG.error(error, facts=ansible_facts, base_dir=base_dir)
            raise AnsibleError(error.message)

        return [path]
