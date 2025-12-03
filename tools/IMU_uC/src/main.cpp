// V1.1

#include <Arduino.h>

#include "imu_target_config.h"
#include "mpu6050.h"
#include "pololu_l3gd20h.h"

#if defined(USE_TARGET_MPU6050)
void setup() {
  imu_mpu6050_setup();
}

void loop() {
  imu_mpu6050_loop();
}
#elif defined(USE_TARGET_POLOLU)
void setup() {
  imu_pololu_setup();
}

void loop() {
  imu_pololu_loop();
}
#endif