from os import path

from ansible.module_utils.basic import AnsibleModule

def main():
    module = AnsibleModule(
        supports_check_mode = False,

        # https://docs.ansible.com/ansible/latest/dev_guide/developing_program_flow_modules.html#argument-spec
        argument_spec   = dict(
            pyenv_root      = dict(
                type            = 'str',
                required        = True,
            ),

            versions        = dict(
                type            = 'list',
                required        = True,
                elements        = 'dict',
                options         = dict(

                    version         = dict(
                        type            = 'str',
                        required        = True
                    ),
                    state           = dict(
                        type            = 'str',
                        required        = True,
                        choices         = ['present', 'absent'],
                    ),
                ),
            ),
        ),
    )

    pyenv_root = module.params['pyenv_root']
    exe = path.join(pyenv_root, 'bin', 'pyenv')
    env = dict(
        PYENV_ROOT = pyenv_root,
    )

    def run(*subcmd):
        cmd = [exe, *subcmd]
        rc, stdout, stderr = module.run_command(cmd, environ_update=env)
        if rc != 0:
            return (dict(rc=rc, cmd=cmd, stdout=stdout, stderr=stderr), None)
        return (None, stdout)

    states = {
        item['version']: item['state']
        for item
        in module.params['versions']
    }

    err, out = run('versions', '--bare')

    if err:
        return module.fail_json(msg="Failed to list pyenv versions", **err)

    existing = out.strip().splitlines()

    install = {
        version
        for version, state
        in states.items() if state == 'present'
    }
    uninstall = set()

    for version in existing:
        if version in install:
            install.remove(version)
        elif version in states and states[version]['state'] == 'absent':
            uninstall.add(version)

    install = sorted(install)
    uninstall = sorted(uninstall)

    for version in install:
        err, out = run('install', version)
        if err:
            return module.fail_json(
                msg=f"Failed to install Python {version}", **err
            )

    for version in uninstall:
        err, out = run('uninstall', version)
        if err:
            return module.fail_json(
                msg=f"Failed to uninstall Python {version}",
                **err
            )

    module.exit_json(
        changed=(len(install) > 0 or len(uninstall) > 0),
        installed=install,
        uninstalled=uninstall,
        states=states,
    )

if __name__ == '__main__':
    main()
