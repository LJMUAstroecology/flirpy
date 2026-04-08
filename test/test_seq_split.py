import os
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


def _make_seq_blob(frame_sizes):
    """Build a synthetic SEQ blob with FFF magic at the start of each frame."""
    return b"".join(FFF_MAGIC + bytes(size - len(FFF_MAGIC)) for size in frame_sizes)


def _seq_from_blob(blob):
    """Construct a Seq object from raw bytes without touching the filesystem."""
    seq = object.__new__(Seq)
    seq.seq_blob = blob
    seq.raw = True
    seq.width = None
    seq.height = None
    positions = [m.start() for m in seq._get_fff_iterator(blob)]
    seq.pos = []
    for i, index in enumerate(positions):
        chunksize = (
            positions[i + 1] - index if i + 1 < len(positions) else len(blob) - index
        )
        seq.pos.append((index, chunksize))
    return seq


class TestChunking:
    def test_seq_uniform_chunk_sizes(self):
        seq = _seq_from_blob(_make_seq_blob([500, 500, 500]))
        assert len(seq.pos) == 3
        assert all(size == 500 for _, size in seq.pos)

    def test_seq_non_uniform_chunk_size(self):
        seq = _seq_from_blob(_make_seq_blob([500, 500, 800]))
        assert seq.pos == [(0, 500), (500, 500), (1000, 800)]

    def test_seq_chunks_start_with_fff_magic(self):
        blob = _make_seq_blob([400, 600, 700])
        seq = _seq_from_blob(blob)
        for offset, size in seq.pos:
            assert blob[offset : offset + 4] == FFF_MAGIC

    def test_seq_chunks_cover_full_file(self):
        blob = _make_seq_blob([500, 500, 500])
        seq = _seq_from_blob(blob)
        assert sum(size for _, size in seq.pos) == len(blob)


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
