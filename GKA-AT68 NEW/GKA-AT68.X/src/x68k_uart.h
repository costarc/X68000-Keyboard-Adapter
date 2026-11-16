#ifndef X68K_UART_H
#define X68K_UART_H
#include <stdint.h>
#include <stdbool.h>

void uart_init(void);
void uart_tx_byte(uint8_t b);
int  uart_rx_byte(uint8_t *out); // returns 1 if a byte was read

#endif
