/**
 * @file power_management.c
 * @brief Power management and battery monitoring
 */

#include "power_management.h"
#include "anc_config.h"

/* ============================================================================
 * Power State
 * ============================================================================ */

static struct {
    power_state_t current_state;
    battery_status_t battery;
    uint32_t idle_time_ms;
    uint32_t last_activity_ms;
    uint32_t uptime_seconds;
    uint32_t cpu_cycles_busy;
    uint32_t cpu_cycles_total;
} power_state = {
    .current_state = POWER_STATE_INIT,
    .idle_time_ms = 0,
    .last_activity_ms = 0,
    .uptime_seconds = 0
};

/* ============================================================================
 * Initialization
 * ============================================================================ */

void power_management_init(void) {
    // Initialize ADC for battery monitoring
    adc_init();

    // Read initial battery level
    power_state.battery.voltage_mv = adc_read_battery_voltage();
    power_state.battery.level_percent = get_battery_level();
    power_state.battery.charging = is_charging();

    power_state.current_state = POWER_STATE_IDLE;
}

/* ============================================================================
 * Battery Monitoring
 * ============================================================================ */

void adc_init(void) {
    // Configure ADC1 for battery voltage monitoring
    // - Single conversion mode
    // - 12-bit resolution
    // - Enable temperature sensor
}

uint16_t adc_read_battery_voltage(void) {
    // Read ADC value
    uint16_t adc_value = 0;  // Read from ADC register

    // Convert to millivolts
    // Assuming voltage divider: Vbat -> R1 (10k) -> ADC -> R2 (10k) -> GND
    // Vref = 3.3V, 12-bit ADC
    uint32_t voltage_mv = (adc_value * 3300 * 2) / 4096;

    return (uint16_t)voltage_mv;
}

uint8_t get_battery_level(void) {
    uint16_t voltage = adc_read_battery_voltage();

    // Convert voltage to percentage
    // 4.2V = 100%, 3.3V = 0%
    if (voltage >= BATTERY_FULL_MV) return 100;
    if (voltage <= BATTERY_EMPTY_MV) return 0;

    int32_t level = ((int32_t)(voltage - BATTERY_EMPTY_MV) * 100) /
                    (BATTERY_FULL_MV - BATTERY_EMPTY_MV);

    return (uint8_t)level;
}

void get_battery_status(battery_status_t *status) {
    status->voltage_mv = adc_read_battery_voltage();
    status->level_percent = get_battery_level();
    status->charging = is_charging();
    status->low_battery = (status->level_percent < LOW_BATTERY_THRESHOLD);

    // Estimate time remaining (simplified)
    // Assuming 500mAh battery, 50mA average current
    if (!status->charging) {
        uint32_t remaining_mah = (status->level_percent * 500) / 100;
        status->time_remaining_min = (remaining_mah * 60) / 50;
    } else {
        status->time_remaining_min = 0;
    }

    // Update cached status
    power_state.battery = *status;
}

bool is_charging(void) {
    // Read charging status from GPIO pin
    // Typically connected to charge controller status pin
    return false;  // Stub
}

/* ============================================================================
 * Power State Management
 * ============================================================================ */

void power_management_update(void) {
    // Update battery status periodically
    static uint32_t last_battery_update = 0;
    uint32_t now = get_uptime_seconds();

    if (now - last_battery_update >= 10) {  // Update every 10 seconds
        get_battery_status(&power_state.battery);
        last_battery_update = now;
    }

    // Check for idle timeout
    uint32_t idle_ms = get_microseconds() / 1000 - power_state.last_activity_ms;

    if (idle_ms > 300000 && power_state.current_state == POWER_STATE_ACTIVE) {
        // 5 minutes idle - go to idle state
        power_set_state(POWER_STATE_IDLE);
    }

    if (idle_ms > 600000 && power_state.current_state == POWER_STATE_IDLE) {
        // 10 minutes idle - go to sleep
        power_set_state(POWER_STATE_SLEEP);
    }
}

power_state_t power_get_state(void) {
    return power_state.current_state;
}

void power_set_state(power_state_t state) {
    power_state.current_state = state;

    switch (state) {
        case POWER_STATE_ACTIVE:
            // Full power - enable all peripherals
            break;

        case POWER_STATE_IDLE:
            // Reduce power - disable unused peripherals
            // Keep Bluetooth active for connection
            break;

        case POWER_STATE_SLEEP:
            // Low power sleep mode
            enter_sleep_mode();
            break;

        case POWER_STATE_SHUTDOWN:
            // Complete shutdown
            shutdown_device();
            break;

        default:
            break;
    }
}

/* ============================================================================
 * Sleep and Shutdown
 * ============================================================================ */

void enter_sleep_mode(void) {
    // Disable audio processing
    audio_hal_stop();

    // Enter STOP mode
    // Wake on button press or Bluetooth event
    // __WFI();
}

void wake_from_sleep(void) {
    // Restore clocks
    clock_init();

    // Re-enable audio
    power_state.current_state = POWER_STATE_ACTIVE;
}

void handle_power_button(void) {
    static uint32_t press_time = 0;
    uint32_t now = get_microseconds() / 1000;

    if (press_time == 0) {
        // Button pressed
        press_time = now;
    } else {
        // Button released
        uint32_t duration = now - press_time;
        press_time = 0;

        if (duration > 3000) {
            // Long press (>3s) - shutdown
            shutdown_device();
        } else {
            // Short press - toggle power state
            if (power_state.current_state == POWER_STATE_SLEEP) {
                wake_from_sleep();
            } else {
                enter_sleep_mode();
            }
        }
    }
}

void shutdown_device(void) {
    // Save state to flash
    save_calibration_data();

    // Disable all peripherals
    audio_hal_stop();

    // Turn off codec
    audio_codec_mute(true);

    // Enter standby mode
    // __WFI();
    while (1) {
        // Wait for power button to wake
    }
}

/* ============================================================================
 * Performance Monitoring
 * ============================================================================ */

uint32_t get_cpu_load(void) {
    // Calculate CPU load percentage
    // This would measure time spent in processing vs idle

    if (power_state.cpu_cycles_total == 0) return 0;

    uint32_t load = (power_state.cpu_cycles_busy * 100) / power_state.cpu_cycles_total;

    // Reset counters periodically
    static uint32_t last_reset = 0;
    if (get_uptime_seconds() - last_reset > 1) {
        power_state.cpu_cycles_busy = 0;
        power_state.cpu_cycles_total = 0;
        last_reset = get_uptime_seconds();
    }

    return load;
}

uint32_t get_uptime_seconds(void) {
    // Return system uptime in seconds
    // This would use RTC or timer
    return power_state.uptime_seconds;
}
