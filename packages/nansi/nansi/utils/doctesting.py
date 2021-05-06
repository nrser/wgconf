import os
import sys
from tempfile import TemporaryDirectory
from typing import Any, Callable, Mapping, Optional

from ansible.template import Templar
from ansible.parsing.dataloader import DataLoader

from nansi import logging

def template(
    expr: str,
    vars: Optional[Mapping[str, str]]=None,
    filters: Optional[Mapping[str, Callable]]=None,
) -> Any:
    # pylint: disable=redefined-builtin
    loader = DataLoader()
    templar = Templar(loader, variables=vars)

    if filters:
        # pylint: disable=protected-access
        templar._filters = {**templar._get_filters(), **filters}

    return templar.template(expr)

def template_for_filters(filter_module):
    def _template(expr, **vars):
        # pylint: disable=redefined-builtin
        return template(expr, vars=vars, filters=filter_module().filters())
    return _template

def temp_paths(*rel_paths):
    handle = TemporaryDirectory()
    base_dir = handle.name
    make_paths(base_dir, rel_paths)
    def rel(path):
        return os.path.relpath(path, base_dir)
    return (handle, base_dir, rel)

def make_paths(base_dir, rel_paths):
    for rel_path in rel_paths:
        path = os.path.join(base_dir, rel_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as _fp:
            pass

def testmod(mod_name: str):
    '''
    Need this stupid shit to avoid things like modules in the Python stdlib
    importing `nansi.utils.collections` instead of the stdlib version because
    fucking Python just goes "oh well the file is here so what the hell let's
    just grab anything around it above all else".

    This allows files to _actually_ be run both ways:

        python PATH_TO_FILE
        python -m doctest PATH_TO_FILE

    '''
    # We want to do some doctest work when either:
    #
    # 1.  `__name__` (passed as `mod_name`) is "__main__", indicating the
    #     calling file is being executed as a script.
    #
    # 2.  My special (as in mentally handicapped) env var `DOCTESTING` is
    #     present, a step taken by my `@/dev/bin/doctest` to let the people here
    #     know there's some testing to be done, since I can't seem to find
    #     any doc regarding what (if anything) `doctest` itself does to meet
    #     this need.
    #
    if mod_name != '__main__' and "DOCTESTING" not in os.environ:
        # We got neither (1) or (2) so bounce the fuck out
        return

    if "DOCTESTING_DEBUG" in os.environ:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.setup(level=level)

    # We want the module ref itself so we can touch it inappropriately
    mod = sys.modules[mod_name]

    # Some ghetto shit to inject a `template` variable *into* the calling module
    # (yay! great idea!) if we find a `FilterModule` class (`type`) in the mod.
    # This avoids having to put a hook function in every Ansible filters file.
    filter_module = getattr(mod, 'FilterModule', None)
    if isinstance(filter_module, type) and not hasattr(mod, 'template'):
        setattr(mod, 'template', template_for_filters(filter_module))

    # And a general hook for whatever else bullshit the file may want to do
    if hasattr(mod, '_doctest_setup_'):
        getattr(mod, '_doctest_setup_')()

    # When run directly (script-style) _we_ need to invoke `doctest`.
    if mod_name == '__main__':
        # pylint: disable=import-outside-toplevel
        import doctest
        results = doctest.testmod(mod)
        if results.failed > 0:
            sys.exit(1)
