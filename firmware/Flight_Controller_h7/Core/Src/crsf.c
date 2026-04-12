/*
 * crsf.c
 *
 *  Created on: Apr 2026
 *      Author: Saleh
 *
 * @brief CRSF receiver driver — UART8 + circular DMA, STM32H7.
 *
 * How it works:
 *   HAL_UART_Receive_DMA starts a circular DMA transfer into _dma_buf.
 *   DMA fills the buffer continuously, wrapping around automatically.
 *   CRSF_Process() reads new bytes from the write position (tracked via
 *   DMA counter) and feeds them through a state machine that assembles
 *   and validates CRSF frames. No interrupts or callbacks required.
 *
 * CubeMX DMA settings for UART8_RX:
 *   Direction : Peripheral To Memory
 *   Mode      : Circular          ← MUST be Circular, not Normal
 *   Peripheral increment : disabled
 *   Memory increment     : enabled
 *   Data width           : Byte / Byte
 *
 * STM32H743 pitfalls handled here:
 *   1. D-cache coherency  — DMA writes bypass cache; invalidate before reading.
 *   2. UART error abort   — HAL_UART_DMAError kills circular DMA on any UART
 *                           error (overrun, framing, noise). Fixed by:
 *                           a) disabling overrun detection (OVRDIS bit), and
 *                           b) disabling the UART error interrupt after DMA
 *                              starts so HAL never sees an error to abort on.
 *   3. DMA watchdog       — CRSF_Process() detects a dead DMA and restarts it.
 */

#include "crsf.h"
#include <string.h>

/* ============== Tuning ============== */
#define CRSF_RAW_MIN   172
#define CRSF_RAW_MID   992
#define CRSF_RAW_MAX  1811
#define RC_DEADBAND     20
#define DMA_BUF_SIZE   128   /* circular DMA buffer — must be power of 2 */

/* ============== Internal state ============== */
static UART_HandleTypeDef *_huart;

/* DMA writes here continuously in circular mode.
 * IMPORTANT: STM32H743 has D-cache enabled. DMA writes bypass cache, so CPU
 * reads stale data unless we invalidate before reading. Buffer must be
 * 32-byte aligned for SCB_InvalidateDCache_by_Addr to work correctly. */
volatile uint8_t _dma_buf[DMA_BUF_SIZE] __attribute__((aligned(32)));
static uint16_t _dma_read_pos = 0;

/* Frame assembly */
static uint8_t _buf[CRSF_MAX_FRAME_LEN];
static uint8_t _idx       = 0;
static uint8_t _frame_len = 0;

/* Public data */
volatile CRSF_Data_t crsf_data = {0};

/* ============== DMA restart helper ============== */
static void _start_dma(void)
{
    /* Clear any pending UART error flags before (re)starting DMA.
     * If these are left set, HAL might immediately abort the new transfer. */
    __HAL_UART_CLEAR_FLAG(_huart, UART_CLEAR_OREF | UART_CLEAR_NEF | UART_CLEAR_FEF);
    __HAL_UART_CLEAR_IT(_huart, UART_CLEAR_IDLEF);

    _dma_read_pos = 0;
    memset((uint8_t*)_dma_buf, 0, sizeof(_dma_buf));

    HAL_UART_Receive_DMA(_huart, (uint8_t*)_dma_buf, DMA_BUF_SIZE);

    /* Disable overrun detection.
     * With OVRDIS set, an overrun just silently drops a byte — DMA keeps
     * running. Without it, overrun sets ORE which HAL treats as a fatal
     * error and aborts the DMA transfer. Must be set AFTER HAL_UART_Receive_DMA
     * because HAL re-writes CR3 during init. */
    SET_BIT(_huart->Instance->CR3, USART_CR3_OVRDIS);

    /* Disable the UART error interrupt (covers framing, noise, overrun).
     * HAL enables this in HAL_UART_Receive_DMA; we turn it back off so
     * HAL_UART_IRQHandler can never call HAL_UART_DMAError and kill DMA.
     * We lose nothing — errors are handled gracefully by the state machine
     * (bad CRC increments crsf_data.crc_errors, sync is re-acquired). */
    __HAL_UART_DISABLE_IT(_huart, UART_IT_ERR);
}

/* ============== CRC-8 DVB-S2 ============== */
static uint8_t crc8_dvb_s2(const uint8_t *data, uint8_t len)
{
    uint8_t crc = 0;
    for (uint8_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (uint8_t b = 0; b < 8; b++)
            crc = (crc & 0x80) ? (crc << 1) ^ 0xD5 : (crc << 1);
    }
    return crc;
}

/* ============== Normalization ============== */
static float map_stick(uint16_t raw)
{
    float val;
    if (raw < CRSF_RAW_MID - RC_DEADBAND)
        val = (float)(raw - CRSF_RAW_MID) / (float)(CRSF_RAW_MID - CRSF_RAW_MIN) * 100.0f;
    else if (raw > CRSF_RAW_MID + RC_DEADBAND)
        val = (float)(raw - CRSF_RAW_MID) / (float)(CRSF_RAW_MAX - CRSF_RAW_MID) * 100.0f;
    else
        val = 0.0f;

    if (val >  100.0f) val =  100.0f;
    if (val < -100.0f) val = -100.0f;
    return val;
}

static float map_throttle(uint16_t raw)
{
    float val = (float)(raw - CRSF_RAW_MIN) / (float)(CRSF_RAW_MAX - CRSF_RAW_MIN) * 100.0f;
    if (val <   0.0f) val =   0.0f;
    if (val > 100.0f) val = 100.0f;
    return val;
}

/* ============== Channel parser (11-bit packing) ============== */
static void parse_rc_channels(const uint8_t *payload)
{
    uint32_t bits  = 0;
    uint8_t  avail = 0;
    uint8_t  idx   = 0;

    for (uint8_t ch = 0; ch < CRSF_NUM_CHANNELS; ch++) {
        while (avail < 11) {
            bits  |= ((uint32_t)payload[idx++]) << avail;
            avail += 8;
        }
        crsf_data.channels[ch] = bits & 0x7FF;
        bits  >>= 11;
        avail  -= 11;
    }

    crsf_data.roll     = map_stick(crsf_data.channels[0]);
    crsf_data.pitch    = map_stick(crsf_data.channels[1]);
    crsf_data.throttle = map_throttle(crsf_data.channels[2]);
    crsf_data.yaw      = map_stick(crsf_data.channels[3]);
    crsf_data.armed    = (crsf_data.channels[4] > 1500);
}

/* ============== State machine — one byte at a time ============== */
static void process_byte(uint8_t byte)
{
    if (_idx == 0) {
        /* Wait for sync byte */
        if (byte == CRSF_SYNC_BYTE)
            _buf[_idx++] = byte;

    } else if (_idx == 1) {
        /* Length byte: total frame = length field + 2 (sync + length itself) */
        _frame_len = byte + 2;
        if (_frame_len > CRSF_MAX_FRAME_LEN || _frame_len < 4)
            _idx = 0;  /* invalid length — reset */
        else
            _buf[_idx++] = byte;

    } else {
        _buf[_idx++] = byte;

        if (_idx >= _frame_len) {
            /* Full frame received — validate CRC */
            uint8_t crc_len      = _buf[1] - 1;          /* type + payload, not CRC itself */
            uint8_t computed_crc = crc8_dvb_s2(&_buf[2], crc_len);
            uint8_t received_crc = _buf[_frame_len - 1];

            if (computed_crc == received_crc) {
                if (_buf[2] == CRSF_FRAMETYPE_RC_CHANNELS) {
                    parse_rc_channels(&_buf[3]);
                    crsf_data.new_frame     = true;
                    crsf_data.last_frame_ms = HAL_GetTick();
                    crsf_data.frame_count++;
                    crsf_data.failsafe      = false;
                }
            } else {
                crsf_data.crc_errors++;
            }
            _idx = 0;
        }
    }
}

/* ============== Public API ============== */

void CRSF_Init(UART_HandleTypeDef *huart)
{
    _huart = huart;
    _idx   = 0;
    memset((void*)&crsf_data, 0, sizeof(crsf_data));

    _start_dma();
}

void CRSF_Process(void)
{
    /* --- Watchdog: restart DMA if HAL killed it due to a UART error --- */
    if (_huart->RxState != HAL_UART_STATE_BUSY_RX) {
        crsf_data.dma_restarts++;   /* visible in Live Expressions — should stay low */
        _idx = 0;                   /* reset frame assembler — partial frame is gone */
        _start_dma();
        return;                     /* fresh DMA, nothing to read yet */
    }

    /* --- D-cache invalidation ---
     * H743 D-cache is enabled; DMA writes bypass it so CPU sees stale data.
     * Invalidating forces the next read to come from actual RAM. */
    SCB_InvalidateDCache_by_Addr((uint32_t*)_dma_buf, DMA_BUF_SIZE);

    /* DMA write position = buffer size minus remaining DMA count */
    uint16_t dma_write_pos = DMA_BUF_SIZE -
        (uint16_t)__HAL_DMA_GET_COUNTER(_huart->hdmarx);

    /* Drain all new bytes */
    while (_dma_read_pos != dma_write_pos) {
        process_byte((uint8_t)_dma_buf[_dma_read_pos]);
        _dma_read_pos = (_dma_read_pos + 1) % DMA_BUF_SIZE;
    }

    /* Failsafe check */
    if (crsf_data.last_frame_ms > 0 &&
        (HAL_GetTick() - crsf_data.last_frame_ms) > CRSF_FAILSAFE_MS) {
        crsf_data.failsafe = true;
    }
}

bool CRSF_IsAlive(void)
{
    return !crsf_data.failsafe &&
           crsf_data.last_frame_ms > 0 &&
           (HAL_GetTick() - crsf_data.last_frame_ms) < CRSF_FAILSAFE_MS;
}
