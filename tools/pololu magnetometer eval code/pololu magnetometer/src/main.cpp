#include <Arduino.h>
#include <Wire.h>

#define SDA_PIN 25
#define SCL_PIN 26


const uint8_t LSM303D_ADDR = 0x1D;

int16_t x_raw, y_raw, z_raw;
float x_g, y_g, z_g;
float heading = 0;

uint16_t sample_count = 0;

float x_avg = 0;
float y_avg = 0;
float z_avg = 0;
float heading_avg = 0;

uint32_t now = 0;
uint32_t last_time = 0;

void setup() {
  Serial.begin(115200);
  Wire.begin(SDA_PIN, SCL_PIN);



  // Initialize LSM303D

  Wire.beginTransmission(LSM303D_ADDR);
  Wire.write(0x1F);    // CTRL0
  Wire.write(0x80);    // Enable auto-increment
  Wire.endTransmission();


  Wire.beginTransmission(LSM303D_ADDR);
  Wire.write(0x20);
  Wire.write(0x08); 
  Wire.endTransmission();

  Wire.beginTransmission(LSM303D_ADDR);
  Wire.write(0x24); 
  Wire.write(0x74);
  Wire.endTransmission();

  Wire.beginTransmission(LSM303D_ADDR);
  Wire.write(0x25);
  Wire.write(0x20);
  Wire.endTransmission();

  Wire.beginTransmission(LSM303D_ADDR);
  Wire.write(0x26);
  Wire.write(0x00);
  Wire.endTransmission();

  now = millis();

}

void readData(){
  uint8_t buffer[6];
  // 0 - 5: OUT_X_L_M, OUT_X_H_M, OUT_Y_L_M, OUT_Y_H_M, OUT_Z_L_M, OUT_Z_H_M
  Wire.beginTransmission(LSM303D_ADDR);
  Wire.write(0x08);
  Wire.endTransmission(false);
  Wire.requestFrom(LSM303D_ADDR, (uint8_t)6);
  for(int i=0; i<6; i++){
    if(Wire.available()){
      buffer[i] = Wire.read();
    }
  }

  x_raw = (int16_t)(buffer[1] << 8 | buffer[0]);
  y_raw = (int16_t)(buffer[3] << 8 | buffer[2]);
  z_raw = (int16_t)(buffer[5] << 8 | buffer[4]);

  x_g = x_raw * 0.00016;
  y_g = y_raw * 0.00016;
  z_g = z_raw * 0.00016;


}

void calculateHeading(){
  heading = atan2(y_g, x_g) * 180 / PI;
  if(heading < 0){
    heading += 360;
  }
}

void loop() {
  // sample_count++;
  last_time = now;
  now = millis();
  //Serial.println(now - last_time);
  if(now - last_time >= 10){
    readData();
    calculateHeading();
    Serial.printf("X: %.2f | Y: %.2f | Z: %.2f | Heading: %.2f\n", x_g, y_g, z_g, heading);
  }

  // if(sample_count == 1000){
  //   Serial.println("Initial samples: ");
  //   Serial.printf("X: %.2f | Y: %.2f | Z: %.2f | Heading: %.2f\n", x_g, y_g, z_g, heading);
  // }

  // if(sample_count > 1000 && sample_count < 21000){
  //   get_average(sample_count - 1000);
  // }

  // if(sample_count == 21000){
  //   Serial.println("Final samples: ");
  //   Serial.printf("X: %.2f | Y: %.2f | Z: %.2f | Heading: %.2f\n", x_g, y_g, z_g, heading);

  //   Serial.println("Averaged samples over 20000 readings: ");
  //   Serial.printf("X: %.2f | Y: %.2f | Z: %.2f | Heading: %.2f\n", x_avg, y_avg, z_avg, heading_avg);

  //   while(1);
  // }

}


void get_average(uint32_t count){

  x_avg += (x_g - x_avg) / count;
  y_avg += (y_g - y_avg) / count;
  z_avg += (z_g - z_avg) / count;
  heading_avg += (heading - heading_avg) / count;


}


