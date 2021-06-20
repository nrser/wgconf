from unittest import TestCase, main

from wgconf.util import join_lines, first, pubkey
from wgconf.config import Config

from test_helpers import *

wg_bin_path = '/usr/local/bin/wg'

class TestCreateConfig(TestCase):
    def test_defaults(self):
        hostname = 'testy.example.com'
        
        server_config = Config(hostname=hostname, wg_bin_path=wg_bin_path)
        server_config.create_interface()
        client_config = server_config.add_client(
            name='urmom',
            private_address='10.10.0.2',
        )
        
        server_private_key = server_config.interface.private_key
        server_public_key = pubkey(server_private_key, wg_bin_path)
        
        client_private_key = client_config.interface.private_key
        client_public_key = pubkey(client_private_key, wg_bin_path)
        
        preshared_key = server_config.peer('urmom').preshared_key
        
        self.assertEqual(
            preshared_key,
            client_config.peer('wg0@testy.example.com').preshared_key
        )
        
        expected_server_str = unblock(f'''
            [Interface]
            # Name = wg0
            Address = 10.10.0.1/32
            PrivateKey = {server_private_key}
            
            [Peer]
            # Name = urmom
            AllowedIPs = 10.10.0.2/32
            PublicKey = {client_public_key}
            PresharedKey = {preshared_key}
            
        ''')
        
        self.assertEqual(str(server_config), expected_server_str)
        
        expected_client_str = unblock(f'''
            [Interface]
            # Description = urmom client for wg0 interface at testy.example.com
            Address = 10.10.0.2/32
            PrivateKey = {client_private_key}
            
            [Peer]
            # Name = wg0@testy.example.com
            AllowedIPs = 0.0.0.0/0, ::/0
            PublicKey = {server_public_key}
            Endpoint = testy.example.com:51820
            PresharedKey = {preshared_key}
            
        ''')
        
        self.assertEqual(str(client_config), expected_client_str)
            
if __name__ == '__main__':
    main()
