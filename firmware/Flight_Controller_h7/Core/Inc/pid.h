/*
 * pid.h — Rate PID controller (Betaflight D-on-measurement style)
 *
 * Architecture mirrors Betaflight's pidController():
 *   P = Kp * error
 *   I = Ki * integral(error * dt)   — with anti-windup clamp
 *   D = -Kd * d(measurement)/dt    — on measurement, NOT error
 *       (avoids derivative kick when setpoint jumps on stick input)
 *
 * Usage:
 *   PID_Init(&pid_roll, Kp, Ki, Kd, i_limit);
 *   float out = PID_Update(&pid_roll, setpoint_dps, gyro_dps, dt_s);
 *   PID_Reset(&pid_roll);   // always call on disarm to clear integrator
 */

#pragma once
#include <stdbool.h>

typedef struct {
    float kp;
    float ki;
    float kd;
    float integral;
    float prev_measurement;
    float i_limit;
    bool  first_run;
} PID_t;

/**
 * @brief  Initialise (or re-initialise) a PID instance.
 * @param  pid      pointer to PID_t
 * @param  kp       proportional gain
 * @param  ki       integral gain
 * @param  kd       derivative gain  (set 0 for first flight — add after confirming P+I works)
 * @param  i_limit  absolute clamp on the integral term output (e.g. 0.3 = ±30% authority)
 */
void  PID_Init  (PID_t *pid, float kp, float ki, float kd, float i_limit);

/**
 * @brief  Run one PID step.
 * @param  setpoint    desired rate (deg/s)
 * @param  measurement actual gyro rate (deg/s)
 * @param  dt          time since last call (seconds)
 * @return normalised output in roughly ±1.0 range (fed to MOTOR_Mix)
 */
float PID_Update(PID_t *pid, float setpoint, float measurement, float dt);

/**
 * @brief  Clear integrator and derivative state — MUST call on every disarm.
 */
void  PID_Reset (PID_t *pid);
