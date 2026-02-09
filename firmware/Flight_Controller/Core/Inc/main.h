/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  *                   This file contains the common defines of the application.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2025 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32f7xx_hal.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */

/* USER CODE END ET */

/* Exported constants --------------------------------------------------------*/
/* USER CODE BEGIN EC */

/* USER CODE END EC */

/* Exported macro ------------------------------------------------------------*/
/* USER CODE BEGIN EM */

/* USER CODE END EM */

void HAL_TIM_MspPostInit(TIM_HandleTypeDef *htim);

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

/* USER CODE BEGIN EFP */

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/
#define INA226_ALERT_Pin GPIO_PIN_13
#define INA226_ALERT_GPIO_Port GPIOC
#define STATUS_LED_1_Pin GPIO_PIN_14
#define STATUS_LED_1_GPIO_Port GPIOC
#define STATUS_LED_2_Pin GPIO_PIN_15
#define STATUS_LED_2_GPIO_Port GPIOC
#define STATUS_LED_3_Pin GPIO_PIN_0
#define STATUS_LED_3_GPIO_Port GPIOC
#define OSD_MOSI_Pin GPIO_PIN_1
#define OSD_MOSI_GPIO_Port GPIOC
#define OSD_MISO_Pin GPIO_PIN_2
#define OSD_MISO_GPIO_Port GPIOC
#define BMP_INT_Pin GPIO_PIN_3
#define BMP_INT_GPIO_Port GPIOC
#define WIFI_TX_Pin GPIO_PIN_0
#define WIFI_TX_GPIO_Port GPIOA
#define WIFI_RX_Pin GPIO_PIN_1
#define WIFI_RX_GPIO_Port GPIOA
#define GPS_TX_Pin GPIO_PIN_2
#define GPS_TX_GPIO_Port GPIOA
#define GPS_RX_Pin GPIO_PIN_3
#define GPS_RX_GPIO_Port GPIOA
#define IMU_CS_Pin GPIO_PIN_4
#define IMU_CS_GPIO_Port GPIOA
#define IMU_SCLK_Pin GPIO_PIN_5
#define IMU_SCLK_GPIO_Port GPIOA
#define IMU_MISO_Pin GPIO_PIN_6
#define IMU_MISO_GPIO_Port GPIOA
#define IMU_MOSI_Pin GPIO_PIN_7
#define IMU_MOSI_GPIO_Port GPIOA
#define ADC_Voltage_Pin GPIO_PIN_0
#define ADC_Voltage_GPIO_Port GPIOB
#define SERVO_3_Pin GPIO_PIN_1
#define SERVO_3_GPIO_Port GPIOB
#define FLASH_MOSI_Pin GPIO_PIN_2
#define FLASH_MOSI_GPIO_Port GPIOB
#define I2C2_SCL_Pin GPIO_PIN_10
#define I2C2_SCL_GPIO_Port GPIOB
#define I2C2_SDA_Pin GPIO_PIN_11
#define I2C2_SDA_GPIO_Port GPIOB
#define OSD_CS_Pin GPIO_PIN_12
#define OSD_CS_GPIO_Port GPIOB
#define OSD_SCLK_Pin GPIO_PIN_13
#define OSD_SCLK_GPIO_Port GPIOB
#define SERVO_2_Pin GPIO_PIN_14
#define SERVO_2_GPIO_Port GPIOB
#define SERVO_1_Pin GPIO_PIN_15
#define SERVO_1_GPIO_Port GPIOB
#define Telemetry_TX_Pin GPIO_PIN_6
#define Telemetry_TX_GPIO_Port GPIOC
#define Telemetry_RX_Pin GPIO_PIN_7
#define Telemetry_RX_GPIO_Port GPIOC
#define IMU_INT_Pin GPIO_PIN_8
#define IMU_INT_GPIO_Port GPIOC
#define GPS_SDA_Pin GPIO_PIN_9
#define GPS_SDA_GPIO_Port GPIOC
#define GPS_SCL_Pin GPIO_PIN_8
#define GPS_SCL_GPIO_Port GPIOA
#define RC_Receiver_TX_Pin GPIO_PIN_9
#define RC_Receiver_TX_GPIO_Port GPIOA
#define RC_Receiver_RX_Pin GPIO_PIN_10
#define RC_Receiver_RX_GPIO_Port GPIOA
#define FLASH_SCK_Pin GPIO_PIN_10
#define FLASH_SCK_GPIO_Port GPIOC
#define FLASH_MISO_Pin GPIO_PIN_11
#define FLASH_MISO_GPIO_Port GPIOC
#define FLASH_CS_Pin GPIO_PIN_12
#define FLASH_CS_GPIO_Port GPIOC
#define MOTOR_1_Pin GPIO_PIN_3
#define MOTOR_1_GPIO_Port GPIOB
#define MOTOR_2_Pin GPIO_PIN_4
#define MOTOR_2_GPIO_Port GPIOB
#define MOTOR_3_Pin GPIO_PIN_5
#define MOTOR_3_GPIO_Port GPIOB
#define MOTOR_4_Pin GPIO_PIN_6
#define MOTOR_4_GPIO_Port GPIOB
#define MOTOR_5_Pin GPIO_PIN_7
#define MOTOR_5_GPIO_Port GPIOB
#define QMC_SCL_Pin GPIO_PIN_8
#define QMC_SCL_GPIO_Port GPIOB
#define QMC_SDA_Pin GPIO_PIN_9
#define QMC_SDA_GPIO_Port GPIOB

/* USER CODE BEGIN Private defines */

/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
