import logging
import os
import platform
import shutil
import subprocess
import sys
from importlib.resources import files

logger = logging.getLogger(__name__)


class Exiftool:
    def __init__(self, path=None):

        if path is None:
            if sys.platform.startswith("win32"):
                self.path = str(files("flirpy").joinpath("bin/exiftool.exe"))
            elif sys.platform.startswith("linux") and not platform.uname()[
                4
            ].startswith("arm"):
                self.path = str(files("flirpy").joinpath("bin/exiftool"))
            else:
                # macOS or Linux ARM: use system exiftool
                self.path = shutil.which("exiftool")
                if self.path is None:
                    logger.warning(
                        "Exiftool not installed, try: brew install exiftool or apt install exiftool"
                    )

        else:
            self.path = path
            self._check_path()

    def _check_path(self):
        try:
            subprocess.check_output([self.path])
            logger.info("Exiftool path verified at {}".format(self.path))
            return True
        except FileNotFoundError:
            logger.error("Couldn't find Exiftool at {}".format(self.path))
            return False

        return False

    def copy_meta(self, folder, filemask="%f.fff", output_folder="./", ext="tiff"):

        cwd = folder

        cmd = [self.path]
        cmd.append("-r")
        cmd.append("-overwrite_original")
        cmd.append("-tagsfromfile")
        cmd.append(filemask)
        cmd.append("-ext")
        cmd.append(ext)
        cmd.append(output_folder)

        logger.debug(" ".join(cmd))

        res = subprocess.call(
            cmd, cwd=cwd, stderr=subprocess.PIPE, stdout=subprocess.PIPE
        )
        return res

    def write_meta(self, filemask):

        # Do some mangling here to avoid busting the command line limit.
        # First, we run the command in the right working directory
        cwd = os.path.dirname(filemask)

        cmd = [self.path]
        cmd.append("-ext")
        cmd.append("fff")
        cmd.append(".")
        cmd.append("-w!")
        cmd.append(".txt")

        logger.debug(" ".join(cmd))

        res = subprocess.call(
            cmd, cwd=cwd, stderr=subprocess.PIPE, stdout=subprocess.PIPE
        )

        return res

    def meta_from_file(self, filename):
        meta = {}

        with open(filename, "r") as f:
            for line in f:
                res = line.split(":")

                key = res[0].strip()
                value = "".join(res[1:])

                meta[key] = value

        return meta
