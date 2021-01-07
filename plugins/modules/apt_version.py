#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, [NRSER]

# https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_documenting.html#documentation-block
DOCUMENTATION = r'''
---
module: apt_version
short_description: Install specific versions of apt packages.
description: >-
    - Installs specific versions of apt packages.
    - Automatically resolves upstream versions to Debian M(apt) counterparts.
    - Fails if B(any) upstream versions can not be resolved.
options:
    state:
        description: >-
            Default state for packages that do not specify one.
        type: str
        choices:
            - present
            - absent
        default: present
    packages:
        description: >-
            One or more maps containing package information.
        type: list
        required: true
        elements: dict
        suboptions:
            state:
                description: Desired state of package.
                type: str
                choices:
                    - present
                    - absent
                default: present
            name:
                description: Name of package (according to M(apt)).
                type: str
                required: true
            version:
                description: Desired B(upstream) version of package.
                type: str
                required: true
note:
    - This is an B(action-only) module that composes others.
seealso:
    - module: nrser.nansi.apt_version_resolve
    - module: apt
author:
    - NRSER
'''

# https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_documenting.html#examples-block
EXAMPLES = r'''
-   name: >-
        Base argument form -- list of multiple packages
    nrser.nansi.apt_version:
        packages:
            -   state:      present
                name:       esl-erlang
                version:    23.0.3

            -   state:      present
                name:       elixir
                version:    1.10.4

-   name: >-
        Concise single-package argument form
    nrser.nansi.apt_version:
        state:      present
        name:       esl-erlang
        version:    23.0.3
'''
