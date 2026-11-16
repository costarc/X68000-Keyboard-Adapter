# SPDX-License-Identifier: CC-BY-SA-4.0   (tool code only; the book text and figures are copyrighted)
"""Chapter 78: checks of the owner's XC8 rewrite of the GKA-AT68 firmware, by simulation.

usage:  python3 code/ch78/gka-review.py "<X68000-Keyboard-Adapter>/GKA-AT68 NEW/src"

It reads the key table from keymap.c (the only thing taken from the owner's files: the table's byte values)
and models three routines statement by statement, written fresh for this book from reading them:
  1. uart_tx_byte() and the transmit part of the Timer0 interrupt (x68k_uart.c): what an 8N1 receiver
     decodes for every byte 00-FF.
  2. ps2_read_byte() (ps2.c): what it returns for real PS/2 device frames. The level waits are modelled as
     consuming one falling clock edge each wait-for-low/wait-for-high pair; the clock idles high and the
     inputs RA2/RA3 are not inverted (system.h, Table 78.2).
  3. ps2_to_x68_base[] indexed by the set-2 code, against the X68000 key codes of Volume 1, Chapter 14:
     as written, read one place later, and with the two-edit correction of section 78.7.
Interrupt latency and the PS/2 clock's real timing are not modelled.
SPDX-License-Identifier: CC-BY-SA-4.0 (tool code only; the book text and figures are copyrighted)
"""
import os
import re
import sys

src = sys.argv[1]
table = re.search(r"ps2_to_x68_base\[\]\s*=\s*\{([^}]*)\}", open(os.path.join(src, "keymap.c")).read()).group(1)
base = [int(x, 16) for x in table.replace("0x", "").split(",")]


# 1. transmit -----------------------------------------------------------------------------------------
def tx_line(b):
    """Line level at the middle of each of the ten bit times, and the ticks where 0 was written then high."""
    shift, bits, sub, line, levels, glitches = (b << 1) & 0xFF, 10, 0, 1, [], []
    for tick in range(120):
        if bits:
            sub += 1
            if sub >= 8:                                  # BIT_TICKS
                sub = 0
                line = shift & 1
                shift >>= 1
                bits -= 1
                if bits == 0:
                    if line == 0:
                        glitches.append(tick)
                    line = 1                              # "idle", in the same interrupt
        levels.append(line)
    return [levels[7 + 8 * k + 4] for k in range(10)], glitches


def decode(bits):
    return sum(bits[1 + i] << i for i in range(8)), bits[0] == 0 and bits[9] == 1


print("1. transmit routine")
wrong = [b for b in range(256) if decode(tx_line(b)[0]) != (b, True)]
for b in (0x1E, 0x9E, 0x70, 0xF0):
    bits, gl = tx_line(b)
    d, ok = decode(bits)
    print("   %02X: line %s -> receiver reads %02X, start/stop %s; 0 written then high at tick %s"
          % (b, "".join(map(str, bits)), d, "valid" if ok else "INVALID", gl))
print("   bytes decoded wrongly: %d of 256 (bit 7 clear: %d; framing errors: %d)"
      % (len(wrong), sum(1 for b in wrong if b < 0x80), sum(1 for b in range(256) if not decode(tx_line(b)[0])[1])))


# 2. PS/2 receive -------------------------------------------------------------------------------------
def ps2_frame(b):
    d = [(b >> i) & 1 for i in range(8)]
    return [0] + d + [1 ^ (sum(d) & 1)] + [1]


def ps2_read(stream):
    edges = [bit for b in stream for bit in ps2_frame(b)]
    pos, out = 0, []
    while pos + 12 <= len(edges):
        e = edges[pos:pos + 12]
        pos += 12                                          # 2 sync edges, 8 data, "parity", "stop"
        data = sum(e[2 + i] << i for i in range(8))
        out.append("%02X" % data if e[11] else "false")
    return out, len(edges) - pos


print("2. PS/2 receive routine (falling edges per call: 12; per PS/2 byte: 11)")
for name, s in (("press A", [0x1C]), ("press and release A", [0x1C, 0xF0, 0x1C]),
                ("press and release Q, W, E", [0x15, 0xF0, 0x15, 0x1D, 0xF0, 0x1D, 0x24, 0xF0, 0x24])):
    got, left = ps2_read(s)
    print("   %-26s sent %-27s returns %s (then waits; %d edges left over)"
          % (name, " ".join("%02X" % b for b in s), " ".join(got) or "nothing", left))

# 3. key table ----------------------------------------------------------------------------------------
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


def score(t, offset=0):
    return [p for p, n in sorted(set2.items()) if not (0 <= p + offset < len(t) and t[p + offset] == x68[n])]


fixed = base[1:0x6E] + [0xFF] + base[0x6E:]
print("3. key table ps2_to_x68_base[] (%d entries), %d keys of Volume 1 Chapter 14 checked" % (len(base), len(set2)))
for name, t, off in (("as written", base, 0), ("read one place later", base, 1),
                     ("corrected (first entry removed, FF added after 6CH)", fixed, 0)):
    bad = score(t, off)
    print("   %-52s right %2d, wrong %2d%s" % (name, len(set2) - len(bad), len(bad),
          (": " + " ".join("%02X" % p for p in bad)) if bad and len(bad) < 20 else ""))
for p in (0x15, 0x1C, 0x1B, 0x1D, 0x6C, 0x70, 0x76):
    print("   %02X %-6s table %02X, should be %02X" % (p, set2[p], base[p], x68[set2[p]]))
