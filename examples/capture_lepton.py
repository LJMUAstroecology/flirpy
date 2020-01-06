from flirpy.camera.lepton import Lepton

cam = Lepton()
image = cam.grab()
print(image)
print(cam.frame_count)
print(cam.frame_mean)
print(cam.ffc_temp_k)
print(cam.fpa_temp_k)
cam.close()