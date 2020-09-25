import shlex
from os import path

from ansible.module_utils.basic import AnsibleModule

STATE_ENABLED = 'enabled'
STATE_DISABLED = 'disabled'

def main():
    module = AnsibleModule(
        supports_check_mode = False,
        
        # https://docs.ansible.com/ansible/latest/dev_guide/developing_program_flow_modules.html#argument-spec
        argument_spec = dict(
            user = dict(
                type        = 'str',
                required    = True,
            ),
            state = dict(
                type    = 'str',
                choices = [ STATE_ENABLED, STATE_DISABLED ],
                default = STATE_ENABLED,
            ),
            loginctl_exe = dict(
                type    = 'path',
                default = '/bin/loginctl',
            )
        ),
    )
    
    user = module.params['user']
    new_state = module.params['state']
    exe = module.params['loginctl_exe']
    
    def run(*subcmd):
        cmd = [exe, *subcmd]
        rc, stdout, stderr = module.run_command(cmd)
        if rc != 0:
            return (dict(rc=rc, cmd=cmd, stdout=stdout, stderr=stderr), None)
        return (None, stdout.strip())
    
    err, out = run('show-user', user, '--property=Linger')
    
    if err:
        if (
            err['rc'] == 1
            and err['stderr'].startswith("Failed to get user:")
        ):
            current_state = STATE_DISABLED
        else:
            return module.fail_json(msg=f"Failed to show user {user}", **err)
    else:
        if out == 'Linger=yes':
            current_state = STATE_ENABLED
        elif out == 'Linger=no':
            current_state = STATE_DISABLED
        else:
            return module.fail_json(msg="Unexpected show user output", out=out)
    
    if new_state == current_state:
        return module.exit_json(changed=False)
    
    if new_state == STATE_ENABLED:
        subcmd = 'enable-linger'
    else:
        subcmd = 'disable-linger'
    
    err, out = run(subcmd, user)
    
    if err:
        return module.fail_json(msg=f"{subcmd} failed for user {user}", **err)
    
    module.exit_json(changed=True)

if __name__ == '__main__':
    main()
