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
#include "stm32h7xx_hal.h"

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
#define OSD_SCLK_Pin GPIO_PIN_2
#define OSD_SCLK_GPIO_Port GPIOE
#define OSD_CS_Pin GPIO_PIN_3
#define OSD_CS_GPIO_Port GPIOE
#define OSD_MISO_Pin GPIO_PIN_5
#define OSD_MISO_GPIO_Port GPIOE
#define OSD_MOSI_Pin GPIO_PIN_6
#define OSD_MOSI_GPIO_Port GPIOE
#define DJI_SBUS_Pin GPIO_PIN_1
#define DJI_SBUS_GPIO_Port GPIOA
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
#define IMU_INT1_Pin GPIO_PIN_4
#define IMU_INT1_GPIO_Port GPIOC
#define STATUS_LED_2_Pin GPIO_PIN_5
#define STATUS_LED_2_GPIO_Port GPIOC
#define STATUS_LED_1_Pin GPIO_PIN_0
#define STATUS_LED_1_GPIO_Port GPIOB
#define BMP_INT1_Pin GPIO_PIN_1
#define BMP_INT1_GPIO_Port GPIOB
#define DJI_RX_Pin GPIO_PIN_7
#define DJI_RX_GPIO_Port GPIOE
#define DJI_TX_Pin GPIO_PIN_8
#define DJI_TX_GPIO_Port GPIOE
#define M5_Pin GPIO_PIN_9
#define M5_GPIO_Port GPIOE
#define M6_Pin GPIO_PIN_11
#define M6_GPIO_Port GPIOE
#define M7_Pin GPIO_PIN_13
#define M7_GPIO_Port GPIOE
#define M8_Pin GPIO_PIN_14
#define M8_GPIO_Port GPIOE
#define ESC_RX_Pin GPIO_PIN_12
#define ESC_RX_GPIO_Port GPIOB
#define ESC_TX_Pin GPIO_PIN_13
#define ESC_TX_GPIO_Port GPIOB
#define WIFI_RC_TX_Pin GPIO_PIN_14
#define WIFI_RC_TX_GPIO_Port GPIOB
#define WIFI_RC_RX_Pin GPIO_PIN_15
#define WIFI_RC_RX_GPIO_Port GPIOB
#define TELEMETRY_TX_Pin GPIO_PIN_8
#define TELEMETRY_TX_GPIO_Port GPIOD
#define TELEMETRY_RX_Pin GPIO_PIN_9
#define TELEMETRY_RX_GPIO_Port GPIOD
#define S1_Pin GPIO_PIN_12
#define S1_GPIO_Port GPIOD
#define S2_Pin GPIO_PIN_13
#define S2_GPIO_Port GPIOD
#define S3_Pin GPIO_PIN_14
#define S3_GPIO_Port GPIOD
#define S4_Pin GPIO_PIN_15
#define S4_GPIO_Port GPIOD
#define M1_Pin GPIO_PIN_6
#define M1_GPIO_Port GPIOC
#define M2_Pin GPIO_PIN_7
#define M2_GPIO_Port GPIOC
#define M3_Pin GPIO_PIN_8
#define M3_GPIO_Port GPIOC
#define M4_Pin GPIO_PIN_9
#define M4_GPIO_Port GPIOC
#define IMU2_SCLK_Pin GPIO_PIN_10
#define IMU2_SCLK_GPIO_Port GPIOC
#define IMU2_MISO_Pin GPIO_PIN_11
#define IMU2_MISO_GPIO_Port GPIOC
#define IMU2_MOSI_Pin GPIO_PIN_12
#define IMU2_MOSI_GPIO_Port GPIOC
#define IMU2_INT1_Pin GPIO_PIN_2
#define IMU2_INT1_GPIO_Port GPIOD
#define IMU2_CS_Pin GPIO_PIN_3
#define IMU2_CS_GPIO_Port GPIOD
#define MAG_DRDY_Pin GPIO_PIN_5
#define MAG_DRDY_GPIO_Port GPIOD
#define FLASH_CS_Pin GPIO_PIN_7
#define FLASH_CS_GPIO_Port GPIOD
#define FLASH_SCLK_Pin GPIO_PIN_3
#define FLASH_SCLK_GPIO_Port GPIOB
#define FLASH_MISO_Pin GPIO_PIN_4
#define FLASH_MISO_GPIO_Port GPIOB
#define FLASH_MOSI_Pin GPIO_PIN_5
#define FLASH_MOSI_GPIO_Port GPIOB
#define GPS_SCL_Pin GPIO_PIN_6
#define GPS_SCL_GPIO_Port GPIOB
#define GPS_SDA_Pin GPIO_PIN_7
#define GPS_SDA_GPIO_Port GPIOB
#define VTX_TX_Pin GPIO_PIN_1
#define VTX_TX_GPIO_Port GPIOE

/* USER CODE BEGIN Private defines */

/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
