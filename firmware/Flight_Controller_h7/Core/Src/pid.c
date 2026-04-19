/*
 * pid.c — Rate PID controller
 *
 * Matches Betaflight's rate PID architecture:
 *   - D term differentiates the measurement (gyro), not the error.
 *     This means a sudden stick input does NOT produce a D spike.
 *   - Integral anti-windup: hard clamp to ±i_limit.
 *   - No setpoint weighting or filter on this pass — add PT1 on the
 *     derivative path once you have the quad flying and want to tune D.
 */

#include "pid.h"

/* ------------------------------------------------------------------ */

void PID_Init(PID_t *pid, float kp, float ki, float kd, float i_limit)
{
    pid->kp               = kp;
    pid->ki               = ki;
    pid->kd               = kd;
    pid->i_limit          = i_limit;
    pid->integral         = 0.0f;
    pid->prev_measurement = 0.0f;
    pid->first_run        = true;
}

/* ------------------------------------------------------------------ */

float PID_Update(PID_t *pid, float setpoint, float measurement, float dt)
{
    float error = setpoint - measurement;

    /* ---- P ---- */
    float p = pid->kp * error;

    /* ---- I  (anti-windup: clamp before accumulating further) ---- */
    pid->integral += pid->ki * error * dt;
    if      (pid->integral >  pid->i_limit) pid->integral =  pid->i_limit;
    else if (pid->integral < -pid->i_limit) pid->integral = -pid->i_limit;

    /* ---- D on measurement ----
     * delta = measurement - prev_measurement (positive when gyro rate rising)
     * Negative sign: if gyro rate is rising, reduce output → dampen motion.
     * On first call prev_measurement is 0; skip D to avoid a huge spike. */
    float d = 0.0f;
    if (!pid->first_run && (pid->kd != 0.0f)) {
        float delta = measurement - pid->prev_measurement;
        /* Divide by dt so gain units are consistent regardless of loop rate */
        d = -(pid->kd * delta) / dt;
    }
    pid->prev_measurement = measurement;
    pid->first_run        = false;

    return p + pid->integral + d;
}

/* ------------------------------------------------------------------ */

void PID_Reset(PID_t *pid)
{
    pid->integral  = 0.0f;
    pid->first_run = true;
    /* prev_measurement intentionally NOT reset so D term stays smooth
     * if re-armed quickly; it will correct itself within one tick anyway. */
}
