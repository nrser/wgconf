from unittest import TestCase, main

from wgconf.file import File
from wgconf.line import Option

class TestEmptyFile(TestCase):
    def setUp(self):
        self.file = File(path='blah.conf')
    
    def test_str(self):
        self.assertEqual(str(self.file), '')
    
    def test_add_default_section_option(self):
        self.file.default_section['x'] = 'ex'
        
        self.assertEqual(
            str(self.file),
            'x = ex\n',
        )
        
        sections = list(self.file.sections())
        self.assertEqual(len(sections), 1)
        
        section = sections[0]
        self.assertEqual(section.kind, None)
    
if __name__ == '__main__':
    main()
