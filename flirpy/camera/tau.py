from . import tau_config as ptc

import serial
import struct
import binascii
import time
import logging

import numpy as np
import tqdm
import math

# Tau Status codes

CAM_OK = 0x00
CAM_NOT_READY = 0x02
CAM_RANGE_ERROR = 0x03
CAM_UNDEFINED_ERROR = 0x04
CAM_UNDEFINED_PROCESS_ERROR = 0x05
CAM_UNDEFINED_FUNCTION_ERROR = 0x06
CAM_TIMEOUT_ERROR = 0x07
CAM_BYTE_COUNT_ERROR = 0x09
CAM_FEATURE_NOT_ENABLED= 0x0A

log = logging.getLogger()

class Tau:

    def __enter__(self):
        return self
    
    def __exit__(self, type, value, traceback):
        if self.conn is not None:
            self.conn.close()
        log.info("Disconnecting from camera.")

    def __init__(self, port=None, baud=921600):
        log.info("Connecting to camera.")

        if port is not None:
            self.conn = serial.Serial(port=port, baudrate=baud)

            if self.conn.is_open:
                log.info("Connected to camera at {}.".format(port))

                self.conn.flushInput()
                self.conn.flushOutput()
                self.conn.timeout = 1

                self.conn.read(self.conn.in_waiting)
            else:
                log.critical("Couldn't connect to camera!")
                raise IOError
        else:
            self.conn = None
            
    
    def ping(self):
        function = ptc.NO_OP

        self._send_packet(function)
        res = self._read_packet(function)

        return res

    def get_serial(self):
        function = ptc.SERIAL_NUMBER

        self._send_packet(function)
        res = self._read_packet(function)

        log.info("Camera serial: {}".format(int.from_bytes(res[7][:4], byteorder='big', signed=False)))
        log.info("Sensor serial: {}".format(int.from_bytes(res[7][4:], byteorder='big', signed=False)))

    def shutter_open(self):
        function = ptc.GET_SHUTTER_POSITION
        self._send_packet(function, "")
        res = self._read_packet(function)

        if int.from_bytes(res[7], byteorder='big', signed=False) == 0:
            return True
        else:
            return False
    
    def shutter_closed(self):
        return not self.shutter_open()

    def enable_test_pattern(self, mode=1):
        function = ptc.SET_TEST_PATTERN
        argument = struct.pack(">h", mode)
        self._send_packet(function, argument)
        time.sleep(0.2)
        res = self._read_packet(function)
    
    def disable_test_pattern(self):
        function = ptc.SET_TEST_PATTERN
        argument = struct.pack(">h", 0x00)
        self._send_packet(function, argument)
        time.sleep(0.2)
        res = self._read_packet(function)

    def get_core_status(self):
        function = ptc.READ_SENSOR_STATUS
        argument = struct.pack(">H", 0x0011)

        self._send_packet(function, argument)
        res = self._read_packet(function)

        status = struct.unpack(">H", res[7])[0]

        overtemp = status & (1 << 0)
        need_ffc = status & (1 << 2)
        gain_switch = status & (1 << 3)
        nuc_switch = status & (1 << 5)
        ffc = status & (1 << 6)

        if overtemp is not 0:
            log.critical("Core overtemperature warning! Remove power immediately!")
        
        if need_ffc is not 0:
            log.warning("Core desires a new flat field correction (FFC).")
        
        if gain_switch is not 0:
            log.warning("Core suggests that the gain be switched (check for over/underexposure).")
        
        if nuc_switch is not 0:
            log.warning("Core suggests that the NUC be switched.")

        if ffc is not 0:
            log.info("FFC is in progress.")

    def get_acceleration(self):
        function = ptc.READ_SENSOR_ACCELEROMETER
        argument = struct.pack(">H", 0x000B)

        self._send_packet(function, argument)
        res = self._read_packet(function)

        x, y, z  = struct.unpack(">HHHxx", res[7])

        x *= 0.1
        y *= 0.1
        z *= 0.1

        log.info("Acceleration: ({}, {}, {}) g".format(x, y, z))

        return (x, y, z)

    def get_fpa_temperature(self):
        function = ptc.READ_SENSOR_TEMPERATURE
        argument = struct.pack(">h", 0x00)
        self._send_packet(function, argument)
        res = self._read_packet(function)

        temperature = struct.unpack(">h", res[7])[0]
        temperature /= 10.0

        log.info("FPA temp: {}C".format(temperature))
        return temperature

    def get_housing_temperature(self):
        function = ptc.READ_SENSOR_TEMPERATURE
        argument = struct.pack(">h", 0x0A)
        self._send_packet(function, argument)
        time.sleep(1)
        res = self._read_packet(function)

        temperature = struct.unpack(">h", res[7])[0]
        temperature /= 100.0

        log.info("Housing temp: {}C".format(temperature))
        return temperature

    def close_shutter(self):
        function = ptc.SET_SHUTTER_POSITION
        argument = struct.pack(">h", 1)
        self._send_packet(function, argument)
        res = self._read_packet(function)

        return
    
    def open_shutter(self):
        function = ptc.SET_SHUTTER_POSITION
        argument = struct.pack(">h", 0)
        self._send_packet(function, argument)
        res = self._read_packet(function)

        return
    
    def digital_output_enabled(self):
        function = ptc.GET_DIGITAL_OUTPUT_MODE

        self._send_packet(function, "")
        res = self._read_packet(function)

        if int.from_bytes(res[7], byteorder='big', signed=False) == 0:
            return True
        else:
            return False
    
    def enable_digital_output(self):
        """
        Enables both LVDS and XP interfaces. Call this, then set the XP mode.
        """
        function = ptc.SET_DIGITAL_OUTPUT_MODE

        argument = struct.pack(">h", 0x0000)
        self._send_packet(function, argument)
        res = self._read_packet(function)

        if int.from_bytes(res[7], byteorder='big', signed=False) == 0:
            return True
        else:
            return False

    def disable_digital_output(self):
        function = ptc.SET_DIGITAL_OUTPUT_MODE
        argument = struct.pack(">h", 0x0002)

        self._send_packet(function, argument)
        res = self._read_packet(function)

        if int.from_bytes(res[7], byteorder='big', signed=False) == 2:
            return True
        else:
            return False
        
    def get_xp_mode(self):
        function = ptc.GET_DIGITAL_OUTPUT_MODE
        argument = struct.pack(">h", 0x0200)

        self._send_packet(function, argument)
        res = self._read_packet(function)

        mode = int.from_bytes(res[7], byteorder='big', signed=False)
        return mode
        
    def set_xp_mode(self, mode=0x02):
        function = ptc.SET_DIGITAL_OUTPUT_MODE
        argument = struct.pack(">h", 0x0300 & mode)

        self._send_packet(function, argument)
        res = self._read_packet(function)

        if int.from_bytes(res[7], byteorder='big', signed=False) == 0x0300 & mode:
            return True
        else:
            return False

    def get_lvds_mode(self):
        pass

    def set_lvds_mode(self):
        pass

    def set_cmos_mode(self, fourteen_bit=True):

        function = ptc.SET_DIGITAL_OUTPUT_MODE

        if fourteen_bit == True:
            mode = 0x00
        else:
            mode = 0x01

        argument = struct.pack(">h", 0x0600 & mode)

        self._send_packet(function, argument)
        res = self._read_packet(function)

        if int.from_bytes(res[7], byteorder='big', signed=False) == 0x0600 & mode:
            return True
        else:
            return False

    def enable_tlinear(self):
        pass
    
    def _sync_teax(self):
        data = self.conn.read(self.conn.in_waiting)
        
        magic = b"TEAX"
        
        while data.find(magic) == -1:
            data = self.conn.read(self.conn.in_waiting)
            
        return data[data.find(magic):]

    def _read_frame_teax(self, offset):
        return self.conn.read(657418-offset)

    def _convert_frame_teax(data):
        raw_image = np.frombuffer(data[10:], dtype='uint8').reshape((512,2*642))
        raw_image = 0x3FFF & raw_image.view('uint16')[:,1:-1]
    
        return 0.04*raw_image - 273
    
    def grab_teax(self):
        data = b''
        data = self._sync_teax()
        data += self._read_frame(len(data))
            
        return self._convert_frame_teax(data)

    def _send_packet(self, command, argument=[]):

        # Refer to Tau 2 Software IDD
        # Packet Protocol (Table 3.2)
        packet_size = len(argument)
        assert(packet_size == command.cmd_bytes)  

        process_code = int(0x6E).to_bytes(1, 'big')
        status = int(0x00).to_bytes(1, 'big')
        function = command.code.to_bytes(1, 'big')

        # First CRC is the first 6 bytes of the packet
        # 1 - Process code
        # 2 - Status code
        # 3 - Reserved
        # 4 - Function
        # 5 - N Bytes MSB
        # 6 - N Bytes LSB

        packet = [process_code, status, function]
        packet.append( ((packet_size & 0xFF00) >> 8).to_bytes(1, 'big') )
        packet.append( (packet_size & 0x00FF).to_bytes(1, 'big') )
        crc_1 = binascii.crc_hqx(struct.pack("ccxccc", *packet), 0)

        packet.append( ((crc_1 & 0xFF00) >> 8).to_bytes(1, 'big') )
        packet.append( (crc_1 & 0x00FF).to_bytes(1, 'big') )

        if packet_size > 0:

            # Second CRC is the CRC of the data (if any)
            crc_2 = binascii.crc_hqx(argument, 0)
            packet.append(argument)
            packet.append( ((crc_2 & 0xFF00) >> 8).to_bytes(1, 'big') )
            packet.append( (crc_2 & 0x00FF).to_bytes(1, 'big') )

            fmt = ">cxcccccc{}scc".format(packet_size)
            
        else:
            fmt = ">cxccccccxxx"

        data = struct.pack(fmt, *packet)
        log.debug("Sending {}".format(data))

        self._send_data(data)
    
    def _check_header(self, data):

        res = struct.unpack(">BBxBBB", data)

        if res[0] != 0x6E:
            log.warning("Initial packet byte incorrect. Byte was: {}".format(res[0]))
            return False
        
        if not self.check_status(res[1]):
            return False
        
        return True

    def _read_packet(self, function, post_delay=0.1):
        argument_length = function.reply_bytes
        data = self.conn.read(10+argument_length)

        log.debug("Received: {}".format(data))

        if self._check_header(data[:6]) and len(data) > 0:
            if argument_length == 0:
                res = struct.unpack(">ccxcccccxx", data)
            else:
                res = struct.unpack(">ccxccccc{}scc".format(argument_length), data)
                #check_data_crc(res[7])
        else:
            res = None
            log.warning("Error reply from camera. Try re-sending command, or check parameters.")

        if post_delay > 0:
            time.sleep(post_delay)

        return res

    def check_status(self, code):

        if code == CAM_OK:
            log.debug("Response OK")
            return True
        elif code == CAM_BYTE_COUNT_ERROR:
            log.warning("Byte count error.")
        elif code == CAM_FEATURE_NOT_ENABLED:
            log.warning("Feature not enabled.")
        elif code == CAM_NOT_READY:
            log.warning("Camera not ready.")
        elif code == CAM_RANGE_ERROR:
            log.warning("Camera range error.")
        elif code == CAM_TIMEOUT_ERROR:
            log.warning("Camera timeout error.")
        elif code == CAM_UNDEFINED_ERROR:
            log.warning("Camera returned an undefined error.")
        elif code == CAM_UNDEFINED_FUNCTION_ERROR:
            log.warning("Camera function undefined. Check the function code.")
        elif code == CAM_UNDEFINED_PROCESS_ERROR:
            log.warning("Camera process undefined.")
        
        return False

    def get_num_snapshots(self):
        log.debug("Query snapshot status")
        function = ptc.GET_MEMORY_ADDRESS
        argument = struct.pack('>HH', 0xFFFE, 0x13)

        self._send_packet(function, argument)
        res = self._read_packet(function)
        snapshot_size, num_snapshots = struct.unpack(">ii", res[7])

        log.info("Used snapshot memory: {} Bytes".format(snapshot_size))
        log.info("Num snapshots: {}".format(num_snapshots))

        return num_snapshots, snapshot_size

    def erase_snapshots(self, frame_id=1):
        log.info("Erasing snapshots")

        num_snapshots, snapshot_used_memory = self.get_num_snapshots()

        if num_snapshots == 0:
            return

        # Get snapshot base address
        log.debug("Get capture address")
        function = ptc.GET_MEMORY_ADDRESS
        argument = struct.pack('>HH', 0xFFFF, 0x13)

        self._send_packet(function, argument)
        res = self._read_packet(function)
        snapshot_address, snapshot_area_size = struct.unpack(">ii", res[7])

        log.debug("Snapshot area size: {} Bytes".format(snapshot_area_size))

        # Get non-volatile memory base address
        function = ptc.GET_NV_MEMORY_SIZE
        argument = struct.pack('>H', 0xFFFF)

        self._send_packet(function, argument)
        res = self._read_packet(function)
        base_address, block_size = struct.unpack(">ii", res[7])

        # Compute the starting block
        starting_block = int((snapshot_address-base_address)/block_size)

        log.debug("Base address: {}".format(base_address))
        log.debug("Snapshot address: {}".format(snapshot_address))
        log.debug("Block size: {}".format(block_size))
        log.debug("Starting block: {}".format(starting_block))

        blocks_to_erase = math.ceil((snapshot_used_memory/block_size))

        log.debug("Number of blocks to erase: {}".format(blocks_to_erase))

        for i in range(blocks_to_erase):
            
            function = ptc.ERASE_BLOCK
            block_id = starting_block + i

            log.debug("Erasing block: {}".format(block_id))

            argument = struct.pack('>H', block_id)
            self._send_packet(function, argument)
            res = self._read_packet(function, post_delay=0.2)

    def snapshot(self, frame_id = 0):
        log.info("Capturing frame")

        self.get_core_status()

        if self.shutter_closed():
            log.warn("Shutter reports that it's closed. This frame may be corrupt!")

        function = ptc.TRANSFER_FRAME
        frame_code = 0x16
        argument = struct.pack('>BBH', frame_code, frame_id, 1)
        
        self._send_packet(function, argument)
        self._read_packet(function, post_delay=1)

        bytes_remaining = self.get_memory_status()
        log.info("{} bytes remaining to write.".format(bytes_remaining))

    def retrieve_snapshot(self, frame_id):
        # Get snapshot address
        log.info("Get capture address")
        function = ptc.GET_MEMORY_ADDRESS
        snapshot_memory = 0x13
        argument = struct.pack('>HH', frame_id, snapshot_memory)

        self._send_packet(function, argument)
        res = self._read_packet(function)
        snapshot_address, snapshot_size = struct.unpack(">ii", res[7])

        log.info("Snapshot size: {}".format(snapshot_size))

        n_transfers = math.ceil(snapshot_size/256)
        function = ptc.READ_MEMORY_256

        log.info("Reading frame {} ({} bytes)".format(frame_id, snapshot_size))
        # For N reads, read data
        data = []
        remaining = snapshot_size
        for i in tqdm.tqdm(range(n_transfers)):

            n_bytes = min(remaining, 256)
            function.reply_bytes = n_bytes

            argument = struct.pack('>iH', snapshot_address+i*256, n_bytes)
            self._send_packet(function, argument)
            res = self._read_packet(function, post_delay=0)

            data += struct.unpack(">{}B".format(int(n_bytes)), res[7])
            remaining -= n_bytes

        image = np.array(data, dtype='uint8')

        return image
    
    def get_memory_status(self):
        function = ptc.MEMORY_STATUS
    
        self._send_packet(function)
        res = self._read_packet(function)

        remaining_bytes = struct.unpack(">H", res[7])[0]

        if remaining_bytes == 0xFFFF:
            log.warn("Erase error")
        elif remaining_bytes == 0xFFFE:
            log.warn("Write error")
        else:
            return remaining_bytes
    
    def ffc(self):
        function = ptc.DO_FFC_SHORT

        self._send_packet(function)
        res = self._read_packet(function)

    def get_last_image(self):
        num_snapshots, _ = self.get_num_snapshots()
        
        if num_snapshots > 0:
            return self.retrieve_snapshot(num_snapshots - 1)
        else:
            return None
    
    def _send_data(self, data):
        nbytes = self.conn.write(data)
        self.conn.flush()
        return
    
    def _recieve_data(self, nbytes):
        return self.conn.read(nbytes)
