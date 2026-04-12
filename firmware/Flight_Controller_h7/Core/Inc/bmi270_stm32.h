/**
 * @file bmi270_stm32.h
 * @brief STM32 HAL wrapper header for Bosch BMI270 SensorAPI
 */

#ifndef BMI270_STM32_H
#define BMI270_STM32_H

#include "bmi2.h"

#ifdef __cplusplus
extern "C" {
#endif

/* BMI270 configured at ±16g / ±2000 dps (16-bit output).
 *   Accel: 2048 LSB/g   → raw / BMI270_ACC_SENSITIVITY gives value in g
 *   Gyro:  16.384 LSB/dps → raw / BMI270_GYR_SENSITIVITY gives value in dps
 *
 * NOTE: az ≈ 2048 at rest is CORRECT — it equals exactly 1g (gravity). */
#define BMI270_ACC_SENSITIVITY   2048.0f
#define BMI270_GYR_SENSITIVITY   16.384f

/**
 * @brief Initialize BMI270 device structure and sensor
 * @param bmi Pointer to bmi2_dev structure
 * @return BMI2_OK on success, error code otherwise
 */
int8_t bmi270_interface_init(struct bmi2_dev *bmi);

/**
 * @brief Configure and enable accelerometer + gyroscope
 * @param bmi Pointer to initialized bmi2_dev structure
 * @return BMI2_OK on success
 */
int8_t bmi270_configure_sensor(struct bmi2_dev *bmi);

/**
 * @brief Read accelerometer and gyroscope data
 * @param bmi Pointer to bmi2_dev
 * @param acc_x/y/z Output: raw acceleration
 * @param gyr_x/y/z Output: raw angular rate
 * @return BMI2_OK on success
 */
int8_t bmi270_read_sensor_data(struct bmi2_dev *bmi,
                                int16_t *acc_x, int16_t *acc_y, int16_t *acc_z,
                                int16_t *gyr_x, int16_t *gyr_y, int16_t *gyr_z);

#ifdef __cplusplus
}
#endif

#endif /* BMI270_STM32_H */
