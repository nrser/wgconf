from __future__ import annotations
from collections import abc
from typing import *

from nansi.plugins.action.compose import ComposeAction
from nansi.plugins.action.args.all import Arg, OpenArgsBase, os_fact_format

# pylint: disable=relative-beyond-top-level
from .apt_version import PackageArgs


def cast_name(value, expected_type, instance, **context):
    if isinstance(value, str):
        return value
    if isinstance(value, abc.Mapping):
        return PackageArgs(value, instance)
    return value


def cast_key_id(value, expected_type, **context):
    if value is None:
        return None
    return value.replace(" ", "")


def cast_respoitory_repo(value, expected_type, instance, **context):
    if value is None:
        return None
    return os_fact_format(value, instance.vars.raw["ansible_facts"])


class Args(OpenArgsBase):
    APT_KEY_PREFIX = "key_"
    APT_REPOSITORY_PREFIX = "repository_"

    names = Arg.one_or_more(
        Union[str, PackageArgs],
        item_cast=cast_name,
        alias=("name", "pkg"),
    )

    state = Arg(Literal["present", "absent"], "present")

    key_id = Arg(Optional[str], cast=cast_key_id)

    respoitory_repo = Arg(
        Optional[str], cast=cast_respoitory_repo, alias="repo"
    )

    # This makes sense to always have when coupled with `cache_valid_time`,
    # which prevents the update from happening on *every* *fucking* *run*
    update_cache = Arg(bool, True)

    # Only actually update ever 24 hours (value in seconds)
    cache_valid_time = Arg(int, 24 * 60 * 60)

    # In order to remove config files
    purge = Arg(bool, True)

    @property
    def has_versions(self) -> bool:
        for name in self.names:  # pylint: disable=not-an-iterable
            if isinstance(name, PackageArgs):
                return True
        return False

    def prefixed_items(self, prefix: str) -> Dict[str, Any]:
        return {
            k.replace(prefix, "", 1): v
            for k, v in self.items()
            if k.startswith(prefix) and v is not None
        }

    def has_key(self) -> bool:
        return len(self.prefixed_items(self.APT_KEY_PREFIX)) > 0

    def has_repository(self) -> bool:
        return len(self.prefixed_items(self.APT_REPOSITORY_PREFIX)) > 0

    def key_args(self) -> Dict:
        return self.prefixed_items(self.APT_KEY_PREFIX)

    def repository_args(self) -> Dict:
        return self.prefixed_items(self.APT_REPOSITORY_PREFIX)

    def apt_args(self) -> Dict:
        return {
            name: value
            for name, value in self.items()
            if name != "names"
            and not name.startswith(self.APT_KEY_PREFIX)
            and not name.startswith(self.APT_REPOSITORY_PREFIX)
        }


class ActionModule(ComposeAction):
    def compose(self):
        args = Args(self._task.args, parent=self)

        if args.has_key():
            self.tasks.apt_key(
                state=args.state,
                **args.key_args(),
            )

        if args.has_repository():
            self.tasks.apt_repository(
                state=args.state,
                update_cache=(args.state == "present"),
                **args.repository_args(),
            )

        if args.has_versions:
            apt_versions = self.tasks["nrser.nansi.apt_version_resolve"](
                packages=[
                    name.to_dict()
                    for name in args.names  # pylint: disable=not-an-iterable
                    if isinstance(name, PackageArgs)
                ]
            )
            names = [
                (
                    apt_versions["names"].pop(0)
                    if isinstance(name, PackageArgs)
                    else name
                )
                for name in args.names  # pylint: disable=not-an-iterable
            ]
        else:
            names = args.names

        self.tasks.apt(
            name=names,
            state=args.state,
        )
