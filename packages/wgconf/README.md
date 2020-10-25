`wgconf` -- Programmatic Wireguard Configuration
==============================================================================

Use
------------------------------------------------------------------------------

```python
from wgconf import Config

# Creating new server and client configs

# Quick version, using all defaults
defaults = Config(
  hostname='bounce.example.com',
)
defaults.create_interface()
defaults_client = defaults.add_client(
  name='laptop',
  private_address='10.10.0.2',
)

defaults.write()
defaults_client.write('/home/me/wireguard/laptop/bounce.conf')

# Same thing, but with everything explicitly specified

from wgconf.util import genkey, genpsk

explicit = Config(
  hostname='bounce.example.com',
  name='wg0',
  dir='/etc/wireguard',
  public_address='bounce.example.com',
  wg_bin_path='/usr/bin/wg'
)

explicit.create_interface(
  name='wg0',
  address='10.10.0.1/32',
  listen_port=51820,
  private_key=genkey(),
  dns=None, table=None, mtu=None, pre_up=None, post_up=None, pre_down=None,
  post_down=None, save_config=None
)

explicit.add_client(
  name='client-1',
  address='10.10.0.2',
  preshared_key=True,
  allowed_ips=None,
  dns=None,
  
)

```
