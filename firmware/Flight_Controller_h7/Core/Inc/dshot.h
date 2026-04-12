#pragma once

#include "stm32h7xx_hal.h"
#include <stdint.h>
#include <stdbool.h>

/* ── Throttle range ─────────────────────────────────────────────
 * 0        = disarm (send repeatedly for ~300ms to arm ESC)
 * 1–47     = reserved for special commands
 * 48–2047  = throttle (48 = min, 2047 = max)
 * ─────────────────────────────────────────────────────────────── */
#define DSHOT_DISARM          0
#define DSHOT_MIN_THROTTLE   48
#define DSHOT_MAX_THROTTLE   2047

void DSHOT_Init(TIM_HandleTypeDef *htim);
void DSHOT_SendThrottle(uint16_t m1, uint16_t m2, uint16_t m3, uint16_t m4);
void DSHOT_Disarm(void);
bool DSHOT_IsReady(void);
