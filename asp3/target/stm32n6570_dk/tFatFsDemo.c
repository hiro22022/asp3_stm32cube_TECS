/*
 *		FatFs 確認タスク
 *
 *  非 TECS の board_sd_demo_task と同じ手順。
 *  ファイル操作は呼び口、表示は LCD コンソールと syslog。
 */

#include "tFatFsDemo_tecsgen.h"
#include "ff.h"
#include "kernel.h"
#include "t_syslog.h"

static void
sd_report(const char *msg)
{
	syslog(LOG_NOTICE, "%s", msg);
	cLcd_print(msg);
	cLcd_print("\n");
}

static void
sd_show_line(const char *title, const uint8_t *data, uint_t length)
{
	char line[97];
	uint_t i;
	uint_t n;

	n = length;
	if (n > 96U) {
		n = 96U;
	}
	for (i = 0U; i < n; i++) {
		char c;

		c = (char) data[i];
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
	cLcd_print(title);
	cLcd_print(line);
	cLcd_print("\n");
}

void
eTaskBody_main(void)
{
	uint8_t buf[128];
	uint_t n;
	int_t result;
	uint32_t blocks;
	uint32_t bsize;
	static const char log_line[] = "ASP3 SD ok\r\n";

	if (cDisk_isPresent() == 0) {
		sd_report("SD: no card");
		ext_tsk();
	}

	result = cFS_mount(0);
	if (result != FR_OK) {
		syslog(LOG_NOTICE, "SD: mount failed (%d)", (int) result);
		cLcd_print("SD: mount failed\n");
		ext_tsk();
	}

	blocks = 0U;
	bsize = 0U;
	if ((cDisk_getInfo(&blocks, &bsize) == 0) && (bsize != 0U) &&
		(bsize <= (1024U * 1024U))) {
		syslog(LOG_NOTICE, "SD: %d MiB",
			   (int) (blocks / ((1024U * 1024U) / bsize)));
		cLcd_print("SD: mounted\n");
	} else {
		sd_report("SD: mounted");
	}

	result = cFile_open("0:TEST.TXT", FA_READ);
	if (result == FR_NO_FILE) {
		sd_report("SD: TEST.TXT not found");
	} else if (result != FR_OK) {
		syslog(LOG_NOTICE, "SD: TEST.TXT open failed (%d)", (int) result);
		cLcd_print("SD: TEST.TXT open failed\n");
	} else {
		n = 0U;
		result = cFile_read(buf, sizeof(buf) - 1U, &n);
		(void) cFile_close();
		if (result != FR_OK) {
			syslog(LOG_NOTICE, "SD: TEST.TXT read failed (%d)", (int) result);
			cLcd_print("SD: TEST.TXT read failed\n");
		} else {
			sd_show_line("SD: TEST.TXT: ", buf, n);
		}
	}

	result = cFile_open("0:ASP3.LOG",
						(uint8_t) (FA_CREATE_ALWAYS | FA_WRITE));
	if (result != FR_OK) {
		syslog(LOG_NOTICE, "SD: ASP3.LOG open failed (%d)", (int) result);
		cLcd_print("SD: ASP3.LOG open failed\n");
		ext_tsk();
	}
	n = 0U;
	result = cFile_write((const uint8_t *) log_line,
						 (uint_t) (sizeof(log_line) - 1U), &n);
	if ((result != FR_OK) || (n != (uint_t) (sizeof(log_line) - 1U))) {
		(void) cFile_close();
		syslog(LOG_NOTICE, "SD: ASP3.LOG write failed (%d)", (int) result);
		cLcd_print("SD: ASP3.LOG write failed\n");
		ext_tsk();
	}
	result = cFile_close();
	if (result != FR_OK) {
		syslog(LOG_NOTICE, "SD: ASP3.LOG close failed (%d)", (int) result);
		cLcd_print("SD: ASP3.LOG close failed\n");
		ext_tsk();
	}

	result = cFile_open("0:ASP3.LOG", FA_READ);
	if (result != FR_OK) {
		syslog(LOG_NOTICE, "SD: ASP3.LOG reopen failed (%d)", (int) result);
		cLcd_print("SD: ASP3.LOG reopen failed\n");
		ext_tsk();
	}
	n = 0U;
	result = cFile_read(buf, sizeof(buf) - 1U, &n);
	(void) cFile_close();
	if (result != FR_OK) {
		syslog(LOG_NOTICE, "SD: ASP3.LOG read failed (%d)", (int) result);
		cLcd_print("SD: ASP3.LOG read failed\n");
		ext_tsk();
	}
	sd_show_line("SD: ASP3.LOG: ", buf, n);
	ext_tsk();
}
