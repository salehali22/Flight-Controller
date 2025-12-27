/*
 * ICM-42688p.h
 *
 *  Created on: Dec 26, 2025
 *      Author: Saleh work and edu
 */

#ifndef INC_ICM42688P_H_
#define INC_ICM42688P_H_

#include "stm32f1xx_hal.h"
#include <stdint.h>

/* ============== Configuration ============== */
#define ICM42688P_SPI           hspi2
#define ICM42688P_CS_PORT       GPIOB
#define ICM42688P_CS_PIN        GPIO_PIN_12

/* ============== Device ID ============== */
#define ICM42688P_WHO_AM_I_VAL  0x47

/* ============== Register Map (Bank 0) ============== */
#define ICM42688P_REG_DEVICE_CONFIG     0x11
#define ICM42688P_REG_INT_CONFIG        0x14
#define ICM42688P_REG_TEMP_DATA1        0x1D
#define ICM42688P_REG_TEMP_DATA0        0x1E
#define ICM42688P_REG_ACCEL_DATA_X1     0x1F
#define ICM42688P_REG_ACCEL_DATA_X0     0x20
#define ICM42688P_REG_ACCEL_DATA_Y1     0x21
#define ICM42688P_REG_ACCEL_DATA_Y0     0x22
#define ICM42688P_REG_ACCEL_DATA_Z1     0x23
#define ICM42688P_REG_ACCEL_DATA_Z0     0x24
#define ICM42688P_REG_GYRO_DATA_X1      0x25
#define ICM42688P_REG_GYRO_DATA_X0      0x26
#define ICM42688P_REG_GYRO_DATA_Y1      0x27
#define ICM42688P_REG_GYRO_DATA_Y0      0x28
#define ICM42688P_REG_GYRO_DATA_Z1      0x29
#define ICM42688P_REG_GYRO_DATA_Z0      0x2A
#define ICM42688P_REG_INT_STATUS        0x2D
#define ICM42688P_REG_PWR_MGMT0         0x4E
#define ICM42688P_REG_GYRO_CONFIG0      0x4F
#define ICM42688P_REG_ACCEL_CONFIG0     0x50
#define ICM42688P_REG_GYRO_CONFIG1      0x51
#define ICM42688P_REG_ACCEL_CONFIG1     0x53
#define ICM42688P_REG_WHO_AM_I          0x75
#define ICM42688P_REG_BANK_SEL          0x76

/* ============== PWR_MGMT0 Bits ============== */
#define ICM42688P_PWR_GYRO_MODE_LN      (0x03 << 2)  // Gyro Low Noise mode
#define ICM42688P_PWR_ACCEL_MODE_LN     (0x03 << 0)  // Accel Low Noise mode

/* ============== GYRO_CONFIG0 Values ============== */
#define ICM42688P_GYRO_FS_2000DPS       (0x00 << 5)
#define ICM42688P_GYRO_FS_1000DPS       (0x01 << 5)
#define ICM42688P_GYRO_FS_500DPS        (0x02 << 5)
#define ICM42688P_GYRO_FS_250DPS        (0x03 << 5)
#define ICM42688P_GYRO_ODR_1KHZ         0x06
#define ICM42688P_GYRO_ODR_500HZ        0x0F

/* ============== ACCEL_CONFIG0 Values ============== */
#define ICM42688P_ACCEL_FS_16G          (0x00 << 5)
#define ICM42688P_ACCEL_FS_8G           (0x01 << 5)
#define ICM42688P_ACCEL_FS_4G           (0x02 << 5)
#define ICM42688P_ACCEL_FS_2G           (0x03 << 5)
#define ICM42688P_ACCEL_ODR_1KHZ        0x06
#define ICM42688P_ACCEL_ODR_500HZ       0x0F

/* ============== Sensitivity (for conversions) ============== */
#define ICM42688P_GYRO_SENS_2000DPS     16.4f    // LSB/dps
#define ICM42688P_ACCEL_SENS_16G        2048.0f  // LSB/g
#define ICM42688P_TEMP_SENS             132.48f  // LSB/°C
#define ICM42688P_TEMP_OFFSET           25.0f    // °C

/* ============== Data Structures ============== */
typedef struct {
    int16_t x;
    int16_t y;
    int16_t z;
} ICM42688P_RawData_t;

typedef struct {
    float x;
    float y;
    float z;
} ICM42688P_ScaledData_t;

typedef struct {
    ICM42688P_RawData_t accel_raw;
    ICM42688P_RawData_t gyro_raw;
    int16_t temp_raw;

    ICM42688P_ScaledData_t accel_g;      // in g
    ICM42688P_ScaledData_t gyro_dps;     // in degrees/sec
    float temp_c;                         // in Celsius
} ICM42688P_Data_t;

typedef enum {
    ICM42688P_OK = 0,
    ICM42688P_ERR_SPI,
    ICM42688P_ERR_ID,
    ICM42688P_ERR_TIMEOUT
} ICM42688P_Status_t;

/* ============== Function Prototypes ============== */

/**
 * @brief Initialize the ICM-42688-P
 * @param hspi Pointer to SPI handle
 * @return ICM42688P_OK on success, error code otherwise
 */
ICM42688P_Status_t ICM42688P_Init(SPI_HandleTypeDef *hspi);

/**
 * @brief Read WHO_AM_I register
 * @param hspi Pointer to SPI handle
 * @param id Pointer to store device ID
 * @return ICM42688P_OK on success
 */
ICM42688P_Status_t ICM42688P_ReadID(SPI_HandleTypeDef *hspi, uint8_t *id);

/**
 * @brief Read all sensor data (accel, gyro, temp)
 * @param hspi Pointer to SPI handle
 * @param data Pointer to data structure
 * @return ICM42688P_OK on success
 */
ICM42688P_Status_t ICM42688P_ReadAll(SPI_HandleTypeDef *hspi, ICM42688P_Data_t *data);

/**
 * @brief Read single register
 * @param hspi Pointer to SPI handle
 * @param reg Register address
 * @param data Pointer to store data
 * @return ICM42688P_OK on success
 */
ICM42688P_Status_t ICM42688P_ReadReg(SPI_HandleTypeDef *hspi, uint8_t reg, uint8_t *data);

/**
 * @brief Write single register
 * @param hspi Pointer to SPI handle
 * @param reg Register address
 * @param data Data to write
 * @return ICM42688P_OK on success
 */
ICM42688P_Status_t ICM42688P_WriteReg(SPI_HandleTypeDef *hspi, uint8_t reg, uint8_t data);

#endif /* INC_ICM42688P_H_ */
