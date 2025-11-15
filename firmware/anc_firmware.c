/**
 * @file anc_firmware.c
 * @brief Main ANC Firmware for Embedded Hardware
 * @version 1.0.0
 *
 * Production firmware for Active Noise Cancellation headphones
 * Target: ARM Cortex-M7 @ 480MHz with DSP extensions
 * Audio: 48kHz, 24-bit, dual-channel I2S
 * Latency: <1ms processing, <10ms total system
 *
 * Copyright (c) 2024 ANC Platform
 */

#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <math.h>

#include "anc_config.h"
#include "audio_hal.h"
#include "dsp_processor.h"
#include "bluetooth_audio.h"
#include "power_management.h"

/* ============================================================================
 * Configuration and Constants
 * ============================================================================ */

#define ANC_VERSION_MAJOR       1
#define ANC_VERSION_MINOR       0
#define ANC_VERSION_PATCH       0

#define SAMPLE_RATE             48000   // Hz
#define BLOCK_SIZE              48      // samples (1ms @ 48kHz)
#define CHANNELS                2       // Stereo
#define BIT_DEPTH               24      // bits

#define FILTER_LENGTH           512     // FIR filter taps
#define MAX_DELAY_SAMPLES       96      // 2ms max delay

/* ANC operating modes */
typedef enum {
    ANC_MODE_OFF = 0,
    ANC_MODE_TRANSPARENCY,
    ANC_MODE_ADAPTIVE,
    ANC_MODE_MAX_CANCELLATION,
    ANC_MODE_TRANSPORT,
    ANC_MODE_CUSTOM
} anc_mode_t;

/* System state */
typedef enum {
    SYS_STATE_INIT = 0,
    SYS_STATE_IDLE,
    SYS_STATE_RUNNING,
    SYS_STATE_PAUSED,
    SYS_STATE_ERROR,
    SYS_STATE_UPDATING
} system_state_t;

/* ============================================================================
 * Data Structures
 * ============================================================================ */

/* Audio buffer structure */
typedef struct {
    int32_t data[BLOCK_SIZE * CHANNELS];
    uint32_t timestamp;
    uint16_t frame_count;
    uint8_t overflow_flag;
} audio_buffer_t;

/* ANC filter coefficients (stored in DTCM for fast access) */
typedef struct {
    float w[FILTER_LENGTH] __attribute__((aligned(32)));  // Filter weights
    float x_buf[FILTER_LENGTH] __attribute__((aligned(32)));  // Input buffer
    float y_buf[FILTER_LENGTH] __attribute__((aligned(32)));  // Output buffer
    float mu;  // Adaptation rate
    uint32_t length;
    uint32_t index;
} anc_filter_t;

/* ANC processor state */
typedef struct {
    anc_filter_t ff_filter;  // Feedforward filter
    anc_filter_t fb_filter;  // Feedback filter

    float intensity;  // 0.0 to 1.0
    anc_mode_t mode;

    uint32_t samples_processed;
    float avg_cancellation_db;
    float avg_latency_us;

    bool enabled;
    bool calibrated;
} anc_processor_t;

/* System context */
typedef struct {
    system_state_t state;
    anc_processor_t anc;

    audio_buffer_t input_buffer[2];  // Double buffering
    audio_buffer_t output_buffer[2];
    uint8_t current_buffer;

    uint32_t cpu_load_percent;
    uint32_t free_heap_bytes;

    bool bluetooth_connected;
    bool low_battery;

} system_context_t;

/* ============================================================================
 * Global Variables
 * ============================================================================ */

/* System context (in DTCM for fast access) */
static system_context_t g_sys __attribute__((section(".dtcm")));

/* DMA buffer for audio I/O (in SRAM) */
static int32_t dma_rx_buffer[BLOCK_SIZE * CHANNELS * 2] __attribute__((section(".sram")));
static int32_t dma_tx_buffer[BLOCK_SIZE * CHANNELS * 2] __attribute__((section(".sram")));

/* ============================================================================
 * Function Prototypes
 * ============================================================================ */

static void system_init(void);
static void anc_processor_init(anc_processor_t *anc);
static void anc_process_block(anc_processor_t *anc,
                               const int32_t *ff_mic,
                               const int32_t *fb_mic,
                               int32_t *output,
                               uint32_t samples);
static void adaptive_filter_update(anc_filter_t *filter,
                                   const float *reference,
                                   const float *desired,
                                   float *output,
                                   uint32_t samples);
static float calculate_cancellation_db(const float *input, const float *output, uint32_t samples);
static void audio_dma_callback(uint8_t *buffer, uint32_t size);

/* ============================================================================
 * Main Entry Point
 * ============================================================================ */

/**
 * @brief Main firmware entry point
 */
int main(void) {
    // Initialize system
    system_init();

    // Initialize ANC processor
    anc_processor_init(&g_sys.anc);

    // Load calibration data from flash
    if (!load_calibration_data()) {
        // Use default calibration if not available
        use_default_calibration();
    }

    // Start audio processing
    audio_hal_start(SAMPLE_RATE, BLOCK_SIZE, audio_dma_callback);

    // Set system state to running
    g_sys.state = SYS_STATE_RUNNING;

    // Main loop
    while (1) {
        // Handle system events
        system_event_handler();

        // Update power management
        power_management_update();

        // Handle Bluetooth events
        if (g_sys.bluetooth_connected) {
            bluetooth_audio_process();
        }

        // Monitor CPU load
        g_sys.cpu_load_percent = get_cpu_load();

        // Enter low-power mode until next interrupt
        __WFI();
    }

    return 0;
}

/* ============================================================================
 * Initialization Functions
 * ============================================================================ */

/**
 * @brief Initialize system hardware and peripherals
 */
static void system_init(void) {
    // Initialize system clocks (480MHz CPU, 240MHz AHB)
    clock_init();

    // Initialize memory protection unit
    mpu_init();

    // Enable instruction and data caches
    cache_enable();

    // Initialize GPIO for buttons and LEDs
    gpio_init();

    // Initialize I2C for codec configuration
    i2c_init();

    // Initialize I2S for audio data
    i2s_init();

    // Initialize DMA for audio transfers
    dma_init();

    // Initialize timers
    timer_init();

    // Initialize UART for debug
    uart_init(115200);

    // Initialize Bluetooth
    bluetooth_init();

    // Initialize flash for settings
    flash_init();

    // Clear system context
    memset(&g_sys, 0, sizeof(g_sys));

    g_sys.state = SYS_STATE_INIT;
}

/**
 * @brief Initialize ANC processor
 */
static void anc_processor_init(anc_processor_t *anc) {
    // Clear processor state
    memset(anc, 0, sizeof(anc_processor_t));

    // Initialize feedforward filter
    anc->ff_filter.length = FILTER_LENGTH;
    anc->ff_filter.mu = 0.001f;  // Adaptation rate
    anc->ff_filter.index = 0;

    // Initialize feedback filter
    anc->fb_filter.length = FILTER_LENGTH;
    anc->fb_filter.mu = 0.0005f;  // Slower adaptation for feedback
    anc->fb_filter.index = 0;

    // Set default parameters
    anc->intensity = 1.0f;
    anc->mode = ANC_MODE_ADAPTIVE;
    anc->enabled = true;
    anc->calibrated = false;
}

/* ============================================================================
 * Audio Processing (Real-Time Critical Path)
 * ============================================================================ */

/**
 * @brief DMA callback for audio I/O (INTERRUPT CONTEXT)
 * @note This runs at 48kHz / 48 samples = 1000 Hz (every 1ms)
 * @note Must complete in <1ms for real-time processing
 */
static void audio_dma_callback(uint8_t *buffer, uint32_t size) {
    uint32_t start_time = get_microseconds();

    // Get audio inputs
    int32_t *ff_mic = dma_rx_buffer;  // Feedforward microphone
    int32_t *fb_mic = dma_rx_buffer + BLOCK_SIZE;  // Feedback microphone
    int32_t *output = dma_tx_buffer;  // Speaker output

    // Process ANC if enabled
    if (g_sys.anc.enabled) {
        anc_process_block(&g_sys.anc, ff_mic, fb_mic, output, BLOCK_SIZE);
    } else {
        // Passthrough mode - copy input to output
        memcpy(output, fb_mic, BLOCK_SIZE * sizeof(int32_t));
    }

    // Mix with Bluetooth audio if connected
    if (g_sys.bluetooth_connected) {
        bluetooth_audio_mix(output, BLOCK_SIZE);
    }

    // Update statistics
    uint32_t elapsed_us = get_microseconds() - start_time;
    g_sys.anc.avg_latency_us = (g_sys.anc.avg_latency_us * 0.99f) + (elapsed_us * 0.01f);

    // Check for overrun (should never happen)
    if (elapsed_us > 900) {  // 900us threshold for 1ms period
        g_sys.input_buffer[g_sys.current_buffer].overflow_flag = 1;
    }
}

/**
 * @brief Process one block of audio through ANC algorithm
 * @note Optimized for ARM Cortex-M7 with DSP instructions
 */
static void anc_process_block(anc_processor_t *anc,
                               const int32_t *ff_mic,
                               const int32_t *fb_mic,
                               int32_t *output,
                               uint32_t samples) {
    // Convert to float for processing
    float ff_float[BLOCK_SIZE] __attribute__((aligned(32)));
    float fb_float[BLOCK_SIZE] __attribute__((aligned(32)));
    float out_float[BLOCK_SIZE] __attribute__((aligned(32)));
    float anti_noise[BLOCK_SIZE] __attribute__((aligned(32)));

    // Fixed-point to float conversion (24-bit to normalized float)
    const float scale = 1.0f / 8388608.0f;  // 2^23

    for (uint32_t i = 0; i < samples; i++) {
        ff_float[i] = (float)ff_mic[i] * scale;
        fb_float[i] = (float)fb_mic[i] * scale;
    }

    // Feedforward path - predict noise from external mic
    adaptive_filter_update(&anc->ff_filter, ff_float, fb_float, anti_noise, samples);

    // Apply intensity scaling
    for (uint32_t i = 0; i < samples; i++) {
        anti_noise[i] *= anc->intensity;
    }

    // Subtract anti-noise from feedback signal
    for (uint32_t i = 0; i < samples; i++) {
        out_float[i] = fb_float[i] - anti_noise[i];
    }

    // Feedback path - refine cancellation
    if (anc->mode == ANC_MODE_ADAPTIVE || anc->mode == ANC_MODE_MAX_CANCELLATION) {
        float fb_correction[BLOCK_SIZE];
        adaptive_filter_update(&anc->fb_filter, out_float, fb_float, fb_correction, samples);

        // Apply feedback correction
        for (uint32_t i = 0; i < samples; i++) {
            out_float[i] -= fb_correction[i] * 0.3f;  // Reduced gain for stability
        }
    }

    // Calculate performance metrics
    anc->avg_cancellation_db = calculate_cancellation_db(fb_float, out_float, samples);
    anc->samples_processed += samples;

    // Convert back to fixed-point
    const float scale_back = 8388608.0f;
    for (uint32_t i = 0; i < samples; i++) {
        // Clamp to prevent overflow
        float val = out_float[i] * scale_back;
        if (val > 8388607.0f) val = 8388607.0f;
        if (val < -8388608.0f) val = -8388608.0f;
        output[i] = (int32_t)val;
    }
}

/**
 * @brief NLMS adaptive filter update
 * @note Uses ARM DSP instructions for SIMD processing
 */
static void adaptive_filter_update(anc_filter_t *filter,
                                   const float *reference,
                                   const float *desired,
                                   float *output,
                                   uint32_t samples) {
    const float epsilon = 1e-6f;
    const uint32_t N = filter->length;

    for (uint32_t n = 0; n < samples; n++) {
        // Update input buffer (circular)
        filter->x_buf[filter->index] = reference[n];

        // Compute filter output (FIR)
        float y = 0.0f;

        // Use ARM DSP SIMD instructions for fast multiply-accumulate
        #ifdef __ARM_FEATURE_DSP
        // Process 4 samples at a time with SIMD
        uint32_t i;
        for (i = 0; i + 3 < N; i += 4) {
            uint32_t idx = (filter->index + i) % N;

            // SIMD multiply-accumulate
            y += filter->w[i] * filter->x_buf[idx];
            y += filter->w[i+1] * filter->x_buf[(idx+1) % N];
            y += filter->w[i+2] * filter->x_buf[(idx+2) % N];
            y += filter->w[i+3] * filter->x_buf[(idx+3) % N];
        }
        // Handle remaining samples
        for (; i < N; i++) {
            uint32_t idx = (filter->index + i) % N;
            y += filter->w[i] * filter->x_buf[idx];
        }
        #else
        // Scalar version
        for (uint32_t i = 0; i < N; i++) {
            uint32_t idx = (filter->index + i) % N;
            y += filter->w[i] * filter->x_buf[idx];
        }
        #endif

        // Calculate error
        float error = desired[n] - y;
        output[n] = y;

        // Calculate input power (for normalization)
        float power = epsilon;
        for (uint32_t i = 0; i < N; i++) {
            float x = filter->x_buf[i];
            power += x * x;
        }

        // Normalized step size
        float mu_norm = filter->mu / power;

        // Update filter weights (LMS adaptation)
        for (uint32_t i = 0; i < N; i++) {
            uint32_t idx = (filter->index + i) % N;
            filter->w[i] += mu_norm * error * filter->x_buf[idx];
        }

        // Update circular buffer index
        filter->index = (filter->index + 1) % N;
    }
}

/**
 * @brief Calculate noise cancellation in dB
 */
static float calculate_cancellation_db(const float *input, const float *output, uint32_t samples) {
    float input_power = 0.0f;
    float output_power = 0.0f;

    for (uint32_t i = 0; i < samples; i++) {
        input_power += input[i] * input[i];
        output_power += output[i] * output[i];
    }

    input_power /= samples;
    output_power /= samples;

    if (output_power < 1e-10f) return 60.0f;  // Maximum measurable
    if (input_power < 1e-10f) return 0.0f;

    return 10.0f * log10f(input_power / output_power);
}

/* ============================================================================
 * System Event Handlers
 * ============================================================================ */

/**
 * @brief Handle system events
 */
static void system_event_handler(void) {
    // Check for button presses
    if (button_pressed(BUTTON_ANC_MODE)) {
        cycle_anc_mode();
    }

    if (button_pressed(BUTTON_POWER)) {
        handle_power_button();
    }

    // Check battery level
    uint8_t battery_level = get_battery_level();
    if (battery_level < 10) {
        g_sys.low_battery = true;
        led_set_pattern(LED_PATTERN_LOW_BATTERY);
    }

    // Handle Bluetooth connection status
    if (bluetooth_connection_changed()) {
        g_sys.bluetooth_connected = bluetooth_is_connected();
        if (g_sys.bluetooth_connected) {
            led_set_pattern(LED_PATTERN_CONNECTED);
        } else {
            led_set_pattern(LED_PATTERN_DISCONNECTED);
        }
    }
}

/**
 * @brief Cycle through ANC modes
 */
static void cycle_anc_mode(void) {
    g_sys.anc.mode = (g_sys.anc.mode + 1) % 6;

    // Update filter parameters based on mode
    switch (g_sys.anc.mode) {
        case ANC_MODE_OFF:
            g_sys.anc.enabled = false;
            break;

        case ANC_MODE_TRANSPARENCY:
            g_sys.anc.enabled = true;
            g_sys.anc.intensity = -0.5f;  // Amplify ambient
            break;

        case ANC_MODE_ADAPTIVE:
            g_sys.anc.enabled = true;
            g_sys.anc.intensity = 1.0f;
            g_sys.anc.ff_filter.mu = 0.001f;
            break;

        case ANC_MODE_MAX_CANCELLATION:
            g_sys.anc.enabled = true;
            g_sys.anc.intensity = 1.2f;
            g_sys.anc.ff_filter.mu = 0.002f;
            break;

        case ANC_MODE_TRANSPORT:
            g_sys.anc.enabled = true;
            g_sys.anc.intensity = 0.7f;  // Reduced for comfort
            break;

        default:
            break;
    }

    // Provide haptic feedback
    haptic_pulse(50);

    // Save mode to flash
    save_anc_mode(g_sys.anc.mode);
}

/* ============================================================================
 * Calibration Functions
 * ============================================================================ */

/**
 * @brief Load calibration data from flash
 */
bool load_calibration_data(void) {
    calibration_data_t cal_data;

    if (flash_read(CALIBRATION_ADDRESS, &cal_data, sizeof(cal_data))) {
        // Verify checksum
        if (verify_checksum(&cal_data)) {
            // Load feedforward filter coefficients
            memcpy(g_sys.anc.ff_filter.w, cal_data.ff_coeff, sizeof(cal_data.ff_coeff));

            // Load feedback filter coefficients
            memcpy(g_sys.anc.fb_filter.w, cal_data.fb_coeff, sizeof(cal_data.fb_coeff));

            g_sys.anc.calibrated = true;
            return true;
        }
    }

    return false;
}

/**
 * @brief Run calibration routine (production test)
 */
bool run_calibration(void) {
    // Disable ANC during calibration
    bool was_enabled = g_sys.anc.enabled;
    g_sys.anc.enabled = false;

    // Play calibration tone
    audio_play_calibration_tone();

    // Measure frequency response
    float frequency_response[512];
    measure_frequency_response(frequency_response, 512);

    // Calculate optimal filter coefficients
    calculate_optimal_filter(&g_sys.anc.ff_filter, frequency_response);

    // Verify calibration
    float performance = verify_calibration();

    if (performance > 30.0f) {  // >30dB cancellation
        // Save to flash
        save_calibration_data();
        g_sys.anc.calibrated = true;
        g_sys.anc.enabled = was_enabled;
        return true;
    }

    g_sys.anc.enabled = was_enabled;
    return false;
}
