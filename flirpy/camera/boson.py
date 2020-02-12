
"""
boson.py
====================================
Class for interacting with FLIR Boson cameras
"""
from flirpy.camera.core import Core
import struct
import ctypes
import binascii
from serial.tools import list_ports
import os
import sys
import logging
import cv2
import time

# FFC Mode enum
FLR_BOSON_MANUAL_FFC = 0
FLR_BOSON_AUTO_FFC = 1
FLR_BOSON_EXTERNAL_FFC = 2
FLR_BOSON_SHUTTER_TEST_FFC = 3
FLR_BOSON_FFCMODE_END = 4

# FFC State enum
FLR_BOSON_NO_FFC_PERFORMED = 0
FLR_BOSON_FFC_IMMINENT = 1
FLR_BOSON_FFC_IN_PROGRESS = 2
FLR_BOSON_FFC_COMPLETE = 3
FLR_BOSON_FFCSTATUS_END = 4

crc_table = [
   0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50A5, 0x60C6, 0x70E7,
   0x8108, 0x9129, 0xA14A, 0xB16B, 0xC18C, 0xD1AD, 0xE1CE, 0xF1EF,
   0x1231, 0x0210, 0x3273, 0x2252, 0x52B5, 0x4294, 0x72F7, 0x62D6,
   0x9339, 0x8318, 0xB37B, 0xA35A, 0xD3BD, 0xC39C, 0xF3FF, 0xE3DE,
   0x2462, 0x3443, 0x0420, 0x1401, 0x64E6, 0x74C7, 0x44A4, 0x5485,
   0xA56A, 0xB54B, 0x8528, 0x9509, 0xE5EE, 0xF5CF, 0xC5AC, 0xD58D,
   0x3653, 0x2672, 0x1611, 0x0630, 0x76D7, 0x66F6, 0x5695, 0x46B4,
   0xB75B, 0xA77A, 0x9719, 0x8738, 0xF7DF, 0xE7FE, 0xD79D, 0xC7BC,
   0x48C4, 0x58E5, 0x6886, 0x78A7, 0x0840, 0x1861, 0x2802, 0x3823,
   0xC9CC, 0xD9ED, 0xE98E, 0xF9AF, 0x8948, 0x9969, 0xA90A, 0xB92B,
   0x5AF5, 0x4AD4, 0x7AB7, 0x6A96, 0x1A71, 0x0A50, 0x3A33, 0x2A12,
   0xDBFD, 0xCBDC, 0xFBBF, 0xEB9E, 0x9B79, 0x8B58, 0xBB3B, 0xAB1A,
   0x6CA6, 0x7C87, 0x4CE4, 0x5CC5, 0x2C22, 0x3C03, 0x0C60, 0x1C41,
   0xEDAE, 0xFD8F, 0xCDEC, 0xDDCD, 0xAD2A, 0xBD0B, 0x8D68, 0x9D49,
   0x7E97, 0x6EB6, 0x5ED5, 0x4EF4, 0x3E13, 0x2E32, 0x1E51, 0x0E70,
   0xFF9F, 0xEFBE, 0xDFDD, 0xCFFC, 0xBF1B, 0xAF3A, 0x9F59, 0x8F78,
   0x9188, 0x81A9, 0xB1CA, 0xA1EB, 0xD10C, 0xC12D, 0xF14E, 0xE16F,
   0x1080, 0x00A1, 0x30C2, 0x20E3, 0x5004, 0x4025, 0x7046, 0x6067,
   0x83B9, 0x9398, 0xA3FB, 0xB3DA, 0xC33D, 0xD31C, 0xE37F, 0xF35E,
   0x02B1, 0x1290, 0x22F3, 0x32D2, 0x4235, 0x5214, 0x6277, 0x7256,
   0xB5EA, 0xA5CB, 0x95A8, 0x8589, 0xF56E, 0xE54F, 0xD52C, 0xC50D,
   0x34E2, 0x24C3, 0x14A0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
   0xA7DB, 0xB7FA, 0x8799, 0x97B8, 0xE75F, 0xF77E, 0xC71D, 0xD73C,
   0x26D3, 0x36F2, 0x0691, 0x16B0, 0x6657, 0x7676, 0x4615, 0x5634,
   0xD94C, 0xC96D, 0xF90E, 0xE92F, 0x99C8, 0x89E9, 0xB98A, 0xA9AB,
   0x5844, 0x4865, 0x7806, 0x6827, 0x18C0, 0x08E1, 0x3882, 0x28A3,
   0xCB7D, 0xDB5C, 0xEB3F, 0xFB1E, 0x8BF9, 0x9BD8, 0xABBB, 0xBB9A,
   0x4A75, 0x5A54, 0x6A37, 0x7A16, 0x0AF1, 0x1AD0, 0x2AB3, 0x3A92,
   0xFD2E, 0xED0F, 0xDD6C, 0xCD4D, 0xBDAA, 0xAD8B, 0x9DE8, 0x8DC9,
   0x7C26, 0x6C07, 0x5C64, 0x4C45, 0x3CA2, 0x2C83, 0x1CE0, 0x0CC1,
   0xEF1F, 0xFF3E, 0xCF5D, 0xDF7C, 0xAF9B, 0xBFBA, 0x8FD9, 0x9FF8,
   0x6E17, 0x7E36, 0x4E55, 0x5E74, 0x2E93, 0x3EB2, 0x0ED1, 0x1EF0
]
import subprocess
import pkg_resources

class Boson(Core):
    """
    Opens a FLIR Boson camera. By default, flirpy will attempt to locate your 
    camera by its USB PID/VID. You can also force a particular port (if you have two
    cameras connected, for example) using the port parameter.

    Parameters
    ---
        port
            the serial port of the camera
        
        baudate
            the baudrate to use when connecting to the camera
        
        loglevel
            logging level, default is level is WARNING

    """
    def __init__(self, port=None, baudrate=921600, loglevel=logging.WARNING):
        self.command_count = 0
        self.cap = None
        self.conn = None

        logging.basicConfig(level=loglevel)
        self.logger = logging.getLogger(__name__)

        if port is None:
            port = self.find_serial_device()
            if port is not None:
                self.connect(port, baudrate)

                if self.conn.is_open:
                    self.logger.info("Connected")

    @classmethod
    def find_serial_device(self):
        """
        Attempts to find and return the serial port that the Boson is connected to.
        
        Returns
        -------
            string
                serial port name
        """
        port = None

        device_list = list_ports.comports()

        VID = 0x09CB
        PID = 0x4007
        
        for device in device_list:
            if device.vid == VID and device.pid == PID:
                port = device.device
                break

        return port

    @classmethod
    def find_video_device(self):
        """
        Attempts to automatically detect which video device corresponds to the Boson by searching for the PID and VID.

        Returns
        -------
            int
                device number
        """

        res = None

        if sys.platform.startswith('win32'):
            device_check_path = pkg_resources.resource_filename('flirpy', 'bin/find_cameras.exe')
            device_id = int(subprocess.check_output([device_check_path, "FLIR Video"]).decode())

            if device_id >= 0:
                return device_id

        elif sys.platform == "darwin":
            output = subprocess.check_output(["system_profiler", "SPCameraDataType"]).decode()
            devices = [line.strip() for line in output.decode().split("\n") if line.strip().startswith("Model")]

            device_id = 0

            for device in devices:
                if device.contains("VendorID_2507") and device.contains("ProductID_16391"):
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
                    vid = udev.properties['ID_VENDOR_ID']
                    pid = udev.properties['ID_MODEL_ID']

                    if vid == "09cb" and pid == "4007":
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
            self.logger.debug("Locating cameras")
            device_id = self.find_video_device()
        
        if device_id is None:
            raise ValueError("Boson not connected.")
        else:
            self.logger.debug("Located camera at {}".format(device_id))

        if sys.platform.startswith('linux'):
            self.cap = cv2.VideoCapture(device_id + cv2.CAP_V4L2)
        elif sys.platform.startswith('win32'):
            self.cap = cv2.VideoCapture(device_id + cv2.CAP_DSHOW)
        else:
            # Catch anything else, e.g. Mac?
            self.cap = cv2.VideoCapture(device_id)

        if not self.cap.isOpened():
           raise IOError("Failed to open capture device {}".format(device_id))

        # Attempt to set 320x256 which only has an effect on the Boson 320
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,320)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT,256)
        
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

        if self.cap is None:
            self.setup_video(device_id)
        
        return self.cap.read()[1]

    def reboot(self):
        """
        Reboot the camera
        """
        function_id = 0x00050010
        self._send_packet(function_id)

        return 


    def get_sensor_serial(self):
        """
        Get the serial number of the sensor

        Returns
        -------
            int
                serial number
        """
        function_id = 0x00050006

        res = self._send_packet(function_id, receive_size=4)
        res = self._decode_packet(res, receive_size=4)

        return struct.unpack(">I", res)[0]
    
    def get_firmware_revision(self):
        """
        Get the camera's software revision.

        Returns
        -------
            tuple (int, int, int)
                revision (Major, Minor, Patch)
        """

        function_id = 0x00050022

        res = self._send_packet(function_id, receive_size=12)
        res = self._decode_packet(res, receive_size=12)

        return struct.Struct(">iii").unpack_from(res)
    
    def get_part_number(self):
        """
        Get the camera part number

        Returns
        -------
            int
                part number
        """
        function_id = 0x00050004
        res = self._send_packet(function_id, receive_size=20)
        res = self._decode_packet(res, receive_size=20)

        return res.decode("utf-8") 

    def do_ffc(self):
        """
        Manually request a flat field correction (FFC)
        """
        function_id = 0x00050007
        self._send_packet(function_id)

        return 
        
    def get_ffc_state(self):
        """
        Returns the FFC state:

        0 = FLR_BOSON_NO_FFC_PERFORMED
        1 = FLR_BOSON_FFC_IMMINENT
        2 = FLR_BOSON_FFC_IN_PROGRESS
        3 = FLR_BOSON_FFC_COMPLETE
        4 = FLR_BOSON_FFCSTATUS_END

        These return values are available as e.g.:

        flirpy.camera.boson.FLR_BOSON_NO_FFC_PERFORMED

        Returns
        -------

            int
                FFC state   

        """
        function_id = 0x0005000C

        res = self._send_packet(function_id, receive_size=2)
        res = self._decode_packet(res, receive_size=2)

        return struct.unpack(">H", res)[0]

    def get_ffc_mode(self):
        """
        Get the current FFC mode

        0 = FLR_BOSON_NO_FFC_PERFORMED
        1 = FLR_BOSON_FFC_IMMINENT
        2 = FLR_BOSON_FFC_IN_PROGRESS
        3 = FLR_BOSON_FFC_COMPLETE
        4 = FLR_BOSON_FFCSTATUS_END

        Returns
        -------

            int
                FFC mode
        """
        function_id = 0x00050013
        res = self._send_packet(function_id, receive_size=4)
        res = self._decode_packet(res, receive_size=4)

        return struct.unpack(">I", res)[0]

    def set_ffc_auto(self):
        """
        Set the FFC mode to automatic
        """
        function_id = 0x00050012
        command = struct.pack(">I", FLR_BOSON_AUTO_FFC)
        res = self._send_packet(function_id, data=command)
        res = self._decode_packet(res)

        return

    def set_ffc_manual(self):
        """
        Set the FFC mode to manual
        """
        function_id = 0x00050012
        command = struct.pack(">I", FLR_BOSON_MANUAL_FFC)
        res = self._send_packet(function_id, data=command)
        res = self._decode_packet(res)

        return
    
    def set_ffc_temperature_threshold(self, temp_change):
        """
        Set the change in camera temperature (Celsius) required before an FFC is requested.

        Parameters
        ----------
            float
                temperature change in Celsius
        """
        function_id = 0x00050008
        command = struct.pack(">H", int(temp_change * 10))
        res = self._send_packet(function_id, data=command)
        res = self._decode_packet(res)

        return
    
    def get_ffc_temperature_threshold(self):
        """
        Get the change in camera temperature before an FFC is requested

        Returns
        -------
            float
                temperature change in Celsius
        """
        function_id = 0x00050009

        res = self._send_packet(function_id, receive_size=2)
        res = self._decode_packet(res, receive_size=2)

        return struct.unpack(">H", res)[0]/10.0
    
    def set_ffc_frame_threshold(self, seconds):
        """
        Set the number of seconds before an FFC is requested.

        Parameters
        ----------
            int
                seconds between FFC requests
        """
        function_id = 0x0005000A
        command = struct.pack(">I", seconds)
        res = self._send_packet(function_id, data=command)
        res = self._decode_packet(res)

        return
    
    def get_ffc_frame_threshold(self):
        """
        Get the number of frames before an FFC is requested.
        """
        function_id = 0x0005000B
        res = self._send_packet(function_id, receive_size=4)
        res = self._decode_packet(res, receive_size=4)

        return struct.unpack(">I", res)[0]
    
    def get_last_ffc_temperature(self):
        """
        Get the temperature (in Kelvin) that the last FFC occured
        """
        function_id = 0x0005005E

        res = self._send_packet(function_id, receive_size=2)
        res = self._decode_packet(res, receive_size=2)

        return struct.unpack(">H", res)[0]/10.0


    def get_last_ffc_frame_count(self):
        """
        Get the frame count when the last FFC occured
        """

        function_id = 0x0005005D

        res = self._send_packet(function_id, receive_size=4)
        res = self._decode_packet(res, receive_size=4)

        return struct.unpack(">I", res)[0]
    
    def get_frame_count(self):
        """
        Get the number of frames captured since the camera was turned on.

        Returns
        -------
            int
                number of frames
        """
        function_id = 0x00020002

        res = self._send_packet(function_id, receive_size=4)
        res = self._decode_packet(res, receive_size=4)

        return struct.unpack(">I", res)[0]

    def get_fpa_temperature(self):
        """
        Get the current focal plane array (FPA) temperature in Celsius.

        Returns
        -------
            float
                FPA temperature in Celsius
        """
        function_id = 0x00050030

        res = self._send_packet(function_id, receive_size=2)
        res = self._decode_packet(res, receive_size=2)

        return struct.unpack(">H", res)[0]/10.0

    def get_camera_serial(self):
        """
        Get the camera serial number 

        Returns
        -------
            int
                serial number
        """
        function_id = 0x00050002

        res = self._send_packet(function_id, receive_size=4)
        res = self._decode_packet(res, receive_size=4)

        return struct.unpack(">I", res)[0]
    
    def _decode_packet(self, data, receive_size=0):
        """
        Decodes a data packet from the camera.

        Packet Format:

        Start frame byte = 0x8E
        Channel ID = 0
        Bytes 0:3 - sequence number
        Bytes 4:7 - function ID
        Bytes 8:11 - return code
        Bytes 12: - payload (optional)
        CRC bytes - unsigned 16-bit CRC
        End frame byte = 0xAE
        
        Non-zero return codes are logged from the camera as warnings.

        """
        payload = None
        payload_len = len(data) - 17

        if payload_len > 0:
            frame = struct.Struct(">BBIII{}sHB".format(payload_len))
            res = frame.unpack(data)

            start_marker, channel_id, sequence, function_id, return_code, payload, crc, end_marker = res
        elif payload_len < 0:
            raise ValueError
        else:
            frame = struct.Struct(">BBIIIHB")
            res = frame.unpack(data)

            start_marker, channel_id, sequence, function_id, return_code, crc, end_marker = res
        
        if return_code == 0x0203:
            self.logger.warning("Boson response: range error")
        elif return_code == 0x017F:
            self.logger.warning("Boson response: buffer overflow")
        elif return_code == 0x017E:
            self.logger.warning("Boson response: excess bytes")
        elif return_code == 0x017D:
            self.logger.warning("Boson response: insufficient bytes")
        elif return_code == 0x0170:
            self.logger.warning("Boson response: unspecified error")
        elif return_code == 0x0162:
            self.logger.warning("Boson response: bad payload")
        elif return_code == 0x0161:
            self.logger.warning("Boson response: bad command ID")

        if start_marker != 0x8E and end_marker != 0xAE:
            self.logger.warning("Invalid frame markers")

        header = struct.Struct(">BBIII")
        header_bytes = bytearray(header.pack(start_marker,
                                channel_id,
                                sequence,
                                function_id,
                                return_code))

        packet = header_bytes     

        unstuffed_payload = None

        if payload_len > 0:
            unstuffed_payload = self._unstuff(payload)

        crc_bytes = self._crc(header_bytes, unstuffed_payload)

        if crc != crc_bytes:
            self.logger.warning("Invalid checksum")

        return unstuffed_payload

    def _bitstuff(self, data):
        """
        Escapes a buffer for transmission over serial
        """
        temp = bytearray()

        for byte in data:
            if byte == 0x8E:
                temp.append(0x9E)
                temp.append(0x81)
            elif byte == 0x9E:
                temp.append(0x9E)
                temp.append(0x91)
            elif byte == 0xAE:
                temp.append(0x9E)
                temp.append(0xA1)
            else:
                temp.append(byte)
        return temp

    def _unstuff(self, data):
        """
        Un-escapes a buffer for transmission over serial
        """
        temp = bytearray()
        unstuff = False

        for byte in data:
            if unstuff:
                temp.append(byte + 0xD)
                unstuff = False
            elif byte == 0x9E:
                unstuff = True
            else:
                temp.append(byte)

        return temp

    def receive(self, timeout=1):
        frame = self.conn.read(17) # Should be at least this big
        tstart = time.time()

        while True:
            if len(frame) > 0 and frame[-1] == 0xAE:
                break

            frame += self.conn.read_all()

            if len(frame) >= 1544:
                break

            if time.time() - tstart > timeout:
                break
        
        return frame

    def _crc(self, header, payload=None):
        """
        Compute a CRC on a data packet
        """
        data = header[1:]

        if payload is not None:
            data += bytes(payload)
        
        return binascii.crc_hqx(data, 0x1D0F)

    def _send_packet(self, function_id, data=None, receive_size=0):
        """
        Sends a data packet to the camera.

        Packet Format:

        Start frame byte = 0x8E
        Channel ID = 0
        Bytes 0:3 - sequence number
        Bytes 4:7 - function ID
        Bytes 8:11 - 0xFFFFFFFF
        Bytes 12: - payload (optional)
        CRC bytes - unsigned 16-bit CRC
        End frame byte = 0xAE
        """

        start_frame = 0x8E
        end_frame = 0xAE
        channel_number = 0x00

        header = struct.Struct(">BBIII")
        header_bytes = bytearray(header.pack(start_frame,
                                channel_number,
                                self.command_count,
                                function_id,
                                0xFFFFFFFF))

        # The CRC is computed from the channel number to the last data byte.
        # It is computed on the "raw" payload, before bitstuffing
        crc_bytes = self._crc(header_bytes, data)

        footer = struct.Struct(">HB")
        footer_bytes = footer.pack(crc_bytes, end_frame)

        # Stuff the data.
        payload = header_bytes

        if data is not None:
            payload += self._bitstuff(data)
        
        payload += footer_bytes

        self.send(payload)
        res = self.receive()

        return res