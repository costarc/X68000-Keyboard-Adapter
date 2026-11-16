"""Verification of the FIXED GKA-AT68 XC8 sources by statement-by-statement simulation.
usage: python -I tests/gka-verify-fixed.py "GKA-AT68.X/src"
Adapted from the X68000-Book review script (gka-review-orig.py); models the fixed code in
x68k_uart.c (uart_tx_byte + Timer0 ISR TX part) and ps2.c (ps2_read_byte), and checks keymap.c.
"""
import os, re, sys
src = sys.argv[1]
table = re.search(r"ps2_to_x68_base\[\]\s*=\s*\{([^}]*)\}", open(os.path.join(src, "keymap.c")).read()).group(1)
base = [int(x, 16) for x in table.replace("0x", "").split(",")]
BIT_TICKS = 8

# 1. transmit: uart_tx_byte() then the ISR, one call per Timer0 tick -------------------------------------
def tx_line(b, ticks=130):
    tx_shift = (1 << 9) | (b << 1)       # uint16_t, as in uart_tx_byte()
    tx_sub, tx_bits, line, levels = 0, 10, 1, []   # tx_bits = 10 armed last
    for _ in range(ticks):
        if tx_bits:
            tx_sub += 1
            if tx_sub >= BIT_TICKS:
                tx_sub = 0
                line = tx_shift & 1
                tx_shift >>= 1
                tx_bits -= 1
                if tx_bits == 0:
                    line = 1             # idle
        levels.append(line)
    return levels

def decode(levels):
    # find start edge, then sample mid-bit (as the X68000 UART does)
    s = levels.index(0)
    bits = [levels[s + 8 * k + 4] for k in range(10)]
    return sum(bits[1 + i] << i for i in range(8)), bits[0] == 0 and bits[9] == 1

print("1. transmit routine (fixed)")
bad = [b for b in range(256) if decode(tx_line(b)) != (b, True)]
print("   bytes decoded correctly: %d of 256 (bad: %s)" % (256 - len(bad), [hex(x) for x in bad[:8]]))
for b in (0x1E, 0x9E, 0x70, 0xF0):
    l = tx_line(b); s = l.index(0)
    print("   %02X: frame %s -> receiver reads %02X" % (b, "".join(str(l[s + 8 * k + 4]) for k in range(10)), decode(l)[0]))
# stop bit: the line must be 1 for at least one bit time after the last data bit
l = tx_line(0xFF); s = l.index(0)
print("   0xFF start-bit low for %d ticks (bit = %d ticks)" % (sum(1 for v in l[s:s+8] if v == 0), BIT_TICKS))

# 2. PS/2 receive: level-polling model of ps2_read_byte() ---------------------------------------------
class End(Exception): pass
class Pins:
    def __init__(self, stream):
        self.t = []                       # list of (clk, data) states; idle high first
        self.t.append((1, 1))
        for b in stream:
            d = [(b >> i) & 1 for i in range(8)]
            fr = [0] + d + [1 ^ (sum(d) & 1)] + [1]
            for bit in fr:
                self.t += [(1, bit), (0, bit)]   # clock high half, then low half (falling edge sample)
            self.t.append((1, 1))
        self.i = 0; self.falls = 0
    def clk(self): return self.t[self.i][0]
    def data(self): return self.t[self.i][1]
    def step(self):
        self.i += 1
        if self.i >= len(self.t): raise End
        if self.t[self.i][0] == 0 and self.t[self.i-1][0] == 1: self.falls += 1

def ps2_read_byte(p):
    while not p.clk(): p.step()
    while p.clk(): p.step()
    if p.data():
        while not p.clk(): p.step()
        return False, None
    while not p.clk(): p.step()
    data = 0; ones = 0
    for i in range(8):
        while p.clk(): p.step()
        if p.data(): data |= 1 << i; ones += 1
        while not p.clk(): p.step()
    while p.clk(): p.step()
    if p.data(): ones += 1
    while not p.clk(): p.step()
    while p.clk(): p.step()
    stop = p.data()
    while not p.clk(): p.step()
    if stop and (ones & 1): return True, data
    return False, None

def run(stream):
    p = Pins(stream); out = []; per = []
    try:
        while True:
            f0 = p.falls
            ok, v = ps2_read_byte(p)
            out.append("%02X" % v if ok else "false"); per.append(p.falls - f0)
    except End: pass
    return out, per

print("2. PS/2 receive routine (fixed; falling edges consumed per call must be 11)")
for name, s in (("press A", [0x1C]), ("press and release A", [0x1C, 0xF0, 0x1C]),
                ("press and release Q, W, E", [0x15, 0xF0, 0x15, 0x1D, 0xF0, 0x1D, 0x24, 0xF0, 0x24])):
    got, per = run(s)
    print("   %-26s sent %-27s returns %-27s edges/call %s %s" % (name, " ".join("%02X" % b for b in s), " ".join(got),
          per, "OK" if got == ["%02X" % b for b in s] else "MISMATCH"))
# error cases: bad parity must be rejected
p = Pins([0x1C]); 
bad_par = Pins([0x1C]); 
# flip parity bit: frame index 9 -> states offset
j = 1 + 2 * 9; bad_par.t[j] = (1, 1 - bad_par.t[j][1]); bad_par.t[j+1] = (0, bad_par.t[j][1])
try: print("   bad-parity frame returns", ps2_read_byte(bad_par)[0], "(expected False)")
except End: print("   bad-parity frame: stream ended")

# 3. key table --------------------------------------------------------------------------------------------

set2 = {0x76: "ESC", 0x16: "1", 0x1E: "2", 0x26: "3", 0x25: "4", 0x2E: "5", 0x36: "6", 0x3D: "7", 0x3E: "8",
        0x46: "9", 0x45: "0", 0x4E: "-", 0x66: "BS", 0x0D: "TAB", 0x15: "Q", 0x1D: "W", 0x24: "E", 0x2D: "R",
        0x2C: "T", 0x35: "Y", 0x3C: "U", 0x43: "I", 0x44: "O", 0x4D: "P", 0x5A: "RETURN", 0x14: "CTRL",
        0x1C: "A", 0x1B: "S", 0x23: "D", 0x2B: "F", 0x34: "G", 0x33: "H", 0x3B: "J", 0x42: "K", 0x4B: "L",
        0x4C: ";", 0x12: "SHIFT", 0x59: "SHIFT", 0x1A: "Z", 0x22: "X", 0x21: "C", 0x2A: "V", 0x32: "B",
        0x31: "N", 0x3A: "M", 0x41: ",", 0x49: ".", 0x4A: "/", 0x29: "SPACE", 0x05: "F1", 0x06: "F2",
        0x04: "F3", 0x0C: "F4", 0x03: "F5", 0x0B: "F6", 0x0A: "F8", 0x01: "F9", 0x09: "F10", 0x58: "CAPS",
        0x70: "KP0", 0x69: "KP1", 0x72: "KP2", 0x7A: "KP3", 0x6B: "KP4", 0x73: "KP5", 0x74: "KP6",
        0x6C: "KP7", 0x75: "KP8", 0x7D: "KP9", 0x71: "KP.", 0x7C: "KP*", 0x7B: "KP-", 0x79: "KP+"}
x68 = {"ESC": 0x01, "1": 0x02, "2": 0x03, "3": 0x04, "4": 0x05, "5": 0x06, "6": 0x07, "7": 0x08, "8": 0x09,
       "9": 0x0A, "0": 0x0B, "-": 0x0C, "BS": 0x0F, "TAB": 0x10, "Q": 0x11, "W": 0x12, "E": 0x13, "R": 0x14,
       "T": 0x15, "Y": 0x16, "U": 0x17, "I": 0x18, "O": 0x19, "P": 0x1A, "RETURN": 0x1D, "CTRL": 0x71,
       "A": 0x1E, "S": 0x1F, "D": 0x20, "F": 0x21, "G": 0x22, "H": 0x23, "J": 0x24, "K": 0x25, "L": 0x26,
       ";": 0x27, "SHIFT": 0x70, "Z": 0x2A, "X": 0x2B, "C": 0x2C, "V": 0x2D, "B": 0x2E, "N": 0x2F, "M": 0x30,
       ",": 0x31, ".": 0x32, "/": 0x33, "SPACE": 0x35, "F1": 0x63, "F2": 0x64, "F3": 0x65, "F4": 0x66,
       "F5": 0x67, "F6": 0x68, "F8": 0x6A, "F9": 0x6B, "F10": 0x6C, "CAPS": 0x5D, "KP0": 0x4F, "KP1": 0x4B,
       "KP2": 0x4C, "KP3": 0x4D, "KP4": 0x47, "KP5": 0x48, "KP6": 0x49, "KP7": 0x43, "KP8": 0x44,
       "KP9": 0x45, "KP.": 0x51, "KP*": 0x41, "KP-": 0x42, "KP+": 0x46}



bad = [p for p, n in sorted(set2.items()) if not (p < len(base) and base[p] == x68[n])]
print("3. key table ps2_to_x68_base[] (%d entries): %d/%d keys right%s" % (len(base), len(set2)-len(bad), len(set2),
      (" wrong: " + " ".join("%02X" % p for p in bad)) if bad else ""))
print("   0x68-0x70:", " ".join("%02X" % v for v in base[0x68:0x71]))
