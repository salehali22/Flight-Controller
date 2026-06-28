TARGET_MCU        := STM32H743xx
TARGET_MCU_FAMILY := STM32H7

H743xI_TARGETS += $(TARGET)

FEATURES       += VCP ONBOARDFLASH

TARGET_SRC = \
    drivers/accgyro/accgyro_spi_icm426xx.c \
    drivers/accgyro/accgyro_spi_bmi270.c \
    drivers/barometer/barometer_bmp388.c \
    drivers/max7456.c
