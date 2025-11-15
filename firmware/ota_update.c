/**
 * @file ota_update.c
 * @brief Over-The-Air firmware update mechanism
 */

#include "anc_config.h"
#include "power_management.h"
#include <string.h>

/* ============================================================================
 * OTA Update State
 * ============================================================================ */

typedef enum {
    OTA_STATE_IDLE = 0,
    OTA_STATE_RECEIVING,
    OTA_STATE_VERIFYING,
    OTA_STATE_INSTALLING,
    OTA_STATE_COMPLETE,
    OTA_STATE_ERROR
} ota_state_t;

static struct {
    ota_state_t state;
    firmware_header_t header;
    uint32_t bytes_received;
    uint32_t total_bytes;
    uint32_t current_address;
    uint32_t crc32_calculated;
    uint8_t packet_buffer[OTA_MAX_PACKET_SIZE];
} ota_state = {
    .state = OTA_STATE_IDLE
};

/* ============================================================================
 * CRC32 Calculation
 * ============================================================================ */

static const uint32_t crc32_table[256] = {
    0x00000000, 0x77073096, 0xEE0E612C, 0x990951BA,
    // ... (full table would be here)
    0xB40BBE37, 0xC30C8EA1, 0x5A05DF1B, 0x2D02EF8D
};

static uint32_t crc32_update(uint32_t crc, const uint8_t *data, uint32_t len) {
    crc = ~crc;
    for (uint32_t i = 0; i < len; i++) {
        crc = crc32_table[(crc ^ data[i]) & 0xFF] ^ (crc >> 8);
    }
    return ~crc;
}

/* ============================================================================
 * Flash Operations
 * ============================================================================ */

extern bool flash_erase_sector(uint32_t address);
extern bool flash_write(uint32_t address, const void *data, uint32_t size);
extern bool flash_read(uint32_t address, void *data, uint32_t size);

static bool ota_erase_backup_partition(void) {
    // Erase backup firmware partition
    for (uint32_t addr = BACKUP_FW_BASE; addr < BACKUP_FW_BASE + BACKUP_FW_SIZE; addr += 0x20000) {
        if (!flash_erase_sector(addr)) {
            return false;
        }
    }
    return true;
}

static bool ota_write_chunk(uint32_t offset, const uint8_t *data, uint32_t size) {
    uint32_t address = BACKUP_FW_BASE + offset;

    // Verify address is within backup partition
    if (address < BACKUP_FW_BASE || address + size > BACKUP_FW_BASE + BACKUP_FW_SIZE) {
        return false;
    }

    return flash_write(address, data, size);
}

/* ============================================================================
 * Signature Verification (RSA)
 * ============================================================================ */

static bool verify_firmware_signature(const firmware_header_t *header, const uint8_t *firmware, uint32_t size) {
    // In production, this would verify RSA signature
    // Using public key stored in bootloader

    // Simplified check for now
    return (header->magic == OTA_MAGIC);
}

/* ============================================================================
 * OTA Update Functions
 * ============================================================================ */

/**
 * @brief Start OTA update process
 * @param header Firmware header received from remote
 * @return true if update can proceed
 */
bool ota_begin_update(const firmware_header_t *header) {
    // Verify header
    if (header->magic != OTA_MAGIC) {
        return false;
    }

    // Check firmware size
    if (header->size > BACKUP_FW_SIZE) {
        return false;
    }

    // Save header
    memcpy(&ota_state.header, header, sizeof(firmware_header_t));

    // Erase backup partition
    if (!ota_erase_backup_partition()) {
        ota_state.state = OTA_STATE_ERROR;
        return false;
    }

    // Initialize state
    ota_state.bytes_received = 0;
    ota_state.total_bytes = header->size;
    ota_state.current_address = BACKUP_FW_BASE;
    ota_state.crc32_calculated = 0;
    ota_state.state = OTA_STATE_RECEIVING;

    return true;
}

/**
 * @brief Receive firmware data packet
 * @param data Packet data
 * @param size Packet size
 * @return true if successful
 */
bool ota_receive_packet(const uint8_t *data, uint32_t size) {
    if (ota_state.state != OTA_STATE_RECEIVING) {
        return false;
    }

    if (size > OTA_MAX_PACKET_SIZE) {
        return false;
    }

    // Update CRC
    ota_state.crc32_calculated = crc32_update(ota_state.crc32_calculated, data, size);

    // Write to flash
    if (!ota_write_chunk(ota_state.bytes_received, data, size)) {
        ota_state.state = OTA_STATE_ERROR;
        return false;
    }

    // Update progress
    ota_state.bytes_received += size;

    // Check if complete
    if (ota_state.bytes_received >= ota_state.total_bytes) {
        ota_state.state = OTA_STATE_VERIFYING;
        return ota_verify_firmware();
    }

    return true;
}

/**
 * @brief Verify received firmware
 * @return true if firmware is valid
 */
bool ota_verify_firmware(void) {
    ota_state.state = OTA_STATE_VERIFYING;

    // Verify CRC32
    if (ota_state.crc32_calculated != ota_state.header.crc32) {
        ota_state.state = OTA_STATE_ERROR;
        return false;
    }

    // Read firmware from flash for signature verification
    uint8_t *firmware_data = (uint8_t*)BACKUP_FW_BASE;

    // Verify signature
    if (!verify_firmware_signature(&ota_state.header, firmware_data, ota_state.total_bytes)) {
        ota_state.state = OTA_STATE_ERROR;
        return false;
    }

    ota_state.state = OTA_STATE_COMPLETE;
    return true;
}

/**
 * @brief Install verified firmware and reboot
 */
void ota_install_firmware(void) {
    if (ota_state.state != OTA_STATE_COMPLETE) {
        return;
    }

    ota_state.state = OTA_STATE_INSTALLING;

    // Set bootloader flag to swap firmware partitions
    uint32_t boot_flag = 0xDEADBEEF;
    flash_write(CALIBRATION_ADDRESS + 0x200, &boot_flag, sizeof(boot_flag));

    // Reset system - bootloader will handle the swap
    NVIC_SystemReset();
}

/**
 * @brief Get OTA update progress
 * @return Progress percentage (0-100)
 */
uint8_t ota_get_progress(void) {
    if (ota_state.total_bytes == 0) return 0;
    return (uint8_t)((ota_state.bytes_received * 100) / ota_state.total_bytes);
}

/**
 * @brief Get OTA state
 */
ota_state_t ota_get_state(void) {
    return ota_state.state;
}

/**
 * @brief Cancel OTA update
 */
void ota_cancel_update(void) {
    ota_state.state = OTA_STATE_IDLE;
    ota_state.bytes_received = 0;
    ota_state.total_bytes = 0;
}

/* ============================================================================
 * Bootloader Communication
 * ============================================================================ */

/**
 * @brief Check if firmware update is pending
 * Called by bootloader during startup
 */
bool bootloader_check_update_pending(void) {
    uint32_t boot_flag;
    flash_read(CALIBRATION_ADDRESS + 0x200, &boot_flag, sizeof(boot_flag));

    return (boot_flag == 0xDEADBEEF);
}

/**
 * @brief Swap firmware partitions
 * Called by bootloader
 */
bool bootloader_swap_firmware(void) {
    // Copy backup firmware to main partition
    uint8_t buffer[4096];

    for (uint32_t offset = 0; offset < FIRMWARE_SIZE; offset += sizeof(buffer)) {
        // Read from backup
        flash_read(BACKUP_FW_BASE + offset, buffer, sizeof(buffer));

        // Erase main if needed
        if (offset % 0x20000 == 0) {
            flash_erase_sector(FIRMWARE_BASE + offset);
        }

        // Write to main
        flash_write(FIRMWARE_BASE + offset, buffer, sizeof(buffer));
    }

    // Clear boot flag
    uint32_t boot_flag = 0;
    flash_write(CALIBRATION_ADDRESS + 0x200, &boot_flag, sizeof(boot_flag));

    return true;
}

/* ============================================================================
 * Bluetooth OTA Protocol
 * ============================================================================ */

/**
 * @brief Handle OTA command received via Bluetooth
 * @param cmd Command byte
 * @param data Command data
 * @param len Data length
 */
void ota_handle_bluetooth_command(uint8_t cmd, const uint8_t *data, uint32_t len) {
    switch (cmd) {
        case 0x01:  // OTA_BEGIN
            {
                firmware_header_t *header = (firmware_header_t*)data;
                if (ota_begin_update(header)) {
                    // Send ACK
                    uint8_t response = 0x01;  // Success
                    bluetooth_send_command((char*)&response, 1);
                } else {
                    uint8_t response = 0x00;  // Failure
                    bluetooth_send_command((char*)&response, 1);
                }
            }
            break;

        case 0x02:  // OTA_DATA
            if (ota_receive_packet(data, len)) {
                // Send progress
                uint8_t progress = ota_get_progress();
                bluetooth_send_command((char*)&progress, 1);
            }
            break;

        case 0x03:  // OTA_END
            if (ota_state.state == OTA_STATE_COMPLETE) {
                // Install and reboot
                ota_install_firmware();
            }
            break;

        case 0x04:  // OTA_CANCEL
            ota_cancel_update();
            break;

        default:
            break;
    }
}
