
import numpy as nump
from PIL import Image
import os
import re
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

class Seq:
    def __init__(self, input_file, height=None, width=None):
        """
        Load a FLIR SEQ file. Currently this must be a SEQ
        file containing FFF files. The resulting object can
        be indexed as a normal array and will return the
        """
        with open(input_file, 'rb') as seq_file:
            self.seq_blob = seq_file.read()

        self._fff_it = self._get_fff_iterator(self.seq_blob)
        
        start_pos = [match.start() for match in self._fff_it]
        fff_offset = start_pos[:-1]
        fff_size = start_pos[1:] - start_pos[:-1]
        self.pos = [(fff_offset[idx], fff_size[idx]) for idx in range(len(fff_offset))]
       
        self.width = width
        self.height = height

    def _get_fff_iterator(self, seq_blob):
        """
        Internal function which returns an iterator containing the
        indices of the files in the SEQ. Probably this should be 
        converted to something a bit more intelligent which 
        actually identifies the size of the records in the file.
        """
        magic_pattern_fff = "\x46\x46\x46\x00".encode()

        valid = re.compile(magic_pattern_fff)
        return valid.finditer(seq_blob)

    def __len__(self):
        """
        Returns the length of the sequence
        """
        return len(self.pos)

    def __getitem__(self, index):
        """
        Retuns a FFF image in the sequence
        """

        offset, chunksize = self.pos[index]
        chunk = self.seq_blob[offset:offset+chunksize]

        return Fff(chunk, self.width, self.height)

class Splitter:
    
    def __init__(self,
                    output_folder="./",
                    exiftool_path=None,
                    start_index=0,
                    step=1,
                    split_folders=True,
                    preview_format="jpg",
                    width=None,
                    height=None):
        
        self.exiftool = Exiftool(exiftool_path)
            
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
        self.width = width
        self.height = height
        
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
        Image.fromarray(data.astype("uint16")).save(filename)

    def _write_preview(self, filename, data):
        drange = data.max()-data.min()
        preview_data = 255.0*((data-data.min())/drange)
        logger.debug("Writing {}", filename)
        Image.fromarray(preview_data.astype('uint8')).save(filename)
            
    def _make_split_folders(self, output_folder):
        Path(os.path.join(output_folder, "raw")).mkdir(exist_ok=True)
        Path(os.path.join(output_folder, "radiometric")).mkdir(exist_ok=True)
        Path(os.path.join(output_folder, "preview")).mkdir(exist_ok=True)

    def _check_overwrite(self, path):
        exists = os.path.exists(path)
        return (not exists) or (exists and self.overwrite)
    
    def _process_seq(self, input_file, output_subfolder):
        
        logger.debug("Processing {}".format(input_file))
        
        for count, frame in enumerate(tqdm(Seq(input_file, self.height, self.width))):

            if frame.meta is None:
                self.frame_count += 1
                continue
                
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
            
            if self.frame_count % self.step == 0:

                if self.export_meta and self._check_overwrite(filename_fff):
                    frame.write(filename_fff)
                
                # Export raw files and/or radiometric convert them
                if self.export_tiff and self._check_overwrite(filename_tiff):
                    if self.export_radiometric:
                        
                        # Use Exiftool to extract metadata
                        if self.width is not None and self.height is not None:
                            # Export the first metadata
                            if count == 0:
                                self.exiftool.write_meta(filename_fff)
                                meta = self.exiftool.meta_from_file(filename_meta)
                        else:
                            meta = None

                        image = frame.get_radiometric_image(meta=meta)
                        image += 273.15 # Convert to Kelvin
                        image /= 0.04 # Standard FLIR scale factor
                    else:
                        image = frame.get_image()

                    self._write_tiff(filename_tiff, image)

                # Export preview frame (crushed to 8-bit)
                if self.export_preview and self._check_overwrite(filename_preview):
                    self._write_preview(filename_preview, image)
        
            self.frame_count += 1
                    
        return
