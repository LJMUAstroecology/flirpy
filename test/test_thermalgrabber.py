from flirpy.camera.tau import TeaxGrabber
import pytest
import os
import time
import numpy as np

with TeaxGrabber() as camera:
    if camera.dev is None:
        pytest.skip("ThermalGrabber not connected, skipping tests", allow_module_level=True)

def test_open_close():
   camera = TeaxGrabber()
   camera.close()

def test_ping():
    with TeaxGrabber() as camera:
        res = camera.ping()
        assert(res is not None)

def test_grab():
    with TeaxGrabber() as camera:
        image = camera.grab()
        assert image.dtype == np.float64

def test_grab_raw():
    with TeaxGrabber() as camera:
        image = camera.grab(radiometric=False)

def test_image_and_uart():
    with TeaxGrabber() as camera:
        temp = camera.get_fpa_temperature()
        assert temp > 0

        image = camera.grab()
        assert image.dtype == np.float64

