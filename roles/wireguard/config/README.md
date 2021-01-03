`wireguard` Ansible Role
==============================================================================

Used to install Wireguard and build `.conf` files for interfaces, including
peering (connecting them to each other) *with* per-connection pre-shared keys
(which was a total pain, key exchange sucks man).


Use
------------------------------------------------------------------------------

Check out the "public" variables listed in `defaults/main.yaml`, they're what 
you want to set when invoking the role.

Examples of use in `//deploy/wireguard/HOST/main.yaml`.


Development
------------------------------------------------------------------------------

Everything interesting is in `tasks/`.

The role starts by entering `tasks/main.yaml` (as *all* Ansible roles
automatically do).

Tasks have been split up by subject into a few separate files in `tasks/` to 
prevent `tasks/main.yaml` from getting huge and hard to paw through.

Task files that start with `_` are used as sort-of parameterized subroutines by
including them with different variables. This is ghetto but hey it's Ansible 
IDK what you're really supposed to do, not gonna write a module for them.

`tasks/_peer.yaml` is the one that really sucks... does pre-shared key 
exchange. It was not fun to write; hopefully it just works at this point.

Have fun!
