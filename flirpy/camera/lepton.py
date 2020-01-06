from flirpy.camera.core import Core
import sys
import pkg_resources
import subprocess
import cv2
import logging

class Lepton(Core):

    def __init__(self, loglevel=logging.WARNING):
        self.cap = None
        self.conn = None

        logging.basicConfig(level=loglevel)
        self.logger = logging.getLogger(__name__)

    def find_video_device(self):
        """
        Attempts to automatically detect which video device corresponds to the PureThermal Lepton by searching for the PID and VID.

        Returns
        -------
            int
                device number
        """

        res = None

        if sys.platform.startswith('win32'):
            device_check_path = pkg_resources.resource_filename('flirpy', 'bin/find_cameras.exe')
            device_id = int(subprocess.check_output([device_check_path, "PureThermal"]).decode())

            if device_id >= 0:
                return device_id

        elif sys.platform == "darwin":
            output = subprocess.check_output(["system_profiler", "SPCameraDataType"]).decode()
            devices = [line.strip() for line in output.decode().split("\n") if line.strip().startswith("Model")]

            device_id = 0

            for device in devices:
                if device.contains("VendorID_1E4E") and device.contains("ProductID_0100"):
                    return device_id
            
        else:
            import pyudev

            context = pyudev.Context()
            devices = pyudev.Enumerator(context)

            path = "/sys/class/video4linux/"
            video_devices = [os.path.join(path, device) for device in os.listdir(path)]
            dev = []
            for i, device in enumerate(video_devices):
                udev = pyudev.Devices.from_path(context, device)

                try:
                    vid = udev.get('ID_VENDOR_ID')
                    pid = udev.get('ID_MODEL_ID')

                    if vid == "1E4E" and pid == "0100":
                        dev.append(i)
                except KeyError:
                    pass
            
            # For some reason multiple devices can show up
            for d in dev:
                cam = cv2.VideoCapture(d + cv2.CAP_V4L2)
                data = cam.read()
                if data is not None:
                    res = d
                    break
                cam.release()

        return res

    def setup_video(self, device_id=None):
        """
        Setup the camera for video/frame capture.

        Attempts to automatically locate the camera, then opens an OpenCV VideoCapture object. The
        capture object is setup to capture raw video.
        """

        if device_id is None:
            device_id = self.find_video_device()
        
        if device_id is None:
            raise ValueError("Boson not connected.")

        if sys.platform.startswith('linux'):
            self.cap = cv2.VideoCapture(device_id + cv2.CAP_V4L2)
        elif sys.platform.startswith('win32'):
            self.cap = cv2.VideoCapture(device_id + cv2.CAP_DSHOW)
        else:
            # Catch anything else, e.g. Mac?
            self.cap = cv2.VideoCapture(device_id)

        if not self.cap.isOpened():
           raise IOError("Failed to open capture device {}".format(device_id))
        
        # The order of these calls matters!
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"Y16 "))
        self.cap.set(cv2.CAP_PROP_CONVERT_RGB, False)
        

    def grab(self, device_id=None):
        """
        Captures and returns an image.

        Parameters
        ----------

            int
                the device ID for the camera. On a laptop, this is likely to be 1 if
                you have an internal webcam.

        Returns
        -------
            
            np.array, or None if an error occurred
                captured image
        """

        if device_id is None:
            device_id = self.find_video_device()

        if self.cap is None:
            self.setup_video(device_id)
        
        return self.cap.read()[1]