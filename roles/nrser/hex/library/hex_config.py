#!/usr/bin/python
# -*- coding: utf-8 -*-

DOCUMENTATION = '''
---
module: hex_config
short_description: Manage Hex config (Elixir package manager) through `mix`
description:
  - See above.
options:
  state:
    description:
      - >-
          Map of Hex config keys to desired values. A value of `null` deletes the
        key, resetting it to it's default.
    default: {}
    type: dict
  mix_exe:
    description:
      - Path to the `mix` executable on the target host.
    type: path
    default: /usr/bin/mix
seealso:
  - name: >-
        `hex.config` Mix task documentation
    link: "https://hexdocs.pm/hex/Mix.Tasks.Hex.Config.html#module-config-keys"
    description: Describes the available config keys and values.
'''

EXAMPLES = '''
- name: Configure Hex for offline mode
  hex_config:
    state:
      offline: yes
'''

# Hex config keys, presumed types, and defaults, as of Hex version `0.20.5`:
# 
# |          key          | type |                  default                  |
# | --------------------- | ---- | ----------------------------------------- |
# | api_key               | str  | nil                                       |
# | api_url               | str  | "https//hex.pm/api"                       |
# | cacerts_path          | str  | nil                                       |
# | diff_command          | str  | "git diff --no-index __PATH1__ __PATH2__" |
# | home                  | str  | "/Users/nrser/.hex"                       |
# | http_concurrency      | int  | 8                                         |
# | http_proxy            | str  | nil                                       |
# | http_timeout¹         | int  | nil                                       |
# | https_proxy           | str  | nil                                       |
# | mirror_url            | str  | nil                                       |
# | no_verify_repo_origin | bool | false                                     |
# | offline               | bool | false                                     |
# | repos_key²            | ?    | nil                                       |
# | resolve_verbose       | bool | false                                     |
# | unsafe_https          | bool | false                                     |
# | unsafe_registry       | bool | false                                     |
# 
# ¹ Does not seem to apply correctly within `mix deps.get`
# ² Undocumented?

from typing import *
import re
import json
import shlex
from functools import wraps
from collections import namedtuple

from ansible.module_utils.basic import AnsibleModule

PARSE_RE = re.compile(r'^([\w]+):\ (.+)\ \((.+)\)$')

class FailError(Exception):
    def __init__(self, msg, **kwds):
        super().__init__(msg)
        self.msg = msg
        for name, value in kwds.items():
            setattr(self, name, value)
    
    def fail_kwds(self):
        return self.__dict__

class CmdFailedError(FailError):
    def __init__(self, cmd, desc, rc, stdout, stderr):
        if desc is None:
            msg = f"Command `{shlex.join(cmd)}` failed"
        else:
            msg = f"Failed to {desc}"
        super().__init__(
            msg=msg, cmd=cmd, desc=desc, rc=rc, stdout=stdout, stderr=stderr
        )

class UnknownKeyError(FailError):
    def __init__(self, key, known_keys):
        super().__init__(
            msg=f"Given unknown Hex config key {repr(key)}",
            known_keys=known_keys,
        )

ConfigValue = namedtuple('ConfigValue', ['value', 'is_default'])

def main(fn):
    @wraps(fn)
    def wrapped_main(self, *args, **kwds):
        try:
            fn(self, *args, **kwds)
        except FailError as error:
            self.module.fail_json(**error.fail_kwds())
            return
        except Exception as error:
            self.module.fail_json(msg=str(error))
            return
        self.module.exit_json(changed=self.changed)
    return wrapped_main

def encode(value) -> str:
    if value is True or value is False:
        return str(value).lower()
    if isinstance(value, str):
        return value
    return str(value)

def decode(matched: str):
    if matched == 'nil':
        return None
    else:
        return json.loads(matched)

def parse(config_output: str) -> Mapping[str, ConfigValue]:
    config = {}
    for line in config_output.splitlines():
        match = PARSE_RE.match( line )
        if match is None:
            raise ValueError(f"Can't parse config line: {line}")
        config[match[1]] = ConfigValue(
            value       = decode(match[2]),
            is_default  = (match[3] == 'default'),
        )
    return config

class HexConfig:
    changed: bool
    
    def __init__(self):
        self.module = AnsibleModule(
            supports_check_mode = False,
            
            # https://docs.ansible.com/ansible/latest/dev_guide/developing_program_flow_modules.html#argument-spec
            argument_spec = dict(
                state = dict(
                    type        = 'dict',
                    default     = {},
                ),
                
                mix_exe = dict(
                    type    = 'path',
                    default = '/usr/bin/mix',
                )
            ),
        )
        self.changed = False
    
    def run(self, *subcmd, desc=None):
        cmd = [self['mix_exe'], 'hex.config', *subcmd]
        rc, stdout, stderr = self.module.run_command(cmd)
        if rc != 0:
            raise CmdFailedError(
                cmd=cmd, desc=desc, rc=rc, stdout=stdout, stderr=stderr
            )
        return stdout.strip()
    
    def get_all(self):
        return parse(self.run(desc="read config"))
    
    def set(self, key, value):
        self.run(
            key,
            encode(value),
            desc=f"set key {repr(key)} to {repr(value)}"
        )
        self.changed = True
    
    def delete(self, key):
        self.run(key, '--delete', desc=f"delete key {repr(key)}")
        self.changed = True
    
    def __getitem__(self, key):
        return self.module.params[key]
    
    @main
    def main(self):
        config = self.get_all()
        
        to_set = {}
        to_del = []
        
        for key, value in self['state'].items():
            if key not in config:
                raise UnknownKeyError(key=key, known_keys=list(config.keys()))
            if value is None or value == '':
                if config[key].is_default is False:
                    to_del.append(key)
            else:
                if value != config[key].value:
                    to_set[key] = value
        
        for key, value in to_set.items():
            self.set(key, value)
        for key in to_del:
            self.delete(key)

if __name__ == '__main__':
    HexConfig().main()
