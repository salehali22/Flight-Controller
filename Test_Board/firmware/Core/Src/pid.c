/*
 * pid.c
 *
 *  Created on: Mar 15, 2026
 *      Author: Saleh
 */


#include "pid.h"

void PID_Init(PID_Handle_t *pid, float kp, float ki, float kd,
              float integral_limit, float output_limit)
{
    pid->kp             = kp;
    pid->ki             = ki;
    pid->kd             = kd;
    pid->integral       = 0.0f;
    pid->prev_error     = 0.0f;
    pid->integral_limit = integral_limit;
    pid->output_limit   = output_limit;
}

float PID_Update(PID_Handle_t *pid, float setpoint, float measurement, float dt)
{
    float error = setpoint - measurement;

    // Proportional
    float p = pid->kp * error;

    // Integral with windup clamp
    pid->integral += error * dt;
    if      (pid->integral >  pid->integral_limit) pid->integral =  pid->integral_limit;
    else if (pid->integral < -pid->integral_limit) pid->integral = -pid->integral_limit;
    float i = pid->ki * pid->integral;

    // Derivative (on measurement to avoid derivative kick on setpoint change)
    float d = pid->kd * (error - pid->prev_error) / dt;
    pid->prev_error = error;

    float output = p + i + d;

    // Clamp output
    if      (output >  pid->output_limit) output =  pid->output_limit;
    else if (output < -pid->output_limit) output = -pid->output_limit;

    return output;
}

void PID_Reset(PID_Handle_t *pid)
{
    pid->integral   = 0.0f;
    pid->prev_error = 0.0f;
}
