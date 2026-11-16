# GKA-AT68 (PIC16F84A, XC8) — PS/2 to X68000 Keyboard Converter

This is a modern C rewrite for MPLAB X + XC8 of your original PIC16F84 assembly.
It translates PS/2 set-2 scancodes (including E0-prefixed codes) to X68000 keycodes and
sends them using a 2400 bps software UART.

## Target
- **MCU:** PIC16F84A
- **Clock:** 9.8304 MHz (HS)
- **Compiler:** XC8
- **IDE:** MPLAB X

## Pins (as used by this firmware)
- RA0: PS/2 DATA driver (open-collector style; `0=release`, `1=drive low`)
- RA1: PS/2 CLK driver  (open-collector; `0=release`, `1=drive low`)
- RA2: PS/2 DATA input
- RA3: PS/2 CLK input
- RB0: Host RX (X68K → adapter) [soft UART RX; optional]
- RB1: Host TX (adapter → X68K) 2400 bps (soft UART TX)
- RB3: Host ready (CTS-like input; must be HIGH to transmit)
- RB4: Remote/TV output (stub)
- RB5: Status LED

## Build in MPLAB X
1. **File → New Project → Standalone Project**
2. Device: `PIC16F84A`
3. Tool: (your PICkit/ICD)
4. Compiler: `XC8`
5. Project Name: `GKA-AT68`
6. Finish.
7. **Right-click the new project → Add Existing Item...** and add all files in `src/`.
8. Build and program.

If your crystal is different, change `_XTAL_FREQ` in `system.h` and adjust the
Timer0 preload in the ISR (comment explains the constants).

## Notes
- Break codes (PS/2 `F0`) are sent to the host by setting bit7 of the X68K code.
- NumLock toggling is supported; the special NumLock table entries from the ASM are included.
- PS/2 TX/LED commands are not required; can be added later if needed.
