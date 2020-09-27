import os
from tempfile import TemporaryDirectory
from typing import *

from ansible.template import Templar
from ansible.parsing.dataloader import DataLoader

def template(
    expr: str,
    vars: Optional[Mapping[str, str]]=None,
    filters: Optional[Mapping[str, Callable]]=None,
) -> Any:
    loader = DataLoader()
    templar = Templar(loader, variables=vars)
    
    if filters:
        templar._filters = {**templar._get_filters(), **filters}
    
    return templar.template(expr)

def template_for_filters(filter_module):
    def _template(expr, **vars):
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
        with open(path, 'w') as fp:
            pass
