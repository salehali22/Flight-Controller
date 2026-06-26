/*
 * iNAV target.h for SALEHFC
 * Custom STM32H743VIT6 flight controller
 *
 * NOTE: ICM42688P is on SPI6 — NOT supported by iNAV H743 HAL (SPI1-4 only)
 *       BMI270 on SPI3 is used as the sole IMU.
 *
 * NOTE: I2C4 and MAG removed — M8N magnetometer was causing I2C bus errors
 *       and triggering HWFAIL arming prevention. RTH works without compass
 *       since iNAV 7.1 using GPS-derived heading.
 */

 #pragma once

 #define TARGET_BOARD_IDENTIFIER "SLEH"
 #define USBD_PRODUCT_STRING     "SALEHFC"
 #define USE_VCP
 // Required by iNAV — declare which GPIO ports exist
 #define TARGET_IO_PORTA 0xffff
 #define TARGET_IO_PORTB 0xffff
 #define TARGET_IO_PORTC 0xffff
 #define TARGET_IO_PORTD 0xffff
 #define TARGET_IO_PORTE 0xffff
 
 // Use target.c for sensor bus registration (MATEKH743 pattern)
 #define USE_TARGET_CONFIG
 
 // ============================================================
 // LEDs
 // ============================================================
 #define LED0                    PB0
 #define LED1                    PC5
 
 // ============================================================
 // UARTs
 // ============================================================
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
 #define USE_SPI_DEVICE_1        // Flash W25Q128
 #define SPI1_SCK_PIN            PA5
 #define SPI1_MISO_PIN           PA6
 #define SPI1_MOSI_PIN           PA7
 
 #define USE_SPI_DEVICE_3        // BMI270
 #define SPI3_SCK_PIN            PC10
 #define SPI3_MISO_PIN           PC11
 #define SPI3_MOSI_PIN           PC12
 
 #define USE_SPI_DEVICE_4        // MAX7456 OSD
 #define SPI4_SCK_PIN            PE2
 #define SPI4_MISO_PIN           PE5
 #define SPI4_MOSI_PIN           PE6
 
 // SPI6 (ICM42688P) is NOT supported by iNAV — omitted
 
 // ============================================================
 // I2C — only I2C2 for BMP388 barometer
 // I2C4 removed: M8N mag caused bus errors → HWFAIL
 // ============================================================
 #define USE_I2C
 #define USE_I2C_DEVICE_2        // BMP388 barometer
 #define I2C2_SCL                PB10
 #define I2C2_SDA                PB11
 
 // ============================================================
 // IMU — BMI270 on SPI3 (sole IMU, ICM42688P on SPI6 unsupported)
 // ============================================================
 #define USE_IMU_BMI270
 #define IMU_BMI270_ALIGN        CW0_DEG
 #define BMI270_CS_PIN           PD3
 #define BMI270_SPI_BUS          BUS_SPI3
 #define GYRO_1_EXTI_PIN         PD2
 
 // ============================================================
 // Barometer — BMP388 on I2C2
 // ============================================================
 #define USE_BARO
 #define USE_BARO_BMP388
 #define BARO_I2C_BUS            BUS_I2C2
 
 // ============================================================
 // Magnetometer — REMOVED
 // M8N QMC5883L on I2C4 caused persistent I2C errors and HWFAIL.
 // RTH works without compass since iNAV 7.1 (GPS-derived heading).
 // To re-enable: add I2C4 back, define USE_MAG + driver + bus.
 // ============================================================
 
 // ============================================================
 // OSD — MAX7456 on SPI4
 // ============================================================
 #define USE_MAX7456
 #define MAX7456_SPI_BUS         BUS_SPI4
 #define MAX7456_CS_PIN          PC13
 
 // ============================================================
 // Flash — W25Q128 on SPI1
 // ============================================================
 #define USE_FLASHFS
 #define USE_FLASH_W25Q128FV
 #define FLASH_CS_PIN            PA4
 #define FLASH_SPI_BUS           BUS_SPI1
 
 // ============================================================
 // ADC
 // PC1  → VBAT  (ADC1)
 // PC3  → Current (ADC3 — H743 quirk for PC3_C)
 // ============================================================
 #define USE_ADC
 #define ADC_CHANNEL_1_PIN               PC1
 #define ADC_CHANNEL_2_PIN               PC3
 #define VBAT_ADC_CHANNEL                ADC_CHN_1
 #define CURRENT_METER_ADC_CHANNEL       ADC_CHN_2
 
 // ============================================================
 // RC Input — CRSF on USART3
 // ============================================================
 #define DEFAULT_RX_TYPE         RX_TYPE_SERIAL
 #define SERIALRX_PROVIDER       SERIALRX_CRSF
 #define SERIALRX_UART           SERIAL_PORT_USART3
 
 // ============================================================
 // GPS — uses UART, not I2C. Kept for RTH/nav modes.
 // ============================================================
 #define USE_GPS
 
 // ============================================================
 // Features
 // ============================================================
 #define USE_DSHOT
 #define USE_ESC_SENSOR
 #define DEFAULT_FEATURES        (FEATURE_TX_PROF_SEL | FEATURE_BLACKBOX | FEATURE_VBAT | FEATURE_CURRENT_METER)
 #define DEFAULT_VOLTAGE_METER_SOURCE    VOLTAGE_METER_ADC
 #define DEFAULT_CURRENT_METER_SOURCE    CURRENT_METER_ADC

 #define MAX_PWM_OUTPUT_PORTS 12
 #define TARGET_MOTOR_COUNT 4