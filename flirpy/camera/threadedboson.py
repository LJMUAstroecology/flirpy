from flirpy.camera.boson import Boson
import cv2
import numpy as np
import warnings
import time
import logging
from . threadedcamera import ThreadedCamera

class ThreadedBoson(ThreadedCamera):
    def __init__(self, device=None, port=None, baudrate=921600, loglevel=logging.WARNING):
        super(ThreadedBoson, self).__init__()
        self.temperature = None
        self._connect(device, port, baudrate, loglevel)

    def _connect(self, device, port, baudrate, loglevel):
        try:
            self.camera = Boson(port, baudrate, loglevel)
            self.camera.setup_video(device)
            self.camera.grab()

            if not self.camera.cap.isOpened():
                warnings.warn("Failed to open camera")
                self.camera = None

        except IOError:
            warnings.warn("Failed to find camera")
            self.camera = None

    def height(self):
        return self.camera.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

    def width(self):
        return self.camera.cap.get(cv2.CAP_PROP_FRAME_WIDTH)

    def channels(self):
        return 1

    def dtype(self):
        return np.uint16

    def _grab(self):
        image = np.expand_dims(self.camera.grab(), -1)
        self.min_count = image.min()
        self.max_count = image.max()
        return image

    def close(self):
        self.camera.close()

    def get_target_fps(self):
        return self.camera.cap.get(cv2.CAP_PROP_FPS)
