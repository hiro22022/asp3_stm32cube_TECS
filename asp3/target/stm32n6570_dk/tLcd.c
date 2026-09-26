/*
 *		STM32N6570-DK TFT（TECS セル実装）
 *
 *  board_lcd.c の描画／コンソール API を受け口に接続する。
 */

#include "tLcd_tecsgen.h"
#include "board_lcd.h"

ER
eDraw_init(void)
{
	return ((ER) board_lcd_init());
}

void
eDraw_clear(uint16_t rgb565)
{
	board_lcd_clear(rgb565);
}

void
eDraw_fillRect(int32_t x, int32_t y, int32_t w, int32_t h, uint16_t rgb565)
{
	board_lcd_fill_rect((int) x, (int) y, (int) w, (int) h, rgb565);
}

void
eDraw_drawChar(int32_t x, int32_t y, char c, uint16_t fg, uint16_t bg)
{
	board_lcd_draw_char((int) x, (int) y, c, fg, bg);
}

void
eDraw_puts(int32_t x, int32_t y, const char *s, uint16_t fg, uint16_t bg)
{
	board_lcd_puts((int) x, (int) y, s, fg, bg);
}

void
eConsole_putChar(char c)
{
	board_lcd_putc(c);
}

void
eConsole_print(const char *s)
{
	board_lcd_print(s);
}

void
eConsole_setColor(uint16_t fg, uint16_t bg)
{
	board_lcd_console_set_color(fg, bg);
}

void
eFeed_putChar(char c)
{
	board_lcd_putc_from_sio(c);
}

void
eiConsolePoll_main(void)
{
	board_lcd_console_poll(0);
}
