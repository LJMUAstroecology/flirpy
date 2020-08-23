from flirpy.camera.boson import Boson
from flirpy.camera.threadedboson import ThreadedBoson
import flirpy.camera.boson
import pytest
import os
import time

if Boson.find_video_device() is None:
    pytest.skip("Boson not connected, skipping tests", allow_module_level=True)

def test_open_boson():
   camera = ThreadedBoson()
   camera.close()

def test_capture():
    camera = ThreadedBoson()
    camera.start()
    time.sleep(1)
    image = camera.latest()
    temp = camera.camera.get_fpa_temperature()
    camera.stop()
    camera.close()

    assert temp is not None
    assert temp > 0

    assert image is not None
    if len(image.shape) == 3:
        assert image.shape[-1] == 1
    else:
        assert len(image.shape) == 2
    assert image.dtype == "uint16"

def test_capture_compressed():
    camera = ThreadedBoson()
    camera.start()
    time.sleep(1)
    image = camera.latest_compressed()

    camera.stop()
    camera.close()

    assert image is not None

