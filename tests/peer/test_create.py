from unittest import TestCase, main

from wgconf.peer import Peer

class TestPeerCreate(TestCase):
    def test_required_args(self):
        name        = 'test-peer'
        allowed_ips = '10.10.0.1/32'
        public_key  = 'not-so-secret'
        
        expected_str = ''.join((
            '[Peer]\n',
            f"# Name = {name}\n",
            f"AllowedIPs = 10.10.0.1/32\n",
            f"PublicKey = {public_key}\n",
        ))
        
        peer = Peer.create(
            name = name,
            allowed_ips = allowed_ips,
            public_key = public_key,
        )
        
        self.assertEqual(peer.name, name)
        self.assertEqual(peer.allowed_ips, [allowed_ips])
        self.assertEqual(peer.public_key, public_key)
        
        self.assertEqual(peer.endpoint, None)
        self.assertEqual(peer.persistent_keepalive, None)
        self.assertEqual(peer.preshared_key, None)
        
        self.assertEqual(str(peer), expected_str)
        
    def test_optional_args(self):
        name        = 'test-peer'
        allowed_ips = '10.10.0.1/32'
        public_key  = 'not-so-secret'
        endpoint = '192.168.0.1:12345'
        persistent_keepalive = 88
        preshared_key = 'shh-dont-tell'
        
        expected_str = ''.join((
            '[Peer]\n',
            f"# Name = {name}\n",
            f"AllowedIPs = 10.10.0.1/32\n",
            f"PublicKey = {public_key}\n",
            f"Endpoint = {endpoint}\n",
            f"PersistentKeepalive = {persistent_keepalive}\n",
            f"PresharedKey = {preshared_key}\n"
        ))
        
        peer = Peer.create(
            name = name,
            allowed_ips = allowed_ips,
            public_key = public_key,
            endpoint = endpoint,
            persistent_keepalive = persistent_keepalive,
            preshared_key = preshared_key,
        )
        
        self.assertEqual(peer.name, name)
        self.assertEqual(peer.allowed_ips, [allowed_ips])
        self.assertEqual(peer.public_key, public_key)
        self.assertEqual(peer.endpoint, endpoint)
        self.assertEqual(peer.persistent_keepalive, persistent_keepalive)
        self.assertEqual(peer.preshared_key, preshared_key)
        
        self.assertEqual(str(peer), expected_str)
        
    def test_allowed_ips_list(self):
        name        = 'test-peer'
        allowed_ips = ['10.10.0.1/32', '10.10.0.2/32']
        public_key  = 'not-so-secret'
        
        expected_str = ''.join((
            '[Peer]\n',
            f"# Name = {name}\n",
            f"AllowedIPs = 10.10.0.1/32, 10.10.0.2/32\n",
            f"PublicKey = {public_key}\n",
        ))
        
        peer = Peer.create(
            name = name,
            allowed_ips = allowed_ips,
            public_key = public_key,
        )
        
        self.assertEqual(peer.name, name)
        self.assertEqual(peer.allowed_ips, allowed_ips)
        self.assertEqual(peer.public_key, public_key)
        
        self.assertEqual(peer.endpoint, None)
        self.assertEqual(peer.persistent_keepalive, None)
        self.assertEqual(peer.preshared_key, None)
        
        self.assertEqual(str(peer), expected_str)
    
if __name__ == '__main__':
    main()
