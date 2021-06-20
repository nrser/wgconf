from unittest import TestCase, main
import configparser
import pathlib

from wgconf.file import File

from test_helpers import *

__DIR__ = pathlib.Path(__file__).parent.absolute()

FILE_PATH = DATA_DIR / 'file' / 'duplicate_options.conf'

class TestDuplicateOptions(TestCase):
    def test_config_parser_fails(self):
        config = configparser.ConfigParser()

        self.assertRaises(
            configparser.DuplicateOptionError,
            config.read,
            FILE_PATH
        )

    def test_read_duplicate_keys(self):
        file = File(
            path =  FILE_PATH,
            dup = 'list',
        )

        self.assertEqual(
            file["Service"]["ExecStart"],
            ["one", "two", "three"]
        )

        self.assertEqual(
            file["Install"]["WantedBy"],
            "multi-user.target"
        )

    def test_write_duplicate_keys(self):
        file = File(
            path =  FILE_PATH,
            dup = 'list',
        )

        file["Service"]["ExecStart"] = ["a", "b"]

        self.assertEqual(
            file["Service"]["ExecStart"],
            ["a", "b"]
        )

        self.assertEqual(
            file["Install"]["WantedBy"],
            "multi-user.target"
        )

        self.assertEqual(
            str(file),
            "\n".join([
                "[Unit]",
                "Description = Blah",
                "",
                "[Service]",
                "ExecStart = a",
                "ExecStart = b",
                "",
                "[Install]",
                "WantedBy = multi-user.target",
                "",
            ])
        )

if __name__ == '__main__':
    main()
