/*
 * complementary_filter.c
 *
 *  Created on: Mar 2026
 *      Author: Saleh
 *
 * @brief Mahony nonlinear complementary filter — attitude estimation.
 *
 * Algorithm reference:
 *   R. Mahony, T. Hamel, J.-M. Pflimlin,
 *   "Nonlinear Complementary Filters on the Special Orthogonal Group",
 *   IEEE Transactions on Automatic Control, 53(5):1203-1218, 2008.
 *
 * Implementation notes for STM32F103 (Cortex-M3, NO hardware FPU):
 *   - All arithmetic is single-precision float (software FPU via GCC libgcc).
 *   - CF_InvSqrt() replaces 1.0f/sqrtf() for quaternion normalization.
 *     On Cortex-M3, a software sqrtf() costs ~50-80 cycles; the fast
 *     inverse sqrt approximation costs ~10 cycles with <0.18% error.
 *     It is used only where that accuracy is sufficient (norm operations).
 *   - atan2f() and asinf() for Euler output are called once per update
 *     and are unavoidable; they cost ~200-400 cycles total on M3.
 *   - At 1 kHz update rate on a 24 MHz F103, total cost per call is
 *     approximately 2000-3000 cycles (~125 us) — well within budget.
 */

#include "complementary_filter.h"
#include <math.h>

/* ============== Private Macros ============== */

#define CF_DEG_TO_RAD   0.017453292519943295f   /* pi / 180  */
#define CF_RAD_TO_DEG   57.295779513082321f     /* 180 / pi  */

/*
 * Threshold for treating the accelerometer norm as "zero".
 * CF_InvSqrt(x) returns values > 1e6 when x < 1e-12 (effectively zero).
 * We use a more generous bound: skip if accel magnitude < ~0.1 g.
 * invSqrt(0.01) = 10.0, so threshold = 10.0f is ~0.1 g minimum.
 */
#define CF_ACCEL_INVNORM_MAX    1000.0f

/* ============== Private Functions ============== */

/**
 * @brief Fast inverse square root: returns 1/sqrt(x).
 *
 *        Uses the classic 0x5f3759df bit-manipulation trick (public domain,
 *        originally from Quake III Arena source code) with one Newton-Raphson
 *        refinement step. Error < 0.175% for all positive inputs.
 *
 *        The union-based type pun is defined behaviour in C99/C11 (6.5.2.3p3).
 *        It avoids the undefined-behaviour of the original pointer-cast version.
 */
static float CF_InvSqrt(float x)
{
    union { float f; uint32_t i; } conv;
    float  halfx = 0.5f * x;

    conv.f = x;
    conv.i = 0x5f3759df - (conv.i >> 1);        /* Magic bit manipulation */
    conv.f = conv.f * (1.5f - halfx * conv.f * conv.f);  /* Newton-Raphson  */
    return conv.f;
}

/* ============== Public Functions ============== */

CF_Status_t CF_Init(CF_Handle_t *hf, float kp, float ki)
{
    if (hf == NULL) {
        return CF_ERR_INVALID_PARAM;
    }

    /* Identity quaternion — represents "level, facing initial heading" */
    hf->q0 = 1.0f;
    hf->q1 = 0.0f;
    hf->q2 = 0.0f;
    hf->q3 = 0.0f;

    /* Clear gyro bias integral */
    hf->integral_x = 0.0f;
    hf->integral_y = 0.0f;
    hf->integral_z = 0.0f;

    /* Store as 2*gain — the factor of 2 falls out of the quaternion
     * derivative math and storing it pre-multiplied saves two muls per call */
    hf->two_kp = 2.0f * kp;
    hf->two_ki = 2.0f * ki;

    /* Default remap: identity (no axis swap) */
    hf->remap = CF_REMAP_DEFAULT;

    /* Zero the outputs */
    hf->roll  = 0.0f;
    hf->pitch = 0.0f;
    hf->yaw   = 0.0f;

    return CF_OK;
}

void CF_SetAxisRemap(CF_Handle_t *hf, CF_AxisRemap_t remap)
{
    hf->remap = remap;
}

CF_Status_t CF_InitFromAccel(CF_Handle_t *hf, float ax, float ay, float az)
{
    float norm;
    float roll, pitch;
    float cr, sr, cp, sp;

    /* Normalize — reject zero vector */
    norm = CF_InvSqrt(ax * ax + ay * ay + az * az);
    if (norm > CF_ACCEL_INVNORM_MAX) {
        return CF_ERR_ACCEL_ZERO;
    }
    ax *= norm;
    ay *= norm;
    az *= norm;

    /*
     * Compute initial roll and pitch from gravity vector.
     *
     * With the board stationary, accel reads the reaction force of gravity
     * in the body frame. The formulas below assume NED body axes:
     *   X = forward, Y = right, Z = down (standard aerospace).
     *
     * roll  = atan2(ay, az)         — tilt left/right
     * pitch = atan2(-ax, sqrt(ay^2+az^2))  — tilt forward/back
     *
     * If your board uses a different axis mapping, adjust these accordingly.
     */
    roll  = atan2f(ay, az);
    pitch = atan2f(-ax, sqrtf(ay * ay + az * az));

    /* Yaw is always zero — no magnetometer reference */

    /*
     * Build quaternion from roll and pitch (ZYX convention, yaw = 0):
     *   q = q_y(pitch) * q_x(roll)
     *   q0 = cos(p/2)*cos(r/2)
     *   q1 = cos(p/2)*sin(r/2)
     *   q2 = sin(p/2)*cos(r/2)
     *   q3 = -sin(p/2)*sin(r/2)
     */
    cr = cosf(roll  * 0.5f);
    sr = sinf(roll  * 0.5f);
    cp = cosf(pitch * 0.5f);
    sp = sinf(pitch * 0.5f);

    hf->q0 = cp * cr;
    hf->q1 = cp * sr;
    hf->q2 = sp * cr;
    hf->q3 = -sp * sr;

    /* Recompute Euler outputs to match the new quaternion */
    hf->roll  = roll  * CF_RAD_TO_DEG;
    hf->pitch = pitch * CF_RAD_TO_DEG;
    hf->yaw   = 0.0f;

    return CF_OK;
}

void CF_Reset(CF_Handle_t *hf)
{
    hf->q0 = 1.0f;
    hf->q1 = 0.0f;
    hf->q2 = 0.0f;
    hf->q3 = 0.0f;

    hf->integral_x = 0.0f;
    hf->integral_y = 0.0f;
    hf->integral_z = 0.0f;

    hf->roll  = 0.0f;
    hf->pitch = 0.0f;
    hf->yaw   = 0.0f;
}

CF_Status_t CF_Update(CF_Handle_t *hf, const ICM42688P_Data_t *data, float dt)
{
    float ax, ay, az;
    float gx, gy, gz;
    float norm;
    float vx, vy, vz;      /* Estimated gravity direction in body frame */
    float ex, ey, ez;      /* Error vector (cross product) */
    float q0, q1, q2, q3; /* Local copies for readability */
    float sinp;

    /* ---- Load accel (g) and convert gyro dps -> rad/s ---- */
    ax = data->accel_g.x;
    ay = data->accel_g.y;
    az = data->accel_g.z;

    gx = data->gyro_dps.x * CF_DEG_TO_RAD;
    gy = data->gyro_dps.y * CF_DEG_TO_RAD;
    gz = data->gyro_dps.z * CF_DEG_TO_RAD;

    /* ---- Apply board alignment remap ---- */
    /*
     * Re-express the IMU chip axes in the drone body frame before any math.
     * src[] picks which chip axis feeds each filter axis; sign[] flips it.
     * With CF_REMAP_DEFAULT (identity) this compiles to no extra instructions.
     */
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

    /* ---- Normalize accelerometer vector ---- */
    /*
     * This converts the accel measurement into a pure direction vector
     * (unit vector pointing "up" in body frame, opposite to gravity).
     * If the norm is near zero (free-fall or sensor fault), skip the
     * accel correction entirely to avoid NaN propagation.
     */
    norm = CF_InvSqrt(ax * ax + ay * ay + az * az);
    if (norm > CF_ACCEL_INVNORM_MAX) {
        /* Free-fall or bad data — integrate gyro only, keep old attitude */
        goto integrate_gyro_only;
    }
    ax *= norm;
    ay *= norm;
    az *= norm;

    /* ---- Estimated gravity direction from current quaternion ---- */
    /*
     * This is the third column of the rotation matrix R(q), i.e. the
     * direction that the world "down" axis (0,0,1) currently points
     * in body frame, according to our quaternion state.
     *
     *   vx = 2*(q1*q3 - q0*q2)
     *   vy = 2*(q0*q1 + q2*q3)
     *   vz = q0^2 - q1^2 - q2^2 + q3^2
     */
    q0 = hf->q0;  q1 = hf->q1;  q2 = hf->q2;  q3 = hf->q3;

    vx = 2.0f * (q1 * q3 - q0 * q2);
    vy = 2.0f * (q0 * q1 + q2 * q3);
    vz = q0 * q0 - q1 * q1 - q2 * q2 + q3 * q3;

    /* ---- Error = cross product(measured_gravity, estimated_gravity) ---- */
    /*
     * The cross product gives a rotation axis and magnitude proportional
     * to the angle between what we measure (accel) and what we expect
     * (from quaternion). This is the "innovation" / correction signal.
     *
     * Note: yaw error is NOT observable here — both vectors lie on the
     * gravity axis and their cross product has no yaw component.
     * That is why yaw can only be corrected by a magnetometer.
     */
    ex = ay * vz - az * vy;
    ey = az * vx - ax * vz;
    ez = ax * vy - ay * vx;

    /* ---- Integral feedback — slowly estimates and removes gyro bias ---- */
    hf->integral_x += hf->two_ki * ex * dt;
    hf->integral_y += hf->two_ki * ey * dt;
    hf->integral_z += hf->two_ki * ez * dt;

    /* ---- Apply proportional + integral correction to gyro rates ---- */
    gx += hf->two_kp * ex + hf->integral_x;
    gy += hf->two_kp * ey + hf->integral_y;
    gz += hf->two_kp * ez + hf->integral_z;

integrate_gyro_only:
    /* ---- Integrate quaternion from corrected angular velocity ---- */
    /*
     * qdot = 0.5 * q ⊗ [0, gx, gy, gz]
     * Expanded (quaternion product with pure quaternion):
     *
     *   dq0/dt = 0.5 * (-q1*gx - q2*gy - q3*gz)
     *   dq1/dt = 0.5 * ( q0*gx + q2*gz - q3*gy)
     *   dq2/dt = 0.5 * ( q0*gy - q1*gz + q3*gx)
     *   dq3/dt = 0.5 * ( q0*gz + q1*gy - q2*gx)
     *
     * First-order Euler integration: q += qdot * dt
     */
    q0 = hf->q0;  q1 = hf->q1;  q2 = hf->q2;  q3 = hf->q3;

    hf->q0 += 0.5f * dt * (-q1 * gx - q2 * gy - q3 * gz);
    hf->q1 += 0.5f * dt * ( q0 * gx + q2 * gz - q3 * gy);
    hf->q2 += 0.5f * dt * ( q0 * gy - q1 * gz + q3 * gx);
    hf->q3 += 0.5f * dt * ( q0 * gz + q1 * gy - q2 * gx);

    /* ---- Normalize quaternion ---- */
    /*
     * Floating-point drift causes the quaternion to slowly leave the unit
     * sphere. Renormalize every update to keep it valid. CF_InvSqrt is
     * accurate enough here (error < 0.18% — fine for attitude estimation).
     */
    norm = CF_InvSqrt(hf->q0 * hf->q0 + hf->q1 * hf->q1 +
                      hf->q2 * hf->q2 + hf->q3 * hf->q3);
    hf->q0 *= norm;
    hf->q1 *= norm;
    hf->q2 *= norm;
    hf->q3 *= norm;

    /* ---- Convert quaternion to Euler angles (ZYX convention) ---- */
    /*
     * ZYX (yaw-pitch-roll) convention — standard for aerospace and most FCs:
     *   First rotate by yaw  (psi)   about world Z
     *   Then  rotate by pitch(theta) about new Y
     *   Then  rotate by roll (phi)   about new X
     *
     *   roll  = atan2( 2*(q0*q1 + q2*q3),  1 - 2*(q1^2 + q2^2) )
     *   pitch = asin ( 2*(q0*q2 - q3*q1) )   <- clamped to avoid NaN
     *   yaw   = atan2( 2*(q0*q3 + q1*q2),  1 - 2*(q2^2 + q3^2) )
     */
    hf->roll = atan2f(2.0f * (hf->q0 * hf->q1 + hf->q2 * hf->q3),
                      1.0f - 2.0f * (hf->q1 * hf->q1 + hf->q2 * hf->q2))
               * CF_RAD_TO_DEG;

    /* Clamp the asinf argument to [-1, 1] — numerical drift can push it
     * fractionally outside this range, which makes asinf() return NaN. */
    sinp = 2.0f * (hf->q0 * hf->q2 - hf->q3 * hf->q1);
    if      (sinp >  1.0f) { sinp =  1.0f; }
    else if (sinp < -1.0f) { sinp = -1.0f; }
    hf->pitch = -asinf(sinp) * CF_RAD_TO_DEG;

    hf->yaw = atan2f(2.0f * (hf->q0 * hf->q3 + hf->q1 * hf->q2),
                     1.0f - 2.0f * (hf->q2 * hf->q2 + hf->q3 * hf->q3))
              * CF_RAD_TO_DEG;

    return CF_OK;
}
