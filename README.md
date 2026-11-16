# X68000 PS/2 Keyboard Adapter (GKA-AT68)

A small adapter that lets a standard PS/2 keyboard drive a Sharp X68000. A PIC16F84 reads the
PS/2 keyboard, translates the scan codes and talks to the X68000 over its 2400 baud keyboard link.

## Repository layout

| Path | What it is |
|---|---|
| `GKA-AT68 Ver1.65 source code (for MPASM).zip` | Original firmware source (PIC assembly, `gkaat68.asm`), Ver1.65 |
| `GKA-AT68 firmware Ver1.65 (INHX8M format for PIC16F84)/` | Original, known-good firmware image (`at68v165.hex`) |
| `GKA-AT68 Assembly Instructions.pdf`, `GKA-AT68 Schematics.png` | Build instructions and schematic |
| `Kicad/` | PCB design (KiCad), fabrication files and interactive BOM |
| `GKA-AT68-C/` | **New:** the firmware rewritten in C for MPLAB X + XC8 (see below) |

## GKA-AT68-C: the C version of the firmware

### Why
The original assembly works, but it is hard to read and hard to change: timing, protocol handling and
key tables are interleaved in one 1,500-line file written for MPASM. The C version exists to give
a firmware that is

- **easier to understand**: one small file per job (PS/2 receive, X68000 UART, key map, main loop);
- **easier to modify**: users can remap keys, change timing or add features without touching assembly;
- **built with a modern toolset**: MPLAB X and the free-mode XC8 compiler (developed with XC8 v2.46).

The assembly version stays in the repository as the reference and the proven firmware. **Its hex is
untouched.** The C version is newer and has been verified by simulation and a compile only, not yet on
hardware (see Status).

### Origin
It is a port of `gkaat68.asm` Ver1.65, not a new design. Kept from the original:

- the hardware and pin roles (PIC16F84 at 9.8304 MHz, PS/2 on RA0-RA3, X68000 link on RB0/RB1/RB3);
- the architecture: a **Timer0 interrupt every ~52 us (1/8 of a 2400 baud bit)** runs a software UART
  for both transmit and receive, with an 8-byte receive FIFO;
- the Timer0 setup and reload constant (`256 - 64 + 3`, prescaler 1:2);
- the PS/2 set-2 to X68000 key tables, transcribed from the assembly.

### Architecture (`GKA-AT68-C/GKA-AT68.X/src`)

| File | Role |
|---|---|
| `main.c` | Port setup and main loop: read PS/2 bytes, handle `E0` (extended) and `F0` (break) prefixes, translate, send to the X68000. Break codes are the make code with bit 7 set. NumLock toggles the LED. |
| `ps2.c` | Blocking PS/2 receiver: one 11-bit frame (start, 8 data LSB first, odd parity, stop), validated for start, parity and stop. |
| `x68k_uart.c` | Timer0 ISR: 2400 baud 8N1 software UART. TX sends a 10-bit frame from a 16-bit shift register; RX centre-samples into a FIFO. TX waits for the host-ready line (RB3). |
| `keymap.c/.h` | `ps2_to_x68_base[]` (index = PS/2 set-2 code), `ps2_to_x68_e0[]` for extended keys, and the NumLock table. `0xFF` = no key. |
| `system.h` | Configuration bits, clock, pin and TRIS definitions. |

### Differences from the assembly
- The C code is a **simpler state machine**, not an instruction-for-instruction translation.
- It only **reads** from the PS/2 keyboard. The assembly's extras are not ported: sending lock-LED
  commands to the keyboard, the 19.2 kbps mode, and host-to-adapter command handling (a stub only).
- PS/2 reception is a plain polling routine in the main loop rather than the assembly's more
  elaborate handling.
- The key tables are the same data, but the C table is indexed directly by the PS/2 code.

### Fixes made after the first port
The first C port had three bugs that each broke the adapter. They are fixed on the branch that
introduced this README:

1. `ps2_read_byte()` waited for 12 clock edges; a PS/2 frame has 11.
2. The UART transmit shift register was 8 bits wide, so bit 7 was lost (every break code arrived as a make).
3. The key table was shifted by one entry.

The original sources are kept in `GKA-AT68-C/GKA-AT68.X/src.orig` for comparison.

### Build
Open `GKA-AT68-C/GKA-AT68.X` in MPLAB X (device PIC16F84A, compiler XC8), or from a shell:

```bash
xc8-cc -mcpu=16F84 -O2 -IGKA-AT68-C/GKA-AT68.X/src GKA-AT68-C/GKA-AT68.X/src/*.c -o at68.elf
```

Result: about 560 of 1024 program words and 40 of 68 data bytes. A prebuilt image is in
`GKA-AT68-C/GKA-AT68.X/at68_xc8_fixed.hex`. If you change the crystal, update `_XTAL_FREQ` in
`system.h` and the Timer0 reload in `x68k_uart.c`.

### Verification and status
`GKA-AT68-C/tests/gka-verify-fixed.py` simulates the transmit routine, the PS/2 receiver and the key
table (run `python -I GKA-AT68-C/tests/gka-verify-fixed.py GKA-AT68-C/GKA-AT68.X/src`). It checks that all
256 bytes transmit with valid framing, that PS/2 frames are received exactly, and that 73 of 73 reference keys map correctly.
It does not model real interrupt latency or clock timing.

**Not yet verified on hardware.** Before relying on it, check: the TX line (RB1) shows about 416.7 us per
bit (2400 baud); keys and releases register on the X68000 with none stuck; keypad and function keys
map correctly; the NumLock LED follows the key.
