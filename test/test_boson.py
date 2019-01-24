from flirpy.camera.boson import Boson
import pytest

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

def test_capture():
    camera = Boson()
    res = camera.grab()
    
    assert res is not None
    assert len(res.shape) == 2
    assert res.dtype == "uint16"
    camera.close()
