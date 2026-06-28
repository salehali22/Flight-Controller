/*
 * Betaflight 4.5.1 target.h for SALFC
 * Custom STM32H743VIT6 flight controller
 */

#pragma once

#define TARGET_BOARD_IDENTIFIER "SLEH"
#define USBD_PRODUCT_STRING     "SALFC"

// ============================================================
// Platform defines (required by STM32H743)
// ============================================================
#define USE_EXTI
#define USE_TIMER_UP_CONFIG
#define USE_USB_DETECT
#define USE_BEEPER
#define USE_ESCSERIAL
#define FLASH_PAGE_SIZE ((uint32_t)0x20000)

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
// UARTs
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
#define SPI_FULL_RECONFIGURABILITY
#define USE_SPI_DMA_ENABLE_LATE

#define USE_SPI_DEVICE_1
#define SPI1_SCK_PIN            PA5
#define SPI1_SDI_PIN            PA6
#define SPI1_SDO_PIN            PA7

#define USE_SPI_DEVICE_3
#define SPI3_SCK_PIN            PC10
#define SPI3_SDI_PIN            PC11
#define SPI3_SDO_PIN            PC12

#define USE_SPI_DEVICE_4
#define SPI4_SCK_PIN            PE2
#define SPI4_SDI_PIN            PE5
#define SPI4_SDO_PIN            PE6

#define USE_SPI_DEVICE_6
#define SPI6_SCK_PIN            PB3
#define SPI6_SDI_PIN            PB4
#define SPI6_SDO_PIN            PB5

// ============================================================
// I2C
// ============================================================
#define USE_I2C
#define I2C_FULL_RECONFIGURABILITY
#define USE_I2C_DEVICE_2
#define I2C2_SCL                PB10
#define I2C2_SDA                PB11

// ============================================================
// Gyro / Acc (dual IMU, BF supports SPI6)
// ============================================================
#define USE_ACC
#define USE_GYRO
#define USE_ACC_SPI_ICM42688P
#define USE_GYRO_SPI_ICM42688P
#define GYRO_1_SPI_INSTANCE     SPI6
#define GYRO_1_CS_PIN           PD7
#define GYRO_1_EXTI_PIN         PE4
#define GYRO_1_ALIGN            CW0_DEG

#define USE_ACC_SPI_BMI270
#define USE_GYRO_SPI_BMI270
#define GYRO_2_SPI_INSTANCE     SPI3
#define GYRO_2_CS_PIN           PD3
#define GYRO_2_EXTI_PIN         PD2
#define GYRO_2_ALIGN            CW0_DEG

// ============================================================
// Baro
// ============================================================
#define USE_BARO
#define USE_BARO_BMP388
#define BARO_I2C_INSTANCE       I2CDEV_2

// ============================================================
// OSD
// ============================================================
#define USE_MAX7456
#define MAX7456_SPI_INSTANCE    SPI4
#define MAX7456_CS_PIN          PC13

// ============================================================
// Flash
// ============================================================
#define ENABLE_BLACKBOX_LOGGING_ON_SPIFLASH_BY_DEFAULT
#define USE_FLASHFS
#define USE_FLASH_W25Q128FV
#define FLASH_CS_PIN            PA4
#define FLASH_SPI_INSTANCE      SPI1

// ============================================================
// ADC
// ============================================================
#define USE_ADC
#define ADC_VBAT_PIN            PC1
#define ADC_CURR_PIN            PC3
#define DEFAULT_VOLTAGE_METER_SOURCE    VOLTAGE_METER_ADC
#define DEFAULT_CURRENT_METER_SOURCE    CURRENT_METER_ADC

// ============================================================
// RC Input (CRSF on UART3)
// ============================================================
#define SERIALRX_UART           SERIAL_PORT_USART3
#define DEFAULT_RX_FEATURE      FEATURE_RX_SERIAL
#define SERIALRX_PROVIDER       SERIALRX_CRSF

// ============================================================
// Motor / Servo / Timer mapping
// M1-M4: TIM1 (PE9, PE11, PE13, PE14)
// M5-M8: TIM8 (PC6, PC7, PC8, PC9)
// S1-S4: TIM4 (PD12, PD13, PD14, PD15)
// ============================================================
#define USE_DSHOT
#define USE_ESC_SENSOR

#define TIMER_PIN_MAPPING \
    TIMER_PIN_MAP( 0, PE9 , 1,  0) \
    TIMER_PIN_MAP( 1, PE11, 1,  1) \
    TIMER_PIN_MAP( 2, PE13, 1,  2) \
    TIMER_PIN_MAP( 3, PE14, 1,  3) \
    TIMER_PIN_MAP( 4, PC6 , 2,  0) \
    TIMER_PIN_MAP( 5, PC7 , 2,  1) \
    TIMER_PIN_MAP( 6, PC8 , 2,  2) \
    TIMER_PIN_MAP( 7, PC9 , 2,  3) \
    TIMER_PIN_MAP( 8, PD12, 1,  0) \
    TIMER_PIN_MAP( 9, PD13, 1,  0) \
    TIMER_PIN_MAP(10, PD14, 1,  0) \
    TIMER_PIN_MAP(11, PD15, 1,  0)

#define ADC1_DMA_OPT            9
#define ADC3_DMA_OPT            10

#define DEFAULT_FEATURES        (FEATURE_OSD)
