/**
 * @file bmp388.c
 * @brief BMP388 Barometric Pressure Sensor Driver Implementation
 *
 * Compensation formulas from Bosch BMP388 Datasheet Appendix 8.
 * Uses floating-point compensation for accuracy.
 */

#include "bmp388.h"
#include <math.h>

/*===========================================================================*/
/* Private Defines                                                           */
/*===========================================================================*/
#define BMP388_I2C_TIMEOUT      100     // I2C timeout in ms
#define BMP388_CALIB_DATA_LEN   21      // Calibration data length in bytes

/*===========================================================================*/
/* Private Function Prototypes                                               */
/*===========================================================================*/
static BMP388_Status BMP388_ReadReg(BMP388_Handle *dev, uint8_t reg, uint8_t *data, uint16_t len);
static BMP388_Status BMP388_WriteReg(BMP388_Handle *dev, uint8_t reg, uint8_t data);
static BMP388_Status BMP388_ReadCalibData(BMP388_Handle *dev);
static void BMP388_ParseCalibData(BMP388_Handle *dev, uint8_t *raw_data);
static double BMP388_CompensateTemperature(BMP388_Handle *dev, uint32_t raw_temp);
static double BMP388_CompensatePressure(BMP388_Handle *dev, uint32_t raw_press);

/*===========================================================================*/
/* I2C Read/Write Functions                                                  */
/*===========================================================================*/

static BMP388_Status BMP388_ReadReg(BMP388_Handle *dev, uint8_t reg, uint8_t *data, uint16_t len)
{
    if (dev == NULL || dev->hi2c == NULL || data == NULL) {
        return BMP388_ERR_NULL_PTR;
    }

    HAL_StatusTypeDef status = HAL_I2C_Mem_Read(
        dev->hi2c,
        (dev->i2c_addr << 1),       // HAL expects 8-bit address
        reg,
        I2C_MEMADD_SIZE_8BIT,
        data,
        len,
        BMP388_I2C_TIMEOUT
    );

    return (status == HAL_OK) ? BMP388_OK : BMP388_ERR_COMM;
}

static BMP388_Status BMP388_WriteReg(BMP388_Handle *dev, uint8_t reg, uint8_t data)
{
    if (dev == NULL || dev->hi2c == NULL) {
        return BMP388_ERR_NULL_PTR;
    }

    HAL_StatusTypeDef status = HAL_I2C_Mem_Write(
        dev->hi2c,
        (dev->i2c_addr << 1),
        reg,
        I2C_MEMADD_SIZE_8BIT,
        &data,
        1,
        BMP388_I2C_TIMEOUT
    );

    return (status == HAL_OK) ? BMP388_OK : BMP388_ERR_COMM;
}

/*===========================================================================*/
/* Calibration Data Functions                                                */
/*===========================================================================*/

static BMP388_Status BMP388_ReadCalibData(BMP388_Handle *dev)
{
    uint8_t raw_data[BMP388_CALIB_DATA_LEN];
    BMP388_Status status;

    status = BMP388_ReadReg(dev, BMP388_REG_CALIB_DATA, raw_data, BMP388_CALIB_DATA_LEN);
    if (status != BMP388_OK) {
        return status;
    }

    BMP388_ParseCalibData(dev, raw_data);
    return BMP388_OK;
}

/**
 * @brief Parse raw calibration bytes into coefficients
 * Reference: Datasheet Table 22 - Trimming Coefficients
 */
static void BMP388_ParseCalibData(BMP388_Handle *dev, uint8_t *raw_data)
{
    // Parse raw NVM data into calibration structure
    dev->calib.par_t1 = (uint16_t)(raw_data[1] << 8 | raw_data[0]);
    dev->calib.par_t2 = (uint16_t)(raw_data[3] << 8 | raw_data[2]);
    dev->calib.par_t3 = (int8_t)raw_data[4];

    dev->calib.par_p1 = (int16_t)(raw_data[6] << 8 | raw_data[5]);
    dev->calib.par_p2 = (int16_t)(raw_data[8] << 8 | raw_data[7]);
    dev->calib.par_p3 = (int8_t)raw_data[9];
    dev->calib.par_p4 = (int8_t)raw_data[10];
    dev->calib.par_p5 = (uint16_t)(raw_data[12] << 8 | raw_data[11]);
    dev->calib.par_p6 = (uint16_t)(raw_data[14] << 8 | raw_data[13]);
    dev->calib.par_p7 = (int8_t)raw_data[15];
    dev->calib.par_p8 = (int8_t)raw_data[16];
    dev->calib.par_p9 = (int16_t)(raw_data[18] << 8 | raw_data[17]);
    dev->calib.par_p10 = (int8_t)raw_data[19];
    dev->calib.par_p11 = (int8_t)raw_data[20];

    // Calculate quantized calibration coefficients
    // Reference: Datasheet Section 8.4 - Calibration Coefficient
    dev->qcalib.par_t1 = (double)dev->calib.par_t1 / pow(2, -8);
    dev->qcalib.par_t2 = (double)dev->calib.par_t2 / pow(2, 30);
    dev->qcalib.par_t3 = (double)dev->calib.par_t3 / pow(2, 48);

    dev->qcalib.par_p1 = ((double)dev->calib.par_p1 - pow(2, 14)) / pow(2, 20);
    dev->qcalib.par_p2 = ((double)dev->calib.par_p2 - pow(2, 14)) / pow(2, 29);
    dev->qcalib.par_p3 = (double)dev->calib.par_p3 / pow(2, 32);
    dev->qcalib.par_p4 = (double)dev->calib.par_p4 / pow(2, 37);
    dev->qcalib.par_p5 = (double)dev->calib.par_p5 / pow(2, -3);
    dev->qcalib.par_p6 = (double)dev->calib.par_p6 / pow(2, 6);
    dev->qcalib.par_p7 = (double)dev->calib.par_p7 / pow(2, 8);
    dev->qcalib.par_p8 = (double)dev->calib.par_p8 / pow(2, 15);
    dev->qcalib.par_p9 = (double)dev->calib.par_p9 / pow(2, 48);
    dev->qcalib.par_p10 = (double)dev->calib.par_p10 / pow(2, 48);
    dev->qcalib.par_p11 = (double)dev->calib.par_p11 / pow(2, 65);
}

/*===========================================================================*/
/* Compensation Functions                                                    */
/* Reference: Datasheet Section 8.5 & 8.6                                    */
/*===========================================================================*/

/**
 * @brief Compensate raw temperature to Celsius
 * Also stores t_lin for pressure compensation
 */
static double BMP388_CompensateTemperature(BMP388_Handle *dev, uint32_t raw_temp)
{
    double partial_data1;
    double partial_data2;

    partial_data1 = (double)(raw_temp - dev->qcalib.par_t1);
    partial_data2 = (double)(partial_data1 * dev->qcalib.par_t2);

    // Store linearized temperature for pressure compensation
    dev->t_lin = partial_data2 + (partial_data1 * partial_data1) * dev->qcalib.par_t3;

    return dev->t_lin;
}

/**
 * @brief Compensate raw pressure to Pascals
 * Must call CompensateTemperature first to set t_lin
 */
static double BMP388_CompensatePressure(BMP388_Handle *dev, uint32_t raw_press)
{
    double partial_data1;
    double partial_data2;
    double partial_data3;
    double partial_data4;
    double partial_out1;
    double partial_out2;
    double comp_press;

    // Get t_lin from previous temperature compensation
    double t_lin = dev->t_lin;

    partial_data1 = dev->qcalib.par_p6 * t_lin;
    partial_data2 = dev->qcalib.par_p7 * (t_lin * t_lin);
    partial_data3 = dev->qcalib.par_p8 * (t_lin * t_lin * t_lin);
    partial_out1 = dev->qcalib.par_p5 + partial_data1 + partial_data2 + partial_data3;

    partial_data1 = dev->qcalib.par_p2 * t_lin;
    partial_data2 = dev->qcalib.par_p3 * (t_lin * t_lin);
    partial_data3 = dev->qcalib.par_p4 * (t_lin * t_lin * t_lin);
    partial_out2 = (double)raw_press *
                   (dev->qcalib.par_p1 + partial_data1 + partial_data2 + partial_data3);

    partial_data1 = (double)raw_press * (double)raw_press;
    partial_data2 = dev->qcalib.par_p9 + dev->qcalib.par_p10 * t_lin;
    partial_data3 = partial_data1 * partial_data2;
    partial_data4 = partial_data3 +
                    ((double)raw_press * (double)raw_press * (double)raw_press) * dev->qcalib.par_p11;

    comp_press = partial_out1 + partial_out2 + partial_data4;

    return comp_press;
}

/*===========================================================================*/
/* Public API Functions                                                      */
/*===========================================================================*/

BMP388_Status BMP388_Init(BMP388_Handle *dev, I2C_HandleTypeDef *hi2c, uint8_t addr)
{
    BMP388_Status status;
    uint8_t chip_id;

    if (dev == NULL || hi2c == NULL) {
        return BMP388_ERR_NULL_PTR;
    }

    // Initialize handle
    dev->hi2c = hi2c;
    dev->i2c_addr = addr;
    dev->t_lin = 0.0;

    // Check if device is present
    if (HAL_I2C_IsDeviceReady(hi2c, (addr << 1), 3, BMP388_I2C_TIMEOUT) != HAL_OK) {
        return BMP388_ERR_COMM;
    }

    // Read and verify chip ID
    status = BMP388_ReadReg(dev, BMP388_REG_CHIP_ID, &chip_id, 1);
    if (status != BMP388_OK) {
        return status;
    }

    dev->chip_id = chip_id;

    // Accept both BMP388 (0x50) and BMP390 (0x60)
    if (chip_id != BMP388_CHIP_ID && chip_id != BMP390_CHIP_ID) {
        return BMP388_ERR_CHIP_ID;
    }

    // Soft reset
    status = BMP388_SoftReset(dev);
    if (status != BMP388_OK) {
        return status;
    }

    // Wait for reset to complete
    HAL_Delay(5);

    // Read calibration data
    status = BMP388_ReadCalibData(dev);
    if (status != BMP388_OK) {
        return status;
    }

    // Apply default configuration (suitable for drones)
    BMP388_Config default_config = {
        .osr_press = BMP388_OSR_x8,      // 8x oversampling for pressure
        .osr_temp = BMP388_OSR_x1,       // 1x for temperature
        .iir_filter = BMP388_IIR_COEF_3, // IIR filter coefficient 3
        .odr = BMP388_ODR_50_HZ          // 50 Hz output rate
    };

    status = BMP388_Configure(dev, &default_config);
    if (status != BMP388_OK) {
        return status;
    }

    return BMP388_OK;
}

BMP388_Status BMP388_SoftReset(BMP388_Handle *dev)
{
    return BMP388_WriteReg(dev, BMP388_REG_CMD, BMP388_CMD_SOFT_RESET);
}

BMP388_Status BMP388_Configure(BMP388_Handle *dev, BMP388_Config *config)
{
    BMP388_Status status;

    if (dev == NULL || config == NULL) {
        return BMP388_ERR_NULL_PTR;
    }

    // Store configuration
    dev->config = *config;

    // Set oversampling register (OSR)
    // Bits [5:3] = osr_t, Bits [2:0] = osr_p
    uint8_t osr_reg = ((config->osr_temp & 0x07) << 3) | (config->osr_press & 0x07);
    status = BMP388_WriteReg(dev, BMP388_REG_OSR, osr_reg);
    if (status != BMP388_OK) return status;

    // Set output data rate (ODR)
    status = BMP388_WriteReg(dev, BMP388_REG_ODR, config->odr);
    if (status != BMP388_OK) return status;

    // Set IIR filter configuration
    // Bits [3:1] = iir_filter
    uint8_t config_reg = (config->iir_filter & 0x07) << 1;
    status = BMP388_WriteReg(dev, BMP388_REG_CONFIG, config_reg);
    if (status != BMP388_OK) return status;

    return BMP388_OK;
}

BMP388_Status BMP388_SetPowerMode(BMP388_Handle *dev, uint8_t mode)
{
    // Enable pressure and temperature, set mode
    uint8_t pwr_ctrl = BMP388_PWR_PRESS_EN | BMP388_PWR_TEMP_EN | mode;
    return BMP388_WriteReg(dev, BMP388_REG_PWR_CTRL, pwr_ctrl);
}

BMP388_Status BMP388_IsDataReady(BMP388_Handle *dev, bool *ready)
{
    uint8_t status_reg;
    BMP388_Status status;

    if (dev == NULL || ready == NULL) {
        return BMP388_ERR_NULL_PTR;
    }

    status = BMP388_ReadReg(dev, BMP388_REG_STATUS, &status_reg, 1);
    if (status != BMP388_OK) {
        return status;
    }

    *ready = (status_reg & (BMP388_STATUS_DRDY_PRESS | BMP388_STATUS_DRDY_TEMP)) ==
             (BMP388_STATUS_DRDY_PRESS | BMP388_STATUS_DRDY_TEMP);

    return BMP388_OK;
}

BMP388_Status BMP388_ReadData(BMP388_Handle *dev, BMP388_Data *data)
{
    BMP388_Status status;
    uint8_t raw_data[6];
    uint32_t raw_press, raw_temp;
    bool ready;
    uint32_t timeout;

    if (dev == NULL || data == NULL) {
        return BMP388_ERR_NULL_PTR;
    }

    // Trigger measurement (forced mode)
    status = BMP388_SetPowerMode(dev, BMP388_PWR_MODE_FORCED);
    if (status != BMP388_OK) {
        return status;
    }

    // Wait for data ready with timeout
    timeout = HAL_GetTick() + 100; // 100ms timeout
    do {
        status = BMP388_IsDataReady(dev, &ready);
        if (status != BMP388_OK) {
            return status;
        }
        if (HAL_GetTick() > timeout) {
            return BMP388_ERR_TIMEOUT;
        }
    } while (!ready);

    // Read pressure and temperature data (6 bytes starting from DATA_0)
    status = BMP388_ReadReg(dev, BMP388_REG_DATA_0, raw_data, 6);
    if (status != BMP388_OK) {
        return status;
    }

    // Parse raw data (XLSB, LSB, MSB order)
    raw_press = (uint32_t)raw_data[0] |
                ((uint32_t)raw_data[1] << 8) |
                ((uint32_t)raw_data[2] << 16);

    raw_temp = (uint32_t)raw_data[3] |
               ((uint32_t)raw_data[4] << 8) |
               ((uint32_t)raw_data[5] << 16);

    // Compensate temperature first (sets t_lin for pressure compensation)
    data->temperature = BMP388_CompensateTemperature(dev, raw_temp);

    // Compensate pressure
    data->pressure = BMP388_CompensatePressure(dev, raw_press);

    // Calculate altitude (using standard sea level pressure)
    data->altitude = BMP388_CalculateAltitude(data->pressure, 101325.0);

    return BMP388_OK;
}

BMP388_Status BMP388_ReadTemperature(BMP388_Handle *dev, double *temperature)
{
    BMP388_Data data;
    BMP388_Status status = BMP388_ReadData(dev, &data);
    if (status == BMP388_OK) {
        *temperature = data.temperature;
    }
    return status;
}

BMP388_Status BMP388_ReadPressure(BMP388_Handle *dev, double *pressure)
{
    BMP388_Data data;
    BMP388_Status status = BMP388_ReadData(dev, &data);
    if (status == BMP388_OK) {
        *pressure = data.pressure;
    }
    return status;
}

double BMP388_CalculateAltitude(double pressure, double sea_level_pressure)
{
    // Hypsometric formula
    // altitude = 44330 * (1 - (P/P0)^(1/5.255))
    return 44330.0 * (1.0 - pow(pressure / sea_level_pressure, 1.0 / 5.255));
}

BMP388_Status BMP388_GetChipID(BMP388_Handle *dev, uint8_t *chip_id)
{
    if (dev == NULL || chip_id == NULL) {
        return BMP388_ERR_NULL_PTR;
    }
    return BMP388_ReadReg(dev, BMP388_REG_CHIP_ID, chip_id, 1);
}

BMP388_Status BMP388_GetError(BMP388_Handle *dev, uint8_t *err)
{
    if (dev == NULL || err == NULL) {
        return BMP388_ERR_NULL_PTR;
    }
    return BMP388_ReadReg(dev, BMP388_REG_ERR_REG, err, 1);
}
