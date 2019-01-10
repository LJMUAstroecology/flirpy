import os
import pkg_resources
import subprocess
import glob

import logging
logger = logging.getLogger(__name__)

class Exiftool:

    def __init__(self, path=None):
        
        if path is None:
            if os.name == "nt":
                self.path = pkg_resources.resource_filename('flirpy', 'bin/exiftool.exe')
            else:
                self.path = pkg_resources.resource_filename('flirpy', 'bin/exiftool')
        else:
            self.path = path
            self.check_path()
    
    def check_path(self):
        try:
            subprocess.check_output([self.path])
            logger.info("Exiftool path verified at {}".format(self.path))
            return True
        except FileNotFoundError:
            logger.error("Couldn't find Exiftool at {}".format(self.path))
            return False

        return False
    
    def write_meta(self, filemask):

        # Do some mangling here to avoid busting the command line limit.
        # First, we run the command in the right working directory
        cwd, mask = os.path.split(filemask)

        # Then we expand the wildcard and pass to the shell 
        # (but don't need to pass the full path since we use cwd)
        files = glob.glob(filemask)
        files = [os.path.split(f)[1] for f in files]

        cmd = [self.path]
        cmd += files
        cmd.append("-w")
        cmd.append(".txt")

        res = subprocess.run(cmd, cwd=cwd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        return res