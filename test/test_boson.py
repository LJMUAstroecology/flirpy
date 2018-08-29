from flirpy.camera.boson import Boson

with Boson("COM7") as cam:
    print("Serial: ", cam.get_camera_serial())
