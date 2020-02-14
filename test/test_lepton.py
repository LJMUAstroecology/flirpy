import time
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

def test_capture_multiple():
    with Lepton() as camera:
        for _ in range(10):
            image = camera.grab()
            print(image.mean)

def test_capture_speed():
    with Lepton() as camera:
        _ = camera.grab()
        tstart = time.time()
        for _ in range(20):
            image = camera.grab()
        tend = time.time()
        
        assert tend - tstart < 2.5

def test_capture_setup_first():
    with Lepton() as camera:
        camera.setup_video()
        image = camera.grab()
        assert image is not None