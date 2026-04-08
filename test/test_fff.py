import os
import re
import subprocess

import numpy as np
import pytest

from flirpy.io.fff import _FFF_RECORD_STRUCT, Fff, FffHeader, FffRecord  # noqa: I001


class TestFff:
    def setup_method(self):

        folder = os.path.dirname(os.path.abspath(__file__))
        self.test_data_fff = os.path.join(folder, "test_data", "frame_000000.fff")
        self.test_data_meta = os.path.join(folder, "test_data", "frame_000000.txt")

        self.frame = Fff(self.test_data_fff)

    def test_read_image(self):
        image = self.frame.get_image()
        assert len(image.shape) == 2
        assert image.dtype == np.uint16

    def test_read_radiometric_image(self):
        image = self.frame.get_radiometric_image()
        assert len(image.shape) == 2
        assert image.dtype == np.float64

    def test_fff_gps(self):
        coord = self.frame.meta["gps"]
        assert len(coord) == 9

    def test_from_bytes(self):

        with open(self.test_data_fff, "rb") as infile:
            self.frame = Fff(infile.read())

            # Check GPS for sanity
            assert len(self.frame.meta["gps"]) == 9


def _parse_exiftool_endian(output):
    """Parse endianness from exiftool -v3 output."""
    m = re.search(r"BinaryData directory, (\d+) bytes, (\w+)-endian", output)
    assert m
    return m.group(2) == "Big"


def _parse_exiftool_record_count(output):
    m = re.search(r"FFF directory with (\d+) entries", output)
    assert m
    return int(m.group(1))


def _parse_exiftool_records(output):
    """Parse records from exiftool -v3 output.

    Lines like:
      | 0) FLIR Record 0x01, offset 0x0200, length 0xa0020
      | 3) FLIR Record 0x00 (empty)
    """
    records = []

    # Gnarly regex that does the job since exiftool doesn't output in
    # an easily parse-able format.
    for m in re.finditer(
        r"\|\s+(\d+)\)\s+FLIR Record (0x[0-9a-fA-F]+)"
        r"(?:,\s+offset (0x[0-9a-fA-F]+),\s+length (0x[0-9a-fA-F]+))?",
        output,
    ):
        rec_type = int(m.group(2), 16)
        rec_offset = int(m.group(3), 16) if m.group(3) else 0
        rec_length = int(m.group(4), 16) if m.group(4) else 0
        records.append((rec_type, rec_offset, rec_length))
    return records


def _run_exiftool(path):
    result = subprocess.run(
        ["exiftool", "-v3", path],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip("exiftool not available")
    return result.stdout


def _check_header_vs_exiftool(path):
    """Compare our FffHeader/FffRecord parsing against exiftool for a single file."""
    output = _run_exiftool(path)

    with open(path, "rb") as f:
        data = f.read()

    bigendian = FffHeader.detect_bigendian(data)
    assert bigendian == _parse_exiftool_endian(output), "endian mismatch"

    header = FffHeader.from_buffer(data, bigendian=bigendian)
    assert header.record_count == _parse_exiftool_record_count(output), (
        "record count mismatch"
    )

    exiftool_records = _parse_exiftool_records(output)
    assert len(exiftool_records) == header.record_count

    for i in range(header.record_count):
        offset = header.record_dir_offset + i * _FFF_RECORD_STRUCT.size
        rec = FffRecord.from_buffer(data, offset, bigendian)
        et_type, et_offset, et_length = exiftool_records[i]

        assert rec.record_type == et_type, f"Record {i}: type mismatch"
        assert rec.record_offset == et_offset, f"Record {i}: offset mismatch"
        assert rec.record_length == et_length, f"Record {i}: length mismatch"


_TEST_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data")


class TestFffHeaderBigEndian:
    """Verify FffHeader/FffRecord parsing against exiftool (big-endian file)."""

    def test_header_vs_exiftool(self):
        _check_header_vs_exiftool(os.path.join(_TEST_DATA, "test.seq"))


class TestFffHeaderLittleEndian:
    """Verify FffHeader/FffRecord parsing against exiftool (little-endian file)."""

    def test_header_vs_exiftool(self):
        _check_header_vs_exiftool(os.path.join(_TEST_DATA, "frame_000000_le.fff"))
