import pytest

from flirpy.util.exiftool import Exiftool


def test_exiftool_exists():
    exiftool = Exiftool()
    if not hasattr(exiftool, "path"):
        pytest.skip("Exiftool not installed")
    assert exiftool._check_path()
