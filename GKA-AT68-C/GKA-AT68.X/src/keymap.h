#ifndef KEYMAP_H
#define KEYMAP_H
#include <stdint.h>

// 0xFF means unmapped/ignore; 0xFE is special (NumLock toggle placeholder, if present)
extern const uint8_t ps2_to_x68_base[]; // 0x00..0x7D
extern const uint8_t ps2_to_x68_e0[];   // index = code-0x69
extern const uint8_t ps2_to_x68_num[];  // sequential subset from ASM

#define PS2_BASE_LEN 0x7E
#define PS2_E0_START 0x69
#define PS2_E0_LEN   (0x7E - 0x69 + 1)

#endif
