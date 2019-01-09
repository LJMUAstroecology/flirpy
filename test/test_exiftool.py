import unittest
import doctest
import pkg_resources
import os
import subprocess

class ExifToolTest(unittest.TestCase):
    """Check for exiftool."""

    def setUp(self):
        if os.name == "nt":
            self.exiftool = pkg_resources.resource_filename('flirpy', 'bin/exiftool.exe')
        else:
            self.exiftool = pkg_resources.resource_filename('flirpy', 'bin/exiftool')
    
    def tearDown(self):
        pass

    def test_exiftool_exists(self):
        # Fails with FileNotFoundError
        subprocess.check_output([self.exiftool])

if __name__ == "__main__":
    unittest.main()