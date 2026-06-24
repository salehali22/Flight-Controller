/*
 * pid.h
 *
 *  Created on: Mar 15, 2026
 *      Author: Saleh
 */

#ifndef INC_PID_H_
#define INC_PID_H_

typedef struct {
    float kp;
    float ki;
    float kd;

    float integral;
    float prev_error;

    float integral_limit;   // anti-windup
    float output_limit;     // clamp output
} PID_Handle_t;

void  PID_Init(PID_Handle_t *pid, float kp, float ki, float kd,
               float integral_limit, float output_limit);
float PID_Update(PID_Handle_t *pid, float setpoint, float measurement, float dt);
void  PID_Reset(PID_Handle_t *pid);

#endif /* INC_PID_H_ */
