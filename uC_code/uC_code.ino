#define SDA_PIN 25
#define SCL_PIN 26

#include <Wire.h>
const int MPU = 0x68;

float AccX, AccY, AccZ;
float GyroX, GyroY, GyroZ;  // Changed to float
float accAngleX, accAngleY, gyroAngleX, gyroAngleY, gyroAngleZ;
float roll, pitch, yaw;
float AccErrorX, AccErrorY, GyroErrorX, GyroErrorY, GyroErrorZ;
float elapsedTime, currentTime, previousTime;
int c = 0;

void setup() {
  Serial.begin(115200);
  while(!Wire.begin(SDA_PIN, SCL_PIN)){
    Serial.println("oi no i2c");
    delay(1000);
  }
  
  Wire.beginTransmission(MPU);
  Wire.write(0x6B);
  Wire.write(0x00);
  Wire.endTransmission(true);
  
  calculate_IMU_error();
  delay(20);
}

void loop() {
  // Read accelerometer
  Wire.beginTransmission(MPU);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU, 6, true);
  
  AccX = (int16_t)(Wire.read() << 8 | Wire.read()) / 16384.0;
  AccY = (int16_t)(Wire.read() << 8 | Wire.read()) / 16384.0;
  AccZ = (int16_t)(Wire.read() << 8 | Wire.read()) / 16384.0;
  
  accAngleX = (atan(AccY / sqrt(pow(AccX, 2) + pow(AccZ, 2))) * 180 / PI) - AccErrorX;
  accAngleY = (atan(-1 * AccX / sqrt(pow(AccY, 2) + pow(AccZ, 2))) * 180 / PI) - AccErrorY;
  
  // Read gyroscope
  previousTime = currentTime;
  currentTime = millis();
  elapsedTime = (currentTime - previousTime) / 1000;
  
  Wire.beginTransmission(MPU);
  Wire.write(0x43);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU, 6, true);
  
  GyroX = (int16_t)(Wire.read() << 8 | Wire.read()) / 131.0;
  GyroY = (int16_t)(Wire.read() << 8 | Wire.read()) / 131.0;
  GyroZ = (int16_t)(Wire.read() << 8 | Wire.read()) / 131.0;
  
  // Correct with calculated error values
  GyroX = GyroX - GyroErrorX;
  GyroY = GyroY - GyroErrorY;
  GyroZ = GyroZ - GyroErrorZ;
  
  // Integrate gyro angles
  gyroAngleX = gyroAngleX + GyroX * elapsedTime;
  gyroAngleY = gyroAngleY + GyroY * elapsedTime;
  yaw = yaw + GyroZ * elapsedTime;
  
  // Complementary filter
  roll = 0.96 * gyroAngleX + 0.04 * accAngleX;
  pitch = 0.96 * gyroAngleY + 0.04 * accAngleY;
  
  Serial.print(roll, 3);
  Serial.print(", ");
  Serial.print(pitch, 3);
  Serial.print(", ");
  Serial.println(yaw, 3);
}

void calculate_IMU_error() {
  Serial.println("wait...");
  delay(5000);
  
  // Accelerometer calibration
  while (c < 200) {
    Wire.beginTransmission(MPU);
    Wire.write(0x3B);
    Wire.endTransmission(false);
    Wire.requestFrom(MPU, 6, true);
    
    AccX = (int16_t)(Wire.read() << 8 | Wire.read()) / 16384.0;
    AccY = (int16_t)(Wire.read() << 8 | Wire.read()) / 16384.0;
    AccZ = (int16_t)(Wire.read() << 8 | Wire.read()) / 16384.0;
    
    AccErrorX = AccErrorX + (atan((AccY) / sqrt(pow((AccX), 2) + pow((AccZ), 2))) * 180 / PI);
    AccErrorY = AccErrorY + (atan(-1 * (AccX) / sqrt(pow((AccY), 2) + pow((AccZ), 2))) * 180 / PI);
    c++;
  }
  
  AccErrorX = AccErrorX / 200;
  AccErrorY = AccErrorY / 200;
  
  // Flush gyro buffers
  for(int i = 0; i < 20; i++) {
    Wire.beginTransmission(MPU);
    Wire.write(0x43);
    Wire.endTransmission(false);
    Wire.requestFrom(MPU, 6, true);
    Wire.read(); Wire.read();
    Wire.read(); Wire.read();
    Wire.read(); Wire.read();
    delay(3);
  }
  
  // Gyro calibration
  c = 0;
  int16_t GyroX_raw, GyroY_raw, GyroZ_raw;
  
  while (c < 200) {
    Wire.beginTransmission(MPU);
    Wire.write(0x43);
    Wire.endTransmission(false);
    Wire.requestFrom(MPU, 6, true);
    
    GyroX_raw = (int16_t)(Wire.read() << 8 | Wire.read());
    GyroY_raw = (int16_t)(Wire.read() << 8 | Wire.read());
    GyroZ_raw = (int16_t)(Wire.read() << 8 | Wire.read());
    
    GyroErrorX = GyroErrorX + (GyroX_raw / 131.0);
    GyroErrorY = GyroErrorY + (GyroY_raw / 131.0);
    GyroErrorZ = GyroErrorZ + (GyroZ_raw / 131.0);
    c++;
  }
  
  GyroErrorX = GyroErrorX / 200;
  GyroErrorY = GyroErrorY / 200;
  GyroErrorZ = GyroErrorZ / 200;
  
  Serial.print("AccErrorX: "); Serial.println(AccErrorX);
  Serial.print("AccErrorY: "); Serial.println(AccErrorY);
  Serial.print("GyroErrorX: "); Serial.println(GyroErrorX);
  Serial.print("GyroErrorY: "); Serial.println(GyroErrorY);
  Serial.print("GyroErrorZ: "); Serial.println(GyroErrorZ);
}