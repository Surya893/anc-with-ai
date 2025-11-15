/**
 * @file bluetooth_audio.h
 * @brief Bluetooth audio stack integration
 */

#ifndef BLUETOOTH_AUDIO_H
#define BLUETOOTH_AUDIO_H

#include <stdint.h>
#include <stdbool.h>

/* ============================================================================
 * Bluetooth Configuration
 * ============================================================================ */

#define BT_AUDIO_BUFFER_SIZE    2048
#define BT_MAX_PACKET_SIZE      512

/* Bluetooth audio codecs */
typedef enum {
    BT_CODEC_SBC = 0,   // Standard Bluetooth audio
    BT_CODEC_AAC,       // Advanced Audio Coding
    BT_CODEC_APTX,      // aptX
    BT_CODEC_APTX_HD,   // aptX HD
    BT_CODEC_LDAC       // Sony LDAC
} bt_codec_t;

/* Bluetooth profiles */
typedef enum {
    BT_PROFILE_A2DP = 0,  // Advanced Audio Distribution Profile
    BT_PROFILE_HSP,       // Headset Profile
    BT_PROFILE_HFP        // Hands-Free Profile
} bt_profile_t;

/* Connection state */
typedef enum {
    BT_STATE_DISCONNECTED = 0,
    BT_STATE_CONNECTING,
    BT_STATE_CONNECTED,
    BT_STATE_STREAMING
} bt_state_t;

/* ============================================================================
 * Bluetooth Functions
 * ============================================================================ */

/**
 * @brief Initialize Bluetooth module
 * @return true if successful
 */
bool bluetooth_init(void);

/**
 * @brief Start Bluetooth discovery (pairing mode)
 */
void bluetooth_start_discovery(void);

/**
 * @brief Stop Bluetooth discovery
 */
void bluetooth_stop_discovery(void);

/**
 * @brief Check if Bluetooth is connected
 * @return true if connected
 */
bool bluetooth_is_connected(void);

/**
 * @brief Get current connection state
 */
bt_state_t bluetooth_get_state(void);

/**
 * @brief Check if connection state changed
 * @return true if state changed since last call
 */
bool bluetooth_connection_changed(void);

/**
 * @brief Process Bluetooth audio (decode and buffer)
 * Called from main loop
 */
void bluetooth_audio_process(void);

/**
 * @brief Mix Bluetooth audio with ANC output
 * @param output Output buffer to mix into
 * @param num_samples Number of samples
 */
void bluetooth_audio_mix(int32_t *output, uint32_t num_samples);

/**
 * @brief Set Bluetooth audio volume
 * @param volume Volume level 0-100
 */
void bluetooth_set_volume(uint8_t volume);

/**
 * @brief Get current codec in use
 * @return Current Bluetooth codec
 */
bt_codec_t bluetooth_get_codec(void);

/**
 * @brief Disconnect Bluetooth
 */
void bluetooth_disconnect(void);

/**
 * @brief Send audio via Bluetooth (for microphone)
 * @param data Audio data to send
 * @param num_samples Number of samples
 */
void bluetooth_send_audio(const int16_t *data, uint32_t num_samples);

/* ============================================================================
 * Low-Level Bluetooth UART
 * ============================================================================ */

/**
 * @brief Initialize Bluetooth UART
 */
bool bluetooth_uart_init(void);

/**
 * @brief Send command to Bluetooth module
 * @param cmd Command string
 * @param len Length of command
 * @return true if successful
 */
bool bluetooth_send_command(const char *cmd, uint32_t len);

/**
 * @brief Read response from Bluetooth module
 * @param buffer Buffer to store response
 * @param max_len Maximum length to read
 * @return Number of bytes read
 */
uint32_t bluetooth_read_response(char *buffer, uint32_t max_len);

#endif /* BLUETOOTH_AUDIO_H */
