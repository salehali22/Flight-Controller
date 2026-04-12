/*
 * crsf.h
 *
 *  Created on: Apr 2026
 *      Author: Saleh
 *
 * @brief CRSF (Crossfire Serial Protocol) receiver driver for STM32H7.
 *        Uses USART3 (PD8 TX / PD9 RX) with circular DMA — CPU-free receive.
 *
 * Baud rate : 420000
 * Sync byte : 0xC8
 * Frame type: 0x16 (RC channels packed, 16 ch × 11 bits)
 *
 * Raw channel range : 172 – 1811  (mid = 992)
 * Normalized outputs: roll/pitch/yaw ±100.0, throttle 0–100.0
 */

#ifndef INC_CRSF_H_
#define INC_CRSF_H_

#include "stm32h7xx_hal.h"
#include <stdint.h>
#include <stdbool.h>

/* ============== Protocol Constants ============== */
#define CRSF_BAUDRATE               420000
#define CRSF_SYNC_BYTE              0xC8
#define CRSF_FRAMETYPE_RC_CHANNELS  0x16
#define CRSF_MAX_FRAME_LEN          64
#define CRSF_NUM_CHANNELS           16

/* Failsafe: if no frame received within this many ms, consider link lost */
#define CRSF_FAILSAFE_MS            500

/* ============== Data Structure ============== */
/*
 * Watch in Live Expressions (no breakpoint needed):
 *   crsf_data.roll      → aileron  (-100 to +100)
 *   crsf_data.pitch     → elevator (-100 to +100)
 *   crsf_data.throttle  → throttle (0 to +100)
 *   crsf_data.yaw       → rudder   (-100 to +100)
 *   crsf_data.armed     → AUX1 > 1500
 *   crsf_data.channels[N] → raw 172–1811
 *   crsf_data.frame_count → increments each good frame (~150 Hz)
 *   crsf_data.crc_errors  → should stay 0
 */
typedef struct {
    uint16_t channels[CRSF_NUM_CHANNELS]; /* raw 172–1811 */

    /* Normalized — use these in flight code */
    float roll;      /* -100.0 to +100.0 */
    float pitch;     /* -100.0 to +100.0 */
    float throttle;  /*    0.0 to +100.0 */
    float yaw;       /* -100.0 to +100.0 */
    bool  armed;     /* AUX1 (ch4) > 1500 = armed */

    /* Diagnostics */
    bool     new_frame;       /* true when fresh data arrived — clear after reading */
    bool     failsafe;        /* true if no frame for CRSF_FAILSAFE_MS */
    uint32_t last_frame_ms;   /* HAL tick of last good frame */
    uint32_t frame_count;     /* total good frames */
    uint32_t crc_errors;      /* CRC mismatches (should stay 0) */
    uint32_t dma_restarts;    /* DMA was killed by HAL error handler — watch this! */
} CRSF_Data_t;

extern volatile CRSF_Data_t crsf_data;

/* ============== API ============== */

/**
 * @brief Initialise CRSF — call once after MX_USART3_UART_Init().
 * @param huart  Pointer to huart3 handle.
 */
void CRSF_Init(UART_HandleTypeDef *huart);

/**
 * @brief Drain DMA buffer and parse any complete frames.
 *        Call as fast as possible in the main loop (or a 1 ms timer).
 */
void CRSF_Process(void);

/**
 * @brief Returns true if the RC link is alive (frame received within CRSF_FAILSAFE_MS).
 */
bool CRSF_IsAlive(void);

#endif /* INC_CRSF_H_ */
