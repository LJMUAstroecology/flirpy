from flirpy.camera.core import Core
import struct
import ctypes
import binascii
import cv2
from serial.tools import list_ports
import os
import cv2
import sys

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

        if os.name == "nt":
            raise OSError("Automatically finding video device only supported in Linux")

        res = None
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

        self.cap.set(cv2.CAP_PROP_CONVERT_RGB, False)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"Y16 "))
        

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