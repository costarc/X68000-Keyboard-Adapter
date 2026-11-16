#include <xc.h>
#include "system.h"
#include "ps2.h"

static inline void ps2_release_clk(void) { PS2_CLK_DRV = 0; }   // release (pull-up brings High)
static inline void ps2_drive_clk_low(void){ PS2_CLK_DRV = 1; }
static inline void ps2_release_data(void){ PS2_DATA_DRV = 0; }
static inline void ps2_drive_data_low(void){ PS2_DATA_DRV = 1; }

// Simple blocking PS/2 receiver (host-only read).
// Reads: start(0), 8 data bits LSB-first, parity(odd), stop(1).
bool ps2_read_byte(uint8_t *out)
{
    // Wait for start (clock falling while data low is ideal; we just sync to clock edges)
    while (PS2_CLK_IN);        // wait while low
    while (!PS2_CLK_IN);       // wait rising to ensure idle-high seen
    // Sync to falling edges for each bit
    uint8_t data = 0;
    uint8_t parity = 1;
    // Start bit
    while (PS2_CLK_IN);
    // (Optionally sample start bit; skip)
    while (!PS2_CLK_IN);

    for (uint8_t i=0;i<8;i++) {
        while (PS2_CLK_IN);
        if (PS2_DATA_IN) { data |= (1u<<i); parity ^= 1; }
        else { parity ^= 0; }
        while (!PS2_CLK_IN);
    }
    // Parity
    while (PS2_CLK_IN);
    uint8_t p = PS2_DATA_IN;
    while (!PS2_CLK_IN);

    // Stop
    while (PS2_CLK_IN);
    uint8_t stop = PS2_DATA_IN;
    while (!PS2_CLK_IN);

    if (stop) { *out = data; return true; }
    return false;
}
