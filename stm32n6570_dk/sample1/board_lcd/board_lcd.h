/**
 * STM32N6570-DK RK050HR18 (800x480) 文字描画。
 * フレームバッファは AXISRAM1（0x34000000、コード配置の AXISRAM2 とは別）。
 */
#ifndef BOARD_LCD_H
#define BOARD_LCD_H

#include <stdint.h>
#include <stddef.h>

#define BOARD_LCD_WIDTH   800
#define BOARD_LCD_HEIGHT  480
#define BOARD_LCD_FONT_W  8
#define BOARD_LCD_FONT_H  8
#define BOARD_LCD_SCALE   2
#define BOARD_LCD_CELL_W  (BOARD_LCD_FONT_W * BOARD_LCD_SCALE)
#define BOARD_LCD_CELL_H  (BOARD_LCD_FONT_H * BOARD_LCD_SCALE)
#define BOARD_LCD_COLS    (BOARD_LCD_WIDTH / BOARD_LCD_CELL_W)
#define BOARD_LCD_ROWS    (BOARD_LCD_HEIGHT / BOARD_LCD_CELL_H)

#define LCD_RGB565(r, g, b) \
    ((uint16_t)(((((r) >> 3) & 0x1FU) << 11) | \
                ((((g) >> 2) & 0x3FU) << 5)  | \
                (((b) >> 3) & 0x1FU)))

#define LCD_COLOR_BLACK   0x0000U
#define LCD_COLOR_WHITE   0xFFFFU
#define LCD_COLOR_NAVY    0x0010U
#define LCD_COLOR_YELLOW  0xFFE0U
#define LCD_COLOR_CYAN    0x07FFU
#define LCD_COLOR_ORANGE  0xFD20U

int board_lcd_init(void);
void board_lcd_clear(uint16_t rgb565);
void board_lcd_fill_rect(int x, int y, int w, int h, uint16_t rgb565);
void board_lcd_draw_char(int x, int y, char c, uint16_t fg, uint16_t bg);
void board_lcd_puts(int x, int y, const char *s, uint16_t fg, uint16_t bg);

/*
 * スクロールするコンソール（ASP3 タスクから直接呼んでよい）。
 * 改行で1行上にスクロールする。
 */
void board_lcd_putc(char c);
void board_lcd_print(const char *s);
void board_lcd_console_set_color(uint16_t fg, uint16_t bg);

/* SIO / target_fput_log からの投入（ISR 可。描画は cyclic が行う） */
void board_lcd_putc_from_sio(char c);
void board_lcd_console_poll(intptr_t exinf);

#endif /* BOARD_LCD_H */
