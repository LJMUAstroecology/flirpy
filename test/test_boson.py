from flirpy.camera.boson import Boson

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
