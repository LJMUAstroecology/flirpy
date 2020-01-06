
import numpy as np
import cv2
import os
import re
import mmap
import tqdm
import logging
from glob import iglob, glob
import subprocess
from tqdm.autonotebook import tqdm

try:
  from pathlib import Path
except ImportError:
  from pathlib2 import Path  # python 2 backport

from flirpy.util.exiftool import Exiftool
from flirpy.io.fff import Fff

logger = logging.getLogger(__name__)

class splitter:
    
    def __init__(self, output_folder="./", exiftool_path=None, start_index=0, step=1, width=640, height=512, split_folders=True, preview_format="jpg"):
        
        self.exiftool = Exiftool(exiftool_path)
            
        self.width = width
        self.height = height
        self.start_index = start_index
        self.step = step
        self.frame_count = self.start_index
        self.export_tiff = True
        self.export_meta = True
        self.export_preview = True
        self.export_radiometric = True
        self.overwrite = True
        self.split_folders = split_folders
        self.split_filetypes = True
        self.use_mmap = True
        
        if preview_format in ["jpg", "jpeg", "png", "tiff"]:
            self.preview_format = preview_format
        else:
            raise ValueError("Preview format not recognised")

        self.output_folder = os.path.expanduser(output_folder)
        Path(self.output_folder).mkdir(exist_ok=True)
    
    def set_start_index(self, index):
        self.start_index = int(index)
        
    def process(self, file_list):

        if isinstance(file_list, str):
            file_list = [file_list]

        file_list = [os.path.expanduser(f) for f in file_list]

        logger.info("Splitting {} files".format(len(file_list)))
        
        self.frame_count = self.start_index

        folders = []
        
        for seq in tqdm(file_list):

            if self.split_folders:
                subfolder, _ = os.path.splitext(os.path.basename(seq))
                folder = os.path.join(self.output_folder, subfolder)
                folders.append(folder)
            else:
                folder = self.output_folder

            Path(folder).mkdir(exist_ok=True)

            logger.info("Splitting {} into {}".format(seq, folder))
            self._process_seq(seq, folder)

            # Batch export meta data
            if self.export_meta:
                logger.info("Extracting metadata")

                if self.split_filetypes:
                    filemask = os.path.join(folder, "raw", "frame_*.fff")
                    copy_filemask = os.path.normpath("./raw/%f.fff")
                    radiometric_folder = os.path.normpath("./radiometric")
                    preview_folder = os.path.normpath("./preview")
                else:
                    filemask = os.path.join(folder, "frame_*.fff")
                    copy_filemask = os.path.normpath("%f.fff")
                    radiometric_folder = os.path.normpath("./")
                    preview_folder = os.path.normpath("./")

                self.exiftool.write_meta(filemask)

                # Copy geotags
                if self.export_tiff:
                    logger.info("Copying tags to radiometric")
                    self.exiftool.copy_meta(folder, filemask=copy_filemask, output_folder=radiometric_folder, ext="tiff")
                
                if self.export_preview:
                    logger.info("Copying tags to preview")
                    self.exiftool.copy_meta(folder, filemask=copy_filemask, output_folder=preview_folder, ext=self.preview_format)
        
        return folders
        
    def _write_tiff(self, filename, data):
        logger.debug("Writing {}", filename)
        cv2.imwrite(filename, data.astype("uint16"))

    def _write_preview(self, filename, data):
        drange = data.max()-data.min()
        preview_data = 255.0*((data-data.min())/drange)
        logger.debug("Writing {}", filename)
        cv2.imwrite(filename, preview_data.astype('uint8'))
            
    def _make_split_folders(self, output_folder):
        Path(os.path.join(output_folder, "raw")).mkdir(exist_ok=True)
        Path(os.path.join(output_folder, "radiometric")).mkdir(exist_ok=True)
        Path(os.path.join(output_folder, "preview")).mkdir(exist_ok=True)

    def _get_fff_iterator(self, seq_blob):
        
        magic_pattern_fff = "\x46\x46\x46\x00".encode()

        valid = re.compile(magic_pattern_fff)
        return valid.finditer(seq_blob)

    def _check_overwrite(self, path):
        exists = os.path.exists(path)
        return (not exists) or (exists and self.overwrite)
    
    def _process_seq(self, input_file, output_subfolder):
        
        logger.debug("Processing {}".format(input_file))
        
        with open(input_file, 'rb') as seq_file:
            
            # Memory mapping may speed up things. This is kinda slow though, because we still have to parse the entire file
            # and then go back through the regexes to find individual frames. Should really use a stream.
            if self.use_mmap:
                seq_blob = mmap.mmap(seq_file.fileno(), 0, access=mmap.ACCESS_READ)
            else:
                seq_blob = seq_file.read()

            it = self._get_fff_iterator(seq_blob)

            pos = []
            prev_pos = 0
            
            meta = None
            
            for i, match in tqdm(enumerate(it)):
                index = match.start()
                chunksize = index-prev_pos
                pos.append((index, chunksize))
                prev_pos = index
                
                if self.split_filetypes:
                    self._make_split_folders(output_subfolder)
                                     
                    filename_fff = os.path.join(output_subfolder, "raw", "frame_{0:06d}.fff".format(self.frame_count))
                    filename_tiff = os.path.join(output_subfolder, "radiometric", "frame_{0:06d}.tiff".format(self.frame_count))
                    filename_preview = os.path.join(output_subfolder, "preview", "frame_{:06d}.{}".format(self.frame_count, self.preview_format))
                    filename_meta = os.path.join(output_subfolder, "raw", "frame_{0:06d}.txt".format(self.frame_count))
                else:
                    filename_fff = os.path.join(output_subfolder, "frame_{0:06d}.fff".format(self.frame_count))
                    filename_tiff = os.path.join(output_subfolder, "frame_{0:06d}.tiff".format(self.frame_count))
                    filename_preview = os.path.join(output_subfolder, "frame_{:06d}.{}".format(self.frame_count, self.preview_format))
                    filename_meta = os.path.join(output_subfolder, "frame_{0:06d}.txt".format(self.frame_count))
                
                if index == 0:
                    continue
                
                # Extract next FFF frame
                if self.use_mmap is False:
                    chunk = seq_blob[index:index+chunksize]
                else:
                    chunk = seq_blob.read(chunksize)
                
                if i % self.step == 0:

                    frame = Fff(chunk)
                    
                    # Need FFF files to extract meta, but we do it one go afterwards
                    if self.export_meta and self._check_overwrite(filename_fff):
                            frame.write(filename_fff)
                    
                    # We need at least one meta file to get the radiometric conversion coefficients
                    if meta is None and self.export_radiometric:
                        frame.write(filename_fff)
                        self.exiftool.write_meta(filename_fff)
                        meta = self.exiftool.meta_from_file(filename_meta)

                    # Export raw files and/or radiometric convert them
                    if self.export_tiff and self._check_overwrite(filename_tiff):
                            if self.export_radiometric and meta is not None:
                                image = frame.get_radiometric_image(meta)
                                image += 273.15 # Convert to Kelvin
                                image /= 0.04
                            else:
                                image = frame.get_image()

                            self._write_tiff(filename_tiff, image)

                    # Export preview frame (crushed to 8-bit)
                    if self.export_preview and self._check_overwrite(filename_preview):
                        self._write_preview(filename_preview, image)
            
                self.frame_count += 1
                    
        return