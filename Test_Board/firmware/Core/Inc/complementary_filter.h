/*
 * complementary_filter.h
 *
 *  Created on: Mar 2026
 *      Author: Saleh
 *
 * @brief Mahony nonlinear complementary filter for attitude estimation.
 *
 * This is a nonlinear complementary filter on SO(3) — the same class of
 * algorithm used in Betaflight, ArduPilot, and iNav. It combines the
 * complementary frequency responses of the gyroscope (accurate at high
 * frequency / fast motion) and accelerometer (accurate at low frequency /
 * static tilt) using quaternion algebra instead of Euler angles, which
 * avoids gimbal lock and eliminates cross-axis coupling errors.
 *
 * Reference:
 *   R. Mahony, T. Hamel, J.-M. Pflimlin, "Nonlinear Complementary Filters
 *   on the Special Orthogonal Group", IEEE Trans. Autom. Control, 2008.
 *
 * Roll / Pitch: corrected by the accelerometer (absolute gravity reference).
 *               Stable, non-drifting.
 *
 * Yaw:          gyro-integrated only — RELATIVE to heading at power-on.
 *               Will drift slowly (~0.1-1 deg/min with ICM-42688-P).
 *               Add a magnetometer (e.g. QMC5883L) for absolute yaw.
 */

#ifndef INC_COMPLEMENTARY_FILTER_H_
#define INC_COMPLEMENTARY_FILTER_H_

#include <stdint.h>
#include "icm42688p.h"

/* ============== Default Tuning Parameters ============== */

/*
 * Mahony proportional gain (Kp).
 *
 * Controls how aggressively the accelerometer corrects the gyro estimate.
 *   Higher -> faster convergence from a tilted start, more vibration noise.
 *   Lower  -> smoother output, slower to correct gyro drift.
 *
 * Relationship to classic complementary filter alpha at 1 kHz:
 *   alpha ≈ 1 / (1 + two_kp * dt)   [approximate, non-linear mapping]
 *   Kp = 0.5 corresponds to alpha ≈ 0.9995 at 1 kHz
 *   Kp = 10  corresponds to alpha ≈ 0.980  at 1 kHz  (same as classic 0.98)
 *
 * Recommended starting point: 0.5 for a clean, low-vibration platform.
 * Increase toward 2.0 if you need faster convergence.
 */
#define CF_KP_DEFAULT   2.0f

/*
 * Mahony integral gain (Ki).
 *
 * Drives the gyro bias estimate to zero over time.
 *   0.0  -> no bias correction (pure proportional Mahony).
 *   0.01 -> recommended: removes steady-state gyro bias in ~30-60 seconds.
 *
 * Set to 0 if you notice the attitude "creeping" after enabling it.
 */
#define CF_KI_DEFAULT   0.01f

/* ============== Axis Remap ============== */

/*
 * The ICM-42688-P's physical axes depend on how it is mounted on the board.
 * The filter's Euler math assumes a specific body-frame convention:
 *   Filter X = drone forward (longitudinal / roll axis)
 *   Filter Y = drone lateral  (pitch axis)
 *   Filter Z = up
 *
 * CF_AxisRemap_t lets you describe how the IMU chip axes map to that frame
 * with a simple source-index + sign table, applied once per CF_Update() call.
 * This is the same concept as Betaflight's board_alignment / align_gyro.
 */
typedef struct {
    uint8_t src[3];     /* src[0/1/2] = which IMU axis (0=X,1=Y,2=Z) feeds filter X/Y/Z */
    int8_t  sign[3];    /* sign[i] = +1 or -1 applied to the selected source axis        */
} CF_AxisRemap_t;

/*
 * CF_REMAP_DEFAULT — no remap.
 *   Use when IMU X points forward, IMU Y points right, IMU Z points up.
 */
static const CF_AxisRemap_t CF_REMAP_DEFAULT = { {0, 1, 2}, { 1,  1,  1} };

/*
 * CF_REMAP_Y_FWD — Y-forward mounting.
 *   Use when the IMU pin-1 dot faces the drone nose and the datasheet shows
 *   +Y pointing forward (+X pointing to the right side, +Z up).
 *   This is the standard ICM-42688-P orientation when dot = front-left corner.
 *
 *   Resulting filter frame: X = forward, Y = left, Z = up  (right-handed, X×Y = Z).
 *     attitude.roll  > 0  →  LEFT  wing up
 *     attitude.pitch > 0  →  NOSE  up
 *     attitude.yaw   > 0  →  heading change (relative, drifts)
 *
 *   If you want RIGHT-wing-up = positive roll (aviation convention), negate
 *   attitude.roll at the point of use:  drone_roll = -attitude.roll;
 */
static const CF_AxisRemap_t CF_REMAP_Y_FWD   = { {1, 0, 2}, { 1, -1,  1} };

/* ============== Data Structures ============== */

typedef struct {
    /* --- Internal quaternion state (w, x, y, z) --- */
    float q0;           /* w — scalar part */
    float q1;           /* x */
    float q2;           /* y */
    float q3;           /* z */

    /* --- Gyro bias integral accumulator (rad/s) --- */
    float integral_x;
    float integral_y;
    float integral_z;

    /* --- Mahony gains (stored as 2*gain for efficiency) --- */
    float two_kp;       /* 2 * proportional gain */
    float two_ki;       /* 2 * integral gain      */

    /* --- Board alignment remap (set once via CF_SetAxisRemap) --- */
    CF_AxisRemap_t remap;   /* Defaults to CF_REMAP_DEFAULT (identity) */

    /* --- Euler angle outputs (degrees, ZYX / aerospace convention) --- */
    float roll;         /* phi   — rotation about X axis, range [-180, +180] deg */
    float pitch;        /* theta — rotation about Y axis, range [-90,  +90]  deg */
    float yaw;          /* psi   — rotation about Z axis, range [-180, +180] deg
                         * NOTE: YAW IS RELATIVE. No magnetometer = no absolute
                         * heading reference. Drift is normal and expected.   */
} CF_Handle_t;

typedef enum {
    CF_OK = 0,
    CF_ERR_INVALID_PARAM,   /* NULL pointer passed */
    CF_ERR_ACCEL_ZERO       /* Accelerometer norm ≈ 0 (free-fall / bad data).
                             * Update was skipped; previous attitude retained. */
} CF_Status_t;

/* ============== Function Prototypes ============== */

/**
 * @brief  Initialize the Mahony complementary filter.
 *
 *         Sets the quaternion to identity (assumes board is level at start).
 *         For a faster start if the board is tilted at power-on, call
 *         CF_InitFromAccel() right after this.
 *
 * @param  hf  Pointer to filter handle
 * @param  kp  Proportional gain (use CF_KP_DEFAULT = 0.5f to start)
 * @param  ki  Integral gain for gyro bias correction (use CF_KI_DEFAULT = 0.01f)
 * @return CF_OK on success, CF_ERR_INVALID_PARAM if hf is NULL
 */
CF_Status_t CF_Init(CF_Handle_t *hf, float kp, float ki);

/**
 * @brief  Initialize quaternion from the first accelerometer reading.
 *
 *         Call this once after CF_Init() and after the first valid sensor
 *         read. It computes the initial roll/pitch from gravity and sets
 *         the quaternion accordingly, so the filter converges instantly
 *         instead of needing a few seconds to "settle" from identity.
 *
 *         Yaw is always set to zero (no magnetometer reference).
 *
 * @param  hf  Pointer to filter handle (must already be CF_Init()'d)
 * @param  ax  Accelerometer X in g
 * @param  ay  Accelerometer Y in g
 * @param  az  Accelerometer Z in g
 * @return CF_OK on success, CF_ERR_ACCEL_ZERO if vector norm is zero
 */
CF_Status_t CF_InitFromAccel(CF_Handle_t *hf, float ax, float ay, float az);

/**
 * @brief  Update attitude estimate with new IMU data.
 *
 *         Call this at a fixed rate. The dt parameter must match your
 *         actual call interval (e.g. 0.001f for 1 kHz).
 *
 *         Reads accel_g.{x,y,z} and gyro_dps.{x,y,z} from the ICM data
 *         struct directly — no extra conversion needed by the caller.
 *
 *         After the call, read hf->roll, hf->pitch, hf->yaw (degrees).
 *
 * @param  hf    Pointer to filter handle
 * @param  data  Pointer to ICM42688P_Data_t with fresh sensor data
 * @param  dt    Time step in seconds since last call (e.g. 0.001f at 1 kHz)
 * @return CF_OK on success
 *         CF_ERR_ACCEL_ZERO if accel norm is zero (update skipped, old
 *         attitude retained — this is safe, just means free-fall detected)
 */
CF_Status_t CF_Update(CF_Handle_t *hf, const ICM42688P_Data_t *data, float dt);

/**
 * @brief  Set the board alignment remap for this filter instance.
 *
 *         Call once after CF_Init() and before the first CF_Update().
 *         The remap is applied at the start of every CF_Update() call,
 *         re-expressing the IMU chip axes in the drone body frame.
 *
 *         Use CF_REMAP_DEFAULT  if IMU X points forward (no remap needed).
 *         Use CF_REMAP_Y_FWD   if IMU pin-1 dot faces the nose (Y = forward).
 *         Custom orientations can be built with CF_AxisRemap_t directly.
 *
 * @param  hf     Pointer to filter handle
 * @param  remap  Axis remap descriptor (use a CF_REMAP_* constant)
 */
void CF_SetAxisRemap(CF_Handle_t *hf, CF_AxisRemap_t remap);

/**
 * @brief  Reset filter to identity quaternion and zero bias.
 *         Useful when switching modes or after a crash detection.
 *
 * @param  hf  Pointer to filter handle
 */
void CF_Reset(CF_Handle_t *hf);

#endif /* INC_COMPLEMENTARY_FILTER_H_ */
