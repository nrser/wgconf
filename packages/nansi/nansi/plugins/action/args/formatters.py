from typing import Any, Type
from nansi.plugins.action.args.base import ArgsBase
from nansi.support.go import GO_ARCH_MAP


def os_fact_format(string: str, ansible_facts, **extras) -> str:
    os_facts = {
        "arch": ansible_facts["architecture"].lower(),
        "system": ansible_facts["system"].lower(),
        "release": ansible_facts["distribution_release"].lower(),
        **extras,
    }
    if os_facts["arch"] in GO_ARCH_MAP:
        os_facts["go_arch"] = GO_ARCH_MAP[os_facts["arch"]]
    return string.format(**os_facts)


def os_fact_formatter(*extra_attrs):
    def cast(
        value: Any, expected_type: Type, instance: ArgsBase, **context
    ) -> str:
        return os_fact_format(
            value,
            # Ansible facts shouldn't be templates that need rendering from my
            # understanding, so we can use the raw values
            instance.vars.raw["ansible_facts"],
            **{name: getattr(instance, name) for name in extra_attrs},
        )

    return cast


def attr_formatter(*names):
    """
    >>> class Args(ArgsBase):
    ...     name = Arg( str )
    ...     path = Arg( str, "{name}.txt", cast=attr_formatter("name") )
    ...
    >>> Args({"name": "blah"}).path
    'blah.txt'
    """
    def cast(
        value: str, expected_type: Type, instance: ArgsBase, **context
    ) -> str:
        return value.format(**{name: getattr(instance, name) for name in names})
    return cast
