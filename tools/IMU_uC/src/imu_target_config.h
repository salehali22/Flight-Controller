#pragma once

// ------------------------------------------------------------------
// Select exactly ONE target below by uncommenting the desired line.
// ------------------------------------------------------------------
// #define USE_TARGET_MPU6050
 #define USE_TARGET_POLOLU

#if defined(USE_TARGET_MPU6050) && defined(USE_TARGET_POLOLU)
#error "Select only one IMU target (MPU6050 or Pololu)."
#elif !defined(USE_TARGET_MPU6050) && !defined(USE_TARGET_POLOLU)
#error "You must select an IMU target."
#endif

// ------------------------------------------------------------------
// Pololu-specific options
// Set to 0 to completely disable magnetometer reads and yaw correction,
// useful for checking pure gyro/accel behaviour.
// ------------------------------------------------------------------
#define POLOLU_USE_MAG 0
