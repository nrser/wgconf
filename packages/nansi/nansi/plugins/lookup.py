from ansible.plugins.lookup import LookupBase as AnsibleLookupBase

class LookupBase(AnsibleLookupBase):
    def run(self, terms, variables=None, **kwds):
        pass
