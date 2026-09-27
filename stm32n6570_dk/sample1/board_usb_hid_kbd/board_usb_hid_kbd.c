/*
 * STM32N6570-DK USB HID Keyboard — USBX Host (UX_STANDALONE)
 *
 * コネクタ: CN17 USB Type-A（USB2_OTG_HS）。VBUS は PB9=PWR_USB2_EN。
 * 注意: このファイルでは kernel.h を include しない（ALIGN_TYPE が衝突する）。
 *       ena_int は TECS タスク側で行う。
 */

#include "board_usb_hid_kbd.h"

#include <string.h>

#include "main.h"
#include "stm32n6xx_hal.h"
#include "stm32n6xx_hal_rif.h"
#include "stm32n6xx_ll_bus.h"
#include "stm32n6xx_ll_rcc.h"

#include "board_lcd.h"

#include "ux_api.h"
#include "ux_system.h"
#include "ux_utility.h"
#include "ux_host_class_hid.h"
#include "ux_host_class_hid_keyboard.h"
#include "ux_hcd_stm32.h"

#define USBX_HOST_MEMORY_STACK_SIZE   (1024U * 40U)
#define KBD_QSIZE                     128U

/* UM3300: CN17 Type-A host、PWR_USB2_EN = PB9 */
#define PWR_USB2_EN_Pin               GPIO_PIN_9
#define PWR_USB2_EN_GPIO_Port         GPIOB

HCD_HandleTypeDef hhcd_USB2_OTG_HS;

static UX_HOST_CLASS_HID          *hid_instance;
static UX_HOST_CLASS_HID_KEYBOARD *keyboard;

static uint8_t  usbx_memory[USBX_HOST_MEMORY_STACK_SIZE];
static char     kbd_q[KBD_QSIZE];
static uint16_t kbd_q_w;
static uint16_t kbd_q_r;
static uint8_t  kbd_ready;
static uint8_t  hcd_started;
static uint8_t  kbd_was_connected;

#define USB_LOG_QSIZE  16U
typedef struct {
	uint8_t  kind;          /* 0=error, 1=event */
	uint8_t  level;
	uint8_t  context;
	uint32_t code;
} usb_log_t;
static usb_log_t usb_log_q[USB_LOG_QSIZE];
static volatile uint16_t usb_log_w;
static uint16_t usb_log_r;
static volatile uint32_t usb_log_lost;

static UINT ux_host_event_callback(ULONG event, UX_HOST_CLASS *current_class,
                                   VOID *current_instance);
static VOID ux_host_error_callback(UINT system_level, UINT system_context,
                                   UINT error_code);
static void usb_hcd_hw_init(void);
static void usb2_vbus_enable(void);
static void kbd_enqueue(char c);

static void
usb_log_push(uint8_t kind, uint32_t level, uint32_t context, uint32_t code)
{
	uint32_t primask = __get_PRIMASK();
	uint16_t next;

	__disable_irq();
	next = (uint16_t)((usb_log_w + 1U) % USB_LOG_QSIZE);
	if (next != usb_log_r) {
		usb_log_q[usb_log_w].kind = kind;
		usb_log_q[usb_log_w].level = (uint8_t)level;
		usb_log_q[usb_log_w].context = (uint8_t)context;
		usb_log_q[usb_log_w].code = code;
		usb_log_w = next;
	} else {
		usb_log_lost++;
	}
	__set_PRIMASK(primask);
}

static char *
put_hex(char *p, uint32_t v, int digits)
{
	static const char hex[] = "0123456789ABCDEF";
	int i;

	for (i = digits - 1; i >= 0; i--) {
		*p++ = hex[(v >> (i * 4)) & 0xFU];
	}
	return p;
}

static void
usb_log_flush(void)
{
	char buf[48];
	char *p;
	usb_log_t e;

	while (usb_log_r != usb_log_w) {
		e = usb_log_q[usb_log_r];
		usb_log_r = (uint16_t)((usb_log_r + 1U) % USB_LOG_QSIZE);

		p = buf;
		if (e.kind == 0U) {
			(void)memcpy(p, "USBX err L", 10); p += 10;
			p = put_hex(p, e.level, 1);
			(void)memcpy(p, " C", 2); p += 2;
			p = put_hex(p, e.context, 2);
			(void)memcpy(p, " E", 2); p += 2;
			p = put_hex(p, e.code, 2);
		} else {
			(void)memcpy(p, "USB ev ", 7); p += 7;
			p = put_hex(p, e.code, 2);
		}
		*p++ = '\n';
		*p = '\0';
		board_lcd_print(buf);
	}
	if (usb_log_lost != 0U) {
		p = buf;
		(void)memcpy(p, "USB log lost ", 13); p += 13;
		p = put_hex(p, usb_log_lost, 4);
		*p++ = '\n';
		*p = '\0';
		usb_log_lost = 0U;
		board_lcd_print(buf);
	}
}

static void
kbd_enqueue(char c)
{
	uint16_t next = (uint16_t)((kbd_q_w + 1U) % KBD_QSIZE);

	if (next != kbd_q_r) {
		kbd_q[kbd_q_w] = c;
		kbd_q_w = next;
	}
}

static void
usb2_vbus_enable(void)
{
	GPIO_InitTypeDef gpio = {0};

	__HAL_RCC_GPIOB_CLK_ENABLE();
	gpio.Pin = PWR_USB2_EN_Pin;
	gpio.Mode = GPIO_MODE_OUTPUT_PP;
	gpio.Pull = GPIO_NOPULL;
	gpio.Speed = GPIO_SPEED_FREQ_LOW;
	HAL_GPIO_Init(PWR_USB2_EN_GPIO_Port, &gpio);
	HAL_GPIO_WritePin(PWR_USB2_EN_GPIO_Port, PWR_USB2_EN_Pin, GPIO_PIN_SET);
}

static void
usb2_rif_config(void)
{
	RIMC_MasterConfig_t master = {0};

	/*
	 * Ux_Host_DualClass と同趣旨。N6 では OTG の RIF SEC/PRIV を
	 * 立てないと Host コントローラが実質動かない。
	 */
	__HAL_RCC_RIFSC_CLK_ENABLE();
	master.MasterCID = RIF_CID_1;
	master.SecPriv = RIF_ATTRIBUTE_SEC | RIF_ATTRIBUTE_PRIV;
	HAL_RIF_RIMC_ConfigMasterAttributes(RIF_MASTER_INDEX_OTG2, &master);
	HAL_RIF_RISC_SetSlaveSecureAttributes(RIF_RISC_PERIPH_INDEX_OTG2HS,
	                                      RIF_ATTRIBUTE_SEC | RIF_ATTRIBUTE_PRIV);
}

void
HAL_HCD_MspInit(HCD_HandleTypeDef *hhcd)
{
	RCC_OscInitTypeDef osc = {0};
	RCC_PeriphCLKInitTypeDef periph = {0};
	uint32_t guard;

	if (hhcd->Instance != USB2_OTG_HS) {
		return;
	}

	usb2_rif_config();

	osc.OscillatorType = RCC_OSCILLATORTYPE_HSE;
	osc.HSEState = RCC_HSE_ON;
	(void)HAL_RCC_OscConfig(&osc);

	__HAL_RCC_PWR_CLK_ENABLE();
	HAL_PWREx_EnableVddUSBVMEN();
	guard = 1000000U;
	while (__HAL_PWR_GET_FLAG(PWR_FLAG_USB33RDY) && (guard-- > 0U)) {
	}
	HAL_PWREx_EnableVddUSB();

	periph.PeriphClockSelection = RCC_PERIPHCLK_USBOTGHS2;
	periph.UsbOtgHs2ClockSelection = RCC_USBOTGHS2CLKSOURCE_HSE_DIRECT;
	(void)HAL_RCCEx_PeriphCLKConfig(&periph);

	periph.PeriphClockSelection = RCC_PERIPHCLK_USBPHY2;
	periph.UsbPhy2ClockSelection = RCC_USBPHY2REFCLKSOURCE_HSE_DIRECT;
	(void)HAL_RCCEx_PeriphCLKConfig(&periph);

	__HAL_RCC_GPIOA_CLK_ENABLE();

	__HAL_RCC_USB2_OTG_HS_CTL_FORCE_RESET();
	__HAL_RCC_USB2_OTG_HS_FORCE_RESET();
	__HAL_RCC_USB2_OTG_HS_PHY_FORCE_RESET();

	LL_RCC_HSE_SelectHSEDiv2AsDiv2Clock();
	__HAL_RCC_USB2_OTG_HS_CTL_RELEASE_RESET();

	__HAL_RCC_USB2_OTG_HS_CLK_ENABLE();
	HAL_Delay(1);

	USB2_HS_PHYC->USBPHYC_CR &= ~(0x7UL << 4);
	USB2_HS_PHYC->USBPHYC_CR |= (0x1UL << 16) | (0x2UL << 4) | (0x1UL << 2) | 0x1UL;

	__HAL_RCC_USB2_OTG_HS_PHY_RELEASE_RESET();
	HAL_Delay(1);
	__HAL_RCC_USB2_OTG_HS_RELEASE_RESET();
	__HAL_RCC_USB2_OTG_HS_PHY_CLK_ENABLE();

	HAL_NVIC_ClearPendingIRQ(USB2_OTG_HS_IRQn);
}

void
HAL_HCD_MspDeInit(HCD_HandleTypeDef *hhcd)
{
	if (hhcd->Instance != USB2_OTG_HS) {
		return;
	}
	__HAL_RCC_USB2_OTG_HS_CLK_DISABLE();
	__HAL_RCC_USB2_OTG_HS_PHY_CLK_DISABLE();
	HAL_GPIO_WritePin(PWR_USB2_EN_GPIO_Port, PWR_USB2_EN_Pin, GPIO_PIN_RESET);
}

static void
usb_hcd_hw_init(void)
{
	(void)memset(&hhcd_USB2_OTG_HS, 0, sizeof(hhcd_USB2_OTG_HS));
	hhcd_USB2_OTG_HS.Instance = USB2_OTG_HS;
	hhcd_USB2_OTG_HS.Init.Host_channels = 16;
	hhcd_USB2_OTG_HS.Init.speed = HCD_SPEED_HIGH;
	hhcd_USB2_OTG_HS.Init.dma_enable = DISABLE;
	hhcd_USB2_OTG_HS.Init.phy_itface = USB_OTG_HS_EMBEDDED_PHY;
	hhcd_USB2_OTG_HS.Init.Sof_enable = DISABLE;
	hhcd_USB2_OTG_HS.Init.vbus_sensing_enable = DISABLE;
	hhcd_USB2_OTG_HS.Init.use_external_vbus = ENABLE;
	(void)HAL_HCD_Init(&hhcd_USB2_OTG_HS);
}

static UINT
ux_host_event_callback(ULONG event, UX_HOST_CLASS *current_class,
                       VOID *current_instance)
{
	UX_HOST_CLASS_HID_CLIENT *client =
		(UX_HOST_CLASS_HID_CLIENT *)current_instance;

	if (event != UX_STANDALONE_WAIT_BACKGROUND_TASK) {
		usb_log_push(1U, 0U, 0U, (uint32_t)event);
	}

	switch (event) {
	case UX_DEVICE_INSERTION:
		if (current_class->ux_host_class_entry_function == ux_host_class_hid_entry) {
			if (hid_instance == UX_NULL) {
				hid_instance = (UX_HOST_CLASS_HID *)current_instance;
				board_lcd_print("USB: HID inserted\n");
			}
		}
		break;

	case UX_DEVICE_REMOVAL:
		if ((VOID *)hid_instance == current_instance) {
			hid_instance = UX_NULL;
			keyboard = UX_NULL;
			kbd_was_connected = 0U;
			board_lcd_print("USB: HID removed\n");
		}
		break;

	case UX_HID_CLIENT_INSERTION:
		if (client->ux_host_class_hid_client_handler ==
		    ux_host_class_hid_keyboard_entry) {
			if (keyboard == UX_NULL) {
				keyboard = (UX_HOST_CLASS_HID_KEYBOARD *)
					client->ux_host_class_hid_client_local_instance;
				board_lcd_print("USB: keyboard ready\n");
			}
		} else {
			board_lcd_print("USB: HID other client\n");
		}
		break;

	case UX_HID_CLIENT_REMOVAL:
		if ((VOID *)keyboard == client->ux_host_class_hid_client_local_instance) {
			keyboard = UX_NULL;
			kbd_was_connected = 0U;
			board_lcd_print("USB: keyboard removed\n");
		}
		break;

	default:
		break;
	}
	return UX_SUCCESS;
}

static VOID
ux_host_error_callback(UINT system_level, UINT system_context, UINT error_code)
{
	usb_log_push(0U, system_level, system_context, error_code);
}

int
board_usb_hid_kbd_init(void)
{
	kbd_q_w = 0;
	kbd_q_r = 0;
	hid_instance = UX_NULL;
	keyboard = UX_NULL;
	kbd_ready = 0U;
	hcd_started = 0U;
	kbd_was_connected = 0U;

	usb2_vbus_enable();

	if (ux_system_initialize(usbx_memory, USBX_HOST_MEMORY_STACK_SIZE,
	                         UX_NULL, 0) != UX_SUCCESS) {
		return -1;
	}
	if (ux_host_stack_initialize(ux_host_event_callback) != UX_SUCCESS) {
		return -2;
	}
	ux_utility_error_callback_register(&ux_host_error_callback);

	if (ux_host_stack_class_register(_ux_system_host_class_hid_name,
	                                 ux_host_class_hid_entry) != UX_SUCCESS) {
		return -3;
	}
	if (ux_host_class_hid_client_register(
		_ux_system_host_class_hid_client_keyboard_name,
		ux_host_class_hid_keyboard_entry) != UX_SUCCESS) {
		return -4;
	}

	usb_hcd_hw_init();

	if (ux_host_stack_hcd_register(_ux_system_host_hcd_stm32_name,
	                               _ux_hcd_stm32_initialize,
	                               (ULONG)USB2_OTG_HS_BASE,
	                               (ULONG)&hhcd_USB2_OTG_HS) != UX_SUCCESS) {
		return -5;
	}

	kbd_ready = 1U;
	return 0;
}

bool
board_usb_hid_kbd_is_connected(void)
{
	return (keyboard != UX_NULL) &&
	       (keyboard->ux_host_class_hid_keyboard_state ==
		(ULONG)UX_HOST_CLASS_INSTANCE_LIVE);
}

int
board_usb_hid_kbd_getchar(void)
{
	int c;

	if (kbd_q_r == kbd_q_w) {
		return -1;
	}
	c = (unsigned char)kbd_q[kbd_q_r];
	kbd_q_r = (uint16_t)((kbd_q_r + 1U) % KBD_QSIZE);
	return c;
}

/*
 * Host 開始。戻り値: 1=今まさに開始した, 0=既に開始済み / 未準備
 * 呼び出し元（タスク）で ena_int(USB_OTG_HS_INTNO) すること。
 */
int
board_usb_hid_kbd_start_host(void)
{
	if (kbd_ready == 0U) {
		return 0;
	}
	if (hcd_started != 0U) {
		return 0;
	}

	(void)HAL_HCD_Start(&hhcd_USB2_OTG_HS);
	HAL_NVIC_ClearPendingIRQ(USB2_OTG_HS_IRQn);
	hcd_started = 1U;
	board_lcd_print("USB: HCD started\n");
	return 1;
}

void
board_usb_hid_kbd_poll(void)
{
	ULONG    key;
	ULONG    state;
	int      i;
	bool     connected;
	uint32_t irq_was_enabled;

	if (kbd_ready == 0U) {
		return;
	}

	/*
	 * UX_STANDALONE ではメモリプールの排他が空で、HID の転送完了処理は
	 * ISR 内でプールを確保・解放する。タスク側で USBX を呼ぶ間は
	 * USB 割込みを止め、ISR と USBX 処理が重ならないようにする。
	 */
	irq_was_enabled = NVIC_GetEnableIRQ(USB2_OTG_HS_IRQn);
	NVIC_DisableIRQ(USB2_OTG_HS_IRQn);
	__DSB();
	__ISB();

	/* 列挙は 1ms 周期でも複数回ポンプした方が安定する */
	for (i = 0; i < 8; i++) {
		(void)ux_system_tasks_run();
	}

	connected = board_usb_hid_kbd_is_connected();
	if (connected) {
		while (ux_host_class_hid_keyboard_key_get(keyboard, &key, &state)
		       == UX_SUCCESS) {
			kbd_enqueue((char)key);
		}
	}

	if (irq_was_enabled != 0U) {
		NVIC_EnableIRQ(USB2_OTG_HS_IRQn);
	}

	usb_log_flush();

	if (connected && (kbd_was_connected == 0U)) {
		kbd_was_connected = 1U;
		board_lcd_print("USB: keyboard LIVE\n");
	} else if (!connected && (kbd_was_connected != 0U)) {
		kbd_was_connected = 0U;
	}
}

void
board_usb_hid_kbd_irq_handler(void)
{
	UX_HCD          *hcd;
	UX_HCD_STM32    *hcd_stm32;
	UX_HCD_STM32_ED *ed;

	HAL_HCD_IRQHandler(&hhcd_USB2_OTG_HS);

	/*
	 * standalone では周期転送（HID interrupt IN）の投入が tasks_run 呼出し時の
	 * フレーム番号一致に依存し、タスク周期によっては永久に投入されない。
	 * ThreadX 版と同様に SOF ごとにスケジューラを回す。
	 */
	hcd = (UX_HCD *)hhcd_USB2_OTG_HS.pData;
	if ((hcd == UX_NULL) || (hcd->ux_hcd_status != UX_HCD_STATUS_OPERATIONAL)) {
		return;
	}
	hcd_stm32 = (UX_HCD_STM32 *)hcd->ux_hcd_controller_hardware;
	if ((hcd_stm32 != UX_NULL) &&
	    ((hcd_stm32->ux_hcd_stm32_controller_flag &
	      UX_HCD_STM32_CONTROLLER_FLAG_SOF) != 0U)) {
		hcd_stm32->ux_hcd_stm32_controller_flag &=
			~UX_HCD_STM32_CONTROLLER_FLAG_SOF;

		/*
		 * 毎フレーム投入（interval_mask==0）の interrupt IN は、NAK で
		 * 停止すると再投入されない。停止中なら再スケジュール対象に戻す。
		 */
		for (ed = hcd_stm32->ux_hcd_stm32_periodic_ed_head; ed != UX_NULL;
		     ed = ed->ux_stm32_ed_next_ed) {
			if ((ed->ux_stm32_ed_interval_mask == 0U) &&
			    (ed->ux_stm32_ed_type == EP_TYPE_INTR) &&
			    (ed->ux_stm32_ed_transfer_request != UX_NULL) &&
			    (HAL_HCD_HC_GetURBState(&hhcd_USB2_OTG_HS,
			                            ed->ux_stm32_ed_channel)
			     == URB_NOTREADY)) {
				ed->ux_stm32_ed_sch_mode = 1U;
			}
		}
		(void)_ux_hcd_stm32_periodic_schedule(hcd_stm32);
	}
}

ALIGN_TYPE
_ux_utility_interrupt_disable(VOID)
{
	ALIGN_TYPE interrupt_save = (ALIGN_TYPE)__get_PRIMASK();

	__disable_irq();
	return interrupt_save;
}

VOID
_ux_utility_interrupt_restore(ALIGN_TYPE flags)
{
	__set_PRIMASK((uint32_t)flags);
}

ULONG
_ux_utility_time_get(VOID)
{
	return (ULONG)HAL_GetTick();
}
