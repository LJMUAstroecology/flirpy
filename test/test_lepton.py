import pytest
from flirpy.camera.lepton import Lepton

if Lepton.find_video_device() is None:
    pytest.skip("Lepton not connected, skipping tests", allow_module_level=True)

def test_open_lepton():

    camera = Lepton()
    camera.close()

def test_find_lepton():
    camera = Lepton()
    camera.find_video_device()
    camera.close()

def test_find_and_capture_lepton():
    camera = Lepton()
    image = camera.grab()
    
    assert image is not None
    assert len(image.shape) == 2
    assert image.dtype == 'uint16'

    camera.close()