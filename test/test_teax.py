import sys

if sys.version.startswith("2"):
    from backports import tempfile
else:
    import tempfile


from flirpy.io.teax import splitter


def test_split_tmc():
    temp_dir = tempfile.gettempdir()
    splitter(output_folder=temp_dir)
