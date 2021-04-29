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
    def cast(args, _, string: str) -> str:
        return os_fact_format(
            string,
            args.task_vars["ansible_facts"],
            **{name: getattr(args, name) for name in extra_attrs},
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
    return lambda args, _, string: string.format(
        **{name: getattr(args, name) for name in names}
    )
