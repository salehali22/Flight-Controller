// V1.1

#include <Arduino.h>
#include <Wire.h>

#define SDA_PIN 25
#define SCL_PIN 26

const uint8_t MPU_ADDR = 0x68;
uint16_t SAMPLE_INTERVAL = 10;  // milliseconds

float AccX = 0.0f, AccY = 0.0f, AccZ = 0.0f;
float GyroX = 0.0f, GyroY = 0.0f, GyroZ = 0.0f;

float accAngleX = 0.0f, accAngleY = 0.0f;
float gyroAngleX = 0.0f, gyroAngleY = 0.0f;
float roll = 0.0f, pitch = 0.0f, yaw = 0.0f;

float AccErrorX = 0.0f, AccErrorY = 0.0f;
float GyroErrorX = 0.0f, GyroErrorY = 0.0f, GyroErrorZ = 0.0f;

unsigned long sample_time = 0;

int calibrationSamples = 1000;
float alphaFactor = 0.83f;
bool runLimited = false;
bool streamingEnabled = true;
unsigned long runStopTime = 0;

void read_accelerometer() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 6, true);

  AccX = (int16_t)(Wire.read() << 8 | Wire.read()) / 16384.0f;
  AccY = (int16_t)(Wire.read() << 8 | Wire.read()) / 16384.0f;
  AccZ = (int16_t)(Wire.read() << 8 | Wire.read()) / 16384.0f;
}

void read_gyroscope() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x43);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 6, true);

  GyroX = (int16_t)(Wire.read() << 8 | Wire.read()) / 131.0f - GyroErrorX;
  GyroY = (int16_t)(Wire.read() << 8 | Wire.read()) / 131.0f - GyroErrorY;
  GyroZ = (int16_t)(Wire.read() << 8 | Wire.read()) / 131.0f - GyroErrorZ;
}

void calculate_acc_angles() {
  accAngleX = (atan(AccY / sqrt(pow(AccX, 2) + pow(AccZ, 2))) * 180.0f / PI) - AccErrorX;
  accAngleY = (atan(-AccX / sqrt(pow(AccY, 2) + pow(AccZ, 2))) * 180.0f / PI) - AccErrorY;
}

void apply_complementary_filter(float dt) {
  // Integrate gyro directly onto the filtered angles
  const float beta = 1.0f - alphaFactor;
  roll = alphaFactor * (roll + GyroX * dt) + beta * accAngleX;
  pitch = alphaFactor * (pitch + GyroY * dt) + beta * accAngleY;

  // Yaw has no accelerometer correction, so keep it as is
  yaw += GyroZ * dt;
}

void print_orientation() {
  Serial.printf("%.3f, %.3f, %.3f\n", roll, pitch, yaw);
}

void clear_calibration_values() {
  AccErrorX = AccErrorY = 0.0f;
  GyroErrorX = GyroErrorY = GyroErrorZ = 0.0f;
  gyroAngleX = gyroAngleY = 0.0f;
  roll = pitch = yaw = 0.0f;
}

void calculate_IMU_error() {
  Serial.printf("Calibrating with %d samples...\n", calibrationSamples);
  Serial.println("Keep sensor stationary");
  delay(3000);

  AccErrorX = AccErrorY = 0.0f;
  GyroErrorX = GyroErrorY = GyroErrorZ = 0.0f;

  for (int i = 0; i < calibrationSamples; ++i) {
    read_accelerometer();
    AccErrorX += atan(AccY / sqrt(pow(AccX, 2) + pow(AccZ, 2))) * 180.0f / PI;
    AccErrorY += atan(-AccX / sqrt(pow(AccY, 2) + pow(AccZ, 2))) * 180.0f / PI;
  }

  AccErrorX /= calibrationSamples;
  AccErrorY /= calibrationSamples;

  for (int i = 0; i < 20; ++i) {
    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x43);
    Wire.endTransmission(false);
    Wire.requestFrom(MPU_ADDR, 6, true);
    for (int j = 0; j < 6; ++j) {
      Wire.read();
    }
    delay(3);
  }

  for (int i = 0; i < calibrationSamples; ++i) {
    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x43);
    Wire.endTransmission(false);
    Wire.requestFrom(MPU_ADDR, 6, true);

    GyroErrorX += (int16_t)(Wire.read() << 8 | Wire.read()) / 131.0f;
    GyroErrorY += (int16_t)(Wire.read() << 8 | Wire.read()) / 131.0f;
    GyroErrorZ += (int16_t)(Wire.read() << 8 | Wire.read()) / 131.0f;
  }

  GyroErrorX /= calibrationSamples;
  GyroErrorY /= calibrationSamples;
  GyroErrorZ /= calibrationSamples;

  Serial.println("Calibration complete");
}

void handleCommand(String line);

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

void setup() {
  Serial.begin(115200);

  while (!Wire.begin(SDA_PIN, SCL_PIN)) {
    Serial.println("ERR:I2C_INIT");
    delay(1000);
  }

  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);
  Wire.write(0x00);
  Wire.endTransmission(true);

  calculate_IMU_error();
  sample_time = millis();
}

void loop() {
  processSerialCommands();

  if (runLimited && streamingEnabled && millis() >= runStopTime) {
    streamingEnabled = false;
    runLimited = false;
    Serial.println("INFO:RUN_COMPLETE");
  }

  if (!streamingEnabled) {
    delay(5);
    return;
  }

  unsigned long now = millis();
  if (now - sample_time >= SAMPLE_INTERVAL) {
    sample_time = now;

    read_accelerometer();
    read_gyroscope();
    calculate_acc_angles();

    const float dt = SAMPLE_INTERVAL / 1000.0f;
    apply_complementary_filter(dt);
    print_orientation();
  }
}