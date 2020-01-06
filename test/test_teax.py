import pkg_resources
import os
import subprocess

import sys
if sys.version.startswith('2'):
    from backports import tempfile
else:
    import tempfile
import glob
import cv2

from flirpy.io.teax import splitter

def test_split_tmc():
    temp_dir = tempfile.gettempdir()
    sp = splitter(output_folder=temp_dir)

    
