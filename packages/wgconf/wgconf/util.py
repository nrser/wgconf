from typing import *
from typing import TextIO # WHY?!?!
from pathlib import Path
from subprocess import check_output
import re
from ipaddress import IPv4Network
from io import IOBase
import os

DEFAULT_WG_BIN_PATH = Path('/usr/bin/wg')

K = TypeVar('K')
T = TypeVar('T')
V = TypeVar('V')

ScalarPropValue = Union[
    str, # Most props
    int, # `ListenPort`
    bool, # `SaveConfig`
]

PropValue = Union[
    ScalarPropValue,
    List[ScalarPropValue]
]

PropValues = NewType(
    'PropValues',
    Dict[str, PropValue]
)

def find(itr: Iterator[T], predicate: Callable[[T], bool]) -> Optional[T]:
    for item in itr:
        if predicate(item):
            return item
    return None

def find_map(itr: Iterator[T], fn: Callable[[T], V]) -> Optional[V]:
    for item in itr:
        if result := fn(item):
            return result

def find_is_a(itr: Iterator[Any], cls: Type[T]) -> Optional[T]:
    for item in itr:
        if isinstance(item, cls):
            return item

def first(iterable: Iterable[T]) -> Optional[T]:
    return next(iter(iterable), None)

def last(itr: Iterable[T]) -> Optional[T]:
    last_item = None
    for item in itr:
        last_item = item
    return last_item

def genkey(
    wg_bin_path: Union[Path, str] = DEFAULT_WG_BIN_PATH,
) -> str:
    return check_output(
        [str(wg_bin_path), 'genkey'],
        encoding='utf_8',
    ).strip()

def pubkey(
    private_key: str,
    wg_bin_path: Union[Path, str] = DEFAULT_WG_BIN_PATH,
) -> str:
    return check_output(
        [str(wg_bin_path), 'pubkey'],
        input=private_key,
        encoding='utf_8',
    ).strip()

def genpsk(
    wg_bin_path: Union[Path, str] = DEFAULT_WG_BIN_PATH,
) -> str:
    return check_output(
        [str(wg_bin_path), 'genpsk'],
        encoding='utf_8',
    ).strip()

def normalize_address(address: str) -> str:
    net = IPv4Network(address)
    return f"{net.network_address}/{net.prefixlen}"

def normalize_client_address(address: str) -> str:
    net = IPv4Network(address)
    if net.prefixlen != 32:
        raise ValueError(
            f"Client addresses prefix length should be /32, given {address}"
        )
    return f"{net.network_address}/{net.prefixlen}"

def pick(dct: Dict[K, V], keys: Container[K]) -> Dict[K, V]:
    return {key: value for key, value in dct.items() if key in keys}

def join_lines(lines: Iterable[str]) -> str:
    return ''.join((f"{line}\n" for line in lines))

def path_property(
    name: str,
    doc: Optional[str] = None,
    required: bool = False,
) -> property:
    kwds = {}
    if required:
        kwds['fget'] = lambda self: getattr(self, name)
        kwds['fset'] = lambda self, v: setattr(
            self,
            name,
            v if isinstance(v, Path) else Path(v)
        )
    else:
        kwds['fget'] = lambda self: getattr(self, name, None)
        kwds['fset'] = lambda self, v: setattr(
            self,
            name,
            v if (v is None or isinstance(v, Path)) else Path(v)
        )
        kwds['fdel'] = lambda self: delattr(self, name)
    if doc is not None:
        kwds['doc'] = doc
    return property(**kwds)

def write(
    dest: Union[TextIO, Path, str],
    string: str,
    *,
    mode: str = 'w',
    encoding: Optional[str] = 'utf_8',
    perms: int = 0o600,
    **other_open_kwds
):
    if isinstance(dest, IOBase):
        dest.write(string)
    else:
        path = dest if isinstance(dest, Path) else Path(dest)

        with path.open(mode=mode, encoding=encoding, **other_open_kwds) as fp:
            fp.write(string)

        os.chmod(path, perms)
