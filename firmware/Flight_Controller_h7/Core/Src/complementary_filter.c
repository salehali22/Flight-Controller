/*
 * complementary_filter.c
 *
 *  Created on: Mar 2026
 *      Author: Saleh
 *
 * @brief Mahony nonlinear complementary filter — adapted for BMI270.
 *
 * Changes from ICM42688P version:
 *   - Input struct changed from BMI270_Data_t to ICM42688P_Data_t
 *   - Global output variables g_roll, g_pitch, g_yaw added
 *   - No other algorithmic changes
 */

#include "complementary_filter.h"
#include <math.h>

/* ============== Global Output Variables ============== */

volatile float g_roll  = 0.0f;
volatile float g_pitch = 0.0f;
volatile float g_yaw   = 0.0f;

/* ============== Private Macros ============== */

#define CF_DEG_TO_RAD           0.017453292519943295f
#define CF_RAD_TO_DEG           57.295779513082321f
#define CF_ACCEL_INVNORM_MAX    1000.0f

/* ============== Private Functions ============== */

static float CF_InvSqrt(float x)
{
    union { float f; uint32_t i; } conv;
    float halfx = 0.5f * x;
    conv.f = x;
    conv.i = 0x5f3759df - (conv.i >> 1);
    conv.f = conv.f * (1.5f - halfx * conv.f * conv.f);
    return conv.f;
}

/* ============== Public Functions ============== */

CF_Status_t CF_Init(CF_Handle_t *hf, float kp, float ki)
{
    if (hf == NULL) return CF_ERR_INVALID_PARAM;

    hf->q0 = 1.0f; hf->q1 = 0.0f; hf->q2 = 0.0f; hf->q3 = 0.0f;
    hf->integral_x = 0.0f;
    hf->integral_y = 0.0f;
    hf->integral_z = 0.0f;
    hf->two_kp = 2.0f * kp;
    hf->two_ki = 2.0f * ki;
    hf->remap  = CF_REMAP_DEFAULT;
    hf->roll   = 0.0f;
    hf->pitch  = 0.0f;
    hf->yaw    = 0.0f;

    return CF_OK;
}

void CF_SetAxisRemap(CF_Handle_t *hf, CF_AxisRemap_t remap)
{
    hf->remap = remap;
}

CF_Status_t CF_InitFromAccel(CF_Handle_t *hf, float ax, float ay, float az)
{
    float norm = CF_InvSqrt(ax * ax + ay * ay + az * az);
    if (norm > CF_ACCEL_INVNORM_MAX) return CF_ERR_ACCEL_ZERO;

    ax *= norm; ay *= norm; az *= norm;

    float roll  = atan2f(ay, az);
    float pitch = atan2f(-ax, sqrtf(ay * ay + az * az));

    float cr = cosf(roll  * 0.5f), sr = sinf(roll  * 0.5f);
    float cp = cosf(pitch * 0.5f), sp = sinf(pitch * 0.5f);

    hf->q0 = cp * cr;
    hf->q1 = cp * sr;
    hf->q2 = sp * cr;
    hf->q3 = -sp * sr;

    hf->roll  = roll  * CF_RAD_TO_DEG;
    hf->pitch = pitch * CF_RAD_TO_DEG;
    hf->yaw   = 0.0f;

    return CF_OK;
}

void CF_Reset(CF_Handle_t *hf)
{
    hf->q0 = 1.0f; hf->q1 = 0.0f; hf->q2 = 0.0f; hf->q3 = 0.0f;
    hf->integral_x = 0.0f;
    hf->integral_y = 0.0f;
    hf->integral_z = 0.0f;
    hf->roll = 0.0f; hf->pitch = 0.0f; hf->yaw = 0.0f;
    g_roll = 0.0f;   g_pitch = 0.0f;   g_yaw  = 0.0f;
}

CF_Status_t CF_Update(CF_Handle_t *hf, const ICM42688P_Data_t *data, float dt)
{
    float ax = data->accel_g.x;
    float ay = data->accel_g.y;
    float az = data->accel_g.z;
    float gx = data->gyro_dps.x * CF_DEG_TO_RAD;
    float gy = data->gyro_dps.y * CF_DEG_TO_RAD;
    float gz = data->gyro_dps.z * CF_DEG_TO_RAD;

    /* Axis remap */
    {
        const float a[3] = { ax, ay, az };
        const float g[3] = { gx, gy, gz };
        ax = (float)hf->remap.sign[0] * a[hf->remap.src[0]];
        ay = (float)hf->remap.sign[1] * a[hf->remap.src[1]];
        az = (float)hf->remap.sign[2] * a[hf->remap.src[2]];
        gx = (float)hf->remap.sign[0] * g[hf->remap.src[0]];
        gy = (float)hf->remap.sign[1] * g[hf->remap.src[1]];
        gz = (float)hf->remap.sign[2] * g[hf->remap.src[2]];
    }

    float norm = CF_InvSqrt(ax * ax + ay * ay + az * az);
    if (norm > CF_ACCEL_INVNORM_MAX) goto integrate_gyro_only;

    ax *= norm; ay *= norm; az *= norm;

    {
        float q0 = hf->q0, q1 = hf->q1, q2 = hf->q2, q3 = hf->q3;
        float vx = 2.0f * (q1 * q3 - q0 * q2);
        float vy = 2.0f * (q0 * q1 + q2 * q3);
        float vz = q0 * q0 - q1 * q1 - q2 * q2 + q3 * q3;

        float ex = ay * vz - az * vy;
        float ey = az * vx - ax * vz;
        float ez = ax * vy - ay * vx;

        hf->integral_x += hf->two_ki * ex * dt;
        hf->integral_y += hf->two_ki * ey * dt;
        hf->integral_z += hf->two_ki * ez * dt;

        gx += hf->two_kp * ex + hf->integral_x;
        gy += hf->two_kp * ey + hf->integral_y;
        gz += hf->two_kp * ez + hf->integral_z;
    }

integrate_gyro_only:
    {
        float q0 = hf->q0, q1 = hf->q1, q2 = hf->q2, q3 = hf->q3;
        hf->q0 += 0.5f * dt * (-q1 * gx - q2 * gy - q3 * gz);
        hf->q1 += 0.5f * dt * ( q0 * gx + q2 * gz - q3 * gy);
        hf->q2 += 0.5f * dt * ( q0 * gy - q1 * gz + q3 * gx);
        hf->q3 += 0.5f * dt * ( q0 * gz + q1 * gy - q2 * gx);
    }

    norm = CF_InvSqrt(hf->q0*hf->q0 + hf->q1*hf->q1 +
                      hf->q2*hf->q2 + hf->q3*hf->q3);
    hf->q0 *= norm; hf->q1 *= norm;
    hf->q2 *= norm; hf->q3 *= norm;

    /* Euler angles */
    hf->roll = atan2f(2.0f * (hf->q0*hf->q1 + hf->q2*hf->q3),
                      1.0f - 2.0f * (hf->q1*hf->q1 + hf->q2*hf->q2))
               * CF_RAD_TO_DEG;

    float sinp = 2.0f * (hf->q0*hf->q2 - hf->q3*hf->q1);
    if      (sinp >  1.0f) sinp =  1.0f;
    else if (sinp < -1.0f) sinp = -1.0f;
    hf->pitch = -asinf(sinp) * CF_RAD_TO_DEG;

    hf->yaw = atan2f(2.0f * (hf->q0*hf->q3 + hf->q1*hf->q2),
                     1.0f - 2.0f * (hf->q2*hf->q2 + hf->q3*hf->q3))
              * CF_RAD_TO_DEG;

    /* Update globals */
    g_roll  = hf->roll;
    g_pitch = hf->pitch;
    g_yaw   = hf->yaw;

    return CF_OK;
}
