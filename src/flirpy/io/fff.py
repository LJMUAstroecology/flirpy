import logging
import os
import re
import struct
import tempfile
from dataclasses import MISSING, dataclass

import numpy as np

from flirpy.util.exiftool import Exiftool
from flirpy.util.raw import raw2temp

logger = logging.getLogger()


@dataclass
class FffRecord:
    # From Exiftool documentation
    # 0x00 - int16u record type
    # 0x02 - int16u record subtype: RawData 1=BE, 2=LE, 3=PNG; 1 for other record types
    # 0x04 - int32u record version: seen 0x64,0x66,0x67,0x68,0x6f,0x104
    # 0x08 - int32u index id = 1
    # 0x0c - int32u record offset from start of FLIR data
    # 0x10 - int32u record length
    # 0x14 - int32u parent = 0 (?)
    # 0x18 - int32u object number = 0 (?)
    # 0x1c - int32u checksum: 0 for no checksum

    record_type: int = MISSING
    record_subtype: int = MISSING
    record_version: int = MISSING
    index_id: int = MISSING
    record_offset: int = MISSING
    record_length: int = MISSING
    parent: int = MISSING
    object_number: int = MISSING
    checksum: int = 0

    def __init__(self, data: bytes, bigendian: bool = False):
        """Generate a FffRecord object from a bytes object

        Parameters
        ----------
        data : bytes
            Data array
        bigendian : bool, optional
            Whether to assume big endian, by default False
        """
        s = get_struct("HHIIIIIII", bigendian)
        res = s.unpack_from(data)

        self.record_type = res[0]
        self.record_subtype = res[1]
        self.record_version = res[2]
        self.index_id = res[3]
        self.record_offset = res[4]
        self.record_length = res[5]
        self.parent = res[6]
        self.object_number = res[7]
        self.checksum = res[8]


def get_struct(s: str, bigendian=False) -> struct.Struct:
    """Generate a struct with optional endianness

    Parameters
    ----------
    s : str
        Struct string
    bigendian : bool, optional
        If True, return a bigendian struct, by default False

    Returns
    -------
    struct.Struct
        Struct with endianness set
    """
    if bigendian:
        endian = ">"
    else:
        endian = "<"

    return struct.Struct(f"{endian}{s}")


class Fff:
    def __init__(self, data, use_exiftool=False):

        self.image = None
        self.filename = None

        # This is a dirty hack to force Python 2 to recognise whether
        # it's a filename or a file. An FFF file is almost always
        # larger than 2kB.
        if isinstance(data, str) and len(data) < 4096:
            self.filename = data
            with open(self.filename, "rb") as fff_file:
                self.data = fff_file.read()
        elif isinstance(data, bytes):
            self.data = data
        else:
            raise TypeError("Data should be a bytes object or a string filename")

        if use_exiftool:
            exiftool = Exiftool()
            exiftool.write_meta(self.filename)
            meta_filename = os.path.splitext(self.filename)[0] + ".txt"

            self.meta = exiftool.meta_from_file(meta_filename)
            self.height = int(self.meta["Raw Thermal Image Height"])
            self.width = int(self.meta["Raw Thermal Image Width"])

            logger.info("Using Exiftool to extract meta")
        else:
            self.meta = {}
            self.records = []
            self._get_records()

            for record in self.records:

                record_data = self.data[
                    record.record_offset : record.record_offset + record.record_length
                ]

                # Raw data
                if record.record_type == 1:
                    logger.debug(
                        f"Raw data at {record.record_offset}, {record.record_length} bytes"
                    )
                    self._get_raw_info(record_data)
                    self.image_offset = record.record_offset + 0x20
                # Camera info
                elif record.record_type == 0x20:
                    logger.debug(
                        f"Camera information at {record.record_offset}, {record.record_length} bytes"
                    )
                    self._get_camera_info(record_data)
                # Palette
                elif record.record_type == 0x2B:
                    self.meta["gps"] = self._get_gps(record_data)
                else:
                    logger.debug(
                        f"Unknown record type {record.record_type} at {record.record_offset}, {record.record_length} bytes"
                    )

    def _get_records(self):
        bigendian = False
        if int.from_bytes(self.data[0x14 : 0x14 + 4], "little") > 200:
            bigendian = True
            logger.debug("Assuming file is bigendian")

        s = get_struct("4s16sIIIIH7H", bigendian)
        res = s.unpack_from(self.data, 0)

        file_format = res[0].decode()
        file_creator = res[1].decode()
        file_format_version = res[2]

        logger.debug("File format: %s", file_format)
        logger.debug("File creator: %s", file_creator)
        logger.debug("File format version: %d", file_format_version)

        record_offset = res[3]
        record_number = res[4]

        for i in range(record_number):
            s = get_struct("HHIIIIIII", bigendian)
            offset = record_offset + i * s.size
            self.records.append(
                FffRecord(self.data[offset : offset + s.size], bigendian)
            )

    def write(self, path):
        with open(path, "wb") as fff_file:
            fff_file.write(self.data)

    def get_radiometric_image(self, dtype="float", meta=None):

        if meta is None:
            image = raw2temp(self.get_image(), self.meta)
        else:
            image = raw2temp(self.get_image(), meta)

        if dtype == "uint16":
            image += 273.15
            image /= 0.04
            image = image.astype("uint16")

        return image

    def get_image(self):
        if self.image is None:
            count = self.height * self.width
            self.image = np.frombuffer(
                self.data, offset=self.image_offset, dtype="uint16", count=count
            ).reshape((self.height, self.width))

        return self.image

    def _get_gps(self, data):
        s = struct.Struct("4xcxcx4xddf32xcxcx4xff")
        return s.unpack_from(data)

    def _get_raw_info(self, data):
        """
        Extract raw image information from the raw data. This function is based on
        offsets defined in ExifTool.

        Used to extract frame width and height.
        """

        bigendian = False
        if int.from_bytes(data[:2], "little") != 0x002:
            bigendian = True

        get_uint16 = lambda x: get_struct("H", bigendian).unpack_from(data, x)[0]

        self.width = get_uint16(0x02)
        self.height = get_uint16(0x04)

    def _get_camera_info(self, data):
        """
        Extract camera information from the raw data. This function is based on
        offsets defined in ExifTool.
        """

        bigendian = False
        if int.from_bytes(data[:2], "little") != 0x002:
            bigendian = True

        get_float = lambda x: get_struct("f", bigendian).unpack_from(data, x)[0]
        get_float_kelvin = (
            lambda x: get_struct("f", bigendian).unpack_from(data, x)[0] - 273.14
        )
        get_uint16 = lambda x: get_struct("H", bigendian).unpack_from(data, x)[0]
        get_uint32 = lambda x: get_struct("L", bigendian).unpack_from(data, x)[0]
        get_int32 = lambda x: get_struct("i", bigendian).unpack_from(data, x)[0]
        get_string = lambda x, l: get_struct(f"{l}s", bigendian).unpack_from(data, x)[0]

        meta = {}
        meta["Width"] = get_uint16(0x02)
        meta["Height"] = get_uint16(0x04)
        meta["Emissivity"] = get_float(0x20)
        meta["Object Distance"] = get_float(0x24)
        meta["Reflected Apparent Temperature"] = get_float_kelvin(0x28)
        meta["Atmospheric Temperature"] = get_float_kelvin(0x2C)
        meta["IR Window Temperature"] = get_float_kelvin(0x30)
        meta["IR Window Transmission"] = get_float(0x34)
        meta["Relative Humidity"] = get_float(0x3C)

        # Check if humidity is a perentage or a ratio
        if meta["Relative Humidity"] / 100 > 2:
            meta["Relative Humidity"] /= 100.0

        meta["Planck R1"] = get_float(0x58)
        meta["Planck R2"] = get_float(0x30C)
        meta["Planck B"] = get_float(0x5C)
        meta["Planck F"] = get_float(0x60)
        meta["Planck O"] = get_int32(0x308)

        meta["Atmospheric Trans Alpha 1"] = get_float(0x70)
        meta["Atmospheric Trans Alpha 2"] = get_float(0x74)
        meta["Atmospheric Trans Beta 1"] = get_float(0x78)
        meta["Atmospheric Trans Beta 2"] = get_float(0x7C)
        meta["Atmospheric Trans X"] = get_float(0x80)

        meta["CameraTemperatureRangeMax"] = get_float_kelvin(0x90)
        meta["CameraTemperatureRangeMin"] = get_float_kelvin(0x94)
        meta["CameraTemperatureMaxClip"] = get_float_kelvin(0x98)
        meta["CameraTemperatureMinClip"] = get_float_kelvin(0x9C)
        meta["CameraTemperatureMaxWarn"] = get_float_kelvin(0xA0)
        meta["CameraTemperatureMinWarn"] = get_float_kelvin(0xA4)
        meta["CameraTemperatureMaxSaturated"] = get_float_kelvin(0xA8)
        meta["CameraTemperatureMinSaturated"] = get_float_kelvin(0xAC)

        meta["CameraModel"] = get_string(0xD4, 32)
        meta["CameraPartNumber"] = get_string(0xF4, 16)
        meta["CameraSerialNumber"] = get_string(104, 16)
        meta["CameraSoftware"] = get_string(114, 16)
        meta["LensModel"] = get_string(0x170, 32)

        meta["RawValueRangeMin"] = get_uint16(0x310)
        meta["RawValueRangeMax"] = get_uint16(0x312)
        meta["RawValueMedian"] = get_uint16(0x338)
        meta["RawValueRange"] = get_uint16(0x33C)
        meta["FilterModel"] = get_string(0x1EC, 16)
        meta["FilterPartNumber"] = get_string(0x1FC, 16)
        meta["FilterSerialNumber"] = get_string(0x21C, 16)
        meta["LensPartNumber"] = get_string(0x190, 16)
        meta["LensSerialNumber"] = get_string(0x1A0, 16)
        meta["FieldOfView"] = get_float(0x1B4)

        meta["FocusStepCount"] = get_uint16(0x390)
        meta["FocusDistance"] = get_float(0x45C)
        meta["FrameRate"] = get_uint16(0x464)
        meta["Timestamp"] = get_uint32(0x384)
        import datetime

        meta["Datetime (UTC)"] = datetime.datetime.fromtimestamp(
            meta["Timestamp"]
        ).strftime("%Y-%m-%d %H:%M:%S")

        self.meta |= meta
