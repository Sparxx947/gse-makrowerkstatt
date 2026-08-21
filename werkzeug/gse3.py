#!/usr/bin/env python3
"""GSE3-Kodierung: CBOR -> Deflate -> Base64, wie in GSE/API/Serialisation.lua."""
import base64, zlib, struct, io

# ---------------------------------------------------------------- CBOR decode
class Tagged:
    def __init__(self, tag, value): self.tag, self.value = tag, value
    def __repr__(self): return f"Tag({self.tag},{self.value!r})"

class Undefined:
    def __repr__(self): return "undefined"
UNDEF = Undefined()

class Dec:
    def __init__(self, data): self.d, self.i = data, 0
    def byte(self):
        b = self.d[self.i]; self.i += 1; return b
    def take(self, n):
        s = self.d[self.i:self.i+n]; self.i += n; return s
    def argument(self, ai):
        if ai < 24: return ai
        if ai == 24: return self.byte()
        if ai == 25: return struct.unpack(">H", self.take(2))[0]
        if ai == 26: return struct.unpack(">I", self.take(4))[0]
        if ai == 27: return struct.unpack(">Q", self.take(8))[0]
        if ai == 31: return None          # unbestimmte Länge
        raise ValueError(f"ungültiges additional info {ai}")
    def decode(self):
        ib = self.byte()
        mt, ai = ib >> 5, ib & 0x1F
        if mt == 0:
            return self.argument(ai)
        if mt == 1:
            return -1 - self.argument(ai)
        if mt == 2:
            n = self.argument(ai)
            if n is None:
                out = b""
                while self.d[self.i] != 0xFF: out += self.decode()
                self.i += 1
                return out
            return self.take(n)
        if mt == 3:
            n = self.argument(ai)
            if n is None:
                out = ""
                while self.d[self.i] != 0xFF: out += self.decode()
                self.i += 1
                return out
            return self.take(n).decode("utf-8", "replace")
        if mt == 4:
            n = self.argument(ai)
            if n is None:
                out = []
                while self.d[self.i] != 0xFF: out.append(self.decode())
                self.i += 1
                return out
            return [self.decode() for _ in range(n)]
        if mt == 5:
            n = self.argument(ai)
            out = {}
            if n is None:
                while self.d[self.i] != 0xFF:
                    k = self.decode(); out[k if not isinstance(k, (list, dict)) else str(k)] = self.decode()
                self.i += 1
                return out
            for _ in range(n):
                k = self.decode()
                out[k if not isinstance(k, (list, dict)) else str(k)] = self.decode()
            return out
        if mt == 6:
            return Tagged(self.argument(ai), self.decode())
        if mt == 7:
            if ai == 20: return False
            if ai == 21: return True
            if ai == 22: return None
            if ai == 23: return UNDEF
            if ai == 25:
                return struct.unpack(">e", self.take(2))[0]
            if ai == 26: return struct.unpack(">f", self.take(4))[0]
            if ai == 27: return struct.unpack(">d", self.take(8))[0]
            if ai == 31: return "BREAK"
            return self.argument(ai)
        raise ValueError(f"unbekannter major type {mt}")

def cbor_decode(data):
    return Dec(data).decode()

# ---------------------------------------------------------------- CBOR encode
def _head(mt, n):
    if n < 24:              return bytes([(mt << 5) | n])
    if n < 0x100:           return bytes([(mt << 5) | 24, n])
    if n < 0x10000:         return bytes([(mt << 5) | 25]) + struct.pack(">H", n)
    if n < 0x100000000:     return bytes([(mt << 5) | 26]) + struct.pack(">I", n)
    return bytes([(mt << 5) | 27]) + struct.pack(">Q", n)

def cbor_encode(o):
    if o is None:               return b"\xf6"
    if o is True:               return b"\xf5"
    if o is False:              return b"\xf4"
    if isinstance(o, Undefined):return b"\xf7"
    if isinstance(o, int):
        return _head(0, o) if o >= 0 else _head(1, -1 - o)
    if isinstance(o, float):
        return b"\xfb" + struct.pack(">d", o)
    if isinstance(o, bytes):
        return _head(2, len(o)) + o
    if isinstance(o, str):
        b = o.encode("utf-8")
        return _head(3, len(b)) + b
    if isinstance(o, (list, tuple)):
        return _head(4, len(o)) + b"".join(cbor_encode(x) for x in o)
    if isinstance(o, dict):
        return _head(5, len(o)) + b"".join(cbor_encode(k) + cbor_encode(v) for k, v in o.items())
    if isinstance(o, Tagged):
        return _head(6, o.tag) + cbor_encode(o.value)
    raise TypeError(f"nicht kodierbar: {type(o)}")

# ---------------------------------------------------------------- GSE3-Hülle
def gse3_decode(s):
    assert s.startswith("!GSE3!"), "kein GSE3-String"
    b64 = s[6:]
    raw = base64.b64decode(b64 + "=" * (-len(b64) % 4))
    last = None
    for wbits in (-15, 15, 31, 47):
        try:
            return cbor_decode(zlib.decompress(raw, wbits)), wbits
        except Exception as e:
            last = e
    # Blizzard könnte ein Präfix-Byte (Methodenkennung) voranstellen
    for skip in (1, 2, 4, 8):
        for wbits in (-15, 15, 31):
            try:
                return cbor_decode(zlib.decompress(raw[skip:], wbits)), (wbits, f"skip{skip}")
            except Exception as e:
                last = e
    raise RuntimeError(f"Dekompression fehlgeschlagen: {last}")

def gse3_encode(obj, wbits=-15, level=9):
    co = zlib.compressobj(level, zlib.DEFLATED, wbits)
    raw = co.compress(cbor_encode(obj)) + co.flush()
    return "!GSE3!" + base64.b64encode(raw).decode("ascii")
