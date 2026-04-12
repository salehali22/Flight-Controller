/*
 * motor_mix.c
 *
 *  Created on: Apr 2026
 *      Author: Saleh
 *
 * @brief X-frame quadcopter motor mixer.
 *
 * Converts throttle + roll/pitch/yaw demands into individual
 * DSHOT throttle values for each motor.
 *
 * Motor layout (top view):
 *
 *   M6 (FL, CW)  |  M5 (FR, CCW)
 *   --------------+--------------
 *   M8 (RL, CCW) |  M7 (RR, CW)
 *
 * TIM1 channel mapping:
 *   TIM1_CH1 (PE9)  → M5 (FR)
 *   TIM1_CH2 (PE11) → M6 (FL)
 *   TIM1_CH3 (PE13) → M7 (RR)
 *   TIM1_CH4 (PE14) → M8 (RL)
 */

#include "motor_mix.h"

/* DSHOT range for actual throttle (0 = disarm, 48-2047 = throttle) */
#define DSHOT_RANGE  ((float)(DSHOT_MAX_THROTTLE - DSHOT_MIN_THROTTLE))

/* Maximum authority given to roll/pitch/yaw relative to throttle.
 * 0.5 means PID terms can use up to ±50% of the DSHOT range.
 * Keep this conservative until PID is tuned.                       */
#define MIX_AUTHORITY  0.5f

static uint16_t _clamp_dshot(float val)
{
    if (val < DSHOT_MIN_THROTTLE) return DSHOT_MIN_THROTTLE;
    if (val > DSHOT_MAX_THROTTLE) return DSHOT_MAX_THROTTLE;
    return (uint16_t)val;
}

void MOTOR_Mix(float throttle, float roll, float pitch, float yaw)
{
    /* Convert 0-1 throttle to DSHOT range */
    float thr = DSHOT_MIN_THROTTLE + throttle * DSHOT_RANGE;

    /* Scale PID terms to DSHOT units */
    float r = roll  * MIX_AUTHORITY * DSHOT_RANGE;
    float p = pitch * MIX_AUTHORITY * DSHOT_RANGE;
    float y = yaw   * MIX_AUTHORITY * DSHOT_RANGE;

    /* Mix — FR, FL, RR, RL
     *          Thr   Roll  Pitch  Yaw  */
    float m5 = thr  -  r  +  p  +  y;   /* FR CCW */
    float m6 = thr  +  r  +  p  -  y;   /* FL CW  */
    float m7 = thr  -  r  -  p  -  y;   /* RR CW  */
    float m8 = thr  +  r  -  p  +  y;   /* RL CCW */

    DSHOT_SendThrottle(_clamp_dshot(m5),
                       _clamp_dshot(m6),
                       _clamp_dshot(m7),
                       _clamp_dshot(m8));
}

void MOTOR_Disarm(void)
{
    DSHOT_SendThrottle(DSHOT_DISARM, DSHOT_DISARM, DSHOT_DISARM, DSHOT_DISARM);
}
