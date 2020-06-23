| Variable                            | nrser-mbp | minimao             |
|-------------------------------------|-----------|---------------------|
| ansible_system                      | Darwin    | Linux               |
| ansible_os_family                   | Darwin    | Debian              |
| ansible_distribution                | MacOSX    | Ubuntu              |
| ansible_distribution_release        | 18.7.0    | bionic              |
| ansible_distribution_major_version  | 10        | 18                  |
| ansible_distribution_version        | 10.14.6   | 18.04               |
| ansible_architecture                | x86_64    | x86_64              |
| ansible_kernel                      | 18.7.0    | 4.15.0-106-generic  |


OSX/MacOS Kernel Releases
==============================================================================

https://en.wikipedia.org/wiki/Darwin_%28operating_system%29#Release_history

Correlates kernel versions to release versions.


Dirs and Task Files
==============================================================================

tasks/os/
  system/
    darwin/
      kernel/
        18.yaml
        18.7.yaml
        18.7.0.yaml
    linux/
      kernel/
        4.yaml
        4.15.yaml
        4.15.0.yaml
    darwin.yaml
    linux.yaml
  family/
    darwin.yaml
    debian.yaml
  distribution/
    macosx/
      release/
        18.7.0.yaml
      version/
        10.yaml
        10.14.yaml
        10.14.6.yaml
    ubuntu/
      release/
        bionic.yaml
      version/
        18.yaml
        18.04.yaml
    macosx.yaml
    ubuntu.yaml


Task File Ranks
==============================================================================

### nrser-mbp ###

1.  distribution/macosx/version/10.14.6.yaml
2.  distribution/macosx/version/10.14.yaml
3.  distribution/macosx/version/10.yaml
4.  distribution/macosx/release/18.7.0.yaml
5.  distribution/macosx.yaml
6.  family/darwin.yaml
7.  system/darwin/kernel/18.7.0.yaml
8.  system/darwin/kernel/18.7.yaml
9.  system/darwin/kernel/18.yaml
10. system/darwin.yaml
11. any.yaml

### minimao ###

1.  distribution/ubuntu/version/18.04.yaml
2.  distribution/ubuntu/version/18.yaml
3.  distribution/ubuntu/release/bionic.yaml
4.  distribution/ubuntu.yaml
5.  family/debian.yaml
6.  system/linux/kernel/4.15.0.yaml
7.  system/linux/kernel/4.15.yaml
8.  system/linux/kernel/4.yaml
9.  system/linux.yaml
10. any.yaml

1.  dist/ubuntu/version/18.04.yaml
2.  dist/ubuntu/version/18.yaml
3.  dist/ubuntu/release/bionic.yaml
4.  dist/ubuntu.yaml
5.  fam/debian.yaml
6.  sys/linux/kernel/4.15.0.yaml
7.  sys/linux/kernel/4.15.yaml
8.  sys/linux/kernel/4.yaml
9.  sys/linux.yaml
10. any.yaml

```
search = [
  [ 'dist', ansible_distribution, 'version', ansible_distribution_version ],
  [ 'dist', ansible_distribution, 'release', ansible_distribution_release ],
  [ 'dist', ansible_distribution ],
  [ 'fam', ansible_os_family ],
  [ 'sys', ansible_system, 'kernel', ansible_kernel ],
  [ 'sys', ansible_system ],
  [ 'any' ],
]
```

Reduced
------------------------------------------------------------------------------

### nrser-mbp ###

1.  macosx/10.14.6.yaml
2.  macosx/10.14.yaml
3.  macosx/10.yaml
4.  macosx/18.7.0.yaml
5.  macosx.yaml # <- Uh-oh...
6.  darwin.yaml
7.  darwin/18.7.0.yaml
8.  darwin/18.7.yaml
9.  darwin/18.yaml
10. darwin.yaml
11. any.yaml

This doesn't really work, because `darwin.yaml` (`ansible_os_family`) should 
**not** win over `darwin/18*.yaml` (`ansible_system`, `ansible_kernel`)... that
just doesn't make inherit sense... the fact it's duplicated fucks everything up.

But... man, it seems way nicer and simpler in the reduced form. Hmm...

Maybe de-dup the list, keeping the lowest priority? How could that go wrong?

system = family = dist = "stupidos"
version = 1.2.3
kernel = 1.2.3

1.  X stupidos/1.2.3.yaml
2.  X stupidos/1.2.yaml
3.  X stupidos/1.yaml
4.  X stupidos.yaml
5.  X stupidos.yaml
6.  stupidos/1.2.3.yaml
7.  stupidos/1.2.yaml
8.  stupidos/1.yaml
9.  stupidos.yaml

Ok, that works, yeah?

system = family = dist = "stupidos"
version = 1.2.3
kernel = 3.4.5

1.  stupidos/1.2.3.yaml
2.  stupidos/1.2.yaml
3.  stupidos/1.yaml
4.  X stupidos.yaml
5.  X stupidos.yaml
6.  stupidos/3.4.5.yaml
7.  stupidos/3.4.yaml
8.  stupidos/3.yaml
9.  stupidos.yaml

Yeah... it doesn't work, 'cause kernel and dist versions can conflict :/

### minimao ###

1.  ubuntu/18.04.yaml
2.  ubuntu/18.yaml
3.  ubuntu/bionic.yaml
4.  ubuntu.yaml
5.  debian.yaml
6.  linux/4.15.0.yaml
7.  linux/4.15.yaml
8.  linux/4.yaml
9.  linux.yaml
10. any.yaml

