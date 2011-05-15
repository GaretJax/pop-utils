

class CIDR(object):
    def __init__(self, base, size=None):
        try:
            base, _size = base.split('/')
        except ValueError:
            pass
        else:
            if size is None:
                size = _size
        
        self.size = 2 ** (32 - int(size))
        self._mask = ~(self.size - 1)
        self._base = self.ip2dec(base) & self._mask
        
        self.base = self.dec2ip(self._base)
        self.block = int(size)
        self.mask = self.dec2ip(self._mask)
    
    @property
    def last(self):
        return self.dec2ip(self._base + self.size - 1)
    
    def __len__(self):
        return self.size
    
    def __str__(self):
        return "{0}/{1}".format(
            self.base,
            self.block,
        )
    
    def __contains__(self, ip):
        return self.ip2dec(ip) & self._mask == self._base
    
    @staticmethod
    def ip2dec(ip):
        return sum([int(q) << i * 8 for i, q in enumerate(reversed(ip.split(".")))])
    
    @staticmethod
    def dec2ip(ip):
        return '.'.join([str((ip >> 8 * i) & 255) for i in range(3, -1, -1)])
    
    class CIDRIterator(object):
        def __init__(self, base, size):
            self.current = base
            self.final = base + size
        
        def __iter__(self):
            return self
        
        def next(self):
            c = self.current
            self.current += 1
            
            if self.current > self.final:
                raise StopIteration
            
            return CIDR.dec2ip(c)
    
    def __iter__(self):
        return self.CIDRIterator(self._base, self.size)