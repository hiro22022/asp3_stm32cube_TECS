/**
 * STM32N6570-DK CN13（SDMMC2）を HAL ポーリングで読む。
 * ピンは UM3300 / STM32N6570-DK BSP に合わせる。1.8V（PO5=SD_SEL）には切替えない。
 * DMA と SDMMC 割込みは使わない。
 */
#include "board_sd.h"

#include <stddef.h>

#include "stm32n6xx_hal.h"

#ifndef HAL_SD_MODULE_ENABLED
#error "HAL_SD_MODULE_ENABLED must be set (CMake, non-TECS only)"
#endif
#ifndef HAL_RIF_MODULE_ENABLED
#error "HAL_RIF_MODULE_ENABLED must be set (CMake stm32cubemx INTERFACE)"
#endif

#include "ff.h"
#include "kernel.h"
#include "t_syslog.h"
#include "board_lcd.h"

/* UM3300 Table 18: CN13 */
#define SD_DETECT_PIN          GPIO_PIN_12
#define SD_DETECT_PORT         GPION
#define PWR_SD_EN_PIN          GPIO_PIN_7
#define PWR_SD_EN_PORT         GPIOQ

#define SD_IO_TIMEOUT_MS       1000U
#define SD_NORMAL_HZ           25000000U

static SD_HandleTypeDef hsd2;
static int sd_powered;
static int sd_ready;

static void
sd_slot_power(void)
{
	GPIO_InitTypeDef gpio = {0};

	if (sd_powered) {
		return;
	}

	HAL_PWREx_EnableVddIO5();

	__HAL_RCC_GPIOQ_CLK_ENABLE();
	gpio.Pin = PWR_SD_EN_PIN;
	gpio.Mode = GPIO_MODE_OUTPUT_PP;
	gpio.Pull = GPIO_NOPULL;
	gpio.Speed = GPIO_SPEED_FREQ_LOW;
	HAL_GPIO_Init(PWR_SD_EN_PORT, &gpio);
	HAL_GPIO_WritePin(PWR_SD_EN_PORT, PWR_SD_EN_PIN, GPIO_PIN_SET);

	__HAL_RCC_GPION_CLK_ENABLE();
	gpio.Pin = SD_DETECT_PIN;
	gpio.Mode = GPIO_MODE_INPUT;
	gpio.Pull = GPIO_NOPULL;
	gpio.Speed = GPIO_SPEED_FREQ_LOW;
	HAL_GPIO_Init(SD_DETECT_PORT, &gpio);

	HAL_Delay(5);
	sd_powered = 1;
}

static void
sd_rif_config(void)
{
	RIMC_MasterConfig_t master = {0};

	__HAL_RCC_RIFSC_CLK_ENABLE();
	master.MasterCID = RIF_CID_1;
	master.SecPriv = RIF_ATTRIBUTE_SEC | RIF_ATTRIBUTE_PRIV;
	HAL_RIF_RIMC_ConfigMasterAttributes(RIF_MASTER_INDEX_SDMMC2, &master);
	HAL_RIF_RISC_SetSlaveSecureAttributes(RIF_RISC_PERIPH_INDEX_SDMMC2,
	                                      RIF_ATTRIBUTE_SEC | RIF_ATTRIBUTE_PRIV);
}

static int
sd_kernel_clock(void)
{
	RCC_PeriphCLKInitTypeDef periph = {0};

	periph.PeriphClockSelection = RCC_PERIPHCLK_SDMMC2;
	periph.Sdmmc2ClockSelection = RCC_SDMMC2CLKSOURCE_HCLK;
	if (HAL_RCCEx_PeriphCLKConfig(&periph) != HAL_OK) {
		return -1;
	}
	return 0;
}

/* SDMMC_CK = sdmmc_clk / (2 * div) を 25MHz 以下に丸める。 */
static uint32_t
sd_transfer_div(uint32_t sdmmc_clk)
{
	uint32_t div;

	div = sdmmc_clk / (2U * SD_NORMAL_HZ);
	if ((div == 0U) || ((sdmmc_clk % (2U * SD_NORMAL_HZ)) != 0U)) {
		if (div < 0x3FFU) {
			div++;
		}
	}
	if (div == 0U) {
		div = 1U;
	}
	return div;
}

static int
sd_wait_transfer(uint32_t timeout_ms)
{
	uint32_t start = HAL_GetTick();

	while (HAL_SD_GetCardState(&hsd2) != HAL_SD_CARD_TRANSFER) {
		if ((HAL_GetTick() - start) >= timeout_ms) {
			return -1;
		}
	}
	return 0;
}

void
HAL_SD_MspInit(SD_HandleTypeDef *hsd)
{
	GPIO_InitTypeDef gpio = {0};

	if (hsd->Instance != SDMMC2) {
		return;
	}

	(void) sd_kernel_clock();
	__HAL_RCC_SDMMC2_CLK_ENABLE();
	__HAL_RCC_SDMMC2_FORCE_RESET();
	__HAL_RCC_SDMMC2_RELEASE_RESET();

	__HAL_RCC_GPIOC_CLK_ENABLE();
	__HAL_RCC_GPIOE_CLK_ENABLE();

	gpio.Mode = GPIO_MODE_AF_PP;
	gpio.Pull = GPIO_PULLUP;
	gpio.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
	gpio.Alternate = GPIO_AF11_SDMMC2;

	/* D2 CK CMD D0 D1 */
	gpio.Pin = GPIO_PIN_0 | GPIO_PIN_2 | GPIO_PIN_3 | GPIO_PIN_4 | GPIO_PIN_5;
	HAL_GPIO_Init(GPIOC, &gpio);

	/* D3 */
	gpio.Pin = GPIO_PIN_4;
	HAL_GPIO_Init(GPIOE, &gpio);
}

int
board_sd_is_present(void)
{
	sd_slot_power();
	return (HAL_GPIO_ReadPin(SD_DETECT_PORT, SD_DETECT_PIN) == GPIO_PIN_RESET);
}

int
board_sd_is_ready(void)
{
	return sd_ready;
}

int
board_sd_init(void)
{
	uint32_t clk;

	if (sd_ready) {
		return 0;
	}
	if (!board_sd_is_present()) {
		return -1;
	}

	sd_rif_config();
	if (sd_kernel_clock() != 0) {
		return -1;
	}
	clk = HAL_RCCEx_GetPeriphCLKFreq(RCC_PERIPHCLK_SDMMC2);
	if (clk == 0U) {
		return -1;
	}

	hsd2.Instance = SDMMC2;
	hsd2.Init.ClockEdge = SDMMC_CLOCK_EDGE_RISING;
	hsd2.Init.ClockPowerSave = SDMMC_CLOCK_POWER_SAVE_DISABLE;
	hsd2.Init.BusWide = SDMMC_BUS_WIDE_4B;
	hsd2.Init.HardwareFlowControl = SDMMC_HARDWARE_FLOW_CONTROL_DISABLE;
	hsd2.Init.ClockDiv = sd_transfer_div(clk);
	hsd2.State = HAL_SD_STATE_RESET;

	if (HAL_SD_Init(&hsd2) != HAL_OK) {
		hsd2.State = HAL_SD_STATE_RESET;
		return -1;
	}
	sd_ready = 1;
	return 0;
}

int
board_sd_get_info(uint32_t *block_count, uint32_t *block_size)
{
	HAL_SD_CardInfoTypeDef info;

	if (!sd_ready) {
		return -1;
	}
	if (HAL_SD_GetCardInfo(&hsd2, &info) != HAL_OK) {
		return -1;
	}
	if (block_count != NULL) {
		*block_count = info.LogBlockNbr;
	}
	if (block_size != NULL) {
		*block_size = info.LogBlockSize;
	}
	return 0;
}

int
board_sd_read(uint8_t *buf, uint32_t block, uint32_t count)
{
	uint32_t timeout;

	if (!sd_ready || (buf == NULL) || (count == 0U)) {
		return -1;
	}
	timeout = SD_IO_TIMEOUT_MS * count;
	if (HAL_SD_ReadBlocks(&hsd2, buf, block, count, timeout) != HAL_OK) {
		return -1;
	}
	return sd_wait_transfer(timeout);
}

int
board_sd_write(const uint8_t *buf, uint32_t block, uint32_t count)
{
	uint32_t timeout;

	if (!sd_ready || (buf == NULL) || (count == 0U)) {
		return -1;
	}
	timeout = SD_IO_TIMEOUT_MS * count;
	if (HAL_SD_WriteBlocks(&hsd2, (uint8_t *) buf, block, count, timeout) != HAL_OK) {
		return -1;
	}
	return sd_wait_transfer(timeout);
}

int
board_sd_sync(void)
{
	if (!sd_ready) {
		return -1;
	}
	return sd_wait_transfer(SD_IO_TIMEOUT_MS);
}

static void
sd_report(const char *msg)
{
	syslog(LOG_NOTICE, "%s", msg);
	board_lcd_print(msg);
	board_lcd_print("\n");
}

static void
sd_show_line(const char *title, const uint8_t *data, UINT n)
{
	char line[97];
	UINT i;
	UINT m;

	m = n;
	if (m > 96U) {
		m = 96U;
	}
	for (i = 0U; i < m; i++) {
		char c = (char) data[i];

		if ((c == '\r') || (c == '\n') || (c == '\0')) {
			break;
		}
		if ((c < 0x20) || (c > 0x7e)) {
			c = '.';
		}
		line[i] = c;
	}
	line[i] = '\0';
	syslog(LOG_NOTICE, "%s%s", title, line);
	board_lcd_print(title);
	board_lcd_print(line);
	board_lcd_print("\n");
}

void
board_sd_demo_task(intptr_t exinf)
{
	static FATFS fs;
	static FIL fil;
	static uint8_t buf[128];
	UINT n;
	FRESULT fr;
	uint32_t blocks;
	uint32_t bsize;
	static const char log_line[] = "ASP3 SD ok\r\n";

	(void) exinf;

	if (!board_sd_is_present()) {
		sd_report("SD: no card");
		ext_tsk();
	}

	fr = f_mount(&fs, "0:", 1);
	if (fr != FR_OK) {
		syslog(LOG_NOTICE, "SD: mount failed (%d)", (int) fr);
		board_lcd_print("SD: mount failed\n");
		ext_tsk();
	}

	if ((board_sd_get_info(&blocks, &bsize) == 0) && (bsize != 0U) &&
	    (bsize <= (1024U * 1024U))) {
		syslog(LOG_NOTICE, "SD: %d MiB",
		       (int) (blocks / ((1024U * 1024U) / bsize)));
		board_lcd_print("SD: mounted\n");
	} else {
		sd_report("SD: mounted");
	}

	fr = f_open(&fil, "0:TEST.TXT", FA_READ);
	if (fr == FR_NO_FILE) {
		sd_report("SD: TEST.TXT not found");
	} else if (fr != FR_OK) {
		syslog(LOG_NOTICE, "SD: TEST.TXT open failed (%d)", (int) fr);
		board_lcd_print("SD: TEST.TXT open failed\n");
	} else {
		n = 0U;
		fr = f_read(&fil, buf, sizeof(buf) - 1U, &n);
		(void) f_close(&fil);
		if (fr != FR_OK) {
			syslog(LOG_NOTICE, "SD: TEST.TXT read failed (%d)", (int) fr);
			board_lcd_print("SD: TEST.TXT read failed\n");
		} else {
			sd_show_line("SD: TEST.TXT: ", buf, n);
		}
	}

	fr = f_open(&fil, "0:ASP3.LOG", FA_CREATE_ALWAYS | FA_WRITE);
	if (fr != FR_OK) {
		syslog(LOG_NOTICE, "SD: ASP3.LOG open failed (%d)", (int) fr);
		board_lcd_print("SD: ASP3.LOG open failed\n");
		ext_tsk();
	}
	n = 0U;
	fr = f_write(&fil, log_line, (UINT) (sizeof(log_line) - 1U), &n);
	if ((fr != FR_OK) || (n != (UINT) (sizeof(log_line) - 1U))) {
		(void) f_close(&fil);
		syslog(LOG_NOTICE, "SD: ASP3.LOG write failed (%d)", (int) fr);
		board_lcd_print("SD: ASP3.LOG write failed\n");
		ext_tsk();
	}
	fr = f_close(&fil);
	if (fr != FR_OK) {
		syslog(LOG_NOTICE, "SD: ASP3.LOG close failed (%d)", (int) fr);
		board_lcd_print("SD: ASP3.LOG close failed\n");
		ext_tsk();
	}

	fr = f_open(&fil, "0:ASP3.LOG", FA_READ);
	if (fr != FR_OK) {
		syslog(LOG_NOTICE, "SD: ASP3.LOG reopen failed (%d)", (int) fr);
		board_lcd_print("SD: ASP3.LOG reopen failed\n");
		ext_tsk();
	}
	n = 0U;
	fr = f_read(&fil, buf, sizeof(buf) - 1U, &n);
	(void) f_close(&fil);
	if (fr != FR_OK) {
		syslog(LOG_NOTICE, "SD: ASP3.LOG read failed (%d)", (int) fr);
		board_lcd_print("SD: ASP3.LOG read failed\n");
		ext_tsk();
	}
	sd_show_line("SD: ASP3.LOG: ", buf, n);
	ext_tsk();
}
