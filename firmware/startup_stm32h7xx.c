/**
 * @file startup_stm32h7xx.c
 * @brief Startup code for STM32H7 series
 * @details Initialize system, copy .data section, clear .bss, call main()
 */

#include <stdint.h>

/* Linker symbols */
extern uint32_t _sidata;
extern uint32_t _sdata;
extern uint32_t _edata;
extern uint32_t _sbss;
extern uint32_t _ebss;
extern uint32_t _estack;

/* Main entry point */
extern int main(void);

/* System initialization */
extern void SystemInit(void);

/* Cortex-M7 core handlers */
void Reset_Handler(void);
void Default_Handler(void);

void NMI_Handler(void) __attribute__((weak, alias("Default_Handler")));
void HardFault_Handler(void) __attribute__((weak, alias("Default_Handler")));
void MemManage_Handler(void) __attribute__((weak, alias("Default_Handler")));
void BusFault_Handler(void) __attribute__((weak, alias("Default_Handler")));
void UsageFault_Handler(void) __attribute__((weak, alias("Default_Handler")));
void SVC_Handler(void) __attribute__((weak, alias("Default_Handler")));
void DebugMon_Handler(void) __attribute__((weak, alias("Default_Handler")));
void PendSV_Handler(void) __attribute__((weak, alias("Default_Handler")));
void SysTick_Handler(void) __attribute__((weak, alias("Default_Handler")));

/* STM32H7 peripheral handlers */
void WWDG_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void PVD_AVD_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void TAMP_STAMP_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void RTC_WKUP_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void FLASH_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void RCC_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void EXTI0_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void EXTI1_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void EXTI2_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void EXTI3_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void EXTI4_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void DMA1_Stream0_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void DMA1_Stream1_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void DMA1_Stream2_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void DMA1_Stream3_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void DMA1_Stream4_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void DMA1_Stream5_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void DMA1_Stream6_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void ADC_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void FDCAN1_IT0_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void FDCAN2_IT0_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void FDCAN1_IT1_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void FDCAN2_IT1_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void EXTI9_5_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void TIM1_BRK_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void TIM1_UP_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void TIM1_TRG_COM_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void TIM1_CC_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void TIM2_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void TIM3_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void TIM4_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void I2C1_EV_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void I2C1_ER_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void I2C2_EV_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void I2C2_ER_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void SPI1_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void SPI2_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void USART1_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void USART2_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void USART3_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void EXTI15_10_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void RTC_Alarm_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));

/**
 * Vector table
 */
__attribute__((section(".isr_vector")))
void (* const g_pfnVectors[])(void) = {
    (void (*)(void))(&_estack),     /* Initial Stack Pointer */
    Reset_Handler,                   /* Reset Handler */
    NMI_Handler,                     /* NMI Handler */
    HardFault_Handler,               /* Hard Fault Handler */
    MemManage_Handler,               /* MPU Fault Handler */
    BusFault_Handler,                /* Bus Fault Handler */
    UsageFault_Handler,              /* Usage Fault Handler */
    0,                               /* Reserved */
    0,                               /* Reserved */
    0,                               /* Reserved */
    0,                               /* Reserved */
    SVC_Handler,                     /* SVCall Handler */
    DebugMon_Handler,                /* Debug Monitor Handler */
    0,                               /* Reserved */
    PendSV_Handler,                  /* PendSV Handler */
    SysTick_Handler,                 /* SysTick Handler */

    /* External Interrupts */
    WWDG_IRQHandler,                 /* Window WatchDog */
    PVD_AVD_IRQHandler,              /* PVD/AVD through EXTI Line detection */
    TAMP_STAMP_IRQHandler,           /* Tamper and TimeStamps through the EXTI line */
    RTC_WKUP_IRQHandler,             /* RTC Wakeup through the EXTI line */
    FLASH_IRQHandler,                /* FLASH */
    RCC_IRQHandler,                  /* RCC */
    EXTI0_IRQHandler,                /* EXTI Line0 */
    EXTI1_IRQHandler,                /* EXTI Line1 */
    EXTI2_IRQHandler,                /* EXTI Line2 */
    EXTI3_IRQHandler,                /* EXTI Line3 */
    EXTI4_IRQHandler,                /* EXTI Line4 */
    DMA1_Stream0_IRQHandler,         /* DMA1 Stream 0 */
    DMA1_Stream1_IRQHandler,         /* DMA1 Stream 1 */
    DMA1_Stream2_IRQHandler,         /* DMA1 Stream 2 */
    DMA1_Stream3_IRQHandler,         /* DMA1 Stream 3 */
    DMA1_Stream4_IRQHandler,         /* DMA1 Stream 4 */
    DMA1_Stream5_IRQHandler,         /* DMA1 Stream 5 */
    DMA1_Stream6_IRQHandler,         /* DMA1 Stream 6 */
    ADC_IRQHandler,                  /* ADC1, ADC2 */
    FDCAN1_IT0_IRQHandler,           /* FDCAN1 interrupt line 0 */
    FDCAN2_IT0_IRQHandler,           /* FDCAN2 interrupt line 0 */
    FDCAN1_IT1_IRQHandler,           /* FDCAN1 interrupt line 1 */
    FDCAN2_IT1_IRQHandler,           /* FDCAN2 interrupt line 1 */
    EXTI9_5_IRQHandler,              /* External Line[9:5]s */
    TIM1_BRK_IRQHandler,             /* TIM1 Break interrupt */
    TIM1_UP_IRQHandler,              /* TIM1 Update Interrupt */
    TIM1_TRG_COM_IRQHandler,         /* TIM1 Trigger and Commutation Interrupt */
    TIM1_CC_IRQHandler,              /* TIM1 Capture Compare */
    TIM2_IRQHandler,                 /* TIM2 */
    TIM3_IRQHandler,                 /* TIM3 */
    TIM4_IRQHandler,                 /* TIM4 */
    I2C1_EV_IRQHandler,              /* I2C1 Event */
    I2C1_ER_IRQHandler,              /* I2C1 Error */
    I2C2_EV_IRQHandler,              /* I2C2 Event */
    I2C2_ER_IRQHandler,              /* I2C2 Error */
    SPI1_IRQHandler,                 /* SPI1 */
    SPI2_IRQHandler,                 /* SPI2 */
    USART1_IRQHandler,               /* USART1 */
    USART2_IRQHandler,               /* USART2 */
    USART3_IRQHandler,               /* USART3 */
    EXTI15_10_IRQHandler,            /* External Line[15:10]s */
    RTC_Alarm_IRQHandler,            /* RTC Alarm (A and B) through EXTI Line */
    /* ... more handlers would be here ... */
};

/**
 * @brief Reset handler - entry point
 */
void Reset_Handler(void) {
    uint32_t *src, *dest;

    /* Copy .data section from Flash to RAM */
    src = &_sidata;
    dest = &_sdata;
    while (dest < &_edata) {
        *dest++ = *src++;
    }

    /* Zero fill .bss section */
    dest = &_sbss;
    while (dest < &_ebss) {
        *dest++ = 0;
    }

    /* System initialization (clocks, etc.) */
    SystemInit();

    /* Call main() */
    main();

    /* Infinite loop if main() returns */
    while (1) {
        __asm__("nop");
    }
}

/**
 * @brief Default interrupt handler
 */
void Default_Handler(void) {
    while (1) {
        __asm__("nop");
    }
}

/**
 * @brief System initialization (called before main)
 */
void SystemInit(void) {
    /* FPU settings */
    #if (__FPU_PRESENT == 1) && (__FPU_USED == 1)
    /* Enable CP10 and CP11 coprocessors (FPU) */
    SCB->CPACR |= ((3UL << 10*2)|(3UL << 11*2));
    #endif

    /* Configure Flash prefetch, Instruction cache, Data cache */
    /* Enable I-Cache */
    /* Enable D-Cache */

    /* Note: Actual clock configuration would go here */
    /* For now, system starts with default HSI clock */
}
