#include "imu_target_config.h"
#if defined(USE_TARGET_POLOLU)

#include "pololu_l3gd20h.h"

#include <Arduino.h>
#include <Wire.h>

#define SDA_PIN 25
#define SCL_PIN 26

// L3GD20H + LSM303D (Pololu 0J8003) I2C addresses
const uint8_t L3GD20H_ADDR = 0x6B;
const uint8_t LSM303D_ADDR = 0x1D;

// Scale factors from datasheets (selected full-scale ranges noted in init)
const float ACC_LSB_TO_G = 0.000061f;    // ±2g => 0.061 mg/LSB
const float GYRO_LSB_TO_DPS = 0.07f;     // ±2000 dps => 70 mdps/LSB
const float MAG_LSB_TO_UT = 0.016f;      // ±4 gauss => 0.16 mgauss/LSB => 0.016 µT/LSB

// Sampling / filtering parameters
uint16_t SAMPLE_INTERVAL = 10;  // milliseconds
int calibrationSamples = 1000;
float alphaFactor = 0.83f;

// Sensor data (g, dps, µT)
float AccX = 0.0f, AccY = 0.0f, AccZ = 0.0f;
float GyroX = 0.0f, GyroY = 0.0f, GyroZ = 0.0f;
float MagX = 0.0f, MagY = 0.0f, MagZ = 0.0f;

// Filter state
float accAngleX = 0.0f, accAngleY = 0.0f;
float roll = 0.0f, pitch = 0.0f, yaw = 0.0f;

// Calibration data
float AccErrorX = 0.0f, AccErrorY = 0.0f;
float GyroErrorX = 0.0f, GyroErrorY = 0.0f, GyroErrorZ = 0.0f;
float MagOffsetX = 0.0f, MagOffsetY = 0.0f, MagOffsetZ = 0.0f;
float MagScaleX = 1.0f, MagScaleY = 1.0f, MagScaleZ = 1.0f;

unsigned long sample_time = 0;
bool runLimited = false;
bool streamingEnabled = true;
unsigned long runStopTime = 0;
bool magVectorValid = false;

// Forward declarations
void read_accelerometer();
void read_gyroscope();
void read_magnetometer();
void calculate_acc_angles();
void apply_complementary_filter(float dt);
void print_orientation();
void clear_calibration_values();
void calculate_IMU_error();
void processSerialCommands();
void handleCommand(String line);
bool initSensors();

// Low-level helpers
bool writeRegister(uint8_t addr, uint8_t reg, uint8_t value) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission(true) == 0;
}

bool readRegisters(uint8_t addr, uint8_t startReg, uint8_t* buffer, size_t len) {
  Wire.beginTransmission(addr);
  Wire.write(startReg);
  if (Wire.endTransmission(false) != 0) {
    return false;
  }
  size_t readBytes = Wire.requestFrom(static_cast<int>(addr), static_cast<int>(len), static_cast<int>(true));
  if (readBytes != len) {
    return false;
  }
  for (size_t i = 0; i < len; ++i) {
    buffer[i] = Wire.read();
  }
  return true;
}

bool readAccelRaw(int16_t& x, int16_t& y, int16_t& z) {
  uint8_t buffer[6];
  if (!readRegisters(LSM303D_ADDR, 0x28 | 0x80, buffer, sizeof(buffer))) {
    return false;
  }
  x = static_cast<int16_t>(buffer[1] << 8 | buffer[0]);
  y = static_cast<int16_t>(buffer[3] << 8 | buffer[2]);
  z = static_cast<int16_t>(buffer[5] << 8 | buffer[4]);
  return true;
}

bool readGyroRaw(int16_t& x, int16_t& y, int16_t& z) {
  uint8_t buffer[6];
  if (!readRegisters(L3GD20H_ADDR, 0x28 | 0x80, buffer, sizeof(buffer))) {
    return false;
  }
  x = static_cast<int16_t>(buffer[1] << 8 | buffer[0]);
  y = static_cast<int16_t>(buffer[3] << 8 | buffer[2]);
  z = static_cast<int16_t>(buffer[5] << 8 | buffer[4]);
  return true;
}

bool readMagRaw(int16_t& x, int16_t& y, int16_t& z) {
  uint8_t buffer[6];
  if (!readRegisters(LSM303D_ADDR, 0x08 | 0x80, buffer, sizeof(buffer))) {
    return false;
  }
  x = static_cast<int16_t>(buffer[1] << 8 | buffer[0]);
  y = static_cast<int16_t>(buffer[3] << 8 | buffer[2]);
  z = static_cast<int16_t>(buffer[5] << 8 | buffer[4]);
  return true;
}

void read_accelerometer() {
  int16_t rawX, rawY, rawZ;
  if (!readAccelRaw(rawX, rawY, rawZ)) {
    return;
  }
  AccX = rawX * ACC_LSB_TO_G;
  AccY = rawY * ACC_LSB_TO_G;
  AccZ = rawZ * ACC_LSB_TO_G;
}

void read_gyroscope() {
  int16_t rawX, rawY, rawZ;
  if (!readGyroRaw(rawX, rawY, rawZ)) {
    return;
  }
  GyroX = rawX * GYRO_LSB_TO_DPS - GyroErrorX;
  GyroY = rawY * GYRO_LSB_TO_DPS - GyroErrorY;
  GyroZ = rawZ * GYRO_LSB_TO_DPS - GyroErrorZ;
}

void read_magnetometer() {
  int16_t rawX, rawY, rawZ;
  if (!readMagRaw(rawX, rawY, rawZ)) {
    magVectorValid = false;
    return;
  }

  float mx = rawX * MAG_LSB_TO_UT;
  float my = rawY * MAG_LSB_TO_UT;
  float mz = rawZ * MAG_LSB_TO_UT;

  mx = (mx - MagOffsetX) * MagScaleX;
  my = (my - MagOffsetY) * MagScaleY;
  mz = (mz - MagOffsetZ) * MagScaleZ;

  MagX = mx;
  MagY = my;
  MagZ = mz;

  const float magNorm = sqrtf(mx * mx + my * my + mz * mz);
  magVectorValid = magNorm > 0.5f;  // Threshold to suppress zero vectors
}

void calculate_acc_angles() {
  const float denomX = sqrtf(powf(AccX, 2.0f) + powf(AccZ, 2.0f));
  const float denomY = sqrtf(powf(AccY, 2.0f) + powf(AccZ, 2.0f));
  if (denomX == 0.0f || denomY == 0.0f) {
    return;
  }
  accAngleX = (atan2f(AccY, denomX) * 180.0f / PI) - AccErrorX;
  accAngleY = (atan2f(-AccX, denomY) * 180.0f / PI) - AccErrorY;
}

float calculateMagHeadingDegrees() {
  if (!magVectorValid) {
    return yaw;
  }

  const float rollRad = roll * DEG_TO_RAD;
  const float pitchRad = pitch * DEG_TO_RAD;

  const float cosPitch = cosf(pitchRad);
  const float sinPitch = sinf(pitchRad);
  const float cosRoll = cosf(rollRad);
  const float sinRoll = sinf(rollRad);

  const float magXComp = MagX * cosPitch + MagZ * sinPitch;
  const float magYComp =
      MagX * sinRoll * sinPitch + MagY * cosRoll - MagZ * sinRoll * cosPitch;

  float heading = atan2f(-magYComp, magXComp) * RAD_TO_DEG;
  if (heading < 0.0f) {
    heading += 360.0f;
  }
  return heading;
}

void apply_complementary_filter(float dt) {
  const float beta = 1.0f - alphaFactor;

  roll = alphaFactor * (roll + GyroX * dt) + beta * accAngleX;
  pitch = alphaFactor * (pitch + GyroY * dt) + beta * accAngleY;

  const float predictedYaw = yaw + GyroZ * dt;
  if (magVectorValid) {
    const float heading = calculateMagHeadingDegrees();
    yaw = alphaFactor * predictedYaw + beta * heading;
  } else {
    yaw = predictedYaw;
  }

  if (yaw > 180.0f || yaw < -180.0f) {
    yaw = fmodf(yaw + 540.0f, 360.0f) - 180.0f;
  }
}

void print_orientation() {
  Serial.printf("%.3f, %.3f, %.3f, %.3f, %.3f, %.3f\n", roll, pitch, yaw, MagX, MagY, MagZ);
}

void clear_calibration_values() {
  AccErrorX = AccErrorY = 0.0f;
  GyroErrorX = GyroErrorY = GyroErrorZ = 0.0f;
  MagOffsetX = MagOffsetY = MagOffsetZ = 0.0f;
  MagScaleX = MagScaleY = MagScaleZ = 1.0f;
  roll = pitch = yaw = 0.0f;
}

void calculate_IMU_error() {
  Serial.printf("Calibrating with %d samples...\n", calibrationSamples);
  Serial.println("Rotate the board slowly through all orientations");
  delay(2000);

  AccErrorX = AccErrorY = 0.0f;
  GyroErrorX = GyroErrorY = GyroErrorZ = 0.0f;
  MagOffsetX = MagOffsetY = MagOffsetZ = 0.0f;

  float magMinX = 1e9f, magMinY = 1e9f, magMinZ = 1e9f;
  float magMaxX = -1e9f, magMaxY = -1e9f, magMaxZ = -1e9f;

  for (int i = 0; i < calibrationSamples; ++i) {
    int16_t ax, ay, az;
    if (readAccelRaw(ax, ay, az)) {
      const float axg = ax * ACC_LSB_TO_G;
      const float ayg = ay * ACC_LSB_TO_G;
      const float azg = az * ACC_LSB_TO_G;
      AccErrorX += atan2f(ayg, sqrtf(powf(axg, 2.0f) + powf(azg, 2.0f))) * 180.0f / PI;
      AccErrorY += atan2f(-axg, sqrtf(powf(ayg, 2.0f) + powf(azg, 2.0f))) * 180.0f / PI;
    }

    int16_t gxRaw, gyRaw, gzRaw;
    if (readGyroRaw(gxRaw, gyRaw, gzRaw)) {
      GyroErrorX += gxRaw * GYRO_LSB_TO_DPS;
      GyroErrorY += gyRaw * GYRO_LSB_TO_DPS;
      GyroErrorZ += gzRaw * GYRO_LSB_TO_DPS;
    }

    int16_t mxRaw, myRaw, mzRaw;
    if (readMagRaw(mxRaw, myRaw, mzRaw)) {
      const float mx = mxRaw * MAG_LSB_TO_UT;
      const float my = myRaw * MAG_LSB_TO_UT;
      const float mz = mzRaw * MAG_LSB_TO_UT;

      magMinX = min(magMinX, mx);
      magMinY = min(magMinY, my);
      magMinZ = min(magMinZ, mz);

      magMaxX = max(magMaxX, mx);
      magMaxY = max(magMaxY, my);
      magMaxZ = max(magMaxZ, mz);
    }

    delay(2);
  }

  AccErrorX /= calibrationSamples;
  AccErrorY /= calibrationSamples;

  GyroErrorX /= calibrationSamples;
  GyroErrorY /= calibrationSamples;
  GyroErrorZ /= calibrationSamples;

  MagOffsetX = (magMaxX + magMinX) * 0.5f;
  MagOffsetY = (magMaxY + magMinY) * 0.5f;
  MagOffsetZ = (magMaxZ + magMinZ) * 0.5f;

  const float rangeX = (magMaxX - magMinX) * 0.5f;
  const float rangeY = (magMaxY - magMinY) * 0.5f;
  const float rangeZ = (magMaxZ - magMinZ) * 0.5f;
  const float avgRange = max(1.0f, (rangeX + rangeY + rangeZ) / 3.0f);

  MagScaleX = avgRange / max(rangeX, 0.01f);
  MagScaleY = avgRange / max(rangeY, 0.01f);
  MagScaleZ = avgRange / max(rangeZ, 0.01f);

  Serial.println("Calibration complete");
}

void processSerialCommands() {
  while (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) {
      continue;
    }
    handleCommand(line);
  }
}

void handleCommand(String line) {
  int spaceIndex = line.indexOf(' ');
  String keyword = (spaceIndex == -1) ? line : line.substring(0, spaceIndex);
  String arg = (spaceIndex == -1) ? "" : line.substring(spaceIndex + 1);
  keyword.toUpperCase();
  arg.trim();

  if (keyword == "SET_SAMPLES") {
    if (arg.length() == 0) {
      Serial.println("ERR:SET_SAMPLES missing value");
      return;
    }
    int value = arg.toInt();
    if (value < 10 || value > 20000) {
      Serial.println("ERR:SET_SAMPLES range 10-20000");
      return;
    }
    calibrationSamples = value;
    Serial.printf("ACK:SET_SAMPLES %d\n", calibrationSamples);
  } else if (keyword == "SET_ALPHA") {
    if (arg.length() == 0) {
      Serial.println("ERR:SET_ALPHA missing value");
      return;
    }
    float value = arg.toFloat();
    value = constrain(value, 0.0f, 0.999f);
    alphaFactor = value;
    Serial.printf("ACK:SET_ALPHA %.4f\n", alphaFactor);
  } else if (keyword == "SET_SAMPLE_RATE") {
    if (arg.length() == 0) {
      Serial.println("ERR:SET_SAMPLE_RATE missing value");
      return;
    }
    int value = arg.toInt();
    if (value < 1 || value > 1000) {
      Serial.println("ERR:SET_SAMPLE_RATE range 1-1000");
      return;
    }
    SAMPLE_INTERVAL = value;
    Serial.printf("ACK:SET_SAMPLE_RATE %d\n", SAMPLE_INTERVAL);
  } else if (keyword == "PAUSE") {
    streamingEnabled = false;
    Serial.println("ACK:PAUSED");
  } else if (keyword == "RESUME") {
    streamingEnabled = true;
    sample_time = millis();
    Serial.println("ACK:RESUMED");
  } else if (keyword == "CLEAR_CAL") {
    clear_calibration_values();
    Serial.println("ACK:CLEAR_CAL");
  } else if (keyword == "CALIBRATE") {
    streamingEnabled = false;
    calculate_IMU_error();
    streamingEnabled = true;
    runLimited = false;
    Serial.println("ACK:CALIBRATE_DONE");
    sample_time = millis();
  } else if (keyword == "RUN_FOR") {
    if (arg.length() == 0) {
      Serial.println("ERR:RUN_FOR missing value");
      return;
    }
    long seconds = arg.toInt();
    if (seconds <= 0) {
      runLimited = false;
      streamingEnabled = true;
      Serial.println("ACK:RUN_CONTINUOUS");
    } else {
      runLimited = true;
      streamingEnabled = true;
      runStopTime = millis() + (unsigned long)seconds * 1000UL;
      Serial.printf("ACK:RUN_FOR %ld\n", seconds);
    }
  } else {
    Serial.println("ERR:UNKNOWN_COMMAND");
  }
}

bool initL3GD20H() {
  uint8_t whoAmI = 0;
  if (!readRegisters(L3GD20H_ADDR, 0x0F, &whoAmI, 1) || whoAmI != 0xD7) {
    Serial.println("ERR:L3GD20H_ID");
    return false;
  }
  if (!writeRegister(L3GD20H_ADDR, 0x20, 0x6F)) {  // ODR 200Hz, cut-off 50Hz, axes enable
    return false;
  }
  if (!writeRegister(L3GD20H_ADDR, 0x21, 0x00)) {  // High-pass disabled
    return false;
  }
  if (!writeRegister(L3GD20H_ADDR, 0x23, 0x30)) {  // 2000 dps full-scale
    return false;
  }
  return true;
}

bool initLSM303D() {
  uint8_t whoAmI = 0;
  if (!readRegisters(LSM303D_ADDR, 0x0F, &whoAmI, 1) || whoAmI != 0x49) {
    Serial.println("ERR:LSM303D_ID");
    return false;
  }
  if (!writeRegister(LSM303D_ADDR, 0x20, 0x57)) {  // Accel 50Hz, all axes on
    return false;
  }
  if (!writeRegister(LSM303D_ADDR, 0x21, 0x00)) {  // ±2g, no filtering
    return false;
  }
  if (!writeRegister(LSM303D_ADDR, 0x24, 0x74)) {  // Mag high-res, 12.5Hz
    return false;
  }
  if (!writeRegister(LSM303D_ADDR, 0x25, 0x20)) {  // ±4 gauss
    return false;
  }
  if (!writeRegister(LSM303D_ADDR, 0x26, 0x00)) {  // Continuous conversion
    return false;
  }
  return true;
}

bool initSensors() {
  if (!initL3GD20H()) {
    return false;
  }
  if (!initLSM303D()) {
    return false;
  }
  return true;
}

void imu_pololu_setup() {
  Serial.begin(115200);

  while (!Wire.begin(SDA_PIN, SCL_PIN)) {
    Serial.println("ERR:I2C_INIT");
    delay(1000);
  }
  Wire.setClock(400000);

  if (!initSensors()) {
    Serial.println("ERR:SENSOR_INIT");
    while (true) {
      delay(1000);
    }
  }

  calculate_IMU_error();
  sample_time = millis();
}

void imu_pololu_loop() {
  processSerialCommands();

  if (!streamingEnabled) {
    delay(5);
    return;
  }

  if (runLimited && millis() >= runStopTime) {
    streamingEnabled = false;
    runLimited = false;
    Serial.println("INFO:RUN_COMPLETE");
    delay(5);
    return;
  }

  unsigned long now = millis();
  if (now - sample_time >= SAMPLE_INTERVAL) {
    unsigned long processing_start = now;

    read_accelerometer();
    read_gyroscope();
    read_magnetometer();
    calculate_acc_angles();

    const float dt = SAMPLE_INTERVAL / 1000.0f;
    apply_complementary_filter(dt);

    if (Serial.availableForWrite() > 0) {
      print_orientation();
    }

    unsigned long processing_time = millis() - processing_start;
    sample_time += SAMPLE_INTERVAL;

    if (processing_time >= SAMPLE_INTERVAL) {
      sample_time = millis();
    }
  }
}

#endif  // USE_TARGET_POLOLU

