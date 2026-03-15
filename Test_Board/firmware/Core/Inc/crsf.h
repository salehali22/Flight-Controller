/*
 * crsf.h
 *
 *  Created on: Mar 13, 2026
 *      Author: Saleh
 */

#ifndef INC_CRSF_H_
#define INC_CRSF_H_

#include "stm32f1xx_hal.h"
#include <stdint.h>
#include <stdbool.h>

// -------------------------------------------------------
// CRSF Protocol Constants
// -------------------------------------------------------
#define CRSF_BAUDRATE               420000
#define CRSF_SYNC_BYTE              0xC8
#define CRSF_FRAMETYPE_RC_CHANNELS  0x16
#define CRSF_MAX_FRAME_LEN          64
#define CRSF_NUM_CHANNELS           16

// -------------------------------------------------------
// CRSF Data Structure
// Watch these in Live Expressions:
//   crsf_data.channels[0]  → Roll
//   crsf_data.channels[1]  → Pitch
//   crsf_data.channels[2]  → Throttle
//   crsf_data.channels[3]  → Yaw
//   crsf_data.channels[4+] → Aux channels
// Raw range: 172–1811 (mid = 992)
// -------------------------------------------------------
typedef struct {
    uint16_t channels[CRSF_NUM_CHANNELS];

    // Normalized outputs — use these in flight code
    float roll;      // -100.0 to +100.0
    float pitch;     // -100.0 to +100.0
    float throttle;  //    0.0 to +100.0
    float yaw;       // -100.0 to +100.0
    bool  armed;     // AUX1 > 1500 = armed


    bool     new_frame;          // true when fresh data arrived
    uint32_t last_frame_ms;      // HAL tick of last good frame
    uint32_t frame_count;        // total good frames received
    uint32_t crc_errors;         // CRC mismatches (should stay 0)
} CRSF_Data_t;

extern CRSF_Data_t crsf_data;



// -------------------------------------------------------
// API
// -------------------------------------------------------
void CRSF_Init(UART_HandleTypeDef *huart);
void CRSF_Process(void);


#endif /* INC_CRSF_H_ */
