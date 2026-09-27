/*
 *		USB HID Keyboard（TECS セル実装）
 *
 *  USBX standalone のポンプはタスク文脈で回す。
 */

#include "tUsbHidKeyboard_tecsgen.h"
#include "board_usb_hid_kbd.h"
#include "kernel.h"
#include "target_tecs.h"

ER
eKeyboard_init(void)
{
	return ((ER) board_usb_hid_kbd_init());
}

bool_t
eKeyboard_isConnected(void)
{
	return (board_usb_hid_kbd_is_connected() ? true : false);
}

int_t
eKeyboard_getChar(void)
{
	return ((int_t) board_usb_hid_kbd_getchar());
}

void
eTaskBody_main(void)
{
	int_t c;

	for (;;) {
		if (board_usb_hid_kbd_start_host() != 0) {
			(void)ena_int(USB_OTG_HS_INTNO);
		}

		board_usb_hid_kbd_poll();

		if (is_cFeed_joined()) {
			while ((c = board_usb_hid_kbd_getchar()) >= 0) {
				cFeed_putChar((char)c);
			}
		}

		/* UX_PERIODIC_RATE=1000 に合わせ 1ms でポンプ */
		(void)dly_tsk(1000);
	}
}

void
eiIrq_main(void)
{
	board_usb_hid_kbd_irq_handler();
}
