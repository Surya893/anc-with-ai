/**
 * @file audio_hal.h
 * @brief Hardware Abstraction Layer for Audio I/O
 */

#ifndef AUDIO_HAL_H
#define AUDIO_HAL_H

#include <stdint.h>
#include <stdbool.h>

/* ============================================================================
 * Type Definitions
 * ============================================================================ */

/**
 * @brief Audio callback function type
 * Called when DMA transfer completes (interrupt context)
 */
typedef void (*audio_callback_t)(uint8_t *buffer, uint32_t size);

/* ============================================================================
 * Audio HAL Functions
 * ============================================================================ */

/**
 * @brief Initialize I2S audio interface
 * @return true if successful
 */
bool i2s_init(void);

/**
 * @brief Start audio streaming
 * @param sample_rate Sample rate in Hz (e.g., 48000)
 * @param block_size Number of samples per block
 * @param callback Function to call when audio block is ready
 * @return true if successful
 */
bool audio_hal_start(uint32_t sample_rate, uint32_t block_size, audio_callback_t callback);

/**
 * @brief Stop audio streaming
 */
void audio_hal_stop(void);

/**
 * @brief Configure audio codec via I2C
 * @return true if successful
 */
bool audio_codec_init(void);

/**
 * @brief Set codec volume
 * @param volume Volume level 0-100
 */
void audio_codec_set_volume(uint8_t volume);

/**
 * @brief Mute/unmute codec
 * @param mute true to mute, false to unmute
 */
void audio_codec_mute(bool mute);

/**
 * @brief Play calibration tone
 * @param frequency Frequency in Hz
 * @param duration Duration in milliseconds
 */
void audio_play_calibration_tone(void);

/**
 * @brief Measure frequency response
 * @param response Output array for frequency response
 * @param num_points Number of frequency points
 * @return true if successful
 */
bool measure_frequency_response(float *response, uint32_t num_points);

/* ============================================================================
 * Low-Level I2S Functions
 * ============================================================================ */

/**
 * @brief Initialize DMA for audio transfers
 */
void dma_init(void);

/**
 * @brief Start DMA transfer
 */
void dma_start(void);

/**
 * @brief Stop DMA transfer
 */
void dma_stop(void);

/**
 * @brief DMA half-transfer complete callback (internal)
 */
void audio_dma_half_transfer_callback(void);

/**
 * @brief DMA full-transfer complete callback (internal)
 */
void audio_dma_full_transfer_callback(void);

/* ============================================================================
 * I2C Codec Control
 * ============================================================================ */

/**
 * @brief Initialize I2C interface
 */
bool i2c_init(void);

/**
 * @brief Write to codec register
 * @param reg Register address
 * @param value Value to write
 * @return true if successful
 */
bool codec_write_register(uint8_t reg, uint8_t value);

/**
 * @brief Read from codec register
 * @param reg Register address
 * @param value Pointer to store read value
 * @return true if successful
 */
bool codec_read_register(uint8_t reg, uint8_t *value);

#endif /* AUDIO_HAL_H */
