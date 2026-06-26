/*
 * Betaflight 4.5.1 target.c for SALEHFC
 *
 * Timer/DMA mapping for 12 PWM outputs:
 *
 *   M1  PE9   TIM1_CH1   DSHOT primary quad
 *   M2  PE11  TIM1_CH2
 *   M3  PE13  TIM1_CH3
 *   M4  PE14  TIM1_CH4
 *
 *   M5  PC6   TIM8_CH1   Aux motors
 *   M6  PC7   TIM8_CH2
 *   M7  PC8   TIM8_CH3
 *   M8  PC9   TIM8_CH4
 *
 *   S1  PD12  TIM4_CH1   Servos
 *   S2  PD13  TIM4_CH2
 *   S3  PD14  TIM4_CH3
 *   S4  PD15  TIM4_CH4
 */

#include <stdint.h>

#include "platform.h"
#include "drivers/io.h"
#include "drivers/dma.h"
#include "drivers/timer.h"
#include "drivers/timer_def.h"

timerHardware_t timerHardware[USABLE_TIMER_CHANNEL_COUNT] = {
    // ---- Primary quad motors on TIM1 (DSHOT capable) ----
    DEF_TIM(TIM1, CH1, PE9,  TIM_USE_MOTOR, 0, 0),   // M1
    DEF_TIM(TIM1, CH2, PE11, TIM_USE_MOTOR, 0, 1),   // M2
    DEF_TIM(TIM1, CH3, PE13, TIM_USE_MOTOR, 0, 2),   // M3
    DEF_TIM(TIM1, CH4, PE14, TIM_USE_MOTOR, 0, 3),   // M4

    // ---- Aux motor outputs on TIM8 ----
    DEF_TIM(TIM8, CH1, PC6,  TIM_USE_MOTOR, 0, 4),   // M5
    DEF_TIM(TIM8, CH2, PC7,  TIM_USE_MOTOR, 0, 5),   // M6
    DEF_TIM(TIM8, CH3, PC8,  TIM_USE_MOTOR, 0, 6),   // M7
    DEF_TIM(TIM8, CH4, PC9,  TIM_USE_MOTOR, 0, 7),   // M8

    // ---- Servo outputs on TIM4 ----
    DEF_TIM(TIM4, CH1, PD12, TIM_USE_ANY,   0, 8),   // S1
    DEF_TIM(TIM4, CH2, PD13, TIM_USE_ANY,   0, 9),   // S2
    DEF_TIM(TIM4, CH3, PD14, TIM_USE_ANY,   0, 10),  // S3
    DEF_TIM(TIM4, CH4, PD15, TIM_USE_ANY,   0, 11),  // S4
};
