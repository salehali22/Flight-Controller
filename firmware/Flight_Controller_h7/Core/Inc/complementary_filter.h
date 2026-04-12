/*
 * complementary_filter.h
 *
 *  Created on: Mar 2026
 *      Author: Saleh
 *
 * @brief Mahony nonlinear complementary filter for attitude estimation.
 *        Adapted for BMI270 via bmi270_stm32 driver.
 *
 * Reference:
 *   R. Mahony, T. Hamel, J.-M. Pflimlin, "Nonlinear Complementary Filters
 *   on the Special Orthogonal Group", IEEE Trans. Autom. Control, 2008.
 */

#ifndef INC_COMPLEMENTARY_FILTER_H_
#define INC_COMPLEMENTARY_FILTER_H_

#include <stdint.h>
#include "icm42688p.h"   /* Input type: ICM42688P_Data_t (accel_g, gyro_dps already in g / dps) */

/* ============== Default Tuning Parameters ============== */

#define CF_KP_DEFAULT   2.0f
#define CF_KI_DEFAULT   0.01f

/* ============== Axis Remap ============== */

typedef struct {
    uint8_t src[3];     /* which IMU axis (0=X,1=Y,2=Z) feeds filter X/Y/Z */
    int8_t  sign[3];    /* +1 or -1 */
} CF_AxisRemap_t;

/* No remap — IMU X=forward, Y=right, Z=up */
static const CF_AxisRemap_t CF_REMAP_DEFAULT = { {0, 1, 2}, { 1,  1,  1} };

/* Y-forward mounting — IMU pin-1 dot faces nose */
static const CF_AxisRemap_t CF_REMAP_Y_FWD   = { {1, 0, 2}, { 1, -1,  1} };

/* ============== Filter Handle ============== */

typedef struct {
    float q0, q1, q2, q3;          /* Quaternion state (w, x, y, z)  */
    float integral_x;               /* Gyro bias integral              */
    float integral_y;
    float integral_z;
    float two_kp;                   /* 2 * proportional gain           */
    float two_ki;                   /* 2 * integral gain               */
    CF_AxisRemap_t remap;
    float roll;                     /* Output: degrees [-180, +180]    */
    float pitch;                    /* Output: degrees [-90,  +90]     */
    float yaw;                      /* Output: degrees [-180, +180]    */
} CF_Handle_t;

typedef enum {
    CF_OK = 0,
    CF_ERR_INVALID_PARAM,
    CF_ERR_ACCEL_ZERO
} CF_Status_t;

/* ============== Global Output Variables ============== */

/*
 * Declare as extern here — define once in complementary_filter.c.
 * These are updated every CF_Update() call and can be watched in
 * the debugger live expressions window without stopping execution.
 */
extern volatile float g_roll;
extern volatile float g_pitch;
extern volatile float g_yaw;

/* ============== Function Prototypes ============== */

CF_Status_t CF_Init(CF_Handle_t *hf, float kp, float ki);
CF_Status_t CF_InitFromAccel(CF_Handle_t *hf, float ax, float ay, float az);
CF_Status_t CF_Update(CF_Handle_t *hf, const ICM42688P_Data_t *data, float dt);
void        CF_SetAxisRemap(CF_Handle_t *hf, CF_AxisRemap_t remap);
void        CF_Reset(CF_Handle_t *hf);

#endif /* INC_COMPLEMENTARY_FILTER_H_ */
