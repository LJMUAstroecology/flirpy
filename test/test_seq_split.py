import pkg_resources
import os
import subprocess
import tempfile

from flirpy.io.seq import splitter
import glob

class TestSeqSplit:
    def setup_method(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.output_folder = self.tempdir.name

        folder = os.path.dirname(os.path.abspath(__file__))
        self.test_data_path = os.path.join(folder, "test_data", "test.seq")

    def teardown_method(self):
        self.tempdir.cleanup()

    def test_output_folder(self):
        self.sp = splitter(self.output_folder)
        assert os.path.exists(self.output_folder)

    def test_process_seq_split(self):
        self.sp = splitter(self.output_folder)

        self.sp.split_folders = True
        self.sp.process(self.test_data_path)

        assert os.path.exists(os.path.join(self.output_folder, "test", "raw"))
        assert os.path.exists(os.path.join(self.output_folder, "test", "preview"))
        assert os.path.exists(os.path.join(self.output_folder, "test", "radiometric"))

        assert len(glob.glob(os.path.join(self.output_folder, "test", "raw", "*.fff"))) > 0
        assert len(glob.glob(os.path.join(self.output_folder, "test", "raw", "*.txt"))) > 0
        assert len(glob.glob(os.path.join(self.output_folder, "test", "preview", "*.png"))) > 0
        assert len(glob.glob(os.path.join(self.output_folder, "test", "radiometric", "*.tiff"))) > 0

    def test_process_no_mmap(self):
        self.sp = splitter(self.output_folder)
        self.sp.use_mmap = False
        self.sp.process(self.test_data_path)

    def test_process_seq_no_split(self):
        self.sp = splitter(self.output_folder)

        self.sp.split_folders = False
        self.sp.process(self.test_data_path)

        assert os.path.exists(os.path.join(self.output_folder, "test", "raw")) is False
        assert os.path.exists(os.path.join(self.output_folder, "test", "preview")) is False
        assert os.path.exists(os.path.join(self.output_folder, "test", "radiometric")) is False
        
        assert len(glob.glob(os.path.join(self.output_folder, "test", "*.fff"))) > 0
        assert len(glob.glob(os.path.join(self.output_folder, "test", "*.txt"))) > 0
        assert len(glob.glob(os.path.join(self.output_folder, "test", "*.png"))) > 0
        assert len(glob.glob(os.path.join(self.output_folder, "test", "*.tiff"))) > 0
