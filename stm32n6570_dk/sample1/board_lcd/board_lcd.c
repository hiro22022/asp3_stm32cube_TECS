/**
 * STM32N6570-DK TFT（RK050HR18 / LTDC RGB）へ ASCII 文字を描画する。
 * タイミング・ピン・RIF は STM32CubeN6 BSP（stm32n6570_discovery_lcd.c）に合わせる。
 */
#include "board_lcd.h"

#include <string.h>
#include "stm32n6xx_hal.h"

#ifndef HAL_RIF_MODULE_ENABLED
#error "HAL_RIF_MODULE_ENABLED must be set (CMake stm32cubemx INTERFACE)"
#endif

#define LCD_FB_ADDR          0x34000000UL  /* AXISRAM1 */
#define LCD_FB_PIXELS        (BOARD_LCD_WIDTH * BOARD_LCD_HEIGHT)

#define RK050HR18_HSYNC      4U
#define RK050HR18_HBP        4U
#define RK050HR18_HFP        4U
#define RK050HR18_VSYNC      4U
#define RK050HR18_VBP        4U
#define RK050HR18_VFP        4U

static LTDC_HandleTypeDef hltdc_lcd;
static uint16_t *const lcd_fb = (uint16_t *)LCD_FB_ADDR;

#define LCD_CONS_QSIZE 1024U
static int cons_col;
static int cons_row;
static uint16_t cons_fg = LCD_COLOR_WHITE;
static uint16_t cons_bg = LCD_COLOR_NAVY;
static volatile uint8_t cons_ready;
static volatile uint16_t cons_q_w;
static volatile uint16_t cons_q_r;
static char cons_q[LCD_CONS_QSIZE];

/*
 * Public-domain 8x8 font (ASCII 0x20-0x7E). Each glyph is 8 row bytes,
 * MSB = leftmost pixel.
 */
static const uint8_t font8x8[95][8] = {
    {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00}, /*   */
    {0x18,0x3C,0x3C,0x18,0x18,0x00,0x18,0x00}, /* ! */
    {0x6C,0x6C,0x6C,0x00,0x00,0x00,0x00,0x00}, /* " */
    {0x6C,0x6C,0xFE,0x6C,0xFE,0x6C,0x6C,0x00}, /* # */
    {0x18,0x7E,0xC0,0x7C,0x06,0xFC,0x18,0x00}, /* $ */
    {0x00,0xC6,0xCC,0x18,0x30,0x66,0xC6,0x00}, /* % */
    {0x38,0x6C,0x38,0x76,0xDC,0xCC,0x76,0x00}, /* & */
    {0x18,0x18,0x30,0x00,0x00,0x00,0x00,0x00}, /* ' */
    {0x0C,0x18,0x30,0x30,0x30,0x18,0x0C,0x00}, /* ( */
    {0x30,0x18,0x0C,0x0C,0x0C,0x18,0x30,0x00}, /* ) */
    {0x00,0x66,0x3C,0xFF,0x3C,0x66,0x00,0x00}, /* * */
    {0x00,0x18,0x18,0x7E,0x18,0x18,0x00,0x00}, /* + */
    {0x00,0x00,0x00,0x00,0x00,0x18,0x18,0x30}, /* , */
    {0x00,0x00,0x00,0x7E,0x00,0x00,0x00,0x00}, /* - */
    {0x00,0x00,0x00,0x00,0x00,0x18,0x18,0x00}, /* . */
    {0x06,0x0C,0x18,0x30,0x60,0xC0,0x80,0x00}, /* / */
    {0x7C,0xC6,0xCE,0xD6,0xE6,0xC6,0x7C,0x00}, /* 0 */
    {0x18,0x38,0x18,0x18,0x18,0x18,0x7E,0x00}, /* 1 */
    {0x7C,0xC6,0x06,0x1C,0x70,0xC0,0xFE,0x00}, /* 2 */
    {0x7C,0xC6,0x06,0x3C,0x06,0xC6,0x7C,0x00}, /* 3 */
    {0x1C,0x3C,0x6C,0xCC,0xFE,0x0C,0x1E,0x00}, /* 4 */
    {0xFE,0xC0,0xFC,0x06,0x06,0xC6,0x7C,0x00}, /* 5 */
    {0x38,0x60,0xC0,0xFC,0xC6,0xC6,0x7C,0x00}, /* 6 */
    {0xFE,0xC6,0x0C,0x18,0x30,0x30,0x30,0x00}, /* 7 */
    {0x7C,0xC6,0xC6,0x7C,0xC6,0xC6,0x7C,0x00}, /* 8 */
    {0x7C,0xC6,0xC6,0x7E,0x06,0x0C,0x78,0x00}, /* 9 */
    {0x00,0x18,0x18,0x00,0x00,0x18,0x18,0x00}, /* : */
    {0x00,0x18,0x18,0x00,0x00,0x18,0x18,0x30}, /* ; */
    {0x06,0x0C,0x18,0x30,0x18,0x0C,0x06,0x00}, /* < */
    {0x00,0x00,0x7E,0x00,0x7E,0x00,0x00,0x00}, /* = */
    {0x60,0x30,0x18,0x0C,0x18,0x30,0x60,0x00}, /* > */
    {0x7C,0xC6,0x0C,0x18,0x18,0x00,0x18,0x00}, /* ? */
    {0x7C,0xC6,0xDE,0xDE,0xDE,0xC0,0x78,0x00}, /* @ */
    {0x38,0x6C,0xC6,0xC6,0xFE,0xC6,0xC6,0x00}, /* A */
    {0xFC,0x66,0x66,0x7C,0x66,0x66,0xFC,0x00}, /* B */
    {0x3C,0x66,0xC0,0xC0,0xC0,0x66,0x3C,0x00}, /* C */
    {0xF8,0x6C,0x66,0x66,0x66,0x6C,0xF8,0x00}, /* D */
    {0xFE,0x62,0x68,0x78,0x68,0x62,0xFE,0x00}, /* E */
    {0xFE,0x62,0x68,0x78,0x68,0x60,0xF0,0x00}, /* F */
    {0x3C,0x66,0xC0,0xC0,0xCE,0x66,0x3E,0x00}, /* G */
    {0xC6,0xC6,0xC6,0xFE,0xC6,0xC6,0xC6,0x00}, /* H */
    {0x3C,0x18,0x18,0x18,0x18,0x18,0x3C,0x00}, /* I */
    {0x1E,0x0C,0x0C,0x0C,0xCC,0xCC,0x78,0x00}, /* J */
    {0xE6,0x66,0x6C,0x78,0x6C,0x66,0xE6,0x00}, /* K */
    {0xF0,0x60,0x60,0x60,0x62,0x66,0xFE,0x00}, /* L */
    {0xC6,0xEE,0xFE,0xFE,0xD6,0xC6,0xC6,0x00}, /* M */
    {0xC6,0xE6,0xF6,0xDE,0xCE,0xC6,0xC6,0x00}, /* N */
    {0x7C,0xC6,0xC6,0xC6,0xC6,0xC6,0x7C,0x00}, /* O */
    {0xFC,0x66,0x66,0x7C,0x60,0x60,0xF0,0x00}, /* P */
    {0x7C,0xC6,0xC6,0xC6,0xD6,0xDE,0x7C,0x06}, /* Q */
    {0xFC,0x66,0x66,0x7C,0x6C,0x66,0xE6,0x00}, /* R */
    {0x7C,0xC6,0xE0,0x78,0x0E,0xC6,0x7C,0x00}, /* S */
    {0x7E,0x7E,0x5A,0x18,0x18,0x18,0x3C,0x00}, /* T */
    {0xC6,0xC6,0xC6,0xC6,0xC6,0xC6,0x7C,0x00}, /* U */
    {0xC6,0xC6,0xC6,0xC6,0xC6,0x6C,0x38,0x00}, /* V */
    {0xC6,0xC6,0xC6,0xD6,0xFE,0xEE,0xC6,0x00}, /* W */
    {0xC6,0xC6,0x6C,0x38,0x6C,0xC6,0xC6,0x00}, /* X */
    {0x66,0x66,0x66,0x3C,0x18,0x18,0x3C,0x00}, /* Y */
    {0xFE,0xC6,0x8C,0x18,0x32,0x66,0xFE,0x00}, /* Z */
    {0x3C,0x30,0x30,0x30,0x30,0x30,0x3C,0x00}, /* [ */
    {0xC0,0x60,0x30,0x18,0x0C,0x06,0x02,0x00}, /* \ */
    {0x3C,0x0C,0x0C,0x0C,0x0C,0x0C,0x3C,0x00}, /* ] */
    {0x10,0x38,0x6C,0xC6,0x00,0x00,0x00,0x00}, /* ^ */
    {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0xFF}, /* _ */
    {0x30,0x18,0x0C,0x00,0x00,0x00,0x00,0x00}, /* ` */
    {0x00,0x00,0x78,0x0C,0x7C,0xCC,0x76,0x00}, /* a */
    {0xE0,0x60,0x7C,0x66,0x66,0x66,0xDC,0x00}, /* b */
    {0x00,0x00,0x7C,0xC6,0xC0,0xC6,0x7C,0x00}, /* c */
    {0x1C,0x0C,0x7C,0xCC,0xCC,0xCC,0x76,0x00}, /* d */
    {0x00,0x00,0x7C,0xC6,0xFE,0xC0,0x7C,0x00}, /* e */
    {0x3C,0x66,0x60,0xF8,0x60,0x60,0xF0,0x00}, /* f */
    {0x00,0x00,0x76,0xCC,0xCC,0x7C,0x0C,0xF8}, /* g */
    {0xE0,0x60,0x6C,0x76,0x66,0x66,0xE6,0x00}, /* h */
    {0x18,0x00,0x38,0x18,0x18,0x18,0x3C,0x00}, /* i */
    {0x06,0x00,0x06,0x06,0x06,0x66,0x66,0x3C}, /* j */
    {0xE0,0x60,0x66,0x6C,0x78,0x6C,0xE6,0x00}, /* k */
    {0x38,0x18,0x18,0x18,0x18,0x18,0x3C,0x00}, /* l */
    {0x00,0x00,0xEC,0xFE,0xD6,0xC6,0xC6,0x00}, /* m */
    {0x00,0x00,0xDC,0x66,0x66,0x66,0x66,0x00}, /* n */
    {0x00,0x00,0x7C,0xC6,0xC6,0xC6,0x7C,0x00}, /* o */
    {0x00,0x00,0xDC,0x66,0x66,0x7C,0x60,0xF0}, /* p */
    {0x00,0x00,0x76,0xCC,0xCC,0x7C,0x0C,0x1E}, /* q */
    {0x00,0x00,0xDC,0x76,0x60,0x60,0xF0,0x00}, /* r */
    {0x00,0x00,0x7E,0xC0,0x7C,0x06,0xFC,0x00}, /* s */
    {0x30,0x30,0xFC,0x30,0x30,0x36,0x1C,0x00}, /* t */
    {0x00,0x00,0xCC,0xCC,0xCC,0xCC,0x76,0x00}, /* u */
    {0x00,0x00,0xC6,0xC6,0xC6,0x6C,0x38,0x00}, /* v */
    {0x00,0x00,0xC6,0xC6,0xD6,0xFE,0x6C,0x00}, /* w */
    {0x00,0x00,0xC6,0x6C,0x38,0x6C,0xC6,0x00}, /* x */
    {0x00,0x00,0xC6,0xC6,0xC6,0x7E,0x06,0xFC}, /* y */
    {0x00,0x00,0xFE,0x8C,0x18,0x32,0xFE,0x00}, /* z */
    {0x0E,0x18,0x18,0x70,0x18,0x18,0x0E,0x00}, /* { */
    {0x18,0x18,0x18,0x18,0x18,0x18,0x18,0x00}, /* | */
    {0x70,0x18,0x18,0x0E,0x18,0x18,0x70,0x00}, /* } */
    {0x76,0xDC,0x00,0x00,0x00,0x00,0x00,0x00}, /* ~ */
};

static void lcd_enable_axisram1(void)
{
    __HAL_RCC_AXISRAM1_MEM_CLK_ENABLE();
}

static void lcd_config_rif(void)
{
    RIMC_MasterConfig_t master = {0};

    master.MasterCID = RIF_CID_1;
    master.SecPriv = RIF_ATTRIBUTE_SEC | RIF_ATTRIBUTE_PRIV;
    HAL_RIF_RIMC_ConfigMasterAttributes(RIF_MASTER_INDEX_LTDC1, &master);
    HAL_RIF_RIMC_ConfigMasterAttributes(RIF_MASTER_INDEX_LTDC2, &master);

    HAL_RIF_RISC_SetSlaveSecureAttributes(RIF_RISC_PERIPH_INDEX_LTDC,
                                          RIF_ATTRIBUTE_SEC | RIF_ATTRIBUTE_PRIV);
    HAL_RIF_RISC_SetSlaveSecureAttributes(RIF_RISC_PERIPH_INDEX_LTDCL1,
                                          RIF_ATTRIBUTE_SEC | RIF_ATTRIBUTE_PRIV);
    HAL_RIF_RISC_SetSlaveSecureAttributes(RIF_RISC_PERIPH_INDEX_LTDCL2,
                                          RIF_ATTRIBUTE_SEC | RIF_ATTRIBUTE_PRIV);
}

static HAL_StatusTypeDef lcd_config_pixel_clock(void)
{
    RCC_OscInitTypeDef osc = {0};
    RCC_PeriphCLKInitTypeDef periph = {0};

    /* PLL4 = HSI bypass → IC16 / 2 ≒ 32 MHz（RK050HR18 の典型画素クロック） */
    osc.OscillatorType = RCC_OSCILLATORTYPE_NONE;
    osc.PLL1.PLLState = RCC_PLL_NONE;
    osc.PLL2.PLLState = RCC_PLL_NONE;
    osc.PLL3.PLLState = RCC_PLL_NONE;
    osc.PLL4.PLLState = RCC_PLL_BYPASS;
    osc.PLL4.PLLSource = RCC_PLLSOURCE_HSI;
    if (HAL_RCC_OscConfig(&osc) != HAL_OK) {
        return HAL_ERROR;
    }

    periph.PeriphClockSelection = RCC_PERIPHCLK_LTDC;
    periph.LtdcClockSelection = RCC_LTDCCLKSOURCE_IC16;
    periph.ICSelection[RCC_IC16].ClockSelection = RCC_ICCLKSOURCE_PLL4;
    periph.ICSelection[RCC_IC16].ClockDivider = 2;
    return HAL_RCCEx_PeriphCLKConfig(&periph);
}

static void lcd_msp_gpio(void)
{
    GPIO_InitTypeDef gpio = {0};

    __HAL_RCC_LTDC_CLK_ENABLE();
    __HAL_RCC_LTDC_FORCE_RESET();
    __HAL_RCC_LTDC_RELEASE_RESET();

    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();
    __HAL_RCC_GPIOE_CLK_ENABLE();
    __HAL_RCC_GPIOG_CLK_ENABLE();
    __HAL_RCC_GPIOH_CLK_ENABLE();
    __HAL_RCC_GPIOQ_CLK_ENABLE();

    gpio.Mode = GPIO_MODE_AF_PP;
    gpio.Pull = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_HIGH;
    gpio.Alternate = GPIO_AF14_LCD;

    /* G3, G2, B7, B1, B6, R5 */
    gpio.Pin = GPIO_PIN_0 | GPIO_PIN_1 | GPIO_PIN_2 | GPIO_PIN_7 | GPIO_PIN_8 | GPIO_PIN_15;
    HAL_GPIO_Init(GPIOA, &gpio);

    /* LCD_CLK, LCD_HSYNC, B2, R3, G6, G5, G4 */
    gpio.Pin = GPIO_PIN_13 | GPIO_PIN_14 | GPIO_PIN_2 | GPIO_PIN_4 | GPIO_PIN_11 |
               GPIO_PIN_12 | GPIO_PIN_15;
    HAL_GPIO_Init(GPIOB, &gpio);

    /* R7, R1, R2 */
    gpio.Pin = GPIO_PIN_8 | GPIO_PIN_9 | GPIO_PIN_15;
    HAL_GPIO_Init(GPIOD, &gpio);

    /* LCD_VSYNC */
    gpio.Pin = GPIO_PIN_11;
    HAL_GPIO_Init(GPIOE, &gpio);

    /* R0, G1, B3, G7, R6, G0 */
    gpio.Pin = GPIO_PIN_0 | GPIO_PIN_1 | GPIO_PIN_6 | GPIO_PIN_8 | GPIO_PIN_11 | GPIO_PIN_12;
    HAL_GPIO_Init(GPIOG, &gpio);

    /* B4, R4, B5 */
    gpio.Pin = GPIO_PIN_3 | GPIO_PIN_4 | GPIO_PIN_6;
    HAL_GPIO_Init(GPIOH, &gpio);

    gpio.Mode = GPIO_MODE_OUTPUT_PP;
    gpio.Pull = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_LOW;
    gpio.Alternate = 0;

    /* NRST */
    gpio.Pin = GPIO_PIN_1;
    HAL_GPIO_Init(GPIOE, &gpio);

    /* LCD_ONOFF (PQ3), LCD_BL_CTRL (PQ6) */
    gpio.Pin = GPIO_PIN_3 | GPIO_PIN_6;
    HAL_GPIO_Init(GPIOQ, &gpio);

    /* LCD_DE */
    gpio.Pin = GPIO_PIN_13;
    HAL_GPIO_Init(GPIOG, &gpio);

    HAL_GPIO_WritePin(GPIOE, GPIO_PIN_1, GPIO_PIN_RESET);
    HAL_Delay(20);
    HAL_GPIO_WritePin(GPIOE, GPIO_PIN_1, GPIO_PIN_SET);
    HAL_Delay(10);

    HAL_GPIO_WritePin(GPIOQ, GPIO_PIN_3, GPIO_PIN_SET);  /* LCD On */
    HAL_GPIO_WritePin(GPIOG, GPIO_PIN_13, GPIO_PIN_SET); /* Display Enable */
    HAL_GPIO_WritePin(GPIOQ, GPIO_PIN_6, GPIO_PIN_SET);  /* Backlight */
}

void HAL_LTDC_MspInit(LTDC_HandleTypeDef *hltdc)
{
    if (hltdc->Instance == LTDC) {
        lcd_msp_gpio();
    }
}

int board_lcd_init(void)
{
    LTDC_LayerCfgTypeDef layer = {0};
    const uint32_t width = BOARD_LCD_WIDTH;
    const uint32_t height = BOARD_LCD_HEIGHT;

    lcd_enable_axisram1();
    lcd_config_rif();

    if (lcd_config_pixel_clock() != HAL_OK) {
        return -1;
    }

    hltdc_lcd.Instance = LTDC;
    hltdc_lcd.Init.HSPolarity = LTDC_HSPOLARITY_AL;
    hltdc_lcd.Init.VSPolarity = LTDC_VSPOLARITY_AL;
    hltdc_lcd.Init.DEPolarity = LTDC_DEPOLARITY_AL;
    hltdc_lcd.Init.PCPolarity = LTDC_PCPOLARITY_IPC;
    hltdc_lcd.Init.HorizontalSync = RK050HR18_HSYNC - 1U;
    hltdc_lcd.Init.AccumulatedHBP = RK050HR18_HSYNC + RK050HR18_HBP - 1U;
    hltdc_lcd.Init.AccumulatedActiveW = RK050HR18_HSYNC + width + RK050HR18_HBP - 1U;
    hltdc_lcd.Init.TotalWidth = RK050HR18_HSYNC + width + RK050HR18_HBP + RK050HR18_HFP - 1U;
    hltdc_lcd.Init.VerticalSync = RK050HR18_VSYNC - 1U;
    hltdc_lcd.Init.AccumulatedVBP = RK050HR18_VSYNC + RK050HR18_VBP - 1U;
    hltdc_lcd.Init.AccumulatedActiveH = RK050HR18_VSYNC + height + RK050HR18_VBP - 1U;
    hltdc_lcd.Init.TotalHeigh = RK050HR18_VSYNC + height + RK050HR18_VBP + RK050HR18_VFP - 1U;
    hltdc_lcd.Init.Backcolor.Blue = 0;
    hltdc_lcd.Init.Backcolor.Green = 0;
    hltdc_lcd.Init.Backcolor.Red = 0;

    /* MSP は上で済んでいる。HAL_LTDC_Init 内の weak MspInit は空でよい */
    if (HAL_LTDC_Init(&hltdc_lcd) != HAL_OK) {
        return -2;
    }

    layer.WindowX0 = 0;
    layer.WindowX1 = width;
    layer.WindowY0 = 0;
    layer.WindowY1 = height;
    layer.PixelFormat = LTDC_PIXEL_FORMAT_RGB565;
    layer.Alpha = 255;
    layer.Alpha0 = 0;
    layer.BlendingFactor1 = LTDC_BLENDING_FACTOR1_CA;
    layer.BlendingFactor2 = LTDC_BLENDING_FACTOR2_CA;
    layer.FBStartAdress = LCD_FB_ADDR;
    layer.ImageWidth = width;
    layer.ImageHeight = height;
    layer.Backcolor.Blue = 0;
    layer.Backcolor.Green = 0;
    layer.Backcolor.Red = 0;
    if (HAL_LTDC_ConfigLayer(&hltdc_lcd, &layer, 0) != HAL_OK) {
        return -3;
    }

    __HAL_LTDC_ENABLE(&hltdc_lcd);
    board_lcd_clear(LCD_COLOR_NAVY);
    cons_col = 0;
    cons_row = 0;
    cons_q_w = 0;
    cons_q_r = 0;
    cons_ready = 1U;
    return 0;
}

void board_lcd_clear(uint16_t rgb565)
{
    uint32_t i;
    uint32_t fill = ((uint32_t)rgb565 << 16) | rgb565;
    uint32_t *p = (uint32_t *)lcd_fb;

    for (i = 0; i < (LCD_FB_PIXELS / 2U); i++) {
        p[i] = fill;
    }
}

void board_lcd_fill_rect(int x, int y, int w, int h, uint16_t rgb565)
{
    int row;
    int col;

    if (x < 0) {
        w += x;
        x = 0;
    }
    if (y < 0) {
        h += y;
        y = 0;
    }
    if ((x >= BOARD_LCD_WIDTH) || (y >= BOARD_LCD_HEIGHT) || (w <= 0) || (h <= 0)) {
        return;
    }
    if ((x + w) > BOARD_LCD_WIDTH) {
        w = BOARD_LCD_WIDTH - x;
    }
    if ((y + h) > BOARD_LCD_HEIGHT) {
        h = BOARD_LCD_HEIGHT - y;
    }

    for (row = 0; row < h; row++) {
        uint16_t *line = &lcd_fb[(y + row) * BOARD_LCD_WIDTH + x];
        for (col = 0; col < w; col++) {
            line[col] = rgb565;
        }
    }
}

void board_lcd_draw_char(int x, int y, char c, uint16_t fg, uint16_t bg)
{
    const uint8_t *glyph;
    int gy;
    int gx;
    int sy;
    int sx;
    unsigned char uc = (unsigned char)c;

    if ((uc < 0x20U) || (uc > 0x7EU)) {
        uc = '?';
    }
    glyph = font8x8[uc - 0x20U];

    for (gy = 0; gy < BOARD_LCD_FONT_H; gy++) {
        uint8_t bits = glyph[gy];
        for (gx = 0; gx < BOARD_LCD_FONT_W; gx++) {
            uint16_t color = (bits & (1U << (7 - gx))) ? fg : bg;
            int px = x + gx * BOARD_LCD_SCALE;
            int py = y + gy * BOARD_LCD_SCALE;
            for (sy = 0; sy < BOARD_LCD_SCALE; sy++) {
                for (sx = 0; sx < BOARD_LCD_SCALE; sx++) {
                    int xx = px + sx;
                    int yy = py + sy;
                    if ((xx >= 0) && (xx < BOARD_LCD_WIDTH) &&
                        (yy >= 0) && (yy < BOARD_LCD_HEIGHT)) {
                        lcd_fb[yy * BOARD_LCD_WIDTH + xx] = color;
                    }
                }
            }
        }
    }
}

void board_lcd_puts(int x, int y, const char *s, uint16_t fg, uint16_t bg)
{
    int cx = x;

    if (s == NULL) {
        return;
    }
    while (*s != '\0') {
        if (*s == '\n') {
            cx = x;
            y += BOARD_LCD_FONT_H * BOARD_LCD_SCALE;
        } else {
            board_lcd_draw_char(cx, y, *s, fg, bg);
            cx += BOARD_LCD_FONT_W * BOARD_LCD_SCALE;
        }
        s++;
    }
}

static uint32_t cons_lock(void)
{
    uint32_t primask = __get_PRIMASK();
    __disable_irq();
    return primask;
}

static void cons_unlock(uint32_t primask)
{
    if (primask == 0U) {
        __enable_irq();
    }
}

static void cons_newline(void)
{
    cons_col = 0;
    if (cons_row < (BOARD_LCD_ROWS - 1)) {
        cons_row++;
        return;
    }

    {
        const uint32_t pitch = (uint32_t)BOARD_LCD_WIDTH;
        const uint32_t cell_h = (uint32_t)BOARD_LCD_CELL_H;
        const uint32_t move_px = pitch * ((uint32_t)BOARD_LCD_HEIGHT - cell_h);
        (void)memmove(lcd_fb, lcd_fb + (pitch * cell_h), move_px * sizeof(uint16_t));
        board_lcd_fill_rect(0, BOARD_LCD_HEIGHT - (int)cell_h,
                            BOARD_LCD_WIDTH, (int)cell_h, cons_bg);
    }
}

static void cons_putc_raw(char c)
{
    unsigned char uc = (unsigned char)c;

    if (cons_ready == 0U) {
        return;
    }

    if (uc == '\r') {
        cons_col = 0;
        return;
    }
    if (uc == '\n') {
        cons_newline();
        return;
    }
    if (uc == '\t') {
        int next = (cons_col + 4) & ~3;
        if (next >= BOARD_LCD_COLS) {
            cons_newline();
        } else {
            cons_col = next;
        }
        return;
    }
    if (uc == 0x08U) {
        if (cons_col > 0) {
            cons_col--;
        }
        return;
    }

    if (cons_col >= BOARD_LCD_COLS) {
        cons_newline();
    }
    board_lcd_draw_char(cons_col * BOARD_LCD_CELL_W,
                        cons_row * BOARD_LCD_CELL_H,
                        c, cons_fg, cons_bg);
    cons_col++;
}

void board_lcd_console_set_color(uint16_t fg, uint16_t bg)
{
    uint32_t key = cons_lock();
    cons_fg = fg;
    cons_bg = bg;
    cons_unlock(key);
}

void board_lcd_putc(char c)
{
    uint32_t key = cons_lock();
    cons_putc_raw(c);
    cons_unlock(key);
}

void board_lcd_print(const char *s)
{
    uint32_t key;

    if (s == NULL) {
        return;
    }
    key = cons_lock();
    while (*s != '\0') {
        cons_putc_raw(*s);
        s++;
    }
    cons_unlock(key);
}

void board_lcd_putc_from_sio(char c)
{
    uint32_t key;
    uint16_t next;

    if (cons_ready == 0U) {
        return;
    }

    key = cons_lock();
    next = (uint16_t)((cons_q_w + 1U) % LCD_CONS_QSIZE);
    if (next != cons_q_r) {
        cons_q[cons_q_w] = c;
        cons_q_w = next;
    }
    cons_unlock(key);
}

void board_lcd_console_poll(intptr_t exinf)
{
    uint32_t key;
    char c;
    int n = 0;

    (void)exinf;
    if (cons_ready == 0U) {
        return;
    }

    /* 1周期あたりの上限。スクロールが重いのでバーストを分割する */
    key = cons_lock();
    while ((cons_q_r != cons_q_w) && (n < 64)) {
        c = cons_q[cons_q_r];
        cons_q_r = (uint16_t)((cons_q_r + 1U) % LCD_CONS_QSIZE);
        cons_putc_raw(c);
        n++;
    }
    cons_unlock(key);
}
