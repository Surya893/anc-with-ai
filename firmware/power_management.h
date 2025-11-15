/**
 * @file power_management.h
 * @brief Power management and battery monitoring
 */

#ifndef POWER_MANAGEMENT_H
#define POWER_MANAGEMENT_H

#include <stdint.h>
#include <stdbool.h>

/* ============================================================================
 * Power States
 * ============================================================================ */

typedef enum {
    POWER_STATE_ACTIVE = 0,   // Full power, ANC active
    POWER_STATE_IDLE,         // Reduced power, no audio
    POWER_STATE_SLEEP,        // Low power sleep
    POWER_STATE_DEEP_SLEEP,   // Deep sleep, quick wake
    POWER_STATE_SHUTDOWN,     // Complete shutdown
    POWER_STATE_CHARGING      // Battery charging
} power_state_t;

/* ============================================================================
 * Battery Status
 * ============================================================================ */

typedef struct {
    uint8_t level_percent;    // 0-100%
    uint16_t voltage_mv;      // Millivolts
    int16_t current_ma;       // Milliamps (negative = charging)
    bool charging;
    bool low_battery;
    uint32_t time_remaining_min;  // Estimated minutes remaining
} battery_status_t;

/* ============================================================================
 * Power Management Functions
 * ============================================================================ */

/**
 * @brief Initialize power management
 */
void power_management_init(void);

/**
 * @brief Update power management (call from main loop)
 */
void power_management_update(void);

/**
 * @brief Get current power state
 */
power_state_t power_get_state(void);

/**
 * @brief Set power state
 * @param state Desired power state
 */
void power_set_state(power_state_t state);

/**
 * @brief Get battery level (0-100%)
 */
uint8_t get_battery_level(void);

/**
 * @brief Get full battery status
 * @param status Pointer to battery_status_t structure
 */
void get_battery_status(battery_status_t *status);

/**
 * @brief Check if charging
 * @return true if battery is charging
 */
bool is_charging(void);

/**
 * @brief Handle power button press
 */
void handle_power_button(void);

/**
 * @brief Enter sleep mode
 */
void enter_sleep_mode(void);

/**
 * @brief Wake from sleep
 */
void wake_from_sleep(void);

/**
 * @brief Shutdown device
 */
void shutdown_device(void);

/**
 * @brief Get CPU load percentage
 * @return CPU load 0-100%
 */
uint32_t get_cpu_load(void);

/**
 * @brief Get system uptime in seconds
 */
uint32_t get_uptime_seconds(void);

/**
 * @brief Get current time in microseconds
 */
uint32_t get_microseconds(void);

/* ============================================================================
 * Clock and Timer Functions
 * ============================================================================ */

/**
 * @brief Initialize system clocks
 */
void clock_init(void);

/**
 * @brief Initialize timers
 */
void timer_init(void);

/**
 * @brief Delay in milliseconds
 */
void delay_ms(uint32_t ms);

/**
 * @brief Delay in microseconds
 */
void delay_us(uint32_t us);

/* ============================================================================
 * ADC Functions (for battery monitoring)
 * ============================================================================ */

/**
 * @brief Initialize ADC for battery monitoring
 */
void adc_init(void);

/**
 * @brief Read battery voltage
 * @return Voltage in millivolts
 */
uint16_t adc_read_battery_voltage(void);

#endif /* POWER_MANAGEMENT_H */
