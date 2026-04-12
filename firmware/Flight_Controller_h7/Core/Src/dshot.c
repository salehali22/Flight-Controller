/*
 * dshot.c — DSHOT600, STM32H743, TIM1 CH1-CH4 (M5-M8)
 *
 * Uses Timer DMA Burst mode:
 *   - One DMA stream (TIM1_UP → DMA1_Stream5) triggered by update event
 *   - Each update event bursts 4 halfwords → CCR1, CCR2, CCR3, CCR4 via DMAR
 *   - Buffer layout: _buf[17][4] — 17 time slots × 4 motors
 *     _buf[N][0..3] = {CCR1, CCR2, CCR3, CCR4} for bit N
 *   - Trailing slot [16] is all zeros (line goes low after last bit)
 *
 * Timing (TIM1 clock = 120 MHz, ARR = 199):
 *   Period = 200 ticks = 1.667 µs  → DSHOT600 bit period ✓
 *   T1H   = 150 ticks = 1.250 µs  → 75% duty ✓
 *   T0H   =  75 ticks = 0.625 µs  → 37.5% duty ✓
 *
 * How burst timing works with preload ON:
 *   Update event N fires → DMA writes _buf[N] to shadow CCR1-4
 *   At update event N+1 → shadow becomes active, period N+1 plays _buf[N]
 *
 *   This means bit[0] needs to be active for period 1, but the first DMA
 *   write (at update 0) only goes to shadow. So we pre-load CCR directly
 *   before starting, fire EGR.UG to push shadow→active, clear SR, then
 *   the DMA handles the rest. The DMA buffer starts from _buf[1] with
 *   NDTR = 16×4 halfwords (bits 1-15 + trailing zero).
 *
 *   Net result: period 1 plays bit[0], periods 2-16 play bits 1-15,
 *   period 17 plays trailing zero (line low).
 *
 * CubeMX requirements:
 *   TIM1_UP → DMA1_Stream5, Mem→Periph, HalfWord, Normal, MemInc ON
 */

#include "dshot.h"

#define DSHOT_BIT_COUNT   16
#define DSHOT_T1H        150    /* 75%    duty → logic 1 */
#define DSHOT_T0H         75    /* 37.5%  duty → logic 0 */

/*
 * Buffer: [17][4] — 17 slots × 4 motors.
 * Slot [16] is the trailing zero (all CCRs = 0).
 * Must be 32-byte aligned and sized to a whole number of cache lines.
 * 17 × 4 × 2 = 136 bytes → round up to 160 bytes (5 cache lines).
 * Pad to [20][4] = 160 bytes.
 */
static uint16_t _buf[20][4] __attribute__((aligned(32)));
static TIM_HandleTypeDef *_htim;

/* ── Pack throttle into a 16-bit DSHOT frame ──────────────────────────── */
static uint16_t _pack(uint16_t throttle)
{
    uint16_t packet = throttle << 1;          /* bit 0 = telemetry off */
    uint8_t  crc    = (packet ^ (packet >> 4) ^ (packet >> 8)) & 0x0F;
    return (packet << 4) | crc;
}

/*
 * Fill the burst buffer for all 4 motors at once.
 * Each row _buf[bit] = {motor0_CCR, motor1_CCR, motor2_CCR, motor3_CCR}
 */
static void _fill_all(uint16_t f0, uint16_t f1, uint16_t f2, uint16_t f3)
{
    for (int bit = 0; bit < DSHOT_BIT_COUNT; bit++) {
        _buf[bit][0] = (f0 & 0x8000) ? DSHOT_T1H : DSHOT_T0H;
        _buf[bit][1] = (f1 & 0x8000) ? DSHOT_T1H : DSHOT_T0H;
        _buf[bit][2] = (f2 & 0x8000) ? DSHOT_T1H : DSHOT_T0H;
        _buf[bit][3] = (f3 & 0x8000) ? DSHOT_T1H : DSHOT_T0H;
        f0 <<= 1; f1 <<= 1; f2 <<= 1; f3 <<= 1;
    }
    /* Trailing zero slot — pulls all outputs low after last bit */
    _buf[DSHOT_BIT_COUNT][0] = 0;
    _buf[DSHOT_BIT_COUNT][1] = 0;
    _buf[DSHOT_BIT_COUNT][2] = 0;
    _buf[DSHOT_BIT_COUNT][3] = 0;
}

/* ── Raw DMA stream arm (bypasses HAL state machine) ─────────────────── */
static void _arm_dma(DMA_Stream_TypeDef *stream, uint32_t src,
                     uint32_t dst, uint32_t ndtr)
{
    /* Disable and wait */
    stream->CR &= ~DMA_SxCR_EN;
    uint32_t t = HAL_GetTick();
    while ((stream->CR & DMA_SxCR_EN) && (HAL_GetTick() - t < 2U));

    /* Clear all flags for Stream5 (HIFCR bits 11:6) */
    DMA1->HIFCR = 0x00000F40UL;

    stream->M0AR = src;
    stream->PAR  = dst;
    stream->NDTR = ndtr;

    stream->CR |= DMA_SxCR_EN;
}

/* ── Public API ───────────────────────────────────────────────────────── */

void DSHOT_Init(TIM_HandleTypeDef *htim)
{
    _htim = htim;

    /*
     * Configure Timer DMA Burst:
     *   DBA  = TIM_DMABASE_CCR1 (0x0D) — burst starts at CCR1
     *   DBL  = 4 transfers per burst (CCR1, CCR2, CCR3, CCR4)
     *
     * DCR layout: DBL[12:8] | DBA[4:0]
     *   DBL = 4 transfers → field value = 3 (= transfers - 1) → bits [12:8] = 0x03 → 0x0300
     *   DBA = 0x0D → bits [4:0]
     *   DCR = 0x0300 | 0x0D = 0x030D
     */
    htim->Instance->DCR = TIM_DMABASE_CCR1 | TIM_DMABURSTLENGTH_4TRANSFERS;

    /* Enable PWM outputs */
    TIM_CCxChannelCmd(htim->Instance, TIM_CHANNEL_1, TIM_CCx_ENABLE);
    TIM_CCxChannelCmd(htim->Instance, TIM_CHANNEL_2, TIM_CCx_ENABLE);
    TIM_CCxChannelCmd(htim->Instance, TIM_CHANNEL_3, TIM_CCx_ENABLE);
    TIM_CCxChannelCmd(htim->Instance, TIM_CHANNEL_4, TIM_CCx_ENABLE);
    __HAL_TIM_MOE_ENABLE(htim);
}

bool DSHOT_IsReady(void) { return true; }

void DSHOT_SendThrottle(uint16_t m1, uint16_t m2, uint16_t m3, uint16_t m4)
{
    /* Build interleaved burst buffer */
    _fill_all(_pack(m1), _pack(m2), _pack(m3), _pack(m4));

    /* Flush D-Cache: 20×4×2 = 160 bytes, aligned(32) → exactly 5 cache lines */
    SCB_CleanDCache_by_Addr((uint32_t*)_buf, 160);

    /* Stop timer cleanly */
    __HAL_TIM_DISABLE(_htim);

    /*
     * Pre-load bit[0] directly into the active CCR registers.
     * With preload ON, writing CCR goes to shadow. Fire EGR.UG to force
     * shadow→active and reset CNT to 0. This makes bit[0] play on period 1.
     * DMA then handles bits[1..15] + trailing zero (starting from _buf[1]).
     */
    _htim->Instance->CCR1 = _buf[0][0];
    _htim->Instance->CCR2 = _buf[0][1];
    _htim->Instance->CCR3 = _buf[0][2];
    _htim->Instance->CCR4 = _buf[0][3];
    _htim->Instance->EGR  = TIM_EGR_UG;   /* shadow → active, CNT → 0 */
    _htim->Instance->SR   = 0;            /* clear UIF + any CCxIF */

    /*
     * Arm DMA1_Stream5 (TIM1_UP):
     *   src  = &_buf[1]        — start from bit[1]
     *   dst  = &TIM1->DMAR    — Timer DMA burst window
     *   ndtr = 16 × 4 = 64   — 16 remaining slots × 4 motors each
     *                           (bits 1-15 = 15 slots, + 1 trailing zero slot)
     */
    _arm_dma(_htim->hdma[TIM_DMA_ID_UPDATE]->Instance,
             (uint32_t)&_buf[1][0],
             (uint32_t)&_htim->Instance->DMAR,
             64U);   /* 16 slots × 4 halfwords */

    /* Enable only the Update DMA request — no CC DMA requests */
    _htim->Instance->DIER &= ~(TIM_DMA_UPDATE | TIM_DMA_CC1 | TIM_DMA_CC2 |
                                TIM_DMA_CC3   | TIM_DMA_CC4);
    __HAL_TIM_ENABLE_DMA(_htim, TIM_DMA_UPDATE);

    /* Re-enable outputs (defensive, EGR.UG can clear MOE on advanced timers) */
    TIM_CCxChannelCmd(_htim->Instance, TIM_CHANNEL_1, TIM_CCx_ENABLE);
    TIM_CCxChannelCmd(_htim->Instance, TIM_CHANNEL_2, TIM_CCx_ENABLE);
    TIM_CCxChannelCmd(_htim->Instance, TIM_CHANNEL_3, TIM_CCx_ENABLE);
    TIM_CCxChannelCmd(_htim->Instance, TIM_CHANNEL_4, TIM_CCx_ENABLE);
    __HAL_TIM_MOE_ENABLE(_htim);

    __HAL_TIM_ENABLE(_htim);
}

void DSHOT_Disarm(void)
{
    DSHOT_SendThrottle(DSHOT_DISARM, DSHOT_DISARM, DSHOT_DISARM, DSHOT_DISARM);
}
