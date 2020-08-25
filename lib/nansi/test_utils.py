import os
from tempfile import TemporaryDirectory

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
