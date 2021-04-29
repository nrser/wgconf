from os import path
import shlex

def splat(f):
    return lambda kwds: f(**kwds)

def is_empty(x):
    return x is None or x == ''

def hook_dest(src, dest_dir):
    if is_empty(src):
        return None

    filename = path.basename(src)
    if filename.endswith('.j2'):
        filename = filename[:-3]

    return path.join(dest_dir, filename)

def hook_value(dest, config, iface):
    '''Produce a coresponding "hook" config value (`PreUp`, `PostDown`, etc.)
    for a hook scrip that is to be coppied or templated onto the target host.

    What is returned here becomes the default for the coreponsing `[Interface]`
    value.

    If `dest` is `None` or '', simply returns `None`.

    If `dest` is not `None`, it must be the path on the target host to the
    hook script. An invocation line for the script is returned, passing `config`
    and `iface` in for use, like:

        >>> hook_value('/etc/wireguard/hooks/post_up.sh', 'wg0', 'eth0')
        /etc/wireguard/hooks/post_up.sh wg0 eth0

    '''
    if is_empty(dest):
        return None
    return shlex.join((dest, config, iface))

def local_client_config_dest(
    dir,
    client_name,
    config_name,
    hostname,
    add_wg0=False,
):
    if config_name is None or (config_name == 'wg0' and not add_wg0):
        filename = f"{hostname}.conf"
    else:
        filename = f"{config_name}@{hostname}.conf"

    return path.join(dir, client_name, filename)

class FilterModule:
    def filters(self):
        return dict(
            wg_cfg_hook_dest=hook_dest,
            wg_cfg_hook_value=hook_value,
            wg_cfg_local_client_config_dest=splat(local_client_config_dest),
        )
