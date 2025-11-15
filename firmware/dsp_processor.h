/**
 * @file dsp_processor.h
 * @brief DSP helper functions optimized for ARM Cortex-M7
 */

#ifndef DSP_PROCESSOR_H
#define DSP_PROCESSOR_H

#include <stdint.h>
#include <arm_math.h>  // CMSIS-DSP library

/* ============================================================================
 * DSP Utility Functions
 * ============================================================================ */

/**
 * @brief Fast FIR filter using CMSIS-DSP
 * @param input Input signal
 * @param coeffs Filter coefficients
 * @param output Output signal
 * @param num_taps Number of filter taps
 * @param block_size Number of samples to process
 */
void dsp_fir_filter(const float *input, const float *coeffs, float *output,
                    uint32_t num_taps, uint32_t block_size);

/**
 * @brief Fast convolution using CMSIS-DSP
 */
void dsp_conv(const float *a, uint32_t len_a, const float *b, uint32_t len_b, float *result);

/**
 * @brief Fast FFT using CMSIS-DSP
 * @param input Input signal (real)
 * @param output Output spectrum (complex)
 * @param fft_size FFT size (must be power of 2)
 */
void dsp_fft(const float *input, float *output, uint32_t fft_size);

/**
 * @brief Fast IFFT using CMSIS-DSP
 */
void dsp_ifft(const float *input, float *output, uint32_t fft_size);

/**
 * @brief Calculate RMS value
 * @param signal Input signal
 * @param length Number of samples
 * @return RMS value
 */
float dsp_rms(const float *signal, uint32_t length);

/**
 * @brief Calculate signal power in dB
 * @param signal Input signal
 * @param length Number of samples
 * @return Power in dB
 */
float dsp_power_db(const float *signal, uint32_t length);

/**
 * @brief Apply window function
 * @param signal Input/output signal
 * @param length Number of samples
 * @param window_type 0=Hamming, 1=Hanning, 2=Blackman
 */
void dsp_apply_window(float *signal, uint32_t length, uint8_t window_type);

/**
 * @brief Normalize signal to [-1, 1]
 */
void dsp_normalize(float *signal, uint32_t length);

/**
 * @brief Apply soft clipping (saturation)
 */
void dsp_soft_clip(float *signal, uint32_t length, float threshold);

/**
 * @brief Calculate optimal filter coefficients using Wiener filter
 * @param reference Reference signal
 * @param desired Desired signal
 * @param coeffs Output filter coefficients
 * @param num_taps Number of filter taps
 * @param num_samples Number of training samples
 */
void calculate_optimal_filter(const float *reference, const float *desired,
                              float *coeffs, uint32_t num_taps, uint32_t num_samples);

/**
 * @brief Verify calibration performance
 * @return Average cancellation in dB
 */
float verify_calibration(void);

/* ============================================================================
 * ARM SIMD Optimizations
 * ============================================================================ */

/**
 * @brief Vector dot product (SIMD optimized)
 */
float dsp_dot_product(const float *a, const float *b, uint32_t length);

/**
 * @brief Vector addition (SIMD optimized)
 */
void dsp_vec_add(const float *a, const float *b, float *result, uint32_t length);

/**
 * @brief Vector subtraction (SIMD optimized)
 */
void dsp_vec_sub(const float *a, const float *b, float *result, uint32_t length);

/**
 * @brief Vector scaling (SIMD optimized)
 */
void dsp_vec_scale(const float *input, float scale, float *output, uint32_t length);

#endif /* DSP_PROCESSOR_H */
