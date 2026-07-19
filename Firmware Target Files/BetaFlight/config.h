/*
 * Betaflight target config for custom H743VIT6 flight controller
 * Board: SALFC
 */

 #pragma once

 #define FC_TARGET_MCU     STM32H743
 
 #define BOARD_NAME        SALFC
 #define MANUFACTURER_ID   SLEH
 
 // ---- Gyros ----
 #define USE_ACC
 #define USE_GYRO
 #define USE_ACC_SPI_ICM42688P
 #define USE_GYRO_SPI_ICM42688P
 #define USE_ACC_SPI_BMI270
 #define USE_GYRO_SPI_BMI270
 
 #define GYRO_1_SPI_INSTANCE      SPI6
 #define GYRO_1_CS_PIN            PD7
 #define GYRO_1_EXTI_PIN          PE4
 #define GYRO_1_ALIGN             CW0_DEG
 
 #define GYRO_2_SPI_INSTANCE      SPI3
 #define GYRO_2_CS_PIN            PD3
 #define GYRO_2_EXTI_PIN          PD2
 #define GYRO_2_ALIGN             CW0_DEG
 
 // ---- Baro ----
 #define USE_BARO
 #define USE_BARO_BMP388
 #define BARO_I2C_INSTANCE        I2CDEV_2
 
 // ---- Mag ----
 #define USE_MAG
 #define MAG_I2C_INSTANCE         I2CDEV_4
 
 // ---- OSD ----
 #define USE_MAX7456
 #define MAX7456_SPI_INSTANCE     SPI4
 #define MAX7456_CS_PIN           PC13
 
 // ---- Flash ----
 #define USE_FLASH_W25Q128FV
 #define FLASH_CS_PIN             PA4
 #define FLASH_SPI_INSTANCE       SPI1
 
 // ---- Motors ----
 #define MOTOR1_PIN               PE9
 #define MOTOR2_PIN               PE11
 #define MOTOR3_PIN               PE13
 #define MOTOR4_PIN               PE14
 #define MOTOR5_PIN               PC6
 #define MOTOR6_PIN               PC7
 #define MOTOR7_PIN               PC8
 #define MOTOR8_PIN               PC9
 
 // ---- Servos ----
 #define SERVO1_PIN               PD12
 #define SERVO2_PIN               PD13
 #define SERVO3_PIN               PD14
 #define SERVO4_PIN               PD15
 
 // ---- UARTs ----
 #define UART1_TX_PIN             PB14
 #define UART1_RX_PIN             PB15
 
 #define UART2_TX_PIN             PA2
 #define UART2_RX_PIN             PA3
 
 #define UART3_TX_PIN             PD8
 #define UART3_RX_PIN             PD9
 
 #define UART4_TX_PIN             PA0
 #define UART4_RX_PIN             PA1
 
 #define UART5_TX_PIN             PB13
 #define UART5_RX_PIN             PB12
 
 #define UART7_TX_PIN             PE8
 #define UART7_RX_PIN             PE7
 
 #define UART8_TX_PIN             PE1
 #define UART8_RX_PIN             PE0
 
 #define SERIALRX_UART            SERIAL_PORT_USART8
 #define DEFAULT_RX_FEATURE       FEATURE_RX_SERIAL
 #define SERIALRX_PROVIDER        SERIALRX_CRSF
 
 // ---- SPI ----
 #define USE_SPI
 #define USE_SPI_DEVICE_1
 #define USE_SPI_DEVICE_3
 #define USE_SPI_DEVICE_4
 #define USE_SPI_DEVICE_6
 
 #define SPI1_SCK_PIN             PA5
 #define SPI1_SDI_PIN             PA6
 #define SPI1_SDO_PIN             PA7
 
 #define SPI3_SCK_PIN             PC10
 #define SPI3_SDI_PIN             PC11
 #define SPI3_SDO_PIN             PC12
 
 #define SPI4_SCK_PIN             PE2
 #define SPI4_SDI_PIN             PE5
 #define SPI4_SDO_PIN             PE6
 
 #define SPI6_SCK_PIN             PB3
 #define SPI6_SDI_PIN             PB4
 #define SPI6_SDO_PIN             PB5
 
 // ---- I2C ----
 #define USE_I2C
 #define USE_I2C_DEVICE_2
 #define I2C2_SCL_PIN             PB10
 #define I2C2_SDA_PIN             PB11
 
 #define USE_I2C_DEVICE_4
 #define I2C4_SCL_PIN             PB6
 #define I2C4_SDA_PIN             PB7
 
 // ---- ADC ----
 #define USE_ADC
 #define ADC_VBAT_PIN             PC1
 #define ADC_CURR_PIN             PC3
 #define DEFAULT_CURRENT_METER_SOURCE CURRENT_METER_ADC
 #define DEFAULT_VOLTAGE_METER_SOURCE VOLTAGE_METER_ADC
 
 // ---- LEDs ----
 #define LED0_PIN                 PB0
 #define LED1_PIN                 PC5
 
 // ---- Timers & DMA ----
 #define TIMER_PIN_MAPPING \
     TIMER_PIN_MAP( 0, PE9 , 1,  0) \
     TIMER_PIN_MAP( 1, PE11, 1,  1) \
     TIMER_PIN_MAP( 2, PE13, 1,  2) \
     TIMER_PIN_MAP( 3, PE14, 1,  3) \
     TIMER_PIN_MAP( 4, PC6 , 2,  4) \
     TIMER_PIN_MAP( 5, PC7 , 2,  5) \
     TIMER_PIN_MAP( 6, PC8 , 2,  6) \
     TIMER_PIN_MAP( 7, PC9 , 2,  7)
 
 #define ADC1_DMA_OPT        9
 #define ADC3_DMA_OPT        10