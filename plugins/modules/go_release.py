#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, [NRSER]

# https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_documenting.html#documentation-block
DOCUMENTATION = r'''
---
module: go_release
short_description: Manage installation of a Go release.
description: >-
    - Uses M(nrser.nansi.release), supporting multi-version installs.
    - Though only one will be in the I($PATH).
options:
    version:
        description: What version to install.
        type: str
        required: true
    name:
        description: Name to use for the release directory.
        type: str
        default: go
    state:
        description: What to do about it.
        type: str
        choices:
            - present
            - absent
        default: present
    url:
        description: >-
            Where go download the archive. M(nrser.nansi.release) will format in
            I(name), I(version), I(arch), I(system), and I(go_arch) (if
            available). See examples.
        type: str
        default: >-
            https://dl.google.com/go/go{version}.{system}-{go_arch}.tar.gz
    checksum:
        description: >-
            Used to verify the download contents. Get it from
            U(https://golang.org/dl/) if you care.
        type: str
    manage_profile_env:
        description: >-
            Create/update/delete a profile (shell) script to set I($GOROOT) and
            I($PATH) to point to this install?
        type: bool
        default: true
    profile_dir:
        description: Where to put the profile script.
        type: str
        default: /etc/profile.d
    profile_basename:
        description: What to name the profile script.
        type: str
        default: >-
            "{name}.sh" B(dynamic)
    profile_path:
        description: >-
            Where to write the file, overriding the other I(profile_) arguments.
        type: str
        default: >-
            "{profile_dir}/{profile_basename}" B(dynamic)
note:
    - This is an B(action-only) module that composes others.
seealso:
    - module: nrser.nansi.release
author:
    - NRSER
'''

# https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_documenting.html#examples-block
EXAMPLES = r'''
-   name: >-
        Ensure Go 1.15.6 is installed and available in the $PATH
    nrser.nansi.go_release:
        state: present
        version: 1.15.6
        checksum: >-
            sha256:3918e6cc85e7eaaa6f859f1bdbaac772e7a825b0eb423c63d3ae68b21f84b844

-   name: >-
        Ensure Go 1.15.6 is installed but don't mess with the profile
    nrser.nansi.go_release:
        state: present
        version: 1.15.6
        checksum: >-
            sha256:3918e6cc85e7eaaa6f859f1bdbaac772e7a825b0eb423c63d3ae68b21f84b844
        manage_profile_env: false

'''
