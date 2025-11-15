##############################################################################
# Makefile for ANC Firmware
# Target: ARM Cortex-M7 (STM32H7 series)
##############################################################################

# Project name
PROJECT = anc_firmware

# Build directory
BUILD_DIR = build

# Optimization
OPT = -O2

# Debug build?
DEBUG = 1

##############################################################################
# Toolchain
##############################################################################

PREFIX = arm-none-eabi-
CC = $(PREFIX)gcc
AS = $(PREFIX)gcc -x assembler-with-cpp
CP = $(PREFIX)objcopy
SZ = $(PREFIX)size
AR = $(PREFIX)ar
GDB = $(PREFIX)gdb

HEX = $(CP) -O ihex
BIN = $(CP) -O binary -S

##############################################################################
# MCU Configuration
##############################################################################

# CPU
CPU = -mcpu=cortex-m7

# FPU
FPU = -mfpu=fpv5-d16

# Float ABI
FLOAT-ABI = -mfloat-abi=hard

# MCU
MCU = $(CPU) -mthumb $(FPU) $(FLOAT-ABI)

##############################################################################
# Source Files
##############################################################################

# C sources
C_SOURCES = \
anc_firmware.c \
hardware.c \
dsp_processor.c \
bluetooth_audio.c \
power_management.c \
ota_update.c \
startup_stm32h7xx.c

# ASM sources
ASM_SOURCES =

##############################################################################
# Include Paths
##############################################################################

C_INCLUDES = \
-I. \
-ICMSIS/Include \
-ICMSIS/Device/ST/STM32H7xx/Include

##############################################################################
# C Defines
##############################################################################

C_DEFS = \
-DSTM32H743xx \
-DUSE_HAL_DRIVER \
-DARM_MATH_CM7 \
-D__FPU_PRESENT=1

##############################################################################
# Compiler Flags
##############################################################################

# C flags
CFLAGS = $(MCU) $(C_DEFS) $(C_INCLUDES) $(OPT) -Wall -fdata-sections -ffunction-sections

ifeq ($(DEBUG), 1)
CFLAGS += -g -gdwarf-2
endif

# Generate dependency files
CFLAGS += -MMD -MP -MF"$(@:%.o=%.d)"

# ASM flags
ASFLAGS = $(MCU) $(AS_DEFS) $(AS_INCLUDES) $(OPT) -Wall -fdata-sections -ffunction-sections

##############################################################################
# Linker Flags
##############################################################################

# Linker script
LDSCRIPT = STM32H743ZI_FLASH.ld

# Libraries
LIBS = -lc -lm -lnosys
LIBDIR =

LDFLAGS = $(MCU) -specs=nano.specs -T$(LDSCRIPT) $(LIBDIR) $(LIBS) -Wl,-Map=$(BUILD_DIR)/$(PROJECT).map,--cref -Wl,--gc-sections

##############################################################################
# Build Targets
##############################################################################

# Default target
all: $(BUILD_DIR)/$(PROJECT).elf $(BUILD_DIR)/$(PROJECT).hex $(BUILD_DIR)/$(PROJECT).bin

# List of objects
OBJECTS = $(addprefix $(BUILD_DIR)/,$(notdir $(C_SOURCES:.c=.o)))
vpath %.c $(sort $(dir $(C_SOURCES)))

OBJECTS += $(addprefix $(BUILD_DIR)/,$(notdir $(ASM_SOURCES:.s=.o)))
vpath %.s $(sort $(dir $(ASM_SOURCES)))

# Build object files
$(BUILD_DIR)/%.o: %.c Makefile | $(BUILD_DIR)
	@echo "CC $<"
	@$(CC) -c $(CFLAGS) -Wa,-a,-ad,-alms=$(BUILD_DIR)/$(notdir $(<:.c=.lst)) $< -o $@

$(BUILD_DIR)/%.o: %.s Makefile | $(BUILD_DIR)
	@echo "AS $<"
	@$(AS) -c $(CFLAGS) $< -o $@

# Link
$(BUILD_DIR)/$(PROJECT).elf: $(OBJECTS) Makefile
	@echo "LD $@"
	@$(CC) $(OBJECTS) $(LDFLAGS) -o $@
	@$(SZ) $@

# Generate hex
$(BUILD_DIR)/%.hex: $(BUILD_DIR)/%.elf | $(BUILD_DIR)
	@echo "HEX $@"
	@$(HEX) $< $@

# Generate bin
$(BUILD_DIR)/%.bin: $(BUILD_DIR)/%.elf | $(BUILD_DIR)
	@echo "BIN $@"
	@$(BIN) $< $@

# Create build directory
$(BUILD_DIR):
	mkdir -p $@

##############################################################################
# Utility Targets
##############################################################################

# Clean
clean:
	-rm -fR $(BUILD_DIR)

# Flash firmware
flash: all
	st-flash write $(BUILD_DIR)/$(PROJECT).bin 0x08000000

# Debug with GDB
debug: all
	$(GDB) -x gdb_init $(BUILD_DIR)/$(PROJECT).elf

# Generate tags for code navigation
tags:
	ctags -R .

# Print size information
size: $(BUILD_DIR)/$(PROJECT).elf
	$(SZ) --format=berkeley $<

# Disassembly
disasm: $(BUILD_DIR)/$(PROJECT).elf
	$(PREFIX)objdump -d $< > $(BUILD_DIR)/$(PROJECT).asm

##############################################################################
# Dependencies
##############################################################################

-include $(wildcard $(BUILD_DIR)/*.d)

##############################################################################
# Phony Targets
##############################################################################

.PHONY: all clean flash debug tags size disasm
