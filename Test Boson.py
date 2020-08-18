from flirpy.camera.boson import Boson

c = Boson(port = "COM14")
c.grab()
c2 = Boson(port = "COM17")
c2.grab()
c.close()
