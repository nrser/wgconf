from typing import *
import shlex

def shell_join(argv: Iterable[str]) -> str:
    '''See [shlex.join][] in the Python stdlib.
    
    Playbook usage:
    
        some_cmd: "{{ ('blah', 'arg one', 'arg two') | shell_join }}
        # => "blah 'arg one' 'arg two'"
    
    [shlex.join]: https://docs.python.org/3.8/library/shlex.html#shlex.join
    '''
    return shlex.join(argv)

def shell_split(
    cmd: str,
    comments: bool=False,
    posix: bool=True
) -> List[str]:
    '''See [shlex.split][] in the Python stdlib.
    
    Playbook usage:
    
        some_argv: "{{ 'blah arg\ one arg\ two' | shell_split }}"
        # => ['blah', 'arg one', 'arg two']
    
    [shlex.split]: https://docs.python.org/3.8/library/shlex.html#shlex.split
    '''
    return shlex.split(cmd, comments=comments, posix=posix)

class FilterModule:
    def filters(self):
        return dict(
            shell_join=shell_join,
            shell_split=shell_split,
            # Backup aliases, since the names are so close
            shlex_join=shell_join,
            shlex_split=shell_split,
        )
