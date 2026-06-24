/*
 * ICM-42688p.c
 *
 *  Created on: Dec 26, 2025
 *      Author: Saleh work and edu
 */


/**
 * @file icm42688p.c
 * @brief ICM-42688-P 6-axis IMU driver implementation
 */

#include "icm42688p.h"

/* ============== Private Macros ============== */
#define ICM42688P_READ_BIT      0x80
#define ICM42688P_SPI_TIMEOUT   100

/* ============== Private Functions ============== */

static inline void CS_Low(void) {
    HAL_GPIO_WritePin(ICM42688P_CS_PORT, ICM42688P_CS_PIN, GPIO_PIN_RESET);
}

static inline void CS_High(void) {
    HAL_GPIO_WritePin(ICM42688P_CS_PORT, ICM42688P_CS_PIN, GPIO_PIN_SET);
}

/* ============== Public Functions ============== */

ICM42688P_Status_t ICM42688P_ReadReg(SPI_HandleTypeDef *hspi, uint8_t reg, uint8_t *data)
{
    uint8_t tx[2] = { reg | ICM42688P_READ_BIT, 0x00 };
    uint8_t rx[2] = { 0 };
    HAL_StatusTypeDef status;

    CS_Low();
    status = HAL_SPI_TransmitReceive(hspi, tx, rx, 2, ICM42688P_SPI_TIMEOUT);
    CS_High();

    if (status != HAL_OK) {
        return ICM42688P_ERR_SPI;
    }

    *data = rx[1];
    return ICM42688P_OK;
}

ICM42688P_Status_t ICM42688P_WriteReg(SPI_HandleTypeDef *hspi, uint8_t reg, uint8_t data)
{
    uint8_t tx[2] = { reg & 0x7F, data };  // Clear read bit for write
    HAL_StatusTypeDef status;

    CS_Low();
    status = HAL_SPI_Transmit(hspi, tx, 2, ICM42688P_SPI_TIMEOUT);
    CS_High();

    if (status != HAL_OK) {
        return ICM42688P_ERR_SPI;
    }

    return ICM42688P_OK;
}

ICM42688P_Status_t ICM42688P_ReadID(SPI_HandleTypeDef *hspi, uint8_t *id)
{
    return ICM42688P_ReadReg(hspi, ICM42688P_REG_WHO_AM_I, id);
}

static ICM42688P_Status_t ICM42688P_ReadMulti(SPI_HandleTypeDef *hspi, uint8_t reg, uint8_t *data, uint16_t len)
{
    uint8_t tx_reg = reg | ICM42688P_READ_BIT;
    HAL_StatusTypeDef status;

    CS_Low();

    // Send register address
    status = HAL_SPI_Transmit(hspi, &tx_reg, 1, ICM42688P_SPI_TIMEOUT);
    if (status != HAL_OK) {
        CS_High();
        return ICM42688P_ERR_SPI;
    }

    // Read data bytes
    status = HAL_SPI_Receive(hspi, data, len, ICM42688P_SPI_TIMEOUT);
    CS_High();

    if (status != HAL_OK) {
        return ICM42688P_ERR_SPI;
    }

    return ICM42688P_OK;
}

ICM42688P_Status_t ICM42688P_Init(SPI_HandleTypeDef *hspi)
{
    ICM42688P_Status_t status;
    uint8_t id;

    // Ensure CS starts high
    CS_High();
    HAL_Delay(10);

    // Soft reset
    status = ICM42688P_WriteReg(hspi, ICM42688P_REG_DEVICE_CONFIG, 0x01);
    if (status != ICM42688P_OK) return status;
    HAL_Delay(10);  // Wait for reset

    // Verify device ID
    status = ICM42688P_ReadID(hspi, &id);
    if (status != ICM42688P_OK) return status;

    if (id != ICM42688P_WHO_AM_I_VAL) {
        return ICM42688P_ERR_ID;  // Wrong device or SPI issue
    }

    // Select Bank 0 (should already be default after reset)
    status = ICM42688P_WriteReg(hspi, ICM42688P_REG_BANK_SEL, 0x00);
    if (status != ICM42688P_OK) return status;

    // Configure Gyro: ±2000dps, 1kHz ODR
    status = ICM42688P_WriteReg(hspi, ICM42688P_REG_GYRO_CONFIG0,
                                 ICM42688P_GYRO_FS_2000DPS | ICM42688P_GYRO_ODR_1KHZ);
    if (status != ICM42688P_OK) return status;

    // Configure Accel: ±16g, 1kHz ODR
    status = ICM42688P_WriteReg(hspi, ICM42688P_REG_ACCEL_CONFIG0,
                                 ICM42688P_ACCEL_FS_16G | ICM42688P_ACCEL_ODR_1KHZ);
    if (status != ICM42688P_OK) return status;

    // Power on Gyro and Accel in Low Noise mode
    status = ICM42688P_WriteReg(hspi, ICM42688P_REG_PWR_MGMT0,
                                 ICM42688P_PWR_GYRO_MODE_LN | ICM42688P_PWR_ACCEL_MODE_LN);
    if (status != ICM42688P_OK) return status;

    HAL_Delay(50);  // Wait for sensors to stabilize

    return ICM42688P_OK;
}

ICM42688P_Status_t ICM42688P_ReadAll(SPI_HandleTypeDef *hspi, ICM42688P_Data_t *data)
{
    ICM42688P_Status_t status;
    uint8_t buf[14];  // Temp(2) + Accel(6) + Gyro(6)

    // Burst read starting from TEMP_DATA1 (0x1D)
    status = ICM42688P_ReadMulti(hspi, ICM42688P_REG_TEMP_DATA1, buf, 14);
    if (status != ICM42688P_OK) return status;

    // Parse raw data (Big Endian: High byte first)
    data->temp_raw = (int16_t)((buf[0] << 8) | buf[1]);

    data->accel_raw.x = (int16_t)((buf[2] << 8) | buf[3]);
    data->accel_raw.y = (int16_t)((buf[4] << 8) | buf[5]);
    data->accel_raw.z = (int16_t)((buf[6] << 8) | buf[7]);

    data->gyro_raw.x = (int16_t)((buf[8] << 8) | buf[9]);
    data->gyro_raw.y = (int16_t)((buf[10] << 8) | buf[11]);
    data->gyro_raw.z = (int16_t)((buf[12] << 8) | buf[13]);

    // Convert to physical units
    data->temp_c = ((float)data->temp_raw / ICM42688P_TEMP_SENS) + ICM42688P_TEMP_OFFSET;

    data->accel_g.x = (float)data->accel_raw.x / ICM42688P_ACCEL_SENS_16G;
    data->accel_g.y = (float)data->accel_raw.y / ICM42688P_ACCEL_SENS_16G;
    data->accel_g.z = (float)data->accel_raw.z / ICM42688P_ACCEL_SENS_16G;

    data->gyro_dps.x = (float)data->gyro_raw.x / ICM42688P_GYRO_SENS_2000DPS;
    data->gyro_dps.y = (float)data->gyro_raw.y / ICM42688P_GYRO_SENS_2000DPS;
    data->gyro_dps.z = (float)data->gyro_raw.z / ICM42688P_GYRO_SENS_2000DPS;

    return ICM42688P_OK;
}
