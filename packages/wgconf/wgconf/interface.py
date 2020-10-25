from __future__ import annotations
from typing import *

from .util import *
from .section import Section, Prop
from .line import SectionHead

class Interface(Section):
    DEFAULT_LISTEN_PORT = 51820
    
    address     = Prop('Address', List[str])
    private_key = Prop('PrivateKey', str)
    listen_port = Prop('ListenPort', Optional[int])
    dns         = Prop('DNS', Optional[List[str]])
    table       = Prop('Table', Optional[Union[int, str]]) # TODO Improve..?
    mtu         = Prop('MTU', Optional[int])
    pre_up      = Prop('PreUp', Optional[str])
    post_up     = Prop('PostUp', Optional[str])
    pre_down    = Prop('PreDown', Optional[str])
    post_down   = Prop('PostDown', Optional[str])
    save_config = Prop('SaveConfig', Optional[bool])
    
    @classmethod
    def create(
        self,
        name:           str,
        address:        address.type,
        private_key:    private_key.type,
        description:    Section.description.type = None,
        listen_port:    listen_port.type = None,
        dns:            dns.type = None,
        table:          table.type = None,
        mtu:            mtu.type = None,
        pre_up:         pre_up.type = None,
        post_up:        post_up.type = None,
        pre_down:       pre_down.type = None,
        post_down:      post_down.type = None,
        save_config:    save_config.type = None,
    ) -> Interface:
        interface = Interface(SectionHead('Interface'))
        interface.update(
            name=name, description=description, address=address,
            private_key=private_key, listen_port=listen_port, dns=dns,
            table=table, mtu=mtu, pre_up=pre_up, post_up=post_up,
            pre_down=pre_down, post_down=post_down, save_config=save_config,
        )
        return interface   

    