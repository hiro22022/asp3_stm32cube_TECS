/*
 *		STM32N6570-DK TFT コンソール（TECS セル実装）
 *
 *  board_lcd.c のコンソール API を受け口に接続する。
 *  初期化（board_lcd_init）と描画プリミティブは従来どおり C から呼ぶ。
 */

#include "tLcd_tecsgen.h"
#include "board_lcd.h"

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
