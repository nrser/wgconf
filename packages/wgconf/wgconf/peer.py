from __future__ import annotations
from typing import List, Optional

from .section import Section, Prop
from .line import SectionHead


class Peer(Section):
    allowed_ips = Prop("AllowedIPs", List[str])
    public_key = Prop("PublicKey", str)
    endpoint = Prop("Endpoint", Optional[str])
    persistent_keepalive = Prop("PersistentKeepalive", Optional[int])
    preshared_key = Prop("PresharedKey", Optional[str])

    @classmethod
    def create(
        cls,
        name: str,
        allowed_ips: allowed_ips.type,
        public_key: public_key.type,
        description: Section.description.type = None,
        endpoint: endpoint.type = None,
        persistent_keepalive: persistent_keepalive.type = None,
        preshared_key: preshared_key.type = None,
    ) -> Peer:
        peer = Peer(SectionHead("Peer"))
        peer.update(
            name=name,
            description=description,
            allowed_ips=allowed_ips,
            public_key=public_key,
            endpoint=endpoint,
            persistent_keepalive=persistent_keepalive,
            preshared_key=preshared_key,
        )
        return peer
