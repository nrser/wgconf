from typing import *

# Need `python3-apt` installed, don't want to duplicate the auto-install logic
#
# SEE   https://github.com/ansible/ansible/blob/devel/lib/ansible/modules/apt.py
#
import apt # pylint: disable=import-error
import apt_pkg # pylint: disable=import-error

class ParsedVersion(apt.package.Version):
    src = Union[str, apt.package.Version]
    epoch = Optional[str]
    upstream_version = str
    debian_revision = Optional[str]

    @staticmethod
    def parse(version: str):
        '''
        Format:

            [epoch:]upstream_version[-debian_revision]

        ### See ###

        1.  https://unix.stackexchange.com/a/96603
        2.  https://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-Version
        3.  https://salsa.debian.org/apt-team/python-apt/-/blob/master/apt/package.py

        ### Examples ###

        1.  `1:23.2.1-1`

        '''
        upstream_version = version
        epoch = None
        debian_revision = None
        if ":" in upstream_version:
            epoch, upstream_version = upstream_version.split(":", 1)
        if "-" in upstream_version:
            upstream_version, debian_revision = upstream_version.rsplit("-", 1)
        return dict(
            epoch=epoch,
            upstream_version=upstream_version,
            debian_revision=debian_revision,
        )

    @classmethod
    def from_str(cls, src: str):
        return cls(src=src, **ParsedVersion.parse(src))

    @classmethod
    def from_version(cls, src: apt.package.Version):
        return cls(src=src, **ParsedVersion.parse(src.version))

    def __init__(
        self,
        src: Union[str, apt.package.Version],
        epoch: Optional[str],
        upstream_version: Optional[str],
        debian_revision: Optional[str],
    ):
        self.src = src
        self.epoch = epoch
        self.upstream_version = upstream_version
        self.debian_revision = debian_revision

    @property
    def apt_version(self) -> str:
        if isinstance(self.src, str):
            return self.src
        return self.src.version

    def _cmp(self, other: Any) -> Union[int, Any]:
        if isinstance(other, str):
            return apt_pkg.version_compare(self.src_str, other)
        if isinstance(other, self.__class__):
            return apt_pkg.version_compare(self.apt_version, other.apt_version)
        return NotImplemented

    def __eq__(self, other: object) -> bool:
        return self._cmp(other) == 0

    def __ge__(self, other) -> bool:
        return self._cmp(other) >= 0

    def __gt__(self, other) -> bool:
        return self._cmp(other) > 0

    def __le__(self, other) -> bool:
        return self._cmp(other) <= 0

    def __lt__(self, other) -> bool:
        return self._cmp(other) < 0

    def __ne__(self, other: object) -> Union[bool, Any]:
        try:
            return self._cmp(other) != 0
        except TypeError:
            return NotImplemented