#pragma once

#include "dshot.h"
#include <stdint.h>

/*
 * Motor layout (top view):
 *
 *   M6 (FL, CW)  |  M5 (FR, CCW)
 *   --------------+--------------
 *   M8 (RL, CCW) |  M7 (RR, CW)
 *
 * Mixing signs:
 *          Throttle  Roll  Pitch  Yaw
 *   M5 FR:    +       -     +     +
 *   M6 FL:    +       +     +     -
 *   M7 RR:    +       -     -     -
 *   M8 RL:    +       +     -     +
 */

/*
 * MOTOR_Mix — compute and send DSHOT values to all 4 motors.
 *
 *  throttle : 0.0 (stopped) to 1.0 (full)
 *  roll     : -1.0 (roll left) to +1.0 (roll right)
 *  pitch    : -1.0 (nose down) to +1.0 (nose up)
 *  yaw      : -1.0 (yaw left)  to +1.0 (yaw right)
 *
 * All PID outputs should be pre-scaled to fit within ±1.0.
 * Call this at your control loop rate.
 */
void MOTOR_Mix(float throttle, float roll, float pitch, float yaw);

/* Send zero throttle to all motors (disarm). */
void MOTOR_Disarm(void);
