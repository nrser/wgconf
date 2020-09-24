from ansible.module_utils.basic import AnsibleModule

def main():
    module = AnsibleModule(
        supports_check_mode = False,
        
        # https://docs.ansible.com/ansible/latest/dev_guide/developing_program_flow_modules.html#argument-spec
        argument_spec   = dict(
            name = dict(type='str', required=True),
        ),
    )   
    
    # I guess this goes to syslog... and then... sits there.
    module.log(f"Yo, we ova here {module.params['name']}!")
    
    module.exit_json(
        changed=False,
    )

if __name__ == '__main__':
    main()
