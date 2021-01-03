import json

from ansible_collections.community.general.plugins.lookup.onepassword import OnePass
from ansible.plugins.lookup import LookupBase

class OnePassFields(OnePass):
    def _parse_field(self, data_json, field_name, section_title=None):
        if isinstance(data_json, (str, bytes)):
            data = json.loads(data_json)
        else:
            data = data_json
        if isinstance(field_name, (list, tuple)):
            return {
                entry: self._parse_field(data_json, entry, section_title=section_title)
                for entry in field_name
            }
        if section_title is None:
            for field_data in data['details'].get('fields', []):
                if field_data.get('name', '').lower() == field_name.lower():
                    return field_data.get('value', '')
        for section_data in data['details'].get('sections', []):
            if section_title is not None and section_title.lower() != section_data['title'].lower():
                continue
            for field_data in section_data.get('fields', []):
                if field_data.get('t', '').lower() == field_name.lower():
                    return field_data.get('v', '')
        return ''

class LookupModule(LookupBase):

    def run(self, terms, variables=None, **kwargs):
        op = OnePassFields()

        field = kwargs.get('field', 'password')
        section = kwargs.get('section')
        vault = kwargs.get('vault')
        op.subdomain = kwargs.get('subdomain')
        op.username = kwargs.get('username')
        op.secret_key = kwargs.get('secret_key')
        op.master_password = kwargs.get('master_password', kwargs.get('vault_password'))

        op.assert_logged_in()

        values = []
        for term in terms:
            values.append(op.get_field(term, field, section, vault))
        return values

