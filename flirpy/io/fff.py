import re
import struct
import numpy as np

from flirpy.util.raw import raw2temp

class Fff:

    def __init__(self, data, height = 512, width = 640):

        self.height = height
        self.width = width
        self.image = None

        if isinstance(data, bytes):
            self.data = data
        elif isinstance(data, str):
            with open(data, 'rb') as fff_file:
                self.data = fff_file.read()
        else:
            raise TypeError("Data should be a bytes object or a string filename")
    
    def write(self, path):
        with open(path, 'wb') as fff_file:
            fff_file.write(self.data)

    def find_data_offset(self, data):
    
        search = (self.width-1).to_bytes(2, 'little')\
                    +b"\x00\x00"\
                    +(self.height-1).to_bytes(2, 'little')

        valid = re.compile(search)
        res = valid.search(data)

        return res.end()+14
    
    def get_radiometric_image(self, meta):
        image = raw2temp(self.get_image(), meta)

        return image

    def get_image(self):
        
        if self.image is None:
            offset = self.find_data_offset(self.data)
            count = self.height*self.width
            self.image = np.frombuffer(self.data, offset=offset, dtype='uint16', count=count).reshape((self.height, self.width))
        
        return self.image
    
    def get_gps(self):
        valid = re.compile("[0-9]{4}[NS]\x00[EW]\x00".encode())

        res = valid.search(self.data)
        start_pos = res.start()

        s = struct.Struct("<4xcxcx4xddf32xcxcx4xff")

        return s.unpack_from(self.data, start_pos)