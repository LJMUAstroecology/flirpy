from flirpy.util.exiftool import Exiftool

def test_exiftool_exists():
    exiftool = Exiftool()
    assert(exiftool.check_path() == True)