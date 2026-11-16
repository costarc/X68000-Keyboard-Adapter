#include <xc.h>
#include "system.h"
#include "x68k_uart.h"

// Timer0 tick ~52us; 2400bps ~416.7us/bit ≈ 8 ticks/bit
#define BIT_TICKS 8

static volatile uint8_t tx_shift = 0;
static volatile uint8_t tx_bits = 0;
static volatile uint8_t tx_sub = 0;
static volatile uint8_t rx_shift = 0;
static volatile uint8_t rx_bits = 0;
static volatile uint8_t rx_sub = 0;
static volatile uint8_t rx_fifo[8];
static volatile uint8_t rx_r=0, rx_w=0;

static inline void fifo_push(uint8_t b){
    uint8_t n = (uint8_t)((rx_w+1)&7);
    if (n != rx_r) { rx_fifo[rx_w]=b; rx_w=n; }
}
static inline int fifo_pop(uint8_t* b){
    if (rx_r==rx_w) return 0;
    *b = rx_fifo[rx_r];
    rx_r = (uint8_t)((rx_r+1)&7);
    return 1;
}

void uart_init(void)
{
    // Ports
    PORTB |= 0b00000010; // TX idle high
    // Timer0: prescaler -> TMR0, 1:2; RBPU=0 pullups enabled; INTEDG=0; PSA=0
    // OPTION_REG bits: 7:RBPU(0),6:INTEDG(0),5:T0CS(0),4:T0SE(0),3:PSA(0),2-0:PS2(000) => 0b00000000
    OPTION_REG = 0b00000000;
    TMR0 = 0;
    T0IE = 1; T0IF = 0;
    GIE = 1;
}

void __interrupt() isr_uart(void)
{
    if (T0IF) {
        // Preload to approx 52us interval (matches original timing assumptions)
        // For 9.8304 MHz Fosc, Fcyc=Fosc/4=2.4576 MHz; each TMR0 tick=1/2.4576MHz=0.40625us.
        // With 1:2 prescaler: tick=0.8125us. 52us/0.8125us ≈ 64 counts.
        // Increment TMR0 so overflow occurs again in ~64 counts.
        TMR0 += (uint8_t)(256 - 64 + 3); // small compensation for ISR latency

        // TX state machine
        if (tx_bits) {
            if (++tx_sub >= BIT_TICKS) {
                tx_sub = 0;
                uint8_t bit = (tx_shift & 1);
                if (bit) PORTB |= 0b00000010; else PORTB &= ~0b00000010; // RB1
                tx_shift >>= 1;
                if (--tx_bits == 0) {
                    PORTB |= 0b00000010; // idle
                }
            }
        }

        // RX state machine: very simple center-sample
        if (rx_bits == 0) {
            // detect start
            if ((PORTB & 0b00000001) == 0) { // RB0 low
                rx_bits = 10; // start + 8 data + stop
                rx_sub = 0;
                rx_shift = 0;
            }
        } else {
            if (++rx_sub >= BIT_TICKS) {
                rx_sub = 0;
                if (rx_bits == 10) {
                    // sample start (ignored)
                } else if (rx_bits > 1) {
                    // data bits LSB-first
                    rx_shift >>= 1;
                    if (PORTB & 0b00000001) rx_shift |= 0x80;
                } else {
                    // stop bit
                    fifo_push(rx_shift);
                }
                rx_bits--;
            }
        }

        T0IF = 0;
    }
}

void uart_tx_byte(uint8_t b)
{
    // Wait for host ready (RB3 high) and idle
    while (tx_bits || !(PORTB & 0b00001000)) { /* spin */ }
    // Frame: start(0) + 8 data + stop(1) => 10 bits
    uint16_t frame = (uint16_t)((1u<<9) | (b<<1)); // stop=1 at bit9, start=0 implicit in LSB
    tx_shift = (uint8_t)frame;
    // We send 10 bits by shifting; the top bits will be sent first as we shift LSB-first here
    // To keep logic simple: we actually place start bit first in LSB:
    tx_shift = (uint8_t)((b<<1) | 0x00); // start=0
    // We'll handle stop as the final '1' by appending after 9 shifts:
    // simpler approach: count 10 transitions and after 9 shifts set line high.
    tx_bits = 10;
    tx_sub = 0;
}

int uart_rx_byte(uint8_t *out)
{
    return fifo_pop(out);
}
