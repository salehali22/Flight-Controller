/*
 * Betaflight 4.5.1 target.h for SALEHFC
 * Custom STM32H743VIT6 flight controller
 *
 * Translated from iNAV SALEHFC target with the following differences:
 *   - Both IMUs enabled (BF supports SPI6 on H743, iNAV does not)
 *     GYRO_1 = ICM42688P on SPI6, GYRO_2 = BMI270 on SPI3
 *   - SERIALRX on UART3 (matching iNAV, changed from original BF UART8)
 *   - Motor order: TIM1 first (M1-M4), TIM8 second (M5-M8)
 *   - Servo outputs on TIM4 (S1-S4) included
 *   - I2C4 / MAG removed (M8N caused bus errors and HWFAIL)
 *
 * Pin naming: BF 4.5.1 uses SDI/SDO, not MISO/MOSI.
 * Do NOT add CONFIG_IN_EXTERNAL_FLASH or USE_EXST (internal flash board).
 */

#pragma once

#define TARGET_BOARD_IDENTIFIER "SLEH"
#define USBD_PRODUCT_STRING     "SALEHFC"

#define USE_TARGET_CONFIG

// Required: declare which GPIO ports are in use
#define TARGET_IO_PORTA 0xffff
#define TARGET_IO_PORTB 0xffff
#define TARGET_IO_PORTC 0xffff
#define TARGET_IO_PORTD 0xffff
#define TARGET_IO_PORTE 0xffff

// ============================================================
// LEDs
// ============================================================
#define LED0_PIN                PB0
#define LED1_PIN                PC5

// ============================================================
// UARTs (7 hardware + VCP = 8 serial ports)
// ============================================================
#define USE_VCP

#define USE_UART1
#define UART1_TX_PIN            PB14
#define UART1_RX_PIN            PB15

#define USE_UART2
#define UART2_TX_PIN            PA2
#define UART2_RX_PIN            PA3

#define USE_UART3
#define UART3_TX_PIN            PD8
#define UART3_RX_PIN            PD9

#define USE_UART4
#define UART4_TX_PIN            PA0
#define UART4_RX_PIN            PA1

#define USE_UART5
#define UART5_TX_PIN            PB13
#define UART5_RX_PIN            PB12

#define USE_UART7
#define UART7_TX_PIN            PE8
#define UART7_RX_PIN            PE7

#define USE_UART8
#define UART8_TX_PIN            PE1
#define UART8_RX_PIN            PE0

#define SERIAL_PORT_COUNT       8

// ============================================================
// SPI
// ============================================================
#define USE_SPI

#define USE_SPI_DEVICE_1                // Flash W25Q128
#define SPI1_SCK_PIN            PA5
#define SPI1_SDI_PIN            PA6
#define SPI1_SDO_PIN            PA7

#define USE_SPI_DEVICE_3                // BMI270 (GYRO_2)
#define SPI3_SCK_PIN            PC10
#define SPI3_SDI_PIN            PC11
#define SPI3_SDO_PIN            PC12

#define USE_SPI_DEVICE_4                // MAX7456 OSD
#define SPI4_SCK_PIN            PE2
#define SPI4_SDI_PIN            PE5
#define SPI4_SDO_PIN            PE6

#define USE_SPI_DEVICE_6                // ICM42688P (GYRO_1)
#define SPI6_SCK_PIN            PB3
#define SPI6_SDI_PIN            PB4
#define SPI6_SDO_PIN            PB5

// ============================================================
// I2C (I2C2 only, I2C4 removed due to M8N mag bus errors)
// ============================================================
#define USE_I2C
#define USE_I2C_DEVICE_2                // BMP388 barometer
#define I2C2_SCL                PB10
#define I2C2_SDA                PB11

// ============================================================
// Gyro / Accelerometer
// GYRO_1 = ICM42688P on SPI6 (BF supports SPI6, iNAV does not)
// GYRO_2 = BMI270 on SPI3
// ============================================================
#define USE_ACC
#define USE_GYRO

#define USE_GYRO_SPI_ICM42688P
#define USE_ACC_SPI_ICM42688P
#define GYRO_1_SPI_INSTANCE     SPI6
#define GYRO_1_CS_PIN           PD7
#define GYRO_1_EXTI_PIN         PE4
#define GYRO_1_ALIGN            CW0_DEG

#define USE_GYRO_SPI_BMI270
#define USE_ACC_SPI_BMI270
#define GYRO_2_SPI_INSTANCE     SPI3
#define GYRO_2_CS_PIN           PD3
#define GYRO_2_EXTI_PIN         PD2
#define GYRO_2_ALIGN            CW0_DEG

// ============================================================
// Barometer (BMP388 on I2C2)
// ============================================================
#define USE_BARO
#define USE_BARO_BMP388
#define BARO_I2C_INSTANCE       I2CDEV_2

// ============================================================
// Magnetometer: REMOVED
// M8N QMC5883L on I2C4 caused persistent I2C errors and HWFAIL.
// To re-enable: add USE_I2C_DEVICE_4, I2C4_SCL/SDA, USE_MAG,
// MAG_I2C_INSTANCE I2CDEV_4.
// ============================================================

// ============================================================
// OSD (MAX7456 on SPI4)
// ============================================================
#define USE_MAX7456
#define MAX7456_SPI_INSTANCE    SPI4
#define MAX7456_CS_PIN          PC13

// ============================================================
// Flash (W25Q128 on SPI1)
// ============================================================
#define ENABLE_BLACKBOX_LOGGING_ON_SPIFLASH_BY_DEFAULT
#define USE_FLASHFS
#define USE_FLASH_W25Q128FV
#define FLASH_CS_PIN            PA4
#define FLASH_SPI_INSTANCE      SPI1

// ============================================================
// ADC
// PC1 = VBAT (ADC1)
// PC3 = Current (ADC3, H743 PC3_C quirk)
// ============================================================
#define USE_ADC
#define ADC_VBAT_PIN            PC1
#define ADC_CURR_PIN            PC3
#define DEFAULT_VOLTAGE_METER_SOURCE    VOLTAGE_METER_ADC
#define DEFAULT_CURRENT_METER_SOURCE    CURRENT_METER_ADC

// ============================================================
// RC Input (CRSF on UART3, matching iNAV)
// ============================================================
#define SERIALRX_UART           SERIAL_PORT_USART3
#define DEFAULT_RX_FEATURE      FEATURE_RX_SERIAL
#define SERIALRX_PROVIDER       SERIALRX_CRSF

// ============================================================
// Motor / Servo outputs
// M1-M4: TIM1 (PE9, PE11, PE13, PE14) - primary quad, DSHOT
// M5-M8: TIM8 (PC6, PC7, PC8, PC9)   - aux motors
// S1-S4: TIM4 (PD12, PD13, PD14, PD15) - servos
// ============================================================
#define USE_DSHOT
#define USE_ESC_SENSOR

// ============================================================
// Timer / DMA
// ============================================================
#define USABLE_TIMER_CHANNEL_COUNT  12
#define USED_TIMERS             (TIM_N(1) | TIM_N(4) | TIM_N(8))

#define ADC1_DMA_OPT            9
#define ADC3_DMA_OPT            10

// ============================================================
// Default features
// ============================================================
#define DEFAULT_FEATURES        (FEATURE_OSD)
