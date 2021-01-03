#!/usr/bin/python
# -*- coding: utf-8 -*-

# pylint: disable=no-name-in-module,import-error,too-few-public-methods

from typing import *

# Need `python3-apt` installed, don't want to duplicate the auto-install logic
#
# SEE   https://github.com/ansible/ansible/blob/devel/lib/ansible/modules/apt.py
#
import apt

from ansible_collections.nrser.nansi.plugins.module_utils.fancy import (
    FancyModule,
)
from ansible_collections.nrser.nansi.plugins.module_utils.apt.parsed_version import (
    ParsedVersion,
)

# https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_documenting.html#documentation-block
DOCUMENTATION = r'''
module: apt_version
short_description: Resolve upstream versions to their Debian I(apt) counterparts.
description:
    - Manages I(apt) packages (such as for Debian/Ubuntu).
version_added: "0.0.1"
options:
    packages:
        description: List of packages and versions to resolve.
        type: list
        required: true
        elements: dict
        options:
            name:
                description: I(apt) package name.
                type: str
                required: true
            version:
                description: Package upstream version.
                type: str
                required: true
    details:
        description: >-
            Include a list of detailed breakdown for each package in return
            value.
        type: bool
        default: False
'''

# https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_documenting.html#return-block
RETURN = r'''
names:
  description:
    - List of package names in `apt`-ready format.
    - All you should need if you just want to figure out what install/remove.
  type: List[str]
  returned: success
  sample: ["esl-erlang=1:23.0.3-1", "elixir=1.10.4-1"]
details:
  description:
    - Detailed breakdown for each package.
    - Useful if you need to work with the data.
  type: List[Dict[str, str]]
  returned: success and given true `details` argument.
  sample:
    - name: esl-erlang
      version: 1:23.0.3-1
      epoch: "1"
      upstream_version: 23.0.3
      debian_revision: "1"
    - name: elixir
      version: 1.10.4-1
      epoch: null
      upsteam_version: 1.10.4
      debian_revision: "1"
'''

class AptVersionResolve(FancyModule):
    def main(self):
        cache = apt.Cache()
        errors = []
        names = []
        details = []
        for package in self["packages"]:
            if package["name"] not in cache:
                errors.append(
                    {
                        "msg": "Package not found (in apt cache, update it?)",
                        **package,
                    }
                )
                continue

            all_versions = [
                ParsedVersion.from_version(v)
                for v in cache[package["name"]].versions
            ]

            matches = sorted(
                (
                    v
                    for v in all_versions
                    if v.upstream_version == package["version"]
                )
            )

            if len(matches) == 0:
                errors.append(
                    {
                        "msg": "No matches found",
                        "versions": [v.apt_version for v in all_versions],
                        **package,
                    }
                )
            else:
                names.append(f"{package['name']}={matches[0].apt_version}")

                if self["details"]:
                    details.append({
                        "name": package["name"],
                        "version": matches[0].apt_version,
                        "epoch": matches[0].epoch,
                        "upstream_version": matches[0].upstream_version,
                        "debian_revision": matches[0].debian_revision,
                    })

        if len(errors) != 0:
            failures = ", ".join(
                (f"{e['name']}={e['version']}" for e in errors)
            )
            self.fail(
                f"Failed to resolve packages {failures}",
                errors=errors,
            )

        result = dict(names=names)
        if self["details"]:
            result["details"] = details

        return result


if __name__ == "__main__":
    AptVersionResolve().run()
