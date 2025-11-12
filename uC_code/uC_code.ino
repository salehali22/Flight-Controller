#include <Wire.h>

// Pin definitions
#define SDA_PIN 25
#define SCL_PIN 26

// MPU6050 settings
const int MPU_ADDR = 0x68;
const int SAMPLE_INTERVAL = 10; // ms

// Sensor data
float AccX, AccY, AccZ;
float GyroX, GyroY, GyroZ;

// Calculated angles
float accAngleX, accAngleY;
float gyroAngleX, gyroAngleY;
float roll, pitch, yaw;

// Error correction values
float AccErrorX, AccErrorY;
float GyroErrorX, GyroErrorY, GyroErrorZ;

// Timing
long sample_time;

void setup() {
  Serial.begin(115200);
  
  while(!Wire.begin(SDA_PIN, SCL_PIN)) {
    Serial.println("Error: I2C initialization failed");
    delay(1000);
  }
  
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);
  Wire.write(0x00);
  Wire.endTransmission(true);
  
  calculate_IMU_error();
  delay(20);
  
  sample_time = millis();
}

void loop() {
  if(millis() - sample_time >= SAMPLE_INTERVAL) {
    sample_time = millis();
    
    read_accelerometer();
    read_gyroscope();
    calculate_acc_angles();
    
    float dt = SAMPLE_INTERVAL / 1000.0;
    
    integrate_gyro(dt);
    apply_complementary_filter();
    
    print_orientation();
  }
}

void read_accelerometer() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 6, true);
  
  AccX = (int16_t)(Wire.read() << 8 | Wire.read()) / 16384.0;
  AccY = (int16_t)(Wire.read() << 8 | Wire.read()) / 16384.0;
  AccZ = (int16_t)(Wire.read() << 8 | Wire.read()) / 16384.0;
}

void read_gyroscope() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x43);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 6, true);
  
  GyroX = (int16_t)(Wire.read() << 8 | Wire.read()) / 131.0 - GyroErrorX;
  GyroY = (int16_t)(Wire.read() << 8 | Wire.read()) / 131.0 - GyroErrorY;
  GyroZ = (int16_t)(Wire.read() << 8 | Wire.read()) / 131.0 - GyroErrorZ;
}

void calculate_acc_angles() {
  accAngleX = (atan(AccY / sqrt(pow(AccX, 2) + pow(AccZ, 2))) * 180 / PI) - AccErrorX;
  accAngleY = (atan(-AccX / sqrt(pow(AccY, 2) + pow(AccZ, 2))) * 180 / PI) - AccErrorY;
}

void integrate_gyro(float dt) {
  gyroAngleX += GyroX * dt;
  gyroAngleY += GyroY * dt;
  yaw += GyroZ * dt;
}

void apply_complementary_filter() {
  roll = 0.83 * gyroAngleX + 0.17 * accAngleX;
  pitch = 0.83 * gyroAngleY + 0.17 * accAngleY;
}

void print_orientation() {
  Serial.print(roll, 3);
  Serial.print(", ");
  Serial.print(pitch, 3);
  Serial.print(", ");
  Serial.println(yaw, 3);
}

void calculate_IMU_error() {
  Serial.println("Calibrating... Please keep sensor stationary");
  delay(5000);
  
  const int NUM_SAMPLES = 1000;
  
  // Accelerometer calibration
  for (int i = 0; i < NUM_SAMPLES; i++) {
    read_accelerometer();
    AccErrorX += atan(AccY / sqrt(pow(AccX, 2) + pow(AccZ, 2))) * 180 / PI;
    AccErrorY += atan(-AccX / sqrt(pow(AccY, 2) + pow(AccZ, 2))) * 180 / PI;
  }
  AccErrorX /= NUM_SAMPLES;
  AccErrorY /= NUM_SAMPLES;
  
  // Flush gyro buffers
  for(int i = 0; i < 20; i++) {
    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x43);
    Wire.endTransmission(false);
    Wire.requestFrom(MPU_ADDR, 6, true);
    for(int j = 0; j < 6; j++) Wire.read();
    delay(3);
  }
  
  // Gyro calibration
  for (int i = 0; i < NUM_SAMPLES; i++) {
    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x43);
    Wire.endTransmission(false);
    Wire.requestFrom(MPU_ADDR, 6, true);
    
    GyroErrorX += (int16_t)(Wire.read() << 8 | Wire.read()) / 131.0;
    GyroErrorY += (int16_t)(Wire.read() << 8 | Wire.read()) / 131.0;
    GyroErrorZ += (int16_t)(Wire.read() << 8 | Wire.read()) / 131.0;
  }
  GyroErrorX /= NUM_SAMPLES;
  GyroErrorY /= NUM_SAMPLES;
  GyroErrorZ /= NUM_SAMPLES;
  
  Serial.print("AccErrorX: "); Serial.println(AccErrorX);
  Serial.print("AccErrorY: "); Serial.println(AccErrorY);
  Serial.print("GyroErrorX: "); Serial.println(GyroErrorX);
  Serial.print("GyroErrorY: "); Serial.println(GyroErrorY);
  Serial.print("GyroErrorZ: "); Serial.println(GyroErrorZ);
}