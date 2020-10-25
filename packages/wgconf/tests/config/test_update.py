from unittest import TestCase, main

from wgconf.util import join_lines, first, pubkey
from wgconf.config import Config

from test_helpers import *

wg_bin_path = '/usr/local/bin/wg'

class TestUpdateConfig(TestCase):
    def test_update_clients(self):
        self.maxDiff = None
        
        hostname = 'testy.example.com'
        
        config = Config(
            hostname=hostname,
            name='wg83',
            wg_bin_path=wg_bin_path,
        )
        
        config.update_interface(
            description="Dat interface.",
            address='10.10.10.10',
            listen_port=12345,
            post_up=config.dir / 'wg83' / 'hooks' / 'go-up.sh',
            post_down=config.dir / 'wg83' / 'hooks' / 'go-down.sh',
            save_config=False,
        )
        
        client_updates = {
            'puter': dict(
                description="Goes on your lap",
                private_address='10.10.10.11',
                dns=['1.1.1.1', '8.8.8.8'],
                persistent_keepalive=25,
            ),
            
            'telle': dict(
                description="Goes in your pocket",
                private_address='10.10.10.12',
                dns='8.8.8.8',
                persistent_keepalive=50,
            ),
        }
        
        client_cfgs = config.update_clients(client_updates)
        
        self.assertEqual(len(client_cfgs), 2)
        
        puter = config.peer('puter')
        telle = config.peer('telle')
        
        self.assertEqual(str(config), unblock(f'''
            [Interface]
            # Name = wg83
            # Description = Dat interface.
            Address = 10.10.10.10/32
            PrivateKey = {config.interface.private_key}
            ListenPort = 12345
            PostUp = /etc/wireguard/wg83/hooks/go-up.sh
            PostDown = /etc/wireguard/wg83/hooks/go-down.sh
            SaveConfig = false
            
            [Peer]
            # Name = puter
            # Description = Goes on your lap
            AllowedIPs = 10.10.10.11/32
            PublicKey = {puter.public_key}
            PresharedKey = {puter.preshared_key}
            
            [Peer]
            # Name = telle
            # Description = Goes in your pocket
            AllowedIPs = 10.10.10.12/32
            PublicKey = {telle.public_key}
            PresharedKey = {telle.preshared_key}
            
        '''))
        
        self.assertEqual(str(client_cfgs['puter']), unblock(f'''
            [Interface]
            # Description = puter client for wg83 interface at testy.example.com
            Address = 10.10.10.11/32
            PrivateKey = {client_cfgs['puter'].interface.private_key}
            DNS = 1.1.1.1, 8.8.8.8
            
            [Peer]
            # Name = wg83@testy.example.com
            AllowedIPs = 0.0.0.0/0, ::/0
            PublicKey = {client_cfgs['puter'].peer().public_key}
            Endpoint = testy.example.com:12345
            PersistentKeepalive = 25
            PresharedKey = {puter.preshared_key}
        '''))
        
        self.assertEqual(str(client_cfgs['telle']), unblock(f'''
            [Interface]
            # Description = telle client for wg83 interface at testy.example.com
            Address = 10.10.10.12/32
            PrivateKey = {client_cfgs['telle'].interface.private_key}
            DNS = 8.8.8.8
            
            [Peer]
            # Name = wg83@testy.example.com
            AllowedIPs = 0.0.0.0/0, ::/0
            PublicKey = {client_cfgs['telle'].peer().public_key}
            Endpoint = testy.example.com:12345
            PersistentKeepalive = 50
            PresharedKey = {telle.preshared_key}
        '''))
        
        client_cfgs_2 = config.update_clients(client_updates)
        
        for name, cfg in client_cfgs_2.items():
            print(f"\n{cfg}\n")
        
        self.assertEqual(len(client_cfgs_2), 0)
            
if __name__ == '__main__':
    main()
