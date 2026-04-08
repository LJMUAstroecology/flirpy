import datetime
import logging
import os
import struct
from dataclasses import MISSING, dataclass
from typing import Union

import numpy as np

from flirpy.util.exiftool import Exiftool
from flirpy.util.raw import raw2temp

logger = logging.getLogger()


# Full FFF file header: 64 bytes (0x40)
_FFF_HEADER_STRUCT = struct.Struct("<4s16sIIIIH7HIII")
_FFF_RECORD_STRUCT = struct.Struct("<HHIIIIIII")


@dataclass
class FffHeader:
    """Dataclass for the FFF file header (0x40 = 64 bytes).

    Field layout from ExifTool FLIR.pm (ProcessFLIR):

    # 0x00 - char[4]    file format magic ("FFF\x00")
    # 0x04 - char[16]   file creator: e.g. "CAMCTRL", "FLIR", "ResearchIR"
    # 0x14 - uint32     file format version (seen 100, 101)
    # 0x18 - uint32     record directory offset (bytes from start of file)
    # 0x1C - uint32     number of entries in record directory
    # 0x20 - uint32     next free index ID = 2
    # 0x24 - uint16     swap pattern = 0 (?)
    # 0x26 - uint16[7]  spares
    # 0x34 - uint32[2]  reserved
    # 0x3C - uint32     checksum
    """

    magic: bytes
    creator: bytes
    format_version: int
    record_dir_offset: int
    record_count: int
    next_free_index: int
    swap_pattern: int
    spares: tuple
    reserved: tuple
    checksum: int

    @staticmethod
    def detect_bigendian(data, offset=0):
        """Detect endianness by checking if the version field (0x14) is valid
        when read as little-endian.  Valid versions are in the range [100, 200)."""
        return int.from_bytes(data[offset + 0x14 : offset + 0x14 + 4], "little") > 200

    @classmethod
    def from_buffer(cls, data, offset=0, bigendian=None):
        if bigendian is None:
            bigendian = cls.detect_bigendian(data, offset)
        s = (
            get_struct("4s16sIIIIH7HIII", bigendian)
            if bigendian
            else _FFF_HEADER_STRUCT
        )
        res = s.unpack_from(data, offset)
        return cls(
            magic=res[0],
            creator=res[1],
            format_version=res[2],
            record_dir_offset=res[3],
            record_count=res[4],
            next_free_index=res[5],
            swap_pattern=res[6],
            spares=res[7:14],
            reserved=(res[14], res[15]),
            checksum=res[16],
        )


@dataclass
class FffRecord:
    """
    Dataclass for FFF records. FFF records are 32 bytes long and contain the following information.

    Endianness must be provided, because it is inferred from the main FFF header and cannot necessarily
    be determened from this record alone (though in principle if you get a record type that is obviously
    incorrect, check it).

    The record offset here is with respect to the start of the FFF file that this record was extracted from.

    # From Exiftool documentation:
    # 0x00 - int16u record type
    # 0x02 - int16u record subtype: RawData 1=BE, 2=LE, 3=PNG; 1 for other record types
    # 0x04 - int32u record version: seen 0x64,0x66,0x67,0x68,0x6f,0x104
    # 0x08 - int32u index id = 1
    # 0x0c - int32u record offset from start of FLIR data
    # 0x10 - int32u record length
    # 0x14 - int32u parent = 0 (?)
    # 0x18 - int32u object number = 0 (?)
    # 0x1c - int32u checksum: 0 for no checksum
    """

    record_type: int = MISSING
    record_subtype: int = MISSING
    record_version: int = MISSING
    index_id: int = MISSING
    record_offset: int = MISSING
    record_length: int = MISSING
    parent: int = MISSING
    object_number: int = MISSING
    checksum: int = 0

    @classmethod
    def from_buffer(cls, data, offset=0, bigendian=None):
        if bigendian is None:
            bigendian = FffHeader.detect_bigendian(data, offset)
        s = get_struct("HHIIIIIII", bigendian) if bigendian else _FFF_RECORD_STRUCT
        res = s.unpack_from(data, offset)
        return cls(
            record_type=res[0],
            record_subtype=res[1],
            record_version=res[2],
            index_id=res[3],
            record_offset=res[4],
            record_length=res[5],
            parent=res[6],
            object_number=res[7],
            checksum=res[8],
        )

    def __init__(self, data=None, bigendian=False, **kwargs):
        """Generate a FffRecord from a bytes object or keyword arguments.

        Parameters
        ----------
        data : bytes, optional
            Raw bytes to unpack. If None, fields are taken from kwargs.
        bigendian : bool, optional
            Whether to assume big endian, by default False
        """
        if data is not None:
            r = self.from_buffer(data, bigendian=bigendian)
            self.__dict__.update(r.__dict__)
        else:
            for k, v in kwargs.items():
                setattr(self, k, v)


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
    def __init__(self, data: Union[str, bytes], use_exiftool: bool = False):
        """
        Create a FFF object from a filename or a bytes object.

        By default we attempt to decode the records in the file, but if there are
        additional records that we don't know about, these will not be extracted. In
        this case you can use Exiftool to attempt to dump these.

        Parameters
        ----------
        data : Union[str, bytes]
            Either a filename or the raw bytes of a FFF file
        use_exiftool : bool, optional
            Use Exiftool to extract metadata, by default False.

        Raises
        ------
        TypeError
            If data is not a string or bytes object
        """

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
        bigendian = FffHeader.detect_bigendian(self.data)
        if bigendian:
            logger.debug("Assuming file is bigendian")

        header = FffHeader.from_buffer(self.data, bigendian=bigendian)

        logger.debug("File format: %s", header.magic.decode())
        logger.debug("File creator: %s", header.creator.decode())
        logger.debug("File format version: %d", header.format_version)

        for i in range(header.record_count):
            offset = header.record_dir_offset + i * _FFF_RECORD_STRUCT.size
            self.records.append(FffRecord.from_buffer(self.data, offset, bigendian))

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

        def get_uint16(x):
            return get_struct("H", bigendian).unpack_from(data, x)[0]

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

        def get_float(x):
            return get_struct("f", bigendian).unpack_from(data, x)[0]

        def get_float_kelvin(x):
            return get_struct("f", bigendian).unpack_from(data, x)[0] - 273.14

        def get_uint16(x):
            return get_struct("H", bigendian).unpack_from(data, x)[0]

        def get_uint32(x):
            return get_struct("L", bigendian).unpack_from(data, x)[0]

        def get_int32(x):
            return get_struct("i", bigendian).unpack_from(data, x)[0]

        def get_string(x, n):
            return get_struct(f"{n}s", bigendian).unpack_from(data, x)[0]

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
        meta["Datetime (UTC)"] = datetime.datetime.fromtimestamp(
            meta["Timestamp"]
        ).strftime("%Y-%m-%d %H:%M:%S")

        self.meta.update(meta)
