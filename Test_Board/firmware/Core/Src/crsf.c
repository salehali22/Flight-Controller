#include "crsf.h"
#include "string.h"

// ── Defines ───────────────────────────────────────────────────────────────────
#define CRSF_RAW_MIN  172
#define CRSF_RAW_MID  992
#define CRSF_RAW_MAX  1811
#define RC_DEADBAND   20
#define DMA_BUF_SIZE  128   // circular DMA buffer — must be power of 2

// ── Internal state ────────────────────────────────────────────────────────────
static UART_HandleTypeDef *_huart;

// DMA circular buffer — DMA writes here continuously
static uint8_t _dma_buf[DMA_BUF_SIZE];
static uint16_t _dma_read_pos = 0;   // our read position in dma_buf

// Frame assembly buffer
static uint8_t  _buf[CRSF_MAX_FRAME_LEN];
static uint8_t  _idx       = 0;
static uint8_t  _frame_len = 0;

// Public
CRSF_Data_t crsf_data = {0};

// ── CRC ───────────────────────────────────────────────────────────────────────
static uint8_t crc8_dvb_s2(const uint8_t *data, uint8_t len)
{
    uint8_t crc = 0;
    for (uint8_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (uint8_t b = 0; b < 8; b++)
            crc = (crc & 0x80) ? (crc << 1) ^ 0xD5 : (crc << 1);
    }
    return crc;
}

// ── Normalization ─────────────────────────────────────────────────────────────
static float map_stick(uint16_t raw)
{
    float val;
    if      (raw < CRSF_RAW_MID - RC_DEADBAND)
        val = (float)(raw - CRSF_RAW_MID) / (float)(CRSF_RAW_MID - CRSF_RAW_MIN) * 100.0f;
    else if (raw > CRSF_RAW_MID + RC_DEADBAND)
        val = (float)(raw - CRSF_RAW_MID) / (float)(CRSF_RAW_MAX - CRSF_RAW_MID) * 100.0f;
    else
        val = 0.0f;
    if (val >  100.0f) val =  100.0f;
    if (val < -100.0f) val = -100.0f;
    return val;
}

static float map_throttle(uint16_t raw)
{
    float val = (float)(raw - CRSF_RAW_MIN) / (float)(CRSF_RAW_MAX - CRSF_RAW_MIN) * 100.0f;
    if (val <   0.0f) val =   0.0f;
    if (val > 100.0f) val = 100.0f;
    return val;
}

// ── Channel parser ────────────────────────────────────────────────────────────
static void parse_rc_channels(const uint8_t *payload)
{
    uint32_t bits  = 0;
    uint8_t  avail = 0;
    uint8_t  idx   = 0;

    for (uint8_t ch = 0; ch < CRSF_NUM_CHANNELS; ch++) {
        while (avail < 11) {
            bits  |= ((uint32_t)payload[idx++]) << avail;
            avail += 8;
        }
        crsf_data.channels[ch] = bits & 0x7FF;
        bits  >>= 11;
        avail  -= 11;
    }

    crsf_data.roll     = map_stick(crsf_data.channels[0]);
    crsf_data.pitch    = map_stick(crsf_data.channels[1]);
    crsf_data.throttle = map_throttle(crsf_data.channels[2]);
    crsf_data.yaw      = map_stick(crsf_data.channels[3]);
    crsf_data.armed    = (crsf_data.channels[4] > 1500);
}

// ── State machine — process one byte ─────────────────────────────────────────
static void process_byte(uint8_t byte)
{
    if (_idx == 0) {
        if (byte == CRSF_SYNC_BYTE)
            _buf[_idx++] = byte;

    } else if (_idx == 1) {
        _frame_len = byte + 2;
        if (_frame_len > CRSF_MAX_FRAME_LEN || _frame_len < 4)
            _idx = 0;
        else
            _buf[_idx++] = byte;

    } else {
        _buf[_idx++] = byte;

        if (_idx >= _frame_len) {
            uint8_t crc_len      = _buf[1] - 1;
            uint8_t computed_crc = crc8_dvb_s2(&_buf[2], crc_len);
            uint8_t received_crc = _buf[_frame_len - 1];

            if (computed_crc == received_crc) {
                if (_buf[2] == CRSF_FRAMETYPE_RC_CHANNELS) {
                    parse_rc_channels(&_buf[3]);
                    crsf_data.new_frame     = true;
                    crsf_data.last_frame_ms = HAL_GetTick();
                    crsf_data.frame_count++;
                }
            } else {
                crsf_data.crc_errors++;
            }
            _idx = 0;
        }
    }
}

// ── Init ──────────────────────────────────────────────────────────────────────
void CRSF_Init(UART_HandleTypeDef *huart)
{
    _huart        = huart;
    _idx          = 0;
    _dma_read_pos = 0;
    memset(_dma_buf, 0, sizeof(_dma_buf));

    // Start circular DMA receive — runs forever, no callback needed
    HAL_UART_Receive_DMA(_huart, _dma_buf, DMA_BUF_SIZE);
}

// ── Process — call this from main loop as fast as possible ───────────────────
void CRSF_Process(void)
{
    // DMA write position = buffer size - remaining count
    uint16_t dma_write_pos = DMA_BUF_SIZE -
        __HAL_DMA_GET_COUNTER(_huart->hdmarx);

    // Drain all new bytes from DMA buffer
    while (_dma_read_pos != dma_write_pos) {
        process_byte(_dma_buf[_dma_read_pos]);
        _dma_read_pos = (_dma_read_pos + 1) % DMA_BUF_SIZE;
    }
}
