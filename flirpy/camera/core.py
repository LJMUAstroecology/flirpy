import serial
import binascii
import time

class Core:

    def __init__(self):
        self.conn = None
    
    def connect(self, port, baudrate):
        self.conn = serial.Serial(port, baudrate, timeout=2)
        self.conn.read_all()
    
    def send(self, packet):
        # Clear input buffer before write
        self.conn.read_all()

        return self.conn.write(packet)
    
    def receive(self, nbytes):
        frame = self.conn.read(nbytes)
        return frame
    
    def grab(self):
        pass
    
    def disconnect(self):
        if self.conn is not None:
            if self.conn.is_open:
                self.conn.close()

    def release(self):
        pass
        
    def close(self):
        self.disconnect()
        self.release()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __del__(self):
        self.close()