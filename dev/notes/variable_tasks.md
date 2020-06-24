Variable Tasks
==============================================================================

Like this:

```YAML
- action:
    module: "{{ task_name }}"
  args: "{{ task_args }}"
```

or, if don't need to take the module/action/task (whatever, so unclear) from a 
var then:

```YAML
- user: "{{ user_args }}"
```

There's also a DIY in `dev/roles/examples/action_plugin`.

Security Warning
------------------------------------------------------------------------------

Need to turn off `inject_facts_as_vars` to avoid the warning, see:

1.  https://docs.ansible.com/ansible/devel/reference_appendices/faq.html#argsplat-unsafe
2.  https://docs.ansible.com/ansible/devel/reference_appendices/config.html#inject-facts-as-vars

> Honestly though, I don't really see the concern... as far as I can figure, you
> wouldn't get a conflict unless you used some `ansible_`-prefix variable in the
> args... which seems like it could always be a problem regardless of _where_
> that var is used. Must be missing something...
