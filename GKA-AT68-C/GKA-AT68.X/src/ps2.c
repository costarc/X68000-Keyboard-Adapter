#include <xc.h>
#include "system.h"
#include "ps2.h"

static inline void ps2_release_clk(void) { PS2_CLK_DRV = 0; }   // release (pull-up brings High)
static inline void ps2_drive_clk_low(void){ PS2_CLK_DRV = 1; }
static inline void ps2_release_data(void){ PS2_DATA_DRV = 0; }
static inline void ps2_drive_data_low(void){ PS2_DATA_DRV = 1; }

// Simple blocking PS/2 receiver (host-only read).
// One frame = exactly 11 falling clock edges:
//   start(0), 8 data bits LSB-first, parity(odd), stop(1).
// Returns true only if start==0, stop==1 and odd parity holds
// (number of 1s in data+parity is odd).
bool ps2_read_byte(uint8_t *out)
{
    // Make sure the clock is idle-high so the next low is a real falling edge
    while (!PS2_CLK_IN);

    // Start bit: falling edge, DATA must be low
    while (PS2_CLK_IN);
    if (PS2_DATA_IN) {              // not a start bit: resync
        while (!PS2_CLK_IN);
        return false;
    }
    while (!PS2_CLK_IN);

    uint8_t data = 0;
    uint8_t ones = 0;               // count of 1s in data + parity
    for (uint8_t i = 0; i < 8; i++) {
        while (PS2_CLK_IN);         // falling edge: data valid
        if (PS2_DATA_IN) { data |= (uint8_t)(1u << i); ones++; }
        while (!PS2_CLK_IN);
    }

    // Parity bit
    while (PS2_CLK_IN);
    if (PS2_DATA_IN) ones++;
    while (!PS2_CLK_IN);

    // Stop bit
    while (PS2_CLK_IN);
    uint8_t stop = PS2_DATA_IN;
    while (!PS2_CLK_IN);

    if (stop && (ones & 1)) { *out = data; return true; }
    return false;
}
