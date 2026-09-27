/* USBX user config — ASP3 / UX_STANDALONE (no ThreadX) */
#ifndef UX_USER_H
#define UX_USER_H

#define UX_STANDALONE
#define UX_HOST_SIDE_ONLY
#define UX_PERIODIC_RATE        1000
#define UX_MAX_CLASS_DRIVER     2
#define UX_MAX_HCD              1
#define UX_MAX_DEVICES          8
#define UX_HOST_CLASS_HID_DECOMPRESSION_BUFFER  512
#define UX_HOST_CLASS_HID_USAGES                256
#define UX_ENABLE_ERROR_CHECKING

#endif /* UX_USER_H */
