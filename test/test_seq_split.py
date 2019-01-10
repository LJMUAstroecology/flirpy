import pkg_resources
import os
import subprocess
import tempfile

from flirpy.io.seq import splitter

class TestSeqSplit:
    def setup_method(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.output_folder = self.tempdir.name
        
        folder = os.path.dirname(os.path.abspath(__file__))
        self.test_data_path = os.path.join(folder, "test_data", "20181105_121443_IR.SEQ")
        
    def teardown_method(self):
        self.tempdir.cleanup()

    def test_output_folder(self):
        self.sp = splitter(self.output_folder)
        assert os.path.exists(self.output_folder)

    def test_process_seq_split(self):
        self.sp = splitter(self.output_folder)

        self.sp.split_folders = True
        self.sp.process(self.test_data_path)
        
        assert os.path.exists(os.path.join(self.output_folder, "20181105_121443_IR", "raw"))
        assert os.path.exists(os.path.join(self.output_folder, "20181105_121443_IR", "preview"))
        assert os.path.exists(os.path.join(self.output_folder, "20181105_121443_IR", "radiometric"))
    
    def test_process_seq_no_split(self):
        self.sp = splitter(self.output_folder)

        self.sp.split_folders = False
        self.sp.process(self.test_data_path)
        
        assert os.path.exists(os.path.join(self.output_folder, "20181105_121443_IR", "raw")) is False
        assert os.path.exists(os.path.join(self.output_folder, "20181105_121443_IR", "preview")) is False
        assert os.path.exists(os.path.join(self.output_folder, "20181105_121443_IR", "radiometric")) is False
