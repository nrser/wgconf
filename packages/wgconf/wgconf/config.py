from __future__ import annotations
from typing import (
    Dict,
    Iterator,
    List,
    TextIO,
    Tuple,
    Union,
    Optional,
)
from pathlib import Path
from collections import namedtuple

from .util import (
    DEFAULT_WG_BIN_PATH,
    PropValue,
    PropValues,
    find,
    first,
    genkey,
    genpsk,
    normalize_address,
    normalize_client_address,
    pick,
    pubkey,
    write,
    path_property,
)
from .file import File
from .peer import Peer
from .interface import Interface
from .section import Section

_SERVER_SIDE_PEER_UPDATE_KEYS = (
    set(Peer.props().keys())
    -
    # Server-peer stuff
    set(("persistent_keepalive", "allowed_ips"))
)

_PeerUpdateAction = namedtuple("_PeerUpdateAction", "name type peer")


class Config:
    DEFAULT_NAME = "wg0"
    DEFAULT_DIR = Path("/etc/wireguard")
    DEFAULT_CLIENT_ALLOWED_IPS = ("0.0.0.0/0", "::/0")
    DEFAULT_PRIVATE_ADDRESS = "10.10.0.1/32"

    hostname: str
    name: Optional[str]
    dir: Optional[Union[Path, str]]
    file: File
    wg_bin_path: Path
    public_address: Optional[str]

    dir = path_property("_dir", doc="Default directory to read/write config")

    # pylint: disable=redefined-builtin
    def __init__(
        self,
        hostname: str,
        name: Optional[str] = DEFAULT_NAME,
        dir: Optional[Union[Path, str]] = DEFAULT_DIR,
        public_address: Optional[str] = None,
        wg_bin_path: Union[str, Path] = DEFAULT_WG_BIN_PATH,
    ):
        self.hostname = hostname
        self.name = name
        self.dir = dir
        self.file = File(self.path)
        self.wg_bin_path = Path(wg_bin_path)
        self.public_address = public_address

    @property
    def filename(self) -> Optional[str]:
        return None if self.name is None else f"{self.name}.conf"

    @property
    def path(self) -> Optional[Path]:
        return None if self.dir is None else (self.dir / self.filename)

    def get_listen_port(self) -> int:
        if interface := self.interface:
            if listen_port := interface.listen_port:
                return listen_port
            return Interface.DEFAULT_LISTEN_PORT
        else:
            raise Exception("No interface defined on this Config")

    def get_public_endpoint(self) -> str:
        if self.public_address is not None:
            return f"{self.public_address}:{self.get_listen_port()}"
        return f"{self.hostname}:{self.get_listen_port()}"

    def __get_interface(self) -> Optional[Interface]:
        if (
            section := find(
                self.file.sections(),
                lambda s: s.kind == "Interface",
            )
        ) :
            return Interface(section.head)
        return None

    def __set_interface(self, interface: Interface) -> None:
        if current := self.interface:
            current.replace(interface)
        else:
            self.file.add_section(interface)

    def __del_interface(self) -> None:
        if interface := self.interface:
            interface.remove()

    interface = property(
        __get_interface,
        __set_interface,
        __del_interface,
        "The (only) [Interface] section (if any)",
    )

    # pylint: disable=too-many-arguments
    def create_interface(
        self,
        name: Section.name.type = None,
        description: Section.description.type = None,
        address: Interface.address.type = DEFAULT_PRIVATE_ADDRESS,
        private_key: Optional[Interface.private_key.type] = None,
        listen_port: Interface.listen_port.type = None,
        dns: Interface.dns.type = None,
        table: Interface.table.type = None,
        mtu: Interface.mtu.type = None,
        pre_up: Interface.pre_up.type = None,
        post_up: Interface.post_up.type = None,
        pre_down: Interface.pre_down.type = None,
        post_down: Interface.post_down.type = None,
        save_config: Interface.save_config.type = None,
    ) -> Interface:
        if private_key is None:
            private_key = genkey(self.wg_bin_path)

        if name is None:
            name = self.name

        interface = Interface.create(
            name=name,
            description=description,
            address=normalize_address(address),
            private_key=private_key,
            listen_port=listen_port,
            dns=dns,
            table=table,
            mtu=mtu,
            pre_up=pre_up,
            post_up=post_up,
            pre_down=pre_down,
            post_down=post_down,
            save_config=save_config,
        )

        self.file.add_section(interface)

        return interface

    def update_interface(self, **props: PropValue) -> None:
        if interface := self.interface:
            interface.update(**props)
        else:
            self.create_interface(**props)

    def peers(self) -> Iterator[Peer]:
        return (
            Peer(section.head)
            for section in self.file.sections()
            if section.kind == "Peer"
        )

    def peer(self, name: Optional[str] = None) -> Optional[Peer]:
        if name is None:
            return first(self.peers())
        return find(self.peers(), lambda p: p.name == name)

    def add_peer(self, **props) -> Peer:
        self._resolve_peer_preshared_key(None, props)
        peer = Peer.create(**props)
        self.file.add_section(peer)
        return peer

    def _process_peer_updates(
        self,
        updates: Dict[str, Union[None, PropValues]],
    ) -> List[_PeerUpdateAction]:
        peers = list(self.peers())
        peers_by_name = {p.name: p for p in peers if p.name is not None}
        peers_by_public_key = {
            p.public_key: p for p in peers if p.public_key is not None
        }

        actions = []

        def add_action(name, type_, peer):
            for action in actions:
                if action.peer is not None and action.peer is peer:
                    raise Exception(
                        f"Existing peer matched for both {action.name} "
                        + f"({action.type}) and {name} ({type_}) updates:"
                        + f"\n\n{peer}"
                    )
            actions.append(_PeerUpdateAction(name, type_, peer))

        for name, update in updates.items():
            peer = peers_by_name.get(name)

            if update is None:
                if peer is not None:
                    add_action(name, "remove", peer)
                continue

            if key := update.get("public_key"):
                if by_pubkey := peers_by_public_key.get(key):
                    if peer is None:
                        peer = by_pubkey
                    elif peer is not by_pubkey:
                        raise Exception(
                            f"Update {name} matched spearate [Peer] by name "
                            + "public key.\n\nBy name:\n\n{peer}\n\nBy public "
                            + "key:\n\n{by_pubkey}"
                        )

            if peer is None:
                add_action(name, "add", None)
            else:
                add_action(name, "modify", peer)

        return actions

    def _resolve_peer_preshared_key(
        self,
        peer: Optional[Peer],
        update: Dict,
    ) -> None:
        """Take care of weird bool values that indicate to generate a psk"""
        if "preshared_key" in update:
            if update["preshared_key"] is True:
                if peer is None or peer.preshared_key is None:
                    update["preshared_key"] = genpsk(self.wg_bin_path)
                else:
                    update["preshared_key"] = peer.preshared_key
            elif update["preshared_key"] is False:
                update["preshared_key"] = None

    def update_peers(self, updates: Dict[str, Union[None, PropValues]]) -> None:
        for action in self._process_peer_updates(updates):
            if action.type == "add":
                self.add_peer(name=action.name, **updates[action.name])
            elif action.type == "modify":
                update = updates[action.name]
                self._resolve_peer_preshared_key(action.peer, update)
                action.peer.update(**update)
            else:
                assert action.type == "remove"
                action.peer.remove()

    def update(
        self,
        interface: Optional[PropValues] = None,
        peers: Optional[Dict[str, PropValues]] = None,
        clients: Optional[Dict[str, PropValues]] = None,
    ) -> None:
        if interface is not None:
            self.update_interface(**interface)
        if peers is not None and len(peers) > 0:
            self.update_peers(peers)
        if clients is not None and len(clients) > 0:
            self.update_clients(clients)

    def _resolve_client_keys(
        self,
        private_key: Optional[str],
        public_key: Optional[str],
    ) -> Tuple[Optional[str], Optional[str]]:
        if (
            private_key is not None
            and public_key is not None
            and pubkey(private_key, self.wg_bin_path) != public_key
        ):
            raise ValueError(
                "Both public and private keys provided, but don't match"
            )

        if public_key is None:
            if private_key is None:
                private_key = genkey(self.wg_bin_path)

            public_key = pubkey(private_key, self.wg_bin_path)

        return (private_key, public_key)

    def add_client(
        self,
        name: str,
        private_address: str,
        description: Optional[str] = None,
        preshared_key: Union[Peer.preshared_key.type, bool] = True,
        allowed_ips: Optional[Peer.allowed_ips.type] = None,
        dns: Interface.dns.type = None,
        persistent_keepalive: Peer.persistent_keepalive.type = None,
        private_key: Optional[Interface.private_key.type] = None,
        public_key: Optional[Peer.public_key.type] = None,
    ) -> Optional[Config]:
        interface = self.interface

        if interface is None:
            raise Exception("No Interface - add one before adding clients")

        private_key, public_key = self._resolve_client_keys(
            private_key, public_key
        )

        if public_key is None:
            if private_key is None:
                private_key = genkey(self.wg_bin_path)

            public_key = pubkey(private_key, self.wg_bin_path)

        if preshared_key is False:
            preshared_key = None
        elif preshared_key is True:
            preshared_key = genpsk(self.wg_bin_path)

        private_address = normalize_client_address(private_address)

        # NOTE  `persistent_keepalive` goes on the *client* Peer
        self.add_peer(
            name=name,
            description=description,
            allowed_ips=private_address,
            public_key=public_key,
            preshared_key=preshared_key,
        )

        if private_key is None:
            return None  # Can't make the config

        return self._make_client_config(
            name=name,
            private_address=private_address,
            allowed_ips=allowed_ips,
            preshared_key=preshared_key,
            dns=dns,
            persistent_keepalive=persistent_keepalive,
            private_key=private_key,
        )

    def _make_client_config(
        self,
        name: str,
        private_address: str,
        private_key: Interface.private_key.type,
        allowed_ips: Peer.allowed_ips.type = None,
        preshared_key: Peer.preshared_key.type = None,
        dns: Interface.dns.type = None,
        persistent_keepalive: Peer.persistent_keepalive.type = None,
    ) -> Config:
        if allowed_ips is None:
            allowed_ips = list(Config.DEFAULT_CLIENT_ALLOWED_IPS)

        client_config = Config(
            hostname=name,
            name=None,
            dir=None,
            wg_bin_path=self.wg_bin_path,
        )
        client_config.create_interface(
            private_key=private_key,
            address=private_address,
            dns=dns,
            description=(
                f"{name} client for {self.interface.name} interface at "
                + f"{self.hostname}"
            ),
        )
        client_config.add_peer(
            name=f"{self.name}@{self.hostname}",
            allowed_ips=allowed_ips,
            endpoint=self.get_public_endpoint(),
            persistent_keepalive=persistent_keepalive,
            preshared_key=preshared_key,
            # TODO Performance... shelling out more than needed props
            public_key=pubkey(self.interface.private_key, self.wg_bin_path),
        )
        return client_config

    def _modify_client(self, peer, update) -> Optional[Config]:
        if "private_key" in update:
            public_key = pubkey(update["private_key"], self.wg_bin_path)
            if "public_key" in update:
                assert public_key == update["public_key"]
            else:
                update["public_key"] = public_key

        self._resolve_peer_preshared_key(peer, update)

        peer_props = pick(update, _SERVER_SIDE_PEER_UPDATE_KEYS)

        if "private_address" in update:
            peer_props["allowed_ips"] = normalize_client_address(
                update["private_address"]
            )

        if not peer.has_changes(**peer_props):
            if "private_key" not in update:
                # No changes, no private key, so no config for you
                return None
            # No changes, but can still make the config, since we have a private
            # key to use
            return self._make_client_config(
                name=peer.name,
                private_address=peer.allowed_ips[0],
                **pick(
                    update,
                    (
                        "private_key",
                        "allowed_ips",
                        "preshared_key",
                        "dns",
                        "persistent_keepalive",
                    ),
                ),
            )

        # Need to make changes, so unless we have a private key we'll need to
        # generate new ones
        if "private_key" in update:
            private_key = update["private_key"]
        else:
            private_key = genkey(self.wg_bin_path)
            peer_props["public_key"] = pubkey(private_key, self.wg_bin_path)

        peer.update(**peer_props)

        return self._make_client_config(
            name=peer.name,
            private_address=peer.allowed_ips[0],
            private_key=private_key,
            **pick(
                update,
                ("allowed_ips", "preshared_key", "dns", "persistent_keepalive"),
            ),
        )

    def update_clients(
        self,
        updates: Dict[Section.name.type, Optional[PropValues]],
    ) -> Dict[str, Config]:
        client_configs = {}
        actions = self._process_peer_updates(updates)

        for action in actions:
            config = None
            update = updates.get(action.name)
            if action.type == "add":
                config = self.add_client(name=action.name, **update)
            elif action.type == "modify":
                config = self._modify_client(action.peer, update)
            elif action.type == "remove":
                action.peer.remove()
            if config is not None:
                client_configs[action.name] = config

        return client_configs

    def __str__(self) -> str:
        return str(self.file)

    def is_diff(self) -> bool:
        return True

    def write(
        self, dest: Union[TextIO, Path, str, None] = None, **util_write_kwds
    ):
        if dest is None:
            if self.dir is None:
                raise Exception(
                    f"Config {self.name} has no default directory to "
                    + "write to, must give one or set `.dir`"
                )
            dest = self.path

        write(dest, str(self), **util_write_kwds)
