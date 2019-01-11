from flirpy.camera.lepton import Lepton

def test_open_lepton():
    camera = Lepton()
    camera.close()
