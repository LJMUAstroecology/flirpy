from flirpy.camera.boson import Boson, find_boson_serial, find_boson_video

def test_open_boson():
    camera = Boson(find_boson_serial())
    camera.close()

def test_get_serial():
    camera = Boson(find_boson_serial())
    assert camera.get_camera_serial() != 0
    camera.close()

def test_capture():
    camera = Boson(find_boson_serial())
    res = camera.grab(find_boson_video())
    
    assert res is not None
    assert res.dtype == "uint16"
    camera.close()
