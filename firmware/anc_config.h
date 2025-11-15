/**
 * @file anc_config.h
 * @brief Hardware configuration for ANC firmware
 */

#ifndef ANC_CONFIG_H
#define ANC_CONFIG_H

#include <stdint.h>
#include <stdbool.h>

/* ============================================================================
 * Hardware Configuration
 * ============================================================================ */

/* MCU: STM32H7 series (ARM Cortex-M7 @ 480MHz) */
#define CPU_FREQ_HZ             480000000
#define AHB_FREQ_HZ             240000000
#define APB1_FREQ_HZ            120000000
#define APB2_FREQ_HZ            120000000

/* Memory Layout */
#define FLASH_BASE              0x08000000
#define FLASH_SIZE              (2 * 1024 * 1024)  // 2MB
#define SRAM_BASE               0x20000000
#define SRAM_SIZE               (512 * 1024)        // 512KB
#define DTCM_BASE               0x20000000
#define DTCM_SIZE               (128 * 1024)        // 128KB fast RAM

/* Flash Partitions */
#define BOOTLOADER_BASE         0x08000000
#define BOOTLOADER_SIZE         (64 * 1024)         // 64KB
#define FIRMWARE_BASE           0x08010000
#define FIRMWARE_SIZE           (960 * 1024)        // 960KB
#define BACKUP_FW_BASE          0x08100000
#define BACKUP_FW_SIZE          (960 * 1024)        // 960KB
#define CALIBRATION_ADDRESS     0x081F0000
#define CALIBRATION_SIZE        (64 * 1024)         // 64KB

/* ============================================================================
 * Audio Hardware Configuration
 * ============================================================================ */

/* Audio Codec: CS43L22 or similar */
#define CODEC_I2C_ADDRESS       0x94
#define CODEC_I2C_BUS           I2C1

/* I2S Configuration */
#define I2S_INSTANCE            SPI3
#define I2S_DMA_RX_STREAM       DMA1_Stream0
#define I2S_DMA_TX_STREAM       DMA1_Stream7

/* Microphone Configuration */
#define FF_MIC_CHANNEL          0  // Feedforward (external)
#define FB_MIC_CHANNEL          1  // Feedback (internal)

/* Speaker Configuration */
#define SPEAKER_LEFT_CHANNEL    0
#define SPEAKER_RIGHT_CHANNEL   1

/* ============================================================================
 * GPIO Pin Assignments
 * ============================================================================ */

/* Buttons */
#define BUTTON_ANC_MODE_PORT    GPIOA
#define BUTTON_ANC_MODE_PIN     0
#define BUTTON_POWER_PORT       GPIOA
#define BUTTON_POWER_PIN        1
#define BUTTON_VOLUME_UP_PORT   GPIOA
#define BUTTON_VOLUME_UP_PIN    2
#define BUTTON_VOLUME_DOWN_PORT GPIOA
#define BUTTON_VOLUME_DOWN_PIN  3

/* LEDs */
#define LED_STATUS_PORT         GPIOB
#define LED_STATUS_PIN          0
#define LED_BT_PORT             GPIOB
#define LED_BT_PIN              1
#define LED_BATTERY_PORT        GPIOB
#define LED_BATTERY_PIN         2

/* I2S Pins */
#define I2S_WS_PORT             GPIOA
#define I2S_WS_PIN              4
#define I2S_CK_PORT             GPIOC
#define I2S_CK_PIN              10
#define I2S_SD_PORT             GPIOC
#define I2S_SD_PIN              12
#define I2S_MCK_PORT            GPIOC
#define I2S_MCK_PIN             7

/* I2C Pins (for codec control) */
#define I2C_SCL_PORT            GPIOB
#define I2C_SCL_PIN             6
#define I2C_SDA_PORT            GPIOB
#define I2C_SDA_PIN             7

/* Bluetooth UART */
#define BT_UART_TX_PORT         GPIOC
#define BT_UART_TX_PIN          6
#define BT_UART_RX_PORT         GPIOC
#define BT_UART_RX_PIN          7

/* ============================================================================
 * Bluetooth Configuration
 * ============================================================================ */

#define BT_UART_INSTANCE        USART6
#define BT_UART_BAUDRATE        921600
#define BT_DEVICE_NAME          "ANC Headphones"
#define BT_PIN_CODE             "0000"

/* ============================================================================
 * Power Management
 * ============================================================================ */

#define BATTERY_ADC_CHANNEL     0
#define BATTERY_FULL_MV         4200
#define BATTERY_EMPTY_MV        3300
#define LOW_BATTERY_THRESHOLD   10  // percent

/* ============================================================================
 * Button Definitions
 * ============================================================================ */

typedef enum {
    BUTTON_ANC_MODE = 0,
    BUTTON_POWER,
    BUTTON_VOLUME_UP,
    BUTTON_VOLUME_DOWN,
    BUTTON_COUNT
} button_id_t;

/* ============================================================================
 * LED Patterns
 * ============================================================================ */

typedef enum {
    LED_PATTERN_OFF = 0,
    LED_PATTERN_ON,
    LED_PATTERN_SLOW_BLINK,
    LED_PATTERN_FAST_BLINK,
    LED_PATTERN_CONNECTED,
    LED_PATTERN_DISCONNECTED,
    LED_PATTERN_LOW_BATTERY,
    LED_PATTERN_CHARGING,
    LED_PATTERN_CALIBRATION
} led_pattern_t;

/* ============================================================================
 * Calibration Data Structure
 * ============================================================================ */

#define CALIBRATION_MAGIC       0xCAFEBABE
#define CALIBRATION_VERSION     1

typedef struct {
    uint32_t magic;
    uint32_t version;
    float ff_coeff[512];  // Feedforward filter coefficients
    float fb_coeff[512];  // Feedback filter coefficients
    float frequency_response[512];
    float avg_cancellation_db;
    uint32_t checksum;
} calibration_data_t;

/* ============================================================================
 * Firmware Update
 * ============================================================================ */

#define OTA_MAGIC               0xDEADBEEF
#define OTA_MAX_PACKET_SIZE     4096

typedef struct {
    uint32_t magic;
    uint32_t version;
    uint32_t size;
    uint32_t crc32;
    uint8_t signature[256];  // RSA signature
} firmware_header_t;

#endif /* ANC_CONFIG_H */
