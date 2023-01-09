import numpy as np
import pytest
import usb

from flirpy.camera.tau import TeaxGrabber

try:
    with TeaxGrabber() as camera:
        if camera.dev is None:
            pytest.skip(
                "ThermalGrabber not connected, skipping tests", allow_module_level=True
            )
except usb.core.NoBackendError:
    pytest.skip("No USB backend available", allow_module_level=True)


def test_open_close():
    camera = TeaxGrabber()
    camera.close()


def test_ping():
    with TeaxGrabber() as camera:
        res = camera.ping()
        assert res is not None


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
