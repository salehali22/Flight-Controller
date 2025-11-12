#include <Arduino.h>
#include <Wire.h>

// Pin definitions
#define SDA_PIN 25
#define SCL_PIN 26

// MPU6050 settings
const int MPU_ADDR = 0x68;

// Streaming control
bool streaming = false;
String mode = "FILTERED";  // RAW, FILTERED, BOTH
int sample_rate = 100;     // Hz
float alpha = 0.98;        // Complementary filter
int duration = 0;          // seconds (0 = infinite)
int target_samples = 0;    // specific sample count (0 = use duration)
unsigned long stream_start_time = 0;
unsigned long sample_count = 0;

// Timing
unsigned long last_sample_time = 0;
unsigned long sample_interval = 10; // ms (100Hz default)

// Sensor data
float AccX, AccY, AccZ;
float GyroX, GyroY, GyroZ;

// Calculated angles
float accAngleX, accAngleY;
float gyroAngleX, gyroAngleY;
float roll, pitch, yaw;

// Error correction values
float AccErrorX = 0, AccErrorY = 0;
float GyroErrorX = 0, GyroErrorY = 0, GyroErrorZ = 0;


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
  roll = alpha * gyroAngleX + (1.0 - alpha) * accAngleX;
  pitch = alpha * gyroAngleY + (1.0 - alpha) * accAngleY;
}

void print_data() {
  if (mode == "RAW") {
    // Raw sensor data only
    Serial.print(GyroX, 3); Serial.print(", ");
    Serial.print(GyroY, 3); Serial.print(", ");
    Serial.print(GyroZ, 3); Serial.print(", ");
    Serial.print(AccX, 3); Serial.print(", ");
    Serial.print(AccY, 3); Serial.print(", ");
    Serial.println(AccZ, 3);
  }
  else if (mode == "FILTERED") {
    // Filtered angles only (default format)
    Serial.print(roll, 3); Serial.print(", ");
    Serial.print(pitch, 3); Serial.print(", ");
    Serial.println(yaw, 3);
  }
  else if (mode == "BOTH") {
    // Both filtered angles and raw sensors
    Serial.print(roll, 3); Serial.print(", ");
    Serial.print(pitch, 3); Serial.print(", ");
    Serial.print(yaw, 3); Serial.print(", ");
    Serial.print(GyroX, 3); Serial.print(", ");
    Serial.print(GyroY, 3); Serial.print(", ");
    Serial.print(GyroZ, 3); Serial.print(", ");
    Serial.print(AccX, 3); Serial.print(", ");
    Serial.print(AccY, 3); Serial.print(", ");
    Serial.println(AccZ, 3);
  }
}

void calibrate_imu(int num_samples) {
  Serial.println("[STATUS] Calibrating... Keep sensor stationary");
  delay(2000);
  
  // Reset errors
  AccErrorX = AccErrorY = 0;
  GyroErrorX = GyroErrorY = GyroErrorZ = 0;
  
  // Accelerometer calibration
  for (int i = 0; i < num_samples; i++) {
    read_accelerometer();
    AccErrorX += atan(AccY / sqrt(pow(AccX, 2) + pow(AccZ, 2))) * 180 / PI;
    AccErrorY += atan(-AccX / sqrt(pow(AccY, 2) + pow(AccZ, 2))) * 180 / PI;
    delay(3);
  }
  AccErrorX /= num_samples;
  AccErrorY /= num_samples;
  
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
  for (int i = 0; i < num_samples; i++) {
    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x43);
    Wire.endTransmission(false);
    Wire.requestFrom(MPU_ADDR, 6, true);
    
    GyroErrorX += (int16_t)(Wire.read() << 8 | Wire.read()) / 131.0;
    GyroErrorY += (int16_t)(Wire.read() << 8 | Wire.read()) / 131.0;
    GyroErrorZ += (int16_t)(Wire.read() << 8 | Wire.read()) / 131.0;
    delay(3);
  }
  GyroErrorX /= num_samples;
  GyroErrorY /= num_samples;
  GyroErrorZ /= num_samples;
  
  Serial.print("[STATUS] Calibration complete: AccErr=(");
  Serial.print(AccErrorX, 3); Serial.print(",");
  Serial.print(AccErrorY, 3); Serial.print(") GyroErr=(");
  Serial.print(GyroErrorX, 3); Serial.print(",");
  Serial.print(GyroErrorY, 3); Serial.print(",");
  Serial.print(GyroErrorZ, 3); Serial.println(")");
}

void send_status() {
  Serial.print("[STATUS] Mode=");
  Serial.print(mode);
  Serial.print(" Rate=");
  Serial.print(sample_rate);
  Serial.print("Hz Alpha=");
  Serial.println(alpha, 2);
}

void start_streaming() {
  streaming = true;
  stream_start_time = millis();
  sample_count = 0;
  
  // Reset angles
  gyroAngleX = accAngleX;
  gyroAngleY = accAngleY;
  yaw = 0;
  
  // Send data block start marker with metadata
  Serial.print("<DATA:MODE=");
  Serial.print(mode);
  Serial.print(",RATE=");
  Serial.print(sample_rate);
  Serial.print(",ALPHA=");
  Serial.print(alpha, 2);
  if (duration > 0) {
    Serial.print(",DURATION=");
    Serial.print(duration);
  }
  if (target_samples > 0) {
    Serial.print(",SAMPLES=");
    Serial.print(target_samples);
  }
  Serial.println(">");
  
  last_sample_time = millis();
}

void stop_streaming() {
  if (streaming) {
    streaming = false;
    Serial.println("</DATA>");
    
    Serial.print("[STATUS] Stream complete: ");
    Serial.print(sample_count);
    Serial.print(" samples in ");
    Serial.print((millis() - stream_start_time) / 1000.0, 2);
    Serial.println(" seconds");
  }
}

void handle_command(String cmd) {
  cmd.trim();
  cmd.toUpperCase();
  
  if (cmd.startsWith("MODE:")) {
    mode = cmd.substring(5);
    mode.trim();
    Serial.print("[STATUS] Mode set to: ");
    Serial.println(mode);
  }
  else if (cmd.startsWith("RATE:")) {
    sample_rate = cmd.substring(5).toInt();
    sample_interval = 1000 / sample_rate;
    Serial.print("[STATUS] Sample rate set to: ");
    Serial.print(sample_rate);
    Serial.println(" Hz");
  }
  else if (cmd.startsWith("ALPHA:")) {
    alpha = cmd.substring(6).toFloat();
    if (alpha < 0.0) alpha = 0.0;
    if (alpha > 1.0) alpha = 1.0;
    Serial.print("[STATUS] Alpha set to: ");
    Serial.println(alpha, 2);
  }
  else if (cmd.startsWith("DURATION:")) {
    duration = cmd.substring(9).toInt();
    target_samples = 0;  // Clear samples target
    Serial.print("[STATUS] Duration set to: ");
    Serial.print(duration);
    Serial.println(" seconds");
  }
  else if (cmd.startsWith("SAMPLES:")) {
    target_samples = cmd.substring(8).toInt();
    duration = 0;  // Clear duration
    Serial.print("[STATUS] Target samples set to: ");
    Serial.println(target_samples);
  }
  else if (cmd.startsWith("CALIBRATE:")) {
    int num_samples = cmd.substring(10).toInt();
    if (num_samples < 100) num_samples = 100;
    if (num_samples > 5000) num_samples = 5000;
    calibrate_imu(num_samples);
  }
  else if (cmd == "START") {
    start_streaming();
  }
  else if (cmd == "STOP") {
    stop_streaming();
  }
  else if (cmd == "STATUS") {
    send_status();
  }
  else if (cmd == "RESET") {
    // Reset filter state
    gyroAngleX = 0;
    gyroAngleY = 0;
    yaw = 0;
    roll = 0;
    pitch = 0;
    Serial.println("[STATUS] Filter state reset");
  }
  else {
    Serial.print("[ERROR] Unknown command: ");
    Serial.println(cmd);
  }
}

void check_serial_commands() {
  while (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    handle_command(cmd);
  }
}

void setup() {
  Serial.begin(115200);
  
  Serial.println("[STATUS] ESP32 IMU Monitor starting...");
  
  while(!Wire.begin(SDA_PIN, SCL_PIN)) {
    Serial.println("[ERROR] I2C initialization failed");
    delay(1000);
  }
  
  // Wake up MPU6050
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);
  Wire.write(0x00);
  Wire.endTransmission(true);
  
  Serial.println("[STATUS] MPU6050 initialized");
  
  // Auto-calibrate on startup
  calibrate_imu(1000);
  
  send_status();
  Serial.println("[STATUS] Ready for commands");
  Serial.println("[INFO] Commands: MODE:FILTERED/RAW/BOTH, RATE:100, ALPHA:0.98, DURATION:60, SAMPLES:1000, CALIBRATE:1000, START, STOP, STATUS, RESET");
  
  sample_interval = 1000 / sample_rate;
}

void loop() {
  // Check for serial commands
  check_serial_commands();
  
  // Stream data if active
  if (streaming) {
    unsigned long current_time = millis();
    
    // Check if stream should stop
    if (duration > 0) {
      if ((current_time - stream_start_time) >= (duration * 1000UL)) {
        stop_streaming();
        return;
      }
    }
    if (target_samples > 0) {
      if (sample_count >= target_samples) {
        stop_streaming();
        return;
      }
    }
    
    // Sample at specified rate
    if (current_time - last_sample_time >= sample_interval) {
      last_sample_time = current_time;
      
      read_accelerometer();
      read_gyroscope();
      calculate_acc_angles();
      
      float dt = sample_interval / 1000.0;
      integrate_gyro(dt);
      apply_complementary_filter();
      
      print_data();
      sample_count++;
    }
  }
}