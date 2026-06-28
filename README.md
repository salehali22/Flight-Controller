<p align="center">
  <img src="Renders and Images/main.png" alt="SAL FC Front" width="420"/>
  &nbsp;&nbsp;&nbsp;
  <img src="Renders and Images/main2.png" alt="SAL FC Back" width="420"/>
</p>

<h1 align="center">SAL FC</h1>

<p align="center">
  Open-source flight controller platform built on the STM32H743VIT6
</p>

<p align="center">
  <img src="https://img.shields.io/badge/MCU-STM32H743VIT6-03234B?style=flat-square&logo=stmicroelectronics&logoColor=white" alt="MCU"/>
  <img src="https://img.shields.io/badge/Betaflight-4.5.1-FFB400?style=flat-square" alt="Betaflight"/>
  <img src="https://img.shields.io/badge/iNAV-9.0.1-1A8CFF?style=flat-square" alt="iNAV"/>
  <img src="https://img.shields.io/badge/ArduPilot-supported-00979D?style=flat-square" alt="ArduPilot"/>
  <img src="https://img.shields.io/badge/KiCad-PCB-314CB0?style=flat-square&logo=kicad&logoColor=white" alt="KiCad"/>
  <img src="https://img.shields.io/badge/license-CERN--OHL--S--2.0-brightgreen?style=flat-square" alt="License"/>
</p>

---

SAL FC is a custom 40.5 x 40.5 mm, six-layer flight controller PCB designed to bridge the gap between compact FPV racing boards and full-size autopilot systems. It supports three open-source firmware stacks (Betaflight, iNAV, and ArduPilot) on a single board with standard 30.5 mm mounting, dual IMUs, and a companion computer interface. Designed as a senior capstone project at Ilia State University, Tbilisi, Georgia.

---

## Table of Contents

- [Features](#features)
- [Hardware Specifications](#hardware-specifications)
- [Pin Mapping](#pin-mapping)
- [Wiring Diagrams](#wiring-diagrams)
- [Getting Started](#getting-started)
  - [Flashing Betaflight](#flashing-betaflight)
  - [Flashing iNAV](#flashing-inav)
  - [Flashing ArduPilot](#flashing-ardupilot)
- [Building from Source](#building-from-source)
- [CLI Backup and Restore](#cli-backup-and-restore)
- [Repository Structure](#repository-structure)
- [License](#license)
- [Credits](#credits)

---

## Features

**Hardware**
- STM32H743VIT6 Cortex-M7 at 480 MHz, 2 MB flash, 1 MB SRAM
- Dual dissimilar IMUs: TDK ICM42688P + Bosch BMI270 on separate SPI buses
- BMP388 barometric pressure sensor
- AT7456E analog OSD controller
- W25Q128 128 Mbit SPI flash for blackbox logging
- CAN bus transceiver (SN65HVD230D)
- USB-C with host and device support, 90 ohm differential impedance routing
- Reverse polarity protection (P-FET) and TVS diode protection on USB and power inputs
- Six-layer PCB (JLC06161H-3313 stackup), ENIG finish, resin-plugged vias

**Firmware**
- Betaflight 4.5.1, iNAV 9.0.1, and ArduPilot compiled from source with custom target definitions
- 12 PWM motor/servo outputs on advanced timers (TIM1, TIM8, TIM4) with independent DMA channels per output
- DSHOT150/300/600 protocol support
- MAVLink v2 companion computer telemetry over dedicated UART
- iNAV SPI6 HAL patch included for ICM42688P detection (see [`Firmware Target Files/iNAV/`](Firmware%20Target%20Files/iNAV/))

**Connectivity**
- 7 UARTs, 4 SPI buses, 3 I2C buses, 1 CAN bus
- CRSF / ExpressLRS receiver input
- GPS (uBlox M8N) with magnetometer passthrough on I2C4
- IRC Tramp VTX control, DJI air unit support
- JST-SH 1.0 mm connectors on all peripheral ports, with solder pad fallback
- 30.5 mm M3 mounting pattern, 40.5 x 40.5 mm board dimensions

---

## Hardware Specifications

<details>
<summary>Click to expand full specifications table</summary>

| Parameter | Value |
|---|---|
| **MCU** | STM32H743VIT6 (Cortex-M7, 480 MHz, 2 MB flash, 1 MB SRAM) |
| **Primary IMU** | TDK ICM42688P (SPI6, up to 32 kHz sampling) |
| **Secondary IMU** | Bosch BMI270 (SPI3, up to 6.4 kHz sampling) |
| **Barometer** | Bosch BMP388 (I2C2) |
| **OSD** | AT7456E (SPI4) |
| **Flash** | Winbond W25Q128JVSIQ, 128 Mbit (SPI1) |
| **CAN transceiver** | SN65HVD230D (ISO 11898) |
| **UARTs** | 7 |
| **SPI buses** | 4 |
| **I2C buses** | 3 |
| **PWM outputs** | 12 (8 motor + 4 servo) |
| **Motor protocol** | DSHOT150 / 300 / 600 |
| **Input voltage** | Up to 6S (25.2 V) |
| **5V rail** | AP63205WU buck converter |
| **9/12V VTX rail** | TPS54302 buck converter |
| **3.3V logic rail** | AP2112K-3.3 LDO |
| **3.3V sensor rail** | AP7343-33W5-7 low-noise LDO (dedicated IMU/baro supply) |
| **USB** | Type-C, host + device, 90 ohm differential routing |
| **Protection** | P-FET reverse polarity (AO3407A), TVS on USB/battery/5V, PTC fuses |
| **PCB** | 6-layer, FR-4, JLC06161H-3313, ENIG finish, resin-plugged vias |
| **Dimensions** | 40.5 x 40.5 mm |
| **Mounting** | 30.5 x 30.5 mm, M3 |
| **Weight (bare board)** | ~8 g |
| **Design tool** | KiCad |
| **Fabrication** | JLCPCB |

</details>

---

## Pin Mapping

### UART Assignments

| UART | Function | Pins (TX / RX) | Protocol |
|---|---|---|---|
| USART1 | Expansion / companion computer | PA9 / PA10 | MAVLink v2 |
| USART2 | VTX | PD5 / PD6 | IRC Tramp |
| USART3 | RC receiver | PD8 / PD9 | CRSF / ELRS |
| UART5 | General telemetry | PB6 / PB12 | User-assigned |
| UART7 | DJI air unit | PE8 / PE7 | MSP |
| UART8 | GPS | PE1 / PE0 | UBX / NMEA |

### SPI Bus Assignments

| SPI | Peripheral | CS | SCK / MISO / MOSI | Interrupt |
|---|---|---|---|---|
| SPI1 | W25Q128 flash | PA4 | PA5 / PA6 / PA7 | -- |
| SPI3 | BMI270 (secondary IMU) | PD3 | PC10 / PC11 / PC12 | PD2 |
| SPI4 | AT7456E OSD | PC13 | PE2 / PE5 / PE6 | -- |
| SPI6 | ICM42688P (primary IMU) | PD7 | PB3 / PB4 / PB5 | PE4 |

### Motor and Servo Outputs

| Output | Timer | Channel | Pin |
|---|---|---|---|
| Motor 1 | TIM1 | CH1 | PE9 |
| Motor 2 | TIM1 | CH2 | PE11 |
| Motor 3 | TIM1 | CH3 | PE13 |
| Motor 4 | TIM1 | CH4 | PE14 |
| Motor 5 | TIM8 | CH1 | PC6 |
| Motor 6 | TIM8 | CH2 | PC7 |
| Motor 7 | TIM8 | CH3 | PC8 |
| Motor 8 | TIM8 | CH4 | PC9 |
| Servo 1 | TIM4 | CH1 | PD12 |
| Servo 2 | TIM4 | CH2 | PD13 |
| Servo 3 | TIM4 | CH3 | PD14 |
| Servo 4 | TIM4 | CH4 | PD15 |

### I2C Bus Assignments

| I2C | Peripheral | Pins (SCL / SDA) |
|---|---|---|
| I2C2 | BMP388 barometer | PB10 / PB11 |
| I2C4 | GPS magnetometer / external | PB8 / PB7 |
| I2C (ext) | Airspeed sensor connector | Exposed on JST-SH |

### CubeMX Pin Map

<!-- Replace the path below with your actual CubeMX screenshot filename -->
<p align="center">
  <img src="Renders%20and%20Images/CubeMX_pinmap.png" alt="STM32CubeMX Pin Assignment" width="700"/>
</p>

### Board Layout

<p align="center">
  <img src="Renders%20and%20Images/FC_P1.png" alt="SAL FC Top View Labeled" width="500"/>
</p>

<p align="center">
  <img src="Renders%20and%20Images/FC_P2.png" alt="SAL FC Bottom View" width="500"/>
</p>

---

## Wiring Diagrams

<!-- Replace with your actual wiring diagram image filenames -->
<p align="center">
  <img src="Renders%20and%20Images/wiring_diagram.png" alt="SAL FC Wiring Diagram" width="700"/>
</p>

<p align="center">
  <img src="Renders%20and%20Images/expansion_wiring.png" alt="Expansion Board Wiring" width="700"/>
</p>

---

## Getting Started

### Flashing Betaflight

**Requirements:** Betaflight Configurator **10.10.0 standalone** (not the web version or the 2026.x alpha, which locks custom boards into CLI-only developer mode).

1. Enter DFU mode: hold the **BOOT** button while connecting USB-C.
2. Open Betaflight Configurator 10.10.0 and navigate to the **Firmware Flasher** tab.
3. Select **Load Firmware [Local]** and choose the SAL FC `.hex` file from [`Firmware Target Files/Betaflight/`](Firmware%20Target%20Files/Betaflight/).
4. Click **Flash Firmware**.
5. After flashing, the board will reboot and appear as a COM port.

> [!NOTE]
> Motor pin assignments (PE9/PE11/PE13/PE14 on TIM1, PC6-PC9 on TIM8) should be defined in `target.h` via `MOTOR1_PIN` through `MOTOR8_PIN`. If your hex was built without these defines, you will need to assign motors manually using the CLI `resource` command after flashing.

### Flashing iNAV

**Requirements:** [STM32CubeProgrammer](https://www.st.com/en/development-tools/stm32cubeprog.html)

1. Enter DFU mode: hold the **BOOT** button while connecting USB-C.
2. Open STM32CubeProgrammer, connect via **USB**, and erase the chip with **Full chip erase**.
3. Load the SAL FC iNAV `.hex` file from [`Firmware Target Files/iNAV/`](Firmware%20Target%20Files/iNAV/) and click **Start Programming**.
4. Disconnect and reconnect USB (without BOOT button). The board should enumerate as a COM port.
5. Open the iNAV Configurator to verify sensor detection.

> [!IMPORTANT]
> iNAV's STM32H743 HAL only enumerates SPI1 through SPI4 by default. The ICM42688P on SPI6 will not be detected without the custom SPI6 patch. The patched firmware hex in this repository already includes the fix. If building from source, apply the patch files in [`Firmware Target Files/iNAV/spi6-patch/`](Firmware%20Target%20Files/iNAV/spi6-patch/) before compiling. See [Building from Source](#building-from-source) for details.

> [!WARNING]
> Do **not** enable GPS in the iNAV Ports tab unless a GPS module is physically connected. Enabling GPS without hardware triggers a HWFAIL arming flag that prevents arming.

### Flashing ArduPilot

**Requirements:** [STM32CubeProgrammer](https://www.st.com/en/development-tools/stm32cubeprog.html), [Mission Planner](https://ardupilot.org/planner/docs/mission-planner-installation.html)

**First flash (bootloader + firmware):**

1. Enter DFU mode: hold the **BOOT** button while connecting USB-C.
2. Open STM32CubeProgrammer, connect via **USB**, and perform a **Full chip erase**.
3. Load the combined `arducopter_with_bl.hex` file from [`Firmware Target Files/ArduPilot/`](Firmware%20Target%20Files/ArduPilot/) and click **Start Programming**. This writes both the bootloader and firmware in one step.
4. Disconnect and reconnect USB. The board should enumerate as a COM port.
5. Open Mission Planner to verify telemetry and sensor detection.

**Subsequent updates:**

Once the bootloader is installed, future firmware updates can be done through Mission Planner: **Setup > Install Firmware > Load custom firmware** and select the new `.apk` / `.hex` file.

> [!IMPORTANT]
> The SAL FC uses a passive 8 MHz crystal, **not** an active oscillator. The ArduPilot `hwdef.dat` must set `STM32_HSE_BYPASS` to **disabled** (i.e., do not define it). If bypass mode is enabled, the PLL will fail to lock and USB will not enumerate. The target files in this repository are already configured correctly.

---

## Building from Source

<details>
<summary>Betaflight 4.5.1</summary>

```bash
# Ubuntu / WSL2
sudo apt install gcc-arm-none-eabi git make

git clone https://github.com/betaflight/betaflight.git
cd betaflight
git checkout v4.5.1

# Copy SAL FC target files into the source tree
cp -r "/path/to/Firmware Target Files/Betaflight/SALEHFC" src/main/target/SALEHFC

make TARGET=SALEHFC

# Output hex: obj/betaflight_4.5.1_SALEHFC.hex
```

</details>

<details>
<summary>iNAV 9.0.1 (with SPI6 patch)</summary>

```bash
# Ubuntu / WSL2
sudo apt install gcc-arm-none-eabi git make cmake

git clone https://github.com/iNavFlight/inav.git
cd inav
git checkout v9.0.1

# Copy SAL FC target
cp -r "/path/to/Firmware Target Files/iNAV/SALEHFC" src/main/target/SALEHFC

# Apply SPI6 patch (5 files, ~60 lines)
# This extends iNAV's SPI bus abstraction from SPI4 to SPI6
# so the ICM42688P on SPI6 is detected.
git apply "/path/to/Firmware Target Files/iNAV/spi6-patch/inav-spi6.patch"

mkdir build && cd build
cmake ..
make SALEHFC

# Output hex: build/bin/inav_9.0.1_SALEHFC.hex
```

The SPI6 patch modifies five files:
- `src/main/drivers/bus_spi.h` -- extends `SPIDevice` enum to include `SPIDEV_5` and `SPIDEV_6`
- `src/main/drivers/bus.h` -- adds `BUS_SPI5`, `BUS_SPI6` defines and `busIndex_e` entries
- `src/main/drivers/bus_spi_stm32h7xx.h` -- adds GPIO AF8 mappings for SPI6 pins (PB3/PB4/PB5)
- `src/main/drivers/bus_spi_hal_ll.c` -- adds SPI6 hardware map entry (APB4 clock, pin assignment)
- `target/SALEHFC/target.h` -- enables `USE_SPI_DEVICE_6` and registers ICM42688P on SPI6

SPI6 operates in polling mode (not DMA), so BDMA/SRAM4 constraints do not apply.

</details>

<details>
<summary>ArduPilot</summary>

```bash
# Ubuntu / WSL2
git clone --recurse-submodules https://github.com/ArduPilot/ardupilot.git
cd ardupilot
Tools/environment_install/install-prereqs-ubuntu.sh -y
. ~/.profile

# Copy SAL FC hardware definition
cp -r "/path/to/Firmware Target Files/ArduPilot/SALEHFC" libraries/AP_HAL_ChibiOS/hwdef/SALEHFC

./waf configure --board SALEHFC
./waf copter

# Output: build/SALEHFC/bin/arducopter_with_bl.hex
```

> [!NOTE]
> Do not define `STM32_HSE_BYPASS` in `hwdef.dat`. The board uses a passive crystal.

</details>

---

## CLI Backup and Restore

All three firmware stacks support CLI-based configuration backup.

**Betaflight / iNAV:**

```bash
# In the CLI tab of the Configurator:
diff all
```

Copy the entire output and save it to a text file. To restore on a freshly flashed board, paste the contents into the CLI tab and type `save`.

**ArduPilot:**

Use Mission Planner: **Config > Full Parameter List > Save to file** / **Load from file**.

---

## Repository Structure

```
Flight-Controller/
├── 3D Files/                       # Fusion 360 / STEP files for frame and mounts
├── Firmware Target Files/          # Custom target definitions and compiled hex files
│   ├── Betaflight/                 #   Betaflight 4.5.1 target and hex
│   ├── iNAV/                       #   iNAV 9.0.1 target, hex, and SPI6 patch
│   └── ArduPilot/                  #   ArduPilot hwdef and hex
├── Hardware/                       # KiCad project, Gerbers, BOM, pick-and-place
├── Renders and Images/             # PCB renders, photos, wiring diagrams, CubeMX
├── Website/                        # Project landing page
├── firmware/
│   └── Flight_Controller_h7/      # Firmware build workspace
├── recordings/                     # Test recordings and data
├── tools/                          # Build and utility scripts
├── LICENSE                         # CERN-OHL-S-2.0
└── README.md
```

> [!NOTE]
> Adjust this tree to match your actual repository layout. If your folder names or structure differ, update accordingly before committing.

---

## License

This project is licensed under the [CERN Open Hardware Licence Version 2 -- Strongly Reciprocal (CERN-OHL-S-2.0)](LICENSE).

You are free to study, modify, manufacture, and distribute this hardware design under the terms of the license.

---

## Credits

| Name | Role | GitHub |
|---|---|---|
| Saleh Alhomeidy | Project lead, PCB design, firmware porting | [@salehali22](https://github.com/salehali22) |
| Akaki Gvelesiani | Mechanical/technical lead, propulsion testing, sensor fusion | |
| Levani Kazaishvili | Schematic capture, soldering, hardware verification | |
