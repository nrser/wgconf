from __future__ import annotations
from collections import abc
from typing import *
from operator import methodcaller, attrgetter

from nansi.plugins.args import Arg, ArgsBase
from nansi.plugins.action.compose_action import ComposeAction
from nansi.support.go import add_go_arch
from nansi.utils.collections import each

from ansible_collections.nrser.nansi.plugins.action.apt_version import (
    PackageArgs,
)  # pylint: disable=no-name-in-module,import-error


def cast_name(apt_ext, value):
    if isinstance(value, str):
        return value
    if isinstance(value, abc.Mapping):
        return PackageArgs(value, apt_ext.task_vars)
    return value


class Args(ArgsBase):
    # @Arg
    # def names(
    #     self,
    #     src: Union[None, str, List[str], Dict, List[Dict]],
    # ) -> List[Union[PackageArgs]]:
    #     return [
    #         (
    #             name
    #             if isinstance(name, str)
    #             else PackageArgs(src, self.task_vars)
    #         )
    #         for name in each((str, dict), src)
    #     ]

    # @Arg
    # def state(
    #     self,
    #     src: Optional[Literal["present", "absent"]],
    # ) -> Literal["present", "absent"]:
    #     return "present" if src is None else src

    # @Arg
    # def key_url(self, src: str) -> str:
    #     return src

    # @Arg
    # def key_id(self, src: str) -> str:
    #     return src.replace(" ", "")

    # @Arg
    # def repo(self, src: str) -> str:
    #     return src.format(
    #         **add_go_arch(
    #             {
    #                 "arch": self.task_vars["ansible_facts"]["architecture"],
    #                 "system": self.task_vars["ansible_facts"]["system"].lower(),
    #                 "release": self.task_vars["ansible_facts"][
    #                     "distribution_release"
    #                 ].lower(),
    #             }
    #         )
    #     )

    # ---

    state = Arg(
        in_type=Optional[Literal["present", "absent"]],
        out_type=Literal["present", "absent"],
        transform=lambda self, src: "present" if src is None else src,
    )
    key_url = Arg(str)
    key_id = Arg(
        in_type=str,
        transform=lambda self, src: src.replace(" ", ""),
    )
    repo = Arg(
        in_type=str,
        transform='transform_repo',
    )
    names = Arg(
        in_type=Union[None, str, Dict, List[str], List[Dict]],
        out_type=List[Union[PackageArgs]],
        transform='transform_names',
    )

    names = Arg(
        Union[None, str, Dict, List[str], List[Dict[str, str]]],
        lambda self, value: [
            (
                name
                if isinstance(name, str)
                else PackageArgs(value, self.task_args)
            )
            for name in each((str, dict), value)
        ],
        List[Union[str, PackageArgs]],
        alias=('name', 'pkg'),
    )

    def transform_names(self, src):
        return [
            (
                name
                if isinstance(name, str)
                else PackageArgs(src, self.task_args)
            )
            for name in each((str, dict), src)
        ]

    def transform_repo(self, src) -> str:
        return src.format(
            **add_go_arch(
                {
                    "arch": self.task_vars["ansible_facts"]["architecture"],
                    "system": self.task_vars["ansible_facts"]["system"].lower(),
                    "release": self.task_vars["ansible_facts"][
                        "distribution_release"
                    ].lower(),
                }
            )
        )

    def has_versions(self) -> bool:
        for name in self.names:
            if isinstance(name, PackageArgs):
                return True
        return False


class ActionModule(ComposeAction):
    def should_update_cache(self) -> bool:
        return self.args.state != "absent"

    def resolve_names(self) -> List[str]:
        if not self.args.has_versions():
            return self.args.names

        resolved = self.tasks["nrser.nansi.apt_version_resolve"](
            packages=[
                name.to_dict()
                for name in self.args.names
                if isinstance(name, PackageArgs)
            ]
        )

        return [
            (
                resolved["names"].pop(0)
                if isinstance(name, PackageArgs)
                else name
            )
            for name in self.args.names
        ]

    def compose(self):
        self.args = Args(self._task.args, self._task_vars)

        self.tasks.apt_key(
            state=self.args.state,
            id=self.args.key_id,
            url=self.args.key_url,
        )

        self.tasks.apt_repository(
            state=self.args.state,
            repo=self.args.repo,
            update_cache=self.should_update_cache(),
        )

        self.tasks.apt(
            name=self.resolve_names(),
            state=self.args.state,
        )
