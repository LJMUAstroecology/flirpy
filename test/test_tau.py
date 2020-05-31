from flirpy.camera.tau import Tau
import pytest
import os
import time

with Tau() as camera:
    if camera.conn is None:
        pytest.skip("Tau not connected, skipping tests", allow_module_level=True)

def test_open_tau():
   camera = Tau()
   camera.close()

def test_ping():
    with Tau() as camera:
        res = camera.ping()
        assert(res is not None)

def test_serial():
    with Tau() as camera:
        camera_serial, sensor_serial = camera.get_serials()

        assert(camera_serial is not None)
        assert(sensor_serial is not None)
        assert(camera_serial > 0)
        assert(sensor_serial > 0)

def test_acceleration():
    with Tau() as camera:
        (x, y, z) = camera.get_acceleration()
        assert(x > 0)
        assert(y > 0)
        assert(z > 0)

def test_test_pattern():
    with Tau() as camera:
        camera.enable_test_pattern()
        camera.snapshot()
        image = camera.retrieve_snapshot()
        print(image)
        assert(False)
        camera.disable_test_pattern()