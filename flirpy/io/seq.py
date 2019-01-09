import numpy as np
import struct
import os
import cv2
import re
import mmap
import tqdm
import logging
from glob import iglob, glob
import subprocess
from PIL import Image
from tqdm.autonotebook import tqdm

logger = logging.getLogger(__name__)

class splitter:
    
    def __init__(self, output_folder="./", exiftool=None):
        
        if exiftool is None:
            self.exitfool = utils.get_exiftool_path()
            
        self.width = 640
        self.height = 512
        self.start_index = 0
        self.step = 1
        self.frame_count = self.start_index
        self.export_tiff = True
        self.export_meta = True
        self.export_preview = True
        self.export_radiometric = True
        self.overwrite = True
        self.split_folders = True
        self.output_folder = output_folder
    
    def raw2temp(self, raw, meta):
        ATA1 = float(meta["Atmospheric Trans Alpha 1"])
        ATA2 = float(meta["Atmospheric Trans Alpha 2"])
        ATB1 = float(meta["Atmospheric Trans Beta 1"])
        ATB2 = float(meta["Atmospheric Trans Beta 2"])
        ATX = float(meta["Atmospheric Trans X"])
        PR1 = float(meta["Planck R1"])
        PR2 = float(meta["Planck R2"])
        PO = float(meta["Planck O"])
        PB = float(meta["Planck B"])
        PF = float(meta["Planck F"])
        E = float(meta["Emissivity"])
        IRT = float(meta["IR Window Transmission"])
        IRWTemp = float(meta["IR Window Temperature"].split('C')[0])
        OD = float(meta["Object Distance"].split('m')[0])
        ATemp = float(meta["Atmospheric Temperature"].split('C')[0])
        RTemp = float(meta["Reflected Apparent Temperature"].split('C')[0])
        humidity = float(meta["Relative Humidity"].split('%')[0])

      # Equations to conert to temperature
      # See http://130.15.24.88/exiftool/forum/index.php/topic,4898.60.html
      # Standard equation: temperature<-PB/log(PR1/(PR2*(raw+PO))+PF)-273.15
      # Other source of information: Minkina and Dudzik's Infrared Thermography: Errors and Uncertainties

        window_emissivity = 1 - IRT
        window_reflectivity = 0

        # Converts relative humidity into water vapour pressure (mmHg)
        water = (humidity/100.0)*exp(1.5587+0.06939*(ATemp)-0.00027816*(ATemp)**2+0.00000068455*(ATemp)**3)

        #tau1 = ATX*np.exp(-np.sqrt(OD/2))
        tau1 = ATX*np.exp(-np.sqrt(OD/2)*(ATA1+ATB1*np.sqrt(water)))+(1-ATX)*np.exp(-np.sqrt(OD/2)*(ATA2+ATB2*np.sqrt(water)))
        tau2 = ATX*np.exp(-np.sqrt(OD/2)*(ATA1+ATB1*np.sqrt(water)))+(1-ATX)*np.exp(-np.sqrt(OD/2)*(ATA2+ATB2*np.sqrt(water)))

        # transmission through atmosphere - equations from Minkina and Dudzik's Infrared Thermography Book
        # Note: for this script, we assume the thermal window is at the mid-point (OD/2) between the source
        # and the camera sensor

        raw_refl = PR1/(PR2*(np.exp(PB/(RTemp+273.15))-PF))-PO   # radiance reflecting off the object before the window
        raw_refl_attn = (1-E)/E*raw_refl   # attn = the attenuated radiance (in raw units) 

        raw_atm1 = PR1/(PR2*(np.exp(PB/(ATemp+273.15))-PF))-PO # radiance from the atmosphere (before the window)
        raw_atm1_attn = (1-tau1)/E/tau1*raw_atm1 # attn = the attenuated radiance (in raw units) 

        raw_window = PR1/(PR2*(exp(PB/(IRWTemp+273.15))-PF))-PO
        raw_window_attn = window_emissivity/E/tau1/IRT*raw_window

        raw_refl2 = PR1/(PR2*(np.exp(PB/(RTemp+273.15))-PF))-PO   
        raw_refl2_attn = window_reflectivity/E/tau1/IRT*raw_refl2

        raw_atm2 = PR1/(PR2*(np.exp(PB/(ATemp+273.15))-PF))-PO
        raw_atm2_attn = (1-tau2)/E/tau1/IRT/tau2*raw_atm2

        raw_object = raw/E/tau1/IRT/tau2-raw_atm1_attn-raw_atm2_attn-raw_window_attn-raw_refl_attn-raw_refl2_attn

        temp = PB/np.log(PR1/(PR2*(raw+PO))+PF)-273.15

        return temp
    
    def set_start_index(self, index):
        self.start_index = int(index)
        
    def process(self, file_list):
        
        self.frame_count = self.start_index
        
        for seq in tqdm(file_list):
            subfolder, ext = os.path.splitext(os.path.basename(seq))
            folder = os.path.join(self.output_folder, subfolder)
            os.makedirs(folder, exist_ok=True)
            
            self.process_seq(seq, folder)
        
    def meta_from_file(self, filename):
        meta = {}

        with open(filename, 'r') as f:
            for line in f:
                res = line.split(":")

                key = res[0].strip()
                value = "".join(res[1:])

                meta[key] = value

        return meta

    def extract_gps(data):
        valid = re.compile("[0-9]{4}[NS]\x00[EW]\x00".encode())

        res = valid.search(data)
        start_pos = res.start()

        s = struct.Struct("<4xcxcx4xddf32xcxcx4xff")

        return s.unpack_from(data, start_pos)
        
    def write_raw(self, filename, data):
        with open(filename, 'wb') as f:
            f.write(data)
    
    def write_tiff(self, filename, data):
        cv2.imwrite(filename, data)
    
    def write_preview(self, filename, data):
        drange = data.max()-data.min()
        preview_data = 255.0*((data-data.min())/drange)
        cv2.imwrite(filename, preview_data.astype('uint8'))
    
    def write_meta(self, filemask = None):
        if filemask is None:
            if self.split_folders:
                filemask = os.path.join(self.output_folder, "raw", "frame_*.fff")
            else:
                filemask = os.path.join(self.output_folder, "frame_*.fff")
        res = subprocess.run([self.exiftool, filemask, "-w", ".txt"], stdout=subprocess.PIPE)
        
    def find_data_offset(self, data):
    
        search = (self.width-1).to_bytes(2, 'little')\
                    +b"\x00\x00"\
                    +(self.height-1).to_bytes(2, 'little')

        valid = re.compile(search)
        res = valid.search(data)

        return res.end()+14
        
    def process_fff_chunk(self, chunk):
        offset = self.find_data_offset(chunk)
        count = self.height*self.width
        data = np.frombuffer(chunk, offset=offset, dtype='uint16', count=count).reshape((self.height, self.width))
        
        return data
    
    def process_seq(self, input_file, output_folder):
        
        logger.info("Processing {}".format(input_file))
        
        with open(input_file, 'rb') as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

            magic_pattern_fff = "\x46\x46\x46\x00".encode()

            valid = re.compile(magic_pattern_fff)
            res = valid.finditer(mm)

            pos = []
            prev_pos = 0
            
            meta = None
            
            for i, match in tqdm(enumerate(res)):
                index = match.start()
                chunksize = index-prev_pos
                pos.append((index, chunksize))
                prev_pos = index
                
                if self.split_folders:
                    os.makedirs(os.path.join(output_folder, "raw"), exist_ok=True)
                    os.makedirs(os.path.join(output_folder, "radiometric"), exist_ok=True)
                    os.makedirs(os.path.join(output_folder, "preview"), exist_ok=True)
                                     
                    filename_fff = os.path.join(output_folder, "raw", "frame_{0:06d}.fff".format(self.frame_count))
                    filename_tiff = os.path.join(output_folder, "radiometric", "frame_{0:06d}.tiff".format(self.frame_count))
                    filename_preview = os.path.join(output_folder, "preview", "frame_{0:06d}.png".format(self.frame_count))
                    filename_meta = os.path.join(output_folder, "raw", "frame_{0:06d}.txt".format(self.frame_count))
                else:
                    filename_fff = os.path.join(output_folder, "frame_{0:06d}.fff".format(self.frame_count))
                    filename_tiff = os.path.join(output_folder, "frame_{0:06d}.tiff".format(self.frame_count))
                    filename_preview = os.path.join(output_folder, "frame_{0:06d}.png".format(self.frame_count))
                    filename_meta = os.path.join(output_folder, "frame_{0:06d}.txt".format(self.frame_count))
                
                if index == 0:
                    continue
                    
                chunk = mm.read(chunksize)
                
                if i % self.step == 0:
                    data = self.process_fff_chunk(chunk)
                    
                    # Need FFF files to extract meta, but we do it one iteration afterwards
                    if self.export_meta:
                        exists = os.path.exists(filename_fff)
                        if not exists or (exists and self.overwrite):
                            self.write_fff(filename_fff, chunk)
                    
                    if meta is None and self.export_radiometric:
                        self.write_raw(filename_fff, chunk)
                        self.write_meta(filename_fff)
                        meta = self.meta_from_file(filename_meta)

                    if self.export_tiff:
                        exists = os.path.exists(filename_tiff)
                        if not exists or (exists and self.overwrite):
                            if self.export_radiometric and meta is not None:
                                data = self.raw2temp(data, meta)
                                data += 273.15 # Convert to Kelvin
                                data /= 0.04 # Scale to fit in 16 bit image

                            self.write_tiff(filename_tiff, data.astype('uint16'))

                    if self.export_preview:
                        exists = os.path.exists(filename_preview)
                        if not exists or (exists and self.overwrite):
                            self.write_preview(filename_preview, data)

                self.frame_count += 1

        if self.export_meta:
            logger.info("Extracting metadata")
            self.write_meta()

        return
