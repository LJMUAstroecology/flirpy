import math

class Encoder16:
    """
    16-bit depth encoder, useful for writing radiometric frames as 8-bit images
    
    Implements "Adapting Standard Video Codecs for Depth Streaming", Pece, Kautz, Weyrich
    
    http://reality.cs.ucl.ac.uk/projects/depth-streaming/depth-streaming.pdf
    """
    
    def __init__(self, n=512, w=65536):
        self.n = float(512)
        self.w = float(65536)

        self.lut = self._make_lut()

    def _make_lut(self):
        lut = []

        n = self.n
        w = self.w
        p = n/w

        for d in range(int(w)):
            l = (float(d)+0.5)/w

            p2 = p/2
            p4 = p/4

            lp2 = l/p2 % 2
            lp4 = (l-p4)/p2 % 2

            if lp2 <= 1:
                ha = lp2
            else:
                ha = 2 - lp2
            
            if lp4 <= 1:
                hb = lp4
            else:
                hb = 2-lp4

            lut.append((l, ha, hb))
        
        return lut
    
    def decode(self, d):
        l, ha, hb = d

        n = self.n
        w = self.w
        p = n/w

        m = math.floor(4*(l/p)-0.5) % 4

        l0 = l - p/8 + (p/4)*m - ( (l-p/8) % p)

        if m == 0:
            delta = (p/2)*ha
        elif m == 1:
            delta = (p/2)*hb
        elif m == 2:
            delta = (p/2)*(1-ha)
        elif m == 3:
            delta = (p/2)*(1-hb)

        return w*(l0+delta)
    
    def encode(self, d):
        return self.lut[d]
