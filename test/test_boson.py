from flirpy.camera.boson import Boson
import pytest
import os

with Boson() as camera:
    if camera.conn is None:
        pytest.skip("Boson not connected, skipping tests", allow_module_level=True)

def test_open_boson():
    camera = Boson()
    camera.close()

def test_get_serial():
    camera = Boson()
    assert camera.get_camera_serial() != 0
    camera.close()

@pytest.mark.skipif(os.name != "nt", reason="Skipping Windows-only test")
def test_capture_windows():
    camera = Boson()
    # Currently have no way of figuring this out
    res = camera.grab(1)
    
    assert res is not None
    assert len(res.shape) == 2
    assert res.dtype == "uint16"
    camera.close()


@pytest.mark.skipif(os.name == "nt", reason="Skipping on Windows")
def test_capture_unix():
    camera = Boson()
    res = camera.grab()
    
    assert res is not None
    assert len(res.shape) == 2
    assert res.dtype == "uint16"
    camera.close()
