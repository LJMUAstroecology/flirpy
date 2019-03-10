from flirpy.util.exiftool import Exiftool

def test_exiftool_exists():
    exiftool = Exiftool()
    assert(exiftool._check_path() == True)