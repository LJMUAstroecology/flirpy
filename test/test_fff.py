import os

import numpy as np

from flirpy.io.fff import Fff
from flirpy.util.exiftool import Exiftool


class TestFff:
    def setup_method(self):

        folder = os.path.dirname(os.path.abspath(__file__))
        self.test_data_fff = os.path.join(folder, "test_data", "frame_000000.fff")
        self.test_data_meta = os.path.join(folder, "test_data", "frame_000000.txt")

        self.frame = Fff(self.test_data_fff)

    def test_read_image(self):
        image = self.frame.get_image()
        assert len(image.shape) == 2
        assert image.dtype == np.uint16

    def test_read_radiometric_image(self):
        image = self.frame.get_radiometric_image()
        assert len(image.shape) == 2
        assert image.dtype == np.float64

    def test_fff_gps(self):
        coord = self.frame.meta["gps"]
        assert len(coord) == 9

    def test_from_bytes(self):

        with open(self.test_data_fff, "rb") as infile:
            self.frame = Fff(infile.read())

            # Check GPS for sanity
            assert len(self.frame.meta["gps"]) == 9
