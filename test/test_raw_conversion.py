import copy
import os

import numpy as np

from flirpy.io.fff import Fff
from flirpy.util.exiftool import Exiftool
from flirpy.util.raw import raw2temp


def test_percent_humidity_matches_ratio():
    # ExifTool reports humidity as text, "30.0 %". raw2temp must treat it like the ratio 0.30.
    folder = os.path.dirname(os.path.abspath(__file__))
    raw = Fff(os.path.join(folder, "test_data", "frame_000000.fff")).get_image().astype(np.float64)
    meta = Exiftool.__new__(Exiftool).meta_from_file(os.path.join(folder, "test_data", "frame_000000.txt"))
    assert meta["Relative Humidity"].strip() == "30.0 %"

    ratio = copy.deepcopy(meta)
    ratio["Relative Humidity"] = 0.30

    diff = np.abs(raw2temp(raw, meta) - raw2temp(raw, ratio)).max()
    assert diff < 1e-6, f"percent vs ratio humidity differ by up to {diff:.3f} C"
