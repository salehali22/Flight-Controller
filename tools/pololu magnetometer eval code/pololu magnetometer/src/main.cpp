#include <Arduino.h>
#include <Wire.h>

#define SDA_PIN 25
#define SCL_PIN 26

const uint8_t LSM303D_ADDR = 0x1D;

int16_t x_raw, y_raw, z_raw;
float x_g, y_g, z_g;
float heading = 0;

uint32_t now = 0;
uint32_t last_time = 0;

void setup() {
  Serial.begin(115200);
  Wire.begin(SDA_PIN, SCL_PIN);

  // Wait for serial port to be ready
  delay(1000);

  // Verify device is present by reading WHO_AM_I register
  Wire.beginTransmission(LSM303D_ADDR);
  Wire.write(0x0F);  // WHO_AM_I register
  if (Wire.endTransmission(false) != 0) {
    Serial.println("ERROR: I2C communication failed - check connections");
    while(1) delay(1000);
  }
  
  uint8_t whoAmI = 0;
  Wire.requestFrom(LSM303D_ADDR, (uint8_t)1);
  if (Wire.available()) {
    whoAmI = Wire.read();
  }
  
  if (whoAmI != 0x49) {
    Serial.printf("ERROR: Wrong device ID. Expected 0x49, got 0x%02X\n", whoAmI);
    while(1) delay(1000);
  }
  Serial.println("LSM303D detected successfully");

  // Initialize LSM303D - Accelerometer disabled
  // Register 0x20: Accelerometer control (power down mode)
  Wire.beginTransmission(LSM303D_ADDR);
  Wire.write(0x20);
  Wire.write(0x00);  // Power down accelerometer
  if (Wire.endTransmission() != 0) {
    Serial.println("ERROR: Failed to write register 0x20");
  }

  // Register 0x24: Magnetometer control (high-res, 12.5Hz)
  Wire.beginTransmission(LSM303D_ADDR);
  Wire.write(0x24); 
  Wire.write(0x74);
  if (Wire.endTransmission() != 0) {
    Serial.println("ERROR: Failed to write register 0x24");
  }

  // Register 0x25: Magnetometer range (±4 gauss)
  Wire.beginTransmission(LSM303D_ADDR);
  Wire.write(0x25);
  Wire.write(0x20);
  if (Wire.endTransmission() != 0) {
    Serial.println("ERROR: Failed to write register 0x25");
  }

  // Register 0x26: Magnetometer mode (continuous conversion)
  Wire.beginTransmission(LSM303D_ADDR);
  Wire.write(0x26);
  Wire.write(0x00);
  if (Wire.endTransmission() != 0) {
    Serial.println("ERROR: Failed to write register 0x26");
  }

  // Give sensor time to stabilize
  delay(100);

  now = millis();
  Serial.println("Initialization complete. Starting readings...");

}

void readData() {
  uint8_t buffer[6];
  
  // Set register pointer to magnetometer output (0x08) with auto-increment
  Wire.beginTransmission(LSM303D_ADDR);
  Wire.write(0x88);
  if (Wire.endTransmission(false) != 0) {
    Serial.println("ERROR: Failed to set register pointer");
    return;
  }
  
  // Request 6 bytes (X, Y, Z magnetometer data)
  uint8_t bytesReceived = Wire.requestFrom(LSM303D_ADDR, (uint8_t)6);
  if (bytesReceived != 6) {
    Serial.printf("ERROR: Expected 6 bytes, got %d\n", bytesReceived);
    return;
  }
  
  // Read all 6 bytes
  for (int i = 0; i < 6; i++) {
    if (Wire.available()) {
      buffer[i] = Wire.read();
    } else {
      Serial.printf("ERROR: Byte %d not available\n", i);
      return;
    }
  }

  // Convert bytes to 16-bit values (little-endian)
  x_raw = (int16_t)(buffer[1] << 8 | buffer[0]);
  y_raw = (int16_t)(buffer[3] << 8 | buffer[2]);
  z_raw = (int16_t)(buffer[5] << 8 | buffer[4]);

  // Scale factor: ±4 gauss range = 0.16 mgauss/LSB = 0.00016 gauss/LSB
  x_g = x_raw * 0.00016f;
  y_g = y_raw * 0.00016f;
  z_g = z_raw * 0.00016f;
}

void calculateHeading() {
  heading = atan2(y_g, x_g) * 180.0f / PI;
  if (heading < 0) {
    heading += 360.0f;
  }
}

void loop() {
  last_time = now;
  now = millis();
  
  if (now - last_time >= 10) {
    readData();
    calculateHeading();
    Serial.printf("X: %.2f | Y: %.2f | Z: %.2f | Heading: %.2f\n", x_g, y_g, z_g, heading);
  }
}


