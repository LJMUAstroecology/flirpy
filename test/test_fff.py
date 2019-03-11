from flirpy.io.fff import Fff
from flirpy.util.exiftool import Exiftool
import os

class TestFff:
    def setup_method(self):

        folder = os.path.dirname(os.path.abspath(__file__))
        self.test_data_fff = os.path.join(folder, "test_data", "frame_000000.fff")
        self.test_data_meta = os.path.join(folder, "test_data", "frame_000000.txt")

        self.frame = Fff(self.test_data_fff)

    def test_read_image(self):
        image = self.frame.get_image()
        assert len(image.shape) == 2

    def test_read_radiometric_image(self):
        meta = Exiftool().meta_from_file(self.test_data_meta)
        image = self.frame.get_radiometric_image(meta)
        assert len(image.shape) == 2

    def test_fff_gps(self):
        coord =  self.frame.get_gps()
        assert len(coord) == 9
    
    def test_from_bytes(self):

        with open(self.test_data_fff, 'rb') as infile:
            self.frame = Fff(infile.read())

            # Check GPS for sanity
            coord =  self.frame.get_gps()
            assert len(coord) == 9
