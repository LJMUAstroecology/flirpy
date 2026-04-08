import os
import struct
import sys

if sys.version.startswith("2"):
    from backports import tempfile
else:
    import tempfile

import glob

import cv2
import pytest

from flirpy.io.seq import Seq, Splitter
from flirpy.util.exiftool import Exiftool

FFF_MAGIC = b"FFF\x00"

# FFF header layout (little-endian), from Exiftool:
#   4s  magic
#   16s creator
#   I   version
#   I   record_dir_offset  (byte offset from frame start to record directory)
#   I   record_count
#   I   (unused)
#   H   (unused)
#   7H  (unused)
_HEADER_STRUCT = struct.Struct("<4s16sIIIIH7H")  # 52 bytes
_RECORD_STRUCT = struct.Struct("<HHIIIIIII")  # 32 bytes


def _make_fff_frame(payload_size):
    """Build a single synthetic FFF frame with one data record.

    The frame has a valid header and record directory so that the
    parser can determine the frame extent.

    Total frame size = record_dir_offset + 1 * record_size + payload_size
    """
    record_count = 1
    # Place the record directory right after the header (padded to 64 bytes
    # to match real files).
    record_dir_offset = 64
    data_offset = record_dir_offset + record_count * _RECORD_STRUCT.size

    header = _HEADER_STRUCT.pack(
        FFF_MAGIC,  # magic
        b"\x00" * 16,  # creator
        100,  # version
        record_dir_offset,  # record_dir_offset
        record_count,  # record_count
        0,  # unused
        0,  # unused
        0,
        0,
        0,
        0,
        0,
        0,
        0,  # 7H unused
    )
    # Pad header to record_dir_offset
    header = header.ljust(record_dir_offset, b"\x00")

    record_entry = _RECORD_STRUCT.pack(
        0x01,  # record_type (raw data)
        1,  # record_subtype
        0,  # record_version
        0,  # index_id
        data_offset,  # record_offset (relative to frame start)
        payload_size,  # record_length
        0,
        0,
        0,  # parent, object_number, checksum
    )

    payload = bytes(payload_size)
    return header + record_entry + payload


def _make_seq_blob(payload_sizes):
    """Build a synthetic SEQ blob with valid FFF headers."""
    return b"".join(_make_fff_frame(ps) for ps in payload_sizes)


def _seq_from_blob(blob):
    """Construct a Seq object from raw bytes without touching the filesystem."""
    seq = object.__new__(Seq)
    seq.seq_blob = blob
    seq.raw = True
    seq.width = None
    seq.height = None
    seq.pos = Seq._get_frame_positions(blob)
    return seq


class TestChunking:
    def test_seq_uniform_chunk_sizes(self):
        seq = _seq_from_blob(_make_seq_blob([500, 500, 500]))
        assert len(seq.pos) == 3
        sizes = [s for _, s in seq.pos]
        assert sizes[0] == sizes[1] == sizes[2]

    def test_seq_non_uniform_chunk_size(self):
        seq = _seq_from_blob(_make_seq_blob([500, 500, 800]))
        assert len(seq.pos) == 3
        assert seq.pos[2][1] > seq.pos[0][1]

    def test_seq_chunks_start_with_fff_magic(self):
        blob = _make_seq_blob([400, 600, 700])
        seq = _seq_from_blob(blob)
        for offset, size in seq.pos:
            assert blob[offset : offset + 4] == FFF_MAGIC

    def test_seq_chunks_cover_full_file(self):
        blob = _make_seq_blob([500, 500, 500])
        seq = _seq_from_blob(blob)
        assert sum(size for _, size in seq.pos) == len(blob)

    def test_false_magic_inside_payload_ignored(self):
        """FFF\x00 appearing inside image data must not create a spurious frame."""
        frame = bytearray(_make_fff_frame(500))
        # Inject FFF magic inside the payload area (after the record directory)
        inject_offset = 64 + _RECORD_STRUCT.size + 100
        frame[inject_offset : inject_offset + 4] = FFF_MAGIC
        blob = bytes(frame) + _make_fff_frame(500)
        seq = _seq_from_blob(blob)
        assert len(seq.pos) == 2


class TestSeqSplit:
    def setup_method(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.output_folder = self.tempdir.name

        folder = os.path.dirname(os.path.abspath(__file__))
        self.test_data_path = os.path.join(folder, "test_data", "test.seq")

    def teardown_method(self):
        self.tempdir.cleanup()

    def test_output_folder(self):
        self.sp = Splitter(self.output_folder)
        assert os.path.exists(self.output_folder)

    def test_process_seq_split(self):
        if Exiftool().path is None:
            pytest.skip("Exiftool not installed")
        self.sp = Splitter(self.output_folder)

        self.sp.split_folders = True
        self.sp.process(self.test_data_path)

        assert os.path.exists(os.path.join(self.output_folder, "test", "raw"))
        assert os.path.exists(os.path.join(self.output_folder, "test", "preview"))
        assert os.path.exists(os.path.join(self.output_folder, "test", "radiometric"))

        assert (
            len(glob.glob(os.path.join(self.output_folder, "test", "raw", "*.fff"))) > 0
        )
        assert (
            len(glob.glob(os.path.join(self.output_folder, "test", "raw", "*.txt"))) > 0
        )
        assert (
            len(glob.glob(os.path.join(self.output_folder, "test", "preview", "*.jpg")))
            > 0
        )
        assert (
            len(
                glob.glob(
                    os.path.join(self.output_folder, "test", "radiometric", "*.tiff")
                )
            )
            > 0
        )

    def test_raw_is_16_bit(self):
        self.sp = Splitter(self.output_folder)
        self.sp.process(self.test_data_path)

        raw_files = glob.glob(
            os.path.join(self.output_folder, "test", "radiometric", "*.tiff")
        )

        for raw_file in raw_files:
            assert cv2.imread(raw_file, cv2.IMREAD_UNCHANGED).dtype == "uint16"

    def test_process_no_mmap(self):
        self.sp = Splitter(self.output_folder)
        self.sp.use_mmap = False
        self.sp.process(self.test_data_path)

    def test_process_with_wh(self):
        self.sp = Splitter(self.output_folder, width=640, height=512)
        self.sp.use_mmap = False
        self.sp.process(self.test_data_path)

    def test_process_seq_no_split(self):
        self.sp = Splitter(self.output_folder)

        self.sp.split_filetypes = False
        self.sp.process(self.test_data_path)

        assert os.path.exists(os.path.join(self.output_folder, "test", "raw")) is False
        assert (
            os.path.exists(os.path.join(self.output_folder, "test", "preview")) is False
        )
        assert (
            os.path.exists(os.path.join(self.output_folder, "test", "radiometric"))
            is False
        )

        assert len(glob.glob(os.path.join(self.output_folder, "test", "*.fff"))) > 0
        assert len(glob.glob(os.path.join(self.output_folder, "test", "*.txt"))) > 0
        assert len(glob.glob(os.path.join(self.output_folder, "test", "*.jpg"))) > 0
        assert len(glob.glob(os.path.join(self.output_folder, "test", "*.tiff"))) > 0
