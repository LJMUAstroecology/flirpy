import re
import struct
import numpy as np
import sys
import six
import logging

from flirpy.util.raw import raw2temp
logger = logging.getLogger()

class Fff:

    def __init__(self, data, width=None, height=None):

        self.image = None
        self.filename = None

        # This is a dirty hack to force Python 2 to recognise whether
        # it's a filename or a file. An FFF file is almost always
        # larger than 2kB.
        if isinstance(data, str) and len(data) < 4096:
            with open(data, 'rb') as fff_file:
                self.filename = fff_file
                self.data = fff_file.read()
        elif isinstance(data, bytes):
            self.data = data
        else:
            raise TypeError("Data should be a bytes object or a string filename")

        if width is not None and height is not None:
            self.width = width
            self.height = height
            self.meta = {}
            self._find_data_offset_simple(width, height)
        else:
            try:
                self._find_data_offset(endianness="be")
            except:
                self._find_data_offset(endianness="le")

            self._get_image_size()

            try:
                self.meta = self.get_meta()
            except:
                self.meta = None
                logger.warn("Failed to get metadata")

    def write(self, path):
        with open(path, 'wb') as fff_file:
            fff_file.write(self.data)

    def _get_image_size(self):
        """
        Analyses the file to determine the dimensions
        of the image.

        """
        s = struct.Struct("<HHH6xH2xH")
        
        # 0x00: byte order
        # 0x01: width
        # 0x02: height
        # 0x03-0x05: 0
        # 0x06: raw image width - 1
        # 0x07: 0
        # 0x08: raw image height - 1
        # 0x09: 0,15,16
        # 0x0a: 0,2,3,11,12,13,30
        # 0x0b: 0,2
        # 0x0c: 0 or a large number
        # 0x0d: 0,3,4,6
        # 0x0e-0x0f: 0

        res = s.unpack_from(self.data, self.data_offset)
        self.width = res[1]
        self.height = res[2]

        # Quick sanity check, later entries are
        # (width-1) and (height-1)
        assert res[1] == res[3]+1
        assert res[2] == res[4]+1
        
        return (self.width, self.height)

    def _find_data_offset_simple(self, width, height):
        search = struct.pack("<H", width-1)\
                    + b"\x00\x00"\
                    + struct.pack("<H", height-1)

        valid = re.compile(search)
        res = valid.search(self.data)

        self.data_offset = res.end() + 14
        
    def _find_data_offset(self, endianness="be"):
        """
        Analyses the file to locate the offset of the
        data record (i.e. the image). Note the offset
        is not the image itself.

        This must be called prior to determining the 
        image dimensions.

        """

        # Get FFF record
        # http://www.workswell.cz/manuals/flir/hardware/A3xx_and_A6xx_models/Streaming_format_ThermoVision.pdf
        # 0x00 - string[4] file format ID = "FFF\0"
        # 0x04 - string[16] file creator: seen "\0","MTX IR\0","CAMCTRL\0"
        # 0x14 - int32u file format version = 100
        # 0x18 - int32u offset to record directory
        # 0x1c - int32u number of entries in record directory
        # 0x20 - int32u next free index ID = 2
        # 0x24 - int16u swap pattern = 0 (?)
        # 0x28 - int16u[7] spares
        # 0x34 - int32u[2] reserved
        # 0x3c - int32u checksum
        if endianness == "le":
            s = struct.Struct("<4s16sIIIIH7H")
        else:
            s = struct.Struct(">4s16sIIIIH7H")

        res = s.unpack_from(self.data, 0)

        file_format = res[0].decode()
        file_creator = res[1].decode()
        file_format_version = res[2]
        record_offset = res[3]
        record_number = res[4]

        # Decode record
        # http://www.workswell.cz/manuals/flir/hardware/A3xx_and_A6xx_models/Streaming_format_ThermoVision.pdf
        # 0x00 - int16u record type
        # 0x02 - int16u record subtype: RawData 1=BE, 2=LE, 3=PNG; 1 for other record types
        # 0x04 - int32u record version: seen 0x64,0x66,0x67,0x68,0x6f,0x104
        # 0x08 - int32u index id = 1
        # 0x0c - int32u record offset from start of FLIR data
        # 0x10 - int32u record length
        # 0x14 - int32u parent = 0 (?)
        # 0x18 - int32u object number = 0 (?)
        # 0x1c - int32u checksum: 0 for no checksum

        if endianness == "le":
            s = struct.Struct("<HHIIIIIII")   
        else:
            s = struct.Struct(">HHIIIIIII") 
        res = s.unpack_from(self.data, record_offset)

        record_type = res[0]
        record_subtype = res[1]

        if record_subtype == 1:
            self.endianness = "big"
        else:
            self.endianness = "little"

        record_version = res[2]
        index_id = res[3]
        self.data_offset = res[4]
        self.data_size = res[5]

        return self.data_offset
    
    def get_radiometric_image(self, dtype='float', meta=None):

        if meta is None:
            image = raw2temp(self.get_image(), self.meta)
        else:
            image = raw2temp(self.get_image(), meta)
        
        if dtype == 'uint16':
            image += 273.15
            image /= 0.04
            image = image.astype('uint16')

        return image

    def get_image(self):
        if self.image is None:
            count = self.height*self.width
            self.image = np.frombuffer(self.data, offset=self.data_offset+0x20, dtype='uint16', count=count).reshape((self.height, self.width))
        
        return self.image

    def get_meta(self):
        """

        Get metadata from FFF file
        
        These byte offsets are largely poached from Exiftool,
        but this allows us to seek directly into FFFs without
        calling Exiftool externally.
        """
        
        meta = {}

        # 0x20 to skip the header info
        header_offset = self.data_offset+0x20+2*self.height*self.width

        s = struct.Struct("<HHH6xII12x8f24x3f12x5f12x8f36x")    
        res = s.unpack_from(self.data, header_offset)

        try:
            meta["Width"] = res[0]
            meta["Height"] = res[1]
            meta["Emissivity"] = res[5]
            meta["Object Distance"] = res[6]
            meta["Reflected Apparent Temperature"] = res[7] - 273.14
            meta["Atmospheric Temperature"] = res[8] - 273.14
            meta["IR Window Temperature"] = res[9] - 273.14
            meta["IR Window Transmission"] = res[10]
            meta["Relative Humidity"] = res[12] * 100
            meta["Planck R1"] = res[13]
            meta["Planck B"] = res[14]
            meta["Planck F"] = res[15]
            meta["Atmospheric Trans Alpha 1"] = res[16]
            meta["Atmospheric Trans Alpha 2"] = res[17]
            meta["Atmospheric Trans Beta 1"] = res[18]
            meta["Atmospheric Trans Beta 2"] = res[19]
            meta["Atmospheric Trans X"] = res[20]
        except:
            logger.warn("Failed to extract radiometric information")
            logger.warn("String: ", res)
        
        s = struct.Struct("<8f32s16s16s16s32s16s16sf")
        res = s.unpack_from(self.data, header_offset+0x90)
        try:
            meta["Camera Temperature Range Max"] = res[0]
            meta["Camera Temperature Range Min"] = res[1]
            meta["Camera Temperature Max Clip"] = res[2]
            meta["Camera Temperature Min Clip"] = res[3]
            meta["Camera Temperature Max Warn"] = res[4]
            meta["Camera Temperature Min Warn"] = res[5]
            meta["Camera Temperature Max Saturated"] = res[6]
            meta["Camera Temperature Min Saturated"] = res[7]
        except UnicodeDecodeError:
            logger.warn("Failed to extract camera temperature information")
            logger.warn("String: ", res)
        
        s = struct.Struct("<32s16s16s16s32s16s16s")
        res = s.unpack_from(self.data, header_offset+0xd4)
        
        try:
            meta["Camera Model"] = res[0].decode()
            meta["Camera Part Number"] = res[1].decode()
            meta["Camera Serial Number"] = res[2].decode()
            meta["Camera Software"] = res[3].decode()
        except UnicodeDecodeError:
            logger.warn("Failed to extract camera information")
            logger.warn("String: ", res)
        
        s = struct.Struct("<32s16s16s4xf")
        res = s.unpack_from(self.data, header_offset+0x170)
        try:
            meta["Lens Model"] = res[0].decode()
            meta["Lens Part Number"] = res[1].decode()
            meta["Lens Serial Number"] = res[2].decode()
            meta["Field of View"] = res[3]
        except UnicodeDecodeError:
            logger.warn("Failed to extract lens details")
            logger.warn("String", res)
        
        s = struct.Struct("<if")
        res = s.unpack_from(self.data, header_offset+0x308)
        try:
            meta["Planck O"] = res[0]
            meta["Planck R2"] = res[1]
        except UnicodeDecodeError:
            logger.warn("Failed to extract Planck O or R2")
            logger.warn("String", res)
        
        s = struct.Struct("<HH")
        res = s.unpack_from(self.data, header_offset+0x310)
        try:
            meta["Raw Value Range Minimum"] = res[0]
            meta["Raw Value Range Maximum"] = res[1]
        except UnicodeDecodeError:
            logger.warn("Failed to extract raw value information")
            logger.warn("String", res)
        
        s = struct.Struct("<H2xH")
        res = s.unpack_from(self.data, header_offset+0x338)
        try:
            meta["Raw Value Range Median"] = res[0]
            meta["Raw Value Range Range"] = res[1]
        except UnicodeDecodeError:
            logger.warn("Failed to extract raw value information")
            logger.warn("String", res)
        
        return meta
    
    def get_gps(self):
        valid = re.compile("[0-9]{4}[NS]\x00[EW]\x00".encode())

        res = valid.search(self.data)
        start_pos = res.start()

        s = struct.Struct("<4xcxcx4xddf32xcxcx4xff")

        return s.unpack_from(self.data, start_pos)
