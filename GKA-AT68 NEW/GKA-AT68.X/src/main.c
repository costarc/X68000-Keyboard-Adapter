#include <xc.h>
#include "system.h"
#include "ps2.h"
#include "x68k_uart.h"
#include "keymap.h"

static uint8_t translate(uint8_t ps2, int e0_mode)
{
    if (e0_mode) {
        if (ps2 >= PS2_E0_START && ps2 < (PS2_E0_START + PS2_E0_LEN)) {
            uint8_t v = ps2_to_x68_e0[ps2 - PS2_E0_START];
            return v;
        }
        return 0xFF;
    } else {
        if (ps2 < PS2_BASE_LEN) {
            return ps2_to_x68_base[ps2];
        }
        return 0xFF;
    }
}

void main(void)
{
    // I/O setup
    PORTA = 0; PORTB = 0;
    TRISA = TRISA_MASK;
    TRISB = TRISB_MASK;

    // Release PS/2 lines (drivers inactive)
    PS2_CLK_DRV  = 0;
    PS2_DATA_DRV = 0;
    LED = 0;

    uart_init();

    int e0 = 0;
    int numlock = 0;

    for (;;) {
        uint8_t b;
        if (ps2_read_byte(&b)) {
            if (b == 0xE0) { e0 = 1; continue; }
            if (b == 0xF0) {
                // break: next byte is the key being released
                if (ps2_read_byte(&b)) {
                    uint8_t x = translate(b, e0);
                    e0 = 0;
                    if (x != 0xFF) {
                        x |= 0x80; // mark break for host
                        uart_tx_byte(x);
                    }
                }
                continue;
            }
            if (b == 0x77) { // NumLock key in set-2
                numlock ^= 1;
                LED = numlock ? 1 : 0; // show state
            }
            uint8_t x = translate(b, e0);
            e0 = 0;
            if (x == 0xFE) {
                // special NumLock placeholder (if present in table); no send
                continue;
            }
            if (x != 0xFF) {
                uart_tx_byte(x);
            }
        }

        // (Optional) consume host->adapter commands
        uint8_t rx;
        if (uart_rx_byte(&rx)) {
            // Stub: ignore or add handlers as needed
            (void)rx;
        }
    }
}
