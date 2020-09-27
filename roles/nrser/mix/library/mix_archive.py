#!/usr/bin/python
# -*- coding: utf-8 -*-

EXAMPLES = '''
- name: Install Hex
  mix_archive:
    name: hex
    version: 0.20.5
'''

from typing import *
import re
import json
import shlex
from functools import wraps

from ansible.module_utils.basic import AnsibleModule

PARSE_RE = re.compile(r'^\*\ (\w+)\-([\d\.]+)$')

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

def main(fn):
    @wraps(fn)
    def wrapped_main(self, *args, **kwds):
        try:
            fn(self, *args, **kwds)
        except FailError as error:
            self.module.fail_json(**error.fail_kwds())
            return
        except Exception as error:
            self.module.fail_json(msg=f"{error.__class__.__name__}: {error}")
            return
        self.module.exit_json(changed=self.changed)
    return wrapped_main

def parse(mix_archive_output: str) -> Mapping[str, str]:
    archives = {}
    for line in mix_archive_output.splitlines():
        if line.startswith('* '):
            match = PARSE_RE.match( line )
            if match is None:
                raise ValueError(f"Can't parse archive line: {line}")
            archives[match[1]] = match[2]
    return archives

class ArgMeta(type):
    def __getattr__(self, name: str):
        return lambda **kwds: dict(type=name, **kwds)

class Arg(metaclass=ArgMeta):
    pass

def is_github_repo(repo: str) -> bool:
    return (len(repo.split('/')) == 2 and ':' not in repo)

class MixArchive:
    changed: bool
    
    def __init__(self):
        self.module = AnsibleModule(
            supports_check_mode = False,
            
            # https://docs.ansible.com/ansible/latest/dev_guide/developing_program_flow_modules.html#argument-spec
            #  
            # https://hexdocs.pm/mix/Mix.Tasks.Archive.Install.html
            # 
            argument_spec = dict(
                name        = Arg.str(required=True),
                state       = Arg.str(
                                choices=['present', 'absent'],
                                default='present'
                            ),
                version     = Arg.str(),
                path        = Arg.path(),
                git         = Arg.dict(
                                options=dict(
                                    repo    = Arg.str(required=True),
                                    branch  = Arg.str(),
                                    tag     = Arg.str(),
                                    ref     = Arg.str(),
                                )
                            ),
                mix_exe = Arg.path(default='/usr/bin/mix'),
            ),
        )
        self.changed = False
    
    def __getitem__(self, key):
        return self.module.params[key]
    
    def run(self, *subcmd, desc=None):
        cmd = [self['mix_exe'], *subcmd]
        rc, stdout, stderr = self.module.run_command(cmd)
        if rc != 0:
            raise CmdFailedError(
                cmd=cmd, desc=desc, rc=rc, stdout=stdout, stderr=stderr
            )
        return stdout.strip()
    
    def get_all(self):
        return parse(self.run('archive', desc="read present archive list"))
    
    def _run_install(self, subcmd, src):
        self.run(
            'archive.install',
            '--force',
            *subcmd,
            desc=f"Install {self['name']} archive from {src}"
        )
        self.changed = True
    
    def _git_install(self):
        subcmd = [
            ('github' if is_github_repo(self['git']['repo']) else 'git'),
            self['git']['repo'],
        ]
        
        for key in ('branch', 'tag', 'ref'):
            if self['git'][key] is not None:
                subcmd += [key, self['git'][key]]
                break
        
        self._run_install(subcmd, src=f"{subcmd[1]} repo")
    
    def _path_install(self):
        self._run_install([self['path']], src=f"path {self['path']}")
    
    def _hex_install(self):
        subcmd = ['hex', self['name']]
        if self['version'] is not None:
            subcmd.append(self['version'])
        self._run_install(subcmd, src="hex")
    
    def install(self):
        if self['path'] is not None:
            self._path_install()
        elif self['git'] is not None:
            self._git_install()
        else:
            self._hex_install()
    
    def uninstall(self):
        self.run('archive.uninstall', '--force', self['name'])
        self.changed = True
    
    def check_arg_conflicts(self):
        if self['git'] is None:
            return
        
        if self['path'] is not None:
            raise FailError(f"Arguments `path` and `git` conflict")
        
        excl_git_keys = [
            f"`git.{k}`" for k, v in self['git'].items()
            if k != 'repo' and v is not None
        ]
        
        if len(excl_git_keys) > 1:            
            raise FailError(f"Arguments {', '.join(excl_git_keys)} conflict")
    
    @main
    def main(self):
        self.check_arg_conflicts()
            
        archive_versions = self.get_all()
        
        if self['state'] == 'present':            
            if (
                self['name'] not in archive_versions
                or (
                    self['version'] is not None
                    and archive_versions[self['name']] != self['version']
                )
            ):
                self.install()
        elif self['state'] == 'absent':
            if self['name'] in archive_versions:
                self.uninstall()

if __name__ == '__main__':
    MixArchive().main()
