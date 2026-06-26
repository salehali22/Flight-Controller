/*
 * iNAV target.c for SALEHFC
 * Based on MATEKH743 pattern
 *
 * Motor outputs (DSHOT via TIM1):
 *   M5 → PE9  (TIM1_CH1) — FR CCW
 *   M6 → PE11 (TIM1_CH2) — FL CW
 *   M7 → PE13 (TIM1_CH3) — RR CW
 *   M8 → PE14 (TIM1_CH4) — RL CCW
 *
 * Aux outputs (TIM8):
 *   M1 → PC6  (TIM8_CH1)
 *   M2 → PC7  (TIM8_CH2)
 *   M3 → PC8  (TIM8_CH3)
 *   M4 → PC9  (TIM8_CH4)
 *
 * Servo outputs (TIM4):
 *   S1 → PD12 (TIM4_CH1)
 *   S2 → PD13 (TIM4_CH2)
 *   S3 → PD14 (TIM4_CH3)
 *   S4 → PD15 (TIM4_CH4)
 *
 * NOTE: ICM42688P is on SPI6 which iNAV does not support.
 *       BMI270 on SPI3 is used as the sole IMU.
 */

 #include <stdint.h>
 #include "platform.h"
 #include "drivers/bus.h"
 #include "drivers/io.h"
 #include "drivers/pwm_mapping.h"
 #include "drivers/timer.h"
 #include "drivers/sensor.h"
 
 // BMI270 on SPI3 — CS=PD3, INT=PD2
 
 timerHardware_t timerHardware[] = {
     // ---- Primary quad motors on TIM1 (DSHOT capable) ----
     DEF_TIM(TIM1, CH1, PE9,  TIM_USE_OUTPUT_AUTO, 0, 0),   // M5 FR
     DEF_TIM(TIM1, CH2, PE11, TIM_USE_OUTPUT_AUTO, 0, 1),   // M6 FL
     DEF_TIM(TIM1, CH3, PE13, TIM_USE_OUTPUT_AUTO, 0, 2),   // M7 RR
     DEF_TIM(TIM1, CH4, PE14, TIM_USE_OUTPUT_AUTO, 0, 3),   // M8 RL
 
     // ---- Aux outputs on TIM8 ----
     DEF_TIM(TIM8, CH1, PC6,  TIM_USE_OUTPUT_AUTO, 0, 0),   // M1
     DEF_TIM(TIM8, CH2, PC7,  TIM_USE_OUTPUT_AUTO, 0, 1),   // M2
     DEF_TIM(TIM8, CH3, PC8,  TIM_USE_OUTPUT_AUTO, 0, 2),   // M3
     DEF_TIM(TIM8, CH4, PC9,  TIM_USE_OUTPUT_AUTO, 0, 3),   // M4
 
     // ---- Servo outputs on TIM4 ----
     DEF_TIM(TIM4, CH1, PD12, TIM_USE_OUTPUT_AUTO, 0, 6),   // S1
     DEF_TIM(TIM4, CH2, PD13, TIM_USE_OUTPUT_AUTO, 0, 7),   // S2
     DEF_TIM(TIM4, CH3, PD14, TIM_USE_OUTPUT_AUTO, 0, 0),   // S3
     DEF_TIM(TIM4, CH4, PD15, TIM_USE_OUTPUT_AUTO, 0, 0),   // S4
 };
 
 const int timerHardwareCount = sizeof(timerHardware) / sizeof(timerHardware[0]);