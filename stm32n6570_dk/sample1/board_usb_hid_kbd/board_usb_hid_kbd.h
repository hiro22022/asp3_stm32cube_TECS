/*
 * STM32N6570-DK USB HID Keyboard（USBX Host, UX_STANDALONE）
 * CN17 USB Type-A（USB2_OTG_HS）。
 */
#ifndef BOARD_USB_HID_KBD_H
#define BOARD_USB_HID_KBD_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

int board_usb_hid_kbd_init(void);
bool board_usb_hid_kbd_is_connected(void);
int board_usb_hid_kbd_getchar(void);

/*
 * カーネル起動後に呼ぶ。1 を返したら呼び出し側で ena_int() すること。
 */
int board_usb_hid_kbd_start_host(void);

void board_usb_hid_kbd_poll(void);
void board_usb_hid_kbd_irq_handler(void);

#ifdef __cplusplus
}
#endif

#endif /* BOARD_USB_HID_KBD_H */
