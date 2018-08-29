import unittest
import doctest

from flirpy.camera.boson import Boson

class BosonTest(unittest.TestCase):
    """Unit tests for Boson."""

    def setUp(self):
        self.camera = Boson("COM7")
    
    def tearDown(self):
        self.camera.close()

    def test_get_serial(self):
        assert(self.camera.get_camera_serial() != 0)

if __name__ == "__main__":
    unittest.main()