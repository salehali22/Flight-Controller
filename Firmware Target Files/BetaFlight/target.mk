# Betaflight 4.5.1 target.mk for SALEHFC
# Place in src/main/target/SALEHFC/

H743xI_TARGETS += $(TARGET)

FEATURES       += VCP ONBOARDFLASH

TARGET_SRC = \
    drivers/accgyro/accgyro_spi_icm426xx.c \
    drivers/accgyro/accgyro_spi_bmi270.c \
    drivers/barometer/barometer_bmp388.c \
    drivers/max7456.c
