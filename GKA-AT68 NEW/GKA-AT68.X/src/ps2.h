#ifndef PS2_H
#define PS2_H
#include <stdint.h>
#include <stdbool.h>

// Blocking read of one PS/2 byte. Returns true on success.
bool ps2_read_byte(uint8_t *out);

#endif
