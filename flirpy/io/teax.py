import numpy as np
import os
import glob
import time
import shutil
import pathlib
import psutil
import tempfile
from tqdm import tqdm
import subprocess
import logging
import cv2

try:
  from pathlib import Path
except ImportError:
  from pathlib2 import Path  # python 2 backport

logger = logging.getLogger()

"""
A couple of utility functions from StackOverflow
"""
def _kill(proc_pid):
    process = psutil.Process(proc_pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()

def _get_size(start_path = '.'):
    total_size = 0
    for dirpath, _, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

class splitter:
    
    def __init__(self, output_folder="./", thermoviewer_path="C:\Program Files (x86)\ThermoViewer\ThermoViewer.exe"):
        self.thermoviewer_path = thermoviewer_path
        
        self.overwrite = True

        self.output_folder = os.path.expanduser(output_folder)
        Path(self.output_folder).mkdir(exist_ok=True)

    def process(self, file_list):

        if isinstance(file_list, str):
            file_list = [file_list]

        file_list = [os.path.abspath(os.path.expanduser(f)) for f in file_list]

        logger.info("Merging {} files".format(len(file_list)))

        working_folder = os.path.join(tempfile.gettempdir(), "flirpy")
        os.makedirs(working_folder, exist_ok=True)

        merge_file = self._merge_files(file_list, working_folder)
        logger.info("Splitting files to: {}".format(self.output_folder))
        self._process_teax(merge_file, self.output_folder)
        self._post_process(self.output_folder)
        shutil.rmtree(working_folder)

    def _process_teax(self, input_file, output_folder):
        """
        Split a TeAX file into frames. Automatically detects if there is
        valid GPS metadata and what format it's in.

        Image output is as TIFF. Estimated progress output assumes a compression 
        ratio of 2.
        """
        os.makedirs(output_folder, exist_ok=True)
        
        serial = "mavlink"
        
        if self._check_gps(input_file, "nmea"):
            serial = "nmea"
            logger.info("NMEA GPS")
        elif self._check_gps(input_file, "mavlink"):
            serial = "mavlink"
            logger.info("mavlink GPS")
        
        args = "-i {} -expa {} -exfo tif -exfn image -exmeta CSVpf -serial {} -c".format(input_file, output_folder, serial)
        cmd = [self.thermoviewer_path]
        cmd += args.split(' ')
        
        proc = subprocess.Popen(cmd)
        
        compression_ratio = 2

        target_size = compression_ratio*os.path.getsize(input_file)
        
        with tqdm(total=target_size, unit='B', unit_scale=True, unit_divisor=1024) as pbar:    
            prev_size = 0
            while 1:
                try:
                    retcode = proc.poll()
                    if retcode is not None: # Process finished.
                        logger.info("Done split.")
                        break
                    else: # No process is done, wait a bit and check again.
                        time.sleep(2)
                        
                        try:
                            size = _get_size(output_folder)
                            delta = size-prev_size
                            prev_size = size

                            pbar.update(delta)
                        except:
                            pass
                        continue
                except KeyboardInterrupt:
                    _kill(proc.pid)

    def _check_gps(self, input_file, serial="nmea"):
        """
        Checks an input TMC or TFC file for meta data which can either be
        provided from mavlink or nmea.

        Keyword arguments:
        
        serial - string with metadata parse format; should be nmea or mavlink

        Returns true if the provided serial method is correct. Note some cameras
        do not provide useful metadata.
        """
        output = tempfile.gettempdir()
        
        # Extract image
        args = "-i {} -expa {} -exsf 1 -exef 2 -exfo tif -exfn image -exmeta CSVpf -serial {} -c".format(input_file, output, serial)
        cmd = [self.thermoviewer_path]
        cmd += args.split(' ')
        
        subprocess.getoutput(cmd)
        
        # Check if time gps is nonzero
        
        meta = np.loadtxt(output+"/image_0001_meta.csv", skiprows=1, usecols=2, delimiter=';')

        if meta == 0:
            return False
        else:
            return True

    def _merge_files(self, input_files, output_folder, filename="merged"):
        """
        Given a folder, merge all the split "videos" into a single file.

        Call this before running split_file on the merged file.
        """        

        if input_files[0].split(".")[-1].lower() == "tmc":
            ext = "tmc"
        else:
            ext = "tfc"

        output_file = os.path.abspath(os.path.join(output_folder, "{}.{}".format(filename, ext)))

        try:
            total_size = sum([os.path.getsize(f) for f in input_files])
        except:
            logger.warn("Failed to get size: {}".format(input_files))
            total_size=0
        
        file_list = " ".join(input_files)

        args = "-exfn {} -c -merge {}".format(output_file, file_list)
        cmd = [self.thermoviewer_path]
        cmd += args.split(' ')
        logger.info(" ".join(cmd))
        proc = subprocess.Popen(cmd)
        
        logger.info("Merging inputs to {}: ".format(output_file))
        
        with tqdm(total=total_size, unit='B', unit_scale=True, unit_divisor=1024) as pbar:    
            prev_size = 0
            while 1:
                try:
                    retcode = proc.poll()
                    if retcode is not None: # Process finished.
                        logger.info("Done merge.")
                        break
                    else: # No process is done, wait a bit and check again.
                        time.sleep(1)
                        try:
                            size = os.path.getsize(output_file)
                            delta = size-prev_size
                            prev_size = size
                            
                            pbar.update(delta)
                        except FileNotFoundError:
                            pass

                        continue
                except KeyboardInterrupt:
                    _kill(proc.pid)
            
        return os.path.normpath(output_file)

    def _post_process(self, folder):
        # Output directories
        rgb_folder = os.path.join(folder, "rgb") 
        os.makedirs(rgb_folder, exist_ok=True)

        radiometric_folder = os.path.join(folder, "radiometric")
        os.makedirs(radiometric_folder, exist_ok=True)

        preview_folder = os.path.join(folder, "preview")
        os.makedirs(preview_folder, exist_ok=True)

        # Convert raw files
        for raw in glob.glob(os.path.join(folder, "*.tiff")):

            base, ext = os.path.splitext(os.path.basename(raw))
            output_name = base+".png"

            raw_im = cv2.imread(raw, cv2.IMREAD_UNCHANGED).astype(np.float32)
            raw_range = raw_im.max() - raw_im.min()
            converted = 255*(raw_im - raw_im.min())/raw_range
            cv2.imwrite(os.path.join(preview_folder, output_name), converted.astype(np.uint8))

            raw_basename = os.path.basename(raw)
            shutil.move(raw, os.path.join(radiometric_folder, raw_basename))

        for rgb in glob.glob(os.path.join(folder, "*.jpg")):
            dst_basename = os.path.basename(rgb)
            shutil.move(rgb, os.path.join(rgb_folder, dst_basename))

        for meta in glob.glob(os.path.join(folder, "*.csv")):
            meta_basename = os.path.basename(meta)
            shutil.move(meta, os.path.join(radiometric_folder, meta_basename))
        

def find_folders(path):
    """
    Recursively searches the path for folders containing TFC or TMC files.
    """
    dirs = set()

    for folder in os.walk(path):
        for subfolder in folder[1]:
            current_folder = os.path.abspath((os.path.join(folder[0], subfolder)))
            nfiles = len(glob.glob("{}".format(current_folder)+os.sep+"*.T*C"))
            
            if nfiles > 0:
                dirs.add(os.path.normpath(current_folder))
    
    return dirs

def find_files(path, heuristics=True):
    """
    """

    files = set()

    for folder in os.walk(path):
        for subfolder in folder[1]:
            current_folder = os.path.abspath((os.path.join(folder[0], subfolder)))
            for f in glob.glob("{}".format(current_folder)+os.sep+"*.T*C"):
                _, filename = os.path.split(f)

                if heuristics and filename[:3] == "000":
                    pass
                else:
                    files.add(f)

    return files

def process_file(input_file):

    logger.info("Working on:", input_file)

    input_folder, full_filename = os.path.split(input_file)
    filename, _ = full_filename.split(".")

    working_folder = os.path.normpath(tempfile.gettempdir()+os.sep+filename)
    os.makedirs(working_folder, exist_ok=True)
    shutil.copy(input_file, working_folder)

    output_folder = input_folder+os.sep+filename
    logger.info(output_folder)

    split_file(working_folder+os.sep+full_filename, input_folder+os.sep+filename)
    
    shutil.rmtree(working_folder)
    logger.info("Finished {}".format(input_folder))

def process_directory(input_folder):
    """
    Takes a folder of thermoviewer files and splits them into frames,
    by default exports into input_folder/frames.
    
    This function first merges the input files onto a local hard disk. This
    allows fast sequential reading and writing from a (presumed) external drive
    to an internal drive. This avoids excessive seeking on the target drive and
    is much faster than reading and writing to the same drive.
    
    The merged file is then split and written back to the drive as separated frames
    using the same logic as above.
    
    Note: the file splitting process is CPU bound, so exporting to a
    mechanical drive won't slow the process down.
    """
    working_folder = os.path.normpath(tempfile.gettempdir()+os.sep+ os.sep.join(input_folder.split('\\')[1:]))
    os.makedirs(working_folder, exist_ok=True)

    merged = merge_folder(input_folder, working_folder)
    
    split_file(merged, input_folder+os.sep+"frames")
    
    shutil.rmtree(working_folder)
    print("Finished {}".format(input_folder))

if __name__ == "__main__":
    pass