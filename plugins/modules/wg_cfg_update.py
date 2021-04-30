from pathlib import Path

from ansible.module_utils.basic import AnsibleModule

from wgconf.config import Config

def req(**kwds):
    return dict(required=True, **kwds)

def opt(**kwds):
    return dict(required=False, **kwds)

ARGUMENT_SPEC = dict(
    hostname            = req(type='str'),
    name                = opt(type='str'),
    dir                 = opt(type='path'),
    public_address      = opt(type='str'),
    interface           = opt(type='dict', default={}),
    peers               = opt(type='dict'),
    clients             = opt(type='dict'),
    wg_bin_path         = opt(type='path'),
    client_defaults     = opt(type='dict', default={}),
    peer_defaults       = opt(type='dict', default={}),
    clients_dir         = opt(type='path'),
)

CONFIG_KWDS = {'hostname', 'name', 'dir', 'public_address', 'wg_bin_path'}
CLIENT_OMIT = {'owner'}

def is_0oX00(path):
    return (path.stat().st_mode & 0o077) == 0

def merge_client(props, defaults):
    if props is None:
        return None
    return {
        **defaults,
        **{k:v for k,v in props.items() if k not in CLIENT_OMIT}
    }

def main():
    # https://docs.ansible.com/ansible/latest/dev_guide/developing_program_flow_modules.html#argument-spec

    mod = AnsibleModule(
        argument_spec=ARGUMENT_SPEC,
        supports_check_mode=False,
    )

    result = dict(changed=False, client_configs={})

    config = Config(**{
        k: v
        for k, v in mod.params.items()
        if k in CONFIG_KWDS and mod.params[k] is not None
    })

    peer_defaults, client_defaults = (
        {k: v for k, v in d.items() if v is not None}
        for d in (mod.params['peer_defaults'], mod.params['client_defaults'])
    )

    config.update_interface(**mod.params['interface'])

    if mod.params.get('clients') is not None:
        client_configs = config.update_clients({
            name: merge_client(props, client_defaults)
            for name, props
            in mod.params['clients'].items()
        })

        if len(client_configs) > 0:
            if clients_dir := mod.params['clients_dir']:
                cc_dir = Path(clients_dir)
            else:
                cc_dir = Path(mod.params['dir']) / 'clients'

            cc_dir.mkdir(exist_ok=True)
            if not is_0oX00(cc_dir):
                cc_dir.chmod(0o700)

            for name, client_config in client_configs.items():
                cc_path = cc_dir / f"{name}.conf"
                client_config.write(cc_path)
                result['client_configs'][name] = str(cc_path)

    if mod.params.get('peers') is not None:
        config.update_peers({
            name: {**peer_defaults, **update}
            for name, update
            in mod.params['peers'].items()
        })

    if config.is_diff():
        config.write()
        result['changed'] = True

    mod.exit_json(**result)

if __name__ == '__main__':
    main()
