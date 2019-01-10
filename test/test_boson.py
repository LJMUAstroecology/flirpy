from flirpy.camera.boson import Boson, find_boson

# Todo - actually find out which COM port it is..

def test_open_boson():
    camera = Boson(find_boson())
    camera.close()

def test_get_serial():
    camera = Boson(find_boson())
    assert(camera.get_camera_serial() != 0)
    camera.close()