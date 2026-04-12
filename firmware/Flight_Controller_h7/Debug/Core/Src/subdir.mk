################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (14.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../Core/Src/bmi2.c \
../Core/Src/bmi270.c \
../Core/Src/bmi270_stm32.c \
../Core/Src/bmp388.c \
../Core/Src/complementary_filter.c \
../Core/Src/crsf.c \
../Core/Src/dshot.c \
../Core/Src/icm42688p.c \
../Core/Src/main.c \
../Core/Src/motor_mix.c \
../Core/Src/stm32h7xx_hal_msp.c \
../Core/Src/stm32h7xx_it.c \
../Core/Src/syscalls.c \
../Core/Src/sysmem.c \
../Core/Src/system_stm32h7xx.c 

OBJS += \
./Core/Src/bmi2.o \
./Core/Src/bmi270.o \
./Core/Src/bmi270_stm32.o \
./Core/Src/bmp388.o \
./Core/Src/complementary_filter.o \
./Core/Src/crsf.o \
./Core/Src/dshot.o \
./Core/Src/icm42688p.o \
./Core/Src/main.o \
./Core/Src/motor_mix.o \
./Core/Src/stm32h7xx_hal_msp.o \
./Core/Src/stm32h7xx_it.o \
./Core/Src/syscalls.o \
./Core/Src/sysmem.o \
./Core/Src/system_stm32h7xx.o 

C_DEPS += \
./Core/Src/bmi2.d \
./Core/Src/bmi270.d \
./Core/Src/bmi270_stm32.d \
./Core/Src/bmp388.d \
./Core/Src/complementary_filter.d \
./Core/Src/crsf.d \
./Core/Src/dshot.d \
./Core/Src/icm42688p.d \
./Core/Src/main.d \
./Core/Src/motor_mix.d \
./Core/Src/stm32h7xx_hal_msp.d \
./Core/Src/stm32h7xx_it.d \
./Core/Src/syscalls.d \
./Core/Src/sysmem.d \
./Core/Src/system_stm32h7xx.d 


# Each subdirectory must supply rules for building sources it contributes
Core/Src/%.o Core/Src/%.su Core/Src/%.cyclo: ../Core/Src/%.c Core/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m7 -std=gnu11 -g3 -DDEBUG -DUSE_PWR_LDO_SUPPLY -DUSE_HAL_DRIVER -DSTM32H743xx -c -I../Core/Inc -I../Drivers/STM32H7xx_HAL_Driver/Inc -I../Drivers/STM32H7xx_HAL_Driver/Inc/Legacy -I../Drivers/CMSIS/Device/ST/STM32H7xx/Include -I../Drivers/CMSIS/Include -I../USB_DEVICE/App -I../USB_DEVICE/Target -I../Middlewares/ST/STM32_USB_Device_Library/Core/Inc -I../Middlewares/ST/STM32_USB_Device_Library/Class/CDC/Inc -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv5-d16 -mfloat-abi=hard -mthumb -o "$@"

clean: clean-Core-2f-Src

clean-Core-2f-Src:
	-$(RM) ./Core/Src/bmi2.cyclo ./Core/Src/bmi2.d ./Core/Src/bmi2.o ./Core/Src/bmi2.su ./Core/Src/bmi270.cyclo ./Core/Src/bmi270.d ./Core/Src/bmi270.o ./Core/Src/bmi270.su ./Core/Src/bmi270_stm32.cyclo ./Core/Src/bmi270_stm32.d ./Core/Src/bmi270_stm32.o ./Core/Src/bmi270_stm32.su ./Core/Src/bmp388.cyclo ./Core/Src/bmp388.d ./Core/Src/bmp388.o ./Core/Src/bmp388.su ./Core/Src/complementary_filter.cyclo ./Core/Src/complementary_filter.d ./Core/Src/complementary_filter.o ./Core/Src/complementary_filter.su ./Core/Src/crsf.cyclo ./Core/Src/crsf.d ./Core/Src/crsf.o ./Core/Src/crsf.su ./Core/Src/dshot.cyclo ./Core/Src/dshot.d ./Core/Src/dshot.o ./Core/Src/dshot.su ./Core/Src/icm42688p.cyclo ./Core/Src/icm42688p.d ./Core/Src/icm42688p.o ./Core/Src/icm42688p.su ./Core/Src/main.cyclo ./Core/Src/main.d ./Core/Src/main.o ./Core/Src/main.su ./Core/Src/motor_mix.cyclo ./Core/Src/motor_mix.d ./Core/Src/motor_mix.o ./Core/Src/motor_mix.su ./Core/Src/stm32h7xx_hal_msp.cyclo ./Core/Src/stm32h7xx_hal_msp.d ./Core/Src/stm32h7xx_hal_msp.o ./Core/Src/stm32h7xx_hal_msp.su ./Core/Src/stm32h7xx_it.cyclo ./Core/Src/stm32h7xx_it.d ./Core/Src/stm32h7xx_it.o ./Core/Src/stm32h7xx_it.su ./Core/Src/syscalls.cyclo ./Core/Src/syscalls.d ./Core/Src/syscalls.o ./Core/Src/syscalls.su ./Core/Src/sysmem.cyclo ./Core/Src/sysmem.d ./Core/Src/sysmem.o ./Core/Src/sysmem.su ./Core/Src/system_stm32h7xx.cyclo ./Core/Src/system_stm32h7xx.d ./Core/Src/system_stm32h7xx.o ./Core/Src/system_stm32h7xx.su

.PHONY: clean-Core-2f-Src

