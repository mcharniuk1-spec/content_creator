import pathlib
import tempfile
import unittest
from scripts.with_fal_key import load_key


class KeyLoaderTests(unittest.TestCase):
    def test_known_formats_and_permissions(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / 'key_fal.yaml'
            for content in ('falai="dummy-value"', 'FAL_KEY: dummy-value'):
                p.write_text(content)
                p.chmod(0o600)
                self.assertEqual(load_key(p), 'dummy-value')
            p.chmod(0o644)
            with self.assertRaises(ValueError):
                load_key(p)

    def test_does_not_execute_input(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / 'key_fal.yaml'
            p.write_text('falai="a"; __import__("os").system("false")')
            p.chmod(0o600)
            with self.assertRaises((SyntaxError, ValueError)):
                load_key(p)
