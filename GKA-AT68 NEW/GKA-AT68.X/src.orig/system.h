#ifndef SYSTEM_H
#define SYSTEM_H

#include <xc.h>
#include <stdint.h>
#include <stdbool.h>

// Configure for HS oscillator @ 9.8304 MHz
#define _XTAL_FREQ 9830400UL

// CONFIG (XC8 v2+ syntax)
#pragma config FOSC = HS        // HS oscillator
#pragma config WDTE = OFF       // Watchdog Timer disabled
#pragma config PWRTE = ON       // Power-up Timer enabled
#pragma config CP   = OFF       // Code protection disabled

// Port bit helpers (read/writes to PORT bits)
#define PS2_DATA_DRV   RA0
#define PS2_CLK_DRV    RA1
#define PS2_DATA_IN    RA2
#define PS2_CLK_IN     RA3

#define HOST_RX        RB0
#define HOST_TX        RB1
#define HOST_RDY       RB3
#define HOST_REMOTE    RB4
#define LED            RB5

// TRIS configuration
#define TRISA_MASK  0b00001100  // RA2,RA3 inputs; RA0,RA1 outputs
#define TRISB_MASK  0b00001001  // RB3,RB0 inputs; RB1,RB4,RB5 outputs

#endif
