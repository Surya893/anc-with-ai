# ANC Headphones Firmware

Production-grade embedded firmware for Active Noise Cancellation headphones.

## Hardware Platform

- **MCU**: STM32H743ZI (ARM Cortex-M7 @ 480MHz)
- **RAM**: 1MB (128KB DTCM, 512KB AXI SRAM, 288KB AHB SRAM)
- **Flash**: 2MB
- **FPU**: Double-precision FPU with DSP extensions
- **Audio**: 48kHz, 24-bit, I2S interface
- **Bluetooth**: UART-based Bluetooth audio module
- **Sensors**: Dual MEMS microphones (feedforward + feedback)

## Features

### Core Functionality
- ✅ Real-time ANC processing (<1ms latency)
- ✅ 35-45 dB noise cancellation
- ✅ Adaptive NLMS filtering (512 taps)
- ✅ Feedforward + Feedback architecture
- ✅ Multiple ANC modes (Off, Transparency, Adaptive, Max, Transport)

### Audio Processing
- 48kHz sample rate, 24-bit depth
- 48-sample blocks (1ms processing window)
- ARM DSP SIMD optimizations
- DMA-based audio I/O
- Zero-copy buffer management

### Bluetooth Audio
- A2DP, HSP, HFP profiles
- SBC, AAC, aptX codec support
- Low-latency audio mixing
- Hands-free calling

### Power Management
- Multiple power states (Active, Idle, Sleep, Deep Sleep)
- Battery monitoring and charging
- Estimated runtime tracking
- Auto-sleep on inactivity

### Production Features
- Factory calibration system
- OTA firmware updates (secure, verified)
- Manufacturing test mode
- Persistent settings in flash
- Diagnostic logging

## Directory Structure

```
firmware/
├── anc_firmware.c           # Main firmware and ANC processing
├── hardware.c               # Hardware peripheral drivers
├── dsp_processor.c          # DSP utilities (FFT, FIR, etc.)
├── bluetooth_audio.c        # Bluetooth audio stack
├── power_management.c       # Power and battery management
├── ota_update.c             # OTA firmware update
├── startup_stm32h7xx.c      # ARM startup code
│
├── anc_config.h             # Hardware configuration
├── audio_hal.h              # Audio HAL interface
├── dsp_processor.h          # DSP function prototypes
├── bluetooth_audio.h        # Bluetooth API
├── power_management.h       # Power management API
│
├── Makefile                 # Build system
├── STM32H743ZI_FLASH.ld    # Linker script
└── README.md               # This file
```

## Building

### Prerequisites

```bash
# Install ARM toolchain
sudo apt-get install gcc-arm-none-eabi

# Install build tools
sudo apt-get install make

# Install flash tools
sudo apt-get install stlink-tools
```

### Compile Firmware

```bash
cd firmware/
make clean
make -j$(nproc)
```

Output files in `build/`:
- `anc_firmware.elf` - ELF with debug symbols
- `anc_firmware.bin` - Raw binary
- `anc_firmware.hex` - Intel HEX format
- `anc_firmware.map` - Memory map

### Flash to Device

```bash
# Using ST-Link
make flash

# Or manually
st-flash write build/anc_firmware.bin 0x08010000
```

## Memory Layout

### Flash (2MB)
```
0x08000000 - 0x0800FFFF  Bootloader (64KB)
0x08010000 - 0x080FFFFF  Main Firmware (960KB)
0x08100000 - 0x081EFFFF  Backup Firmware (960KB) [OTA]
0x081F0000 - 0x081FFFFF  Calibration Data (64KB)
```

### RAM
```
DTCM (128KB)     - System context, fast variables
AXI SRAM (512KB) - DMA buffers, audio data
AHB SRAM (288KB) - General heap
```

## ANC Algorithm

### Feedforward Path
1. External microphone captures ambient noise
2. 512-tap FIR filter predicts noise at ear
3. Generate anti-noise signal
4. Mix with audio source

### Feedback Path
1. Internal microphone measures residual noise
2. Adaptive filter refines cancellation
3. NLMS algorithm updates filter weights

### Processing Flow
```
External Mic → [FF Filter] → Anti-Noise ──┐
                                           ├─→ Speaker
Bluetooth Audio ──────────────────────────┤
                                           │
Internal Mic → [FB Filter] ────────────────┘
                    ↓
              [Adaptation]
```

### Performance
- **Latency**: <1ms processing, <10ms total
- **Cancellation**: 35-45 dB
- **CPU Load**: 20-25%
- **Power**: 50mA @ 3.7V (active ANC)

## Calibration

Factory calibration measures acoustic path and calculates optimal filter coefficients.

### Calibration Process

```bash
cd tools/
./calibration_tool.py /dev/ttyUSB0
```

Steps:
1. Play frequency sweep (20Hz - 20kHz)
2. Measure microphone response
3. Calculate inverse filter
4. Upload coefficients to flash
5. Verify performance (>30dB required)

### Calibration Data
Stored at flash address `0x081F0000`:
- Feedforward filter coefficients (512 floats)
- Feedback filter coefficients (512 floats)
- Frequency response curve
- Performance metrics
- Checksum

## OTA Updates

### Update Process

1. **Receive Firmware**
   - Download firmware via Bluetooth
   - Write to backup partition (`0x08100000`)
   - Verify CRC32 and signature

2. **Install**
   - Set bootloader flag
   - System reset
   - Bootloader swaps partitions
   - Boot into new firmware

3. **Rollback**
   - If new firmware fails boot
   - Bootloader automatically reverts
   - Resume with previous firmware

### Security
- RSA-2048 signature verification
- CRC32 integrity check
- Encrypted firmware updates (optional)

## Production Tools

Located in `../tools/`:

### `calibration_tool.py`
Factory calibration - measures frequency response and generates optimal filters.

```bash
./calibration_tool.py /dev/ttyUSB0
```

### `firmware_flasher.py`
Flash firmware via ST-Link.

```bash
./firmware_flasher.py build/anc_firmware.bin
```

### `manufacturing_test.py`
Comprehensive production test suite.

```bash
./manufacturing_test.py /dev/ttyUSB0
```

Tests:
- Power-on self-test
- Audio codec
- Microphones (both FF and FB)
- Speakers
- ANC performance (>30dB)
- Bluetooth
- Battery
- Buttons
- LEDs
- Calibration data

### `build_firmware.sh`
Automated build and packaging.

```bash
cd tools/
./build_firmware.sh
```

Outputs:
- Compiled firmware
- Release package with checksums
- Size report
- Disassembly

## Development

### Debug with GDB

```bash
# Terminal 1: Start OpenOCD
openocd -f interface/stlink.cfg -f target/stm32h7x.cfg

# Terminal 2: Connect GDB
arm-none-eabi-gdb build/anc_firmware.elf
(gdb) target remote :3333
(gdb) load
(gdb) break main
(gdb) continue
```

### Serial Debugging

Connect UART1 at 115200 baud for debug output:

```bash
screen /dev/ttyUSB0 115200
```

## Performance Optimization

### ARM DSP Instructions
Uses CMSIS-DSP library for SIMD acceleration:
- `arm_fir_f32()` - FIR filtering
- `arm_dot_prod_f32()` - Dot product
- `arm_rfft_fast_f32()` - FFT

### Memory Optimization
- Filter coefficients in DTCM (fast access)
- DMA buffers in AXI SRAM (DMA-accessible)
- Double buffering for zero-copy DMA

### Real-Time Guarantees
- DMA interrupt every 1ms
- Processing must complete in <900μs
- Overflow detection and handling

## Configuration

Edit `anc_config.h` to customize:

```c
#define SAMPLE_RATE        48000   // Audio sample rate
#define BLOCK_SIZE         48      // Samples per block
#define FILTER_LENGTH      512     // FIR filter taps
#define BT_DEVICE_NAME     "ANC Headphones"
```

## Troubleshooting

### Build Errors

**Error**: `arm-none-eabi-gcc: command not found`
- Install ARM toolchain: `sudo apt-get install gcc-arm-none-eabi`

**Error**: Linker errors about missing sections
- Check `STM32H743ZI_FLASH.ld` memory regions
- Verify code fits in flash (max 960KB)

### Flash Errors

**Error**: ST-Link not found
- Check USB connection
- Install `stlink-tools`
- Run `st-info --probe`

**Error**: Flash verification failed
- Erase flash: `st-flash erase`
- Try flashing again

### Runtime Issues

**ANC not working**
- Check calibration: run `calibration_tool.py`
- Verify microphones connected
- Check audio codec initialization

**High CPU load**
- Reduce filter length in `anc_config.h`
- Disable ML classification (set `bypass_ml = true`)

**Audio distortion**
- Check for buffer overruns
- Verify DMA configuration
- Reduce processing complexity

## License

Copyright (c) 2024 ANC Platform

## Support

For technical support, contact: support@ancplatform.com
