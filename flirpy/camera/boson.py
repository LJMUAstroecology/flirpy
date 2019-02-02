from flirpy.camera.core import Core
import struct
import ctypes
import binascii
import cv2
from serial.tools import list_ports
import os
import cv2
import sys
import subprocess
import pkg_resources

class Boson(Core):

    def __init__(self, port=None, baudrate=921600):
        self.command_count = 0
        self.cap = None
        self.conn = None

        if port is None:
            port = self.find_serial_device()
            if port is not None:
                self.connect(port, baudrate)

                if self.conn.is_open:
                    print("Connected")

    def find_serial_device(self):

        port = None

        device_list = list_ports.comports()

        VID = 0x09CB
        PID = 0x4007
        
        for device in device_list:
            if device.vid == VID and device.pid == PID:
                port = device.device
                break

        return port

    def find_video_device(self):

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
            path = "/sys/class/video4linux/"
            devices = [os.path.join(path, device) for device in os.listdir(path)]
            
            for device in devices:
                with open(os.path.join(device, "name"), 'r') as d:
                    device_name = d.read()

                    if device_name == "Boson: FLIR Video\n":
                        return int(device[-1])

        return res
        
    def setup_video(self, device_id=None):

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
           raise IOError("Failed to open capture device")
        
        # The order of these calls matters!
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"Y16 "))
        self.cap.set(cv2.CAP_PROP_CONVERT_RGB, False)
        

    def grab(self, device_id=None):
        if self.cap is None:
            self.setup_video(device_id)
        
        return self.cap.read()[1]

    def get_sensor_serial(self):
        pass

    def get_camera_serial(self):

        function_id = 0x00050002

        res = self.send_packet(function_id, receive_size=4)
        res = self.decode_packet(res, receive_size=4)

        return int.from_bytes(res, byteorder='big')
    
    def decode_packet(self, data, receive_size=0):

        if receive_size > 0:
            frame = struct.Struct(">BBIII{}sHB".format(receive_size))
            res = frame.unpack(data)

            start_marker, channel_id, sequence, function_id, return_code, payload, crc, end_marker = res
        else:
            frame = struct.Struct(">BBIIIHB")
            res = frame.unpack(data)

            start_marker, channel_id, sequence, function_id, return_code, crc, end_marker = res
        
        if start_marker != 0x8E and end_marker != 0xAE:
            print("Invalid frame markers")
        
        crc_bytes = binascii.crc_hqx(data[1:-3], 0x1D0F)

        if crc != crc_bytes:
            print("Invalid checksum")
        
        return payload

    def send_packet(self, function_id, data=None, receive_size=0):

        """
        Send Package Format:

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

        payload = header_bytes

        if data is not None:
            payload += bytes(data)

        # The CRC is computed from the channel number to the last data byte.
        # This is actually incorrect, since we need to escape certain characters
        # in the payload (e.g. the start/end markers). But this will work for 
        # simple commands.
        crc_bytes = binascii.crc_hqx(payload[1:], 0x1D0F)

        footer = struct.Struct(">HB")
        footer_bytes = footer.pack(crc_bytes, end_frame)
        payload += footer_bytes

        self.send(payload)
        res = self.receive(17+receive_size)

        return res