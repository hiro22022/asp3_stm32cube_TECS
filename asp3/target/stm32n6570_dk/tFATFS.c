/*
 *		tFATFS（論理ドライブ 0）
 *
 *  ボリュームオブジェクトはセル内の static FATFS。
 *  R0.04 版のように ff.c を書き換えて CB を FATFS にはしない。
 */

#include "tFATFS_tecsgen.h"
#include "ff.h"
#include "diskio.h"

static FATFS fatfs_volume;

int_t
eF_mount(uint8_t Drive)
{
	int_t status;
	FRESULT result;

	if (Drive != 0U) {
		return ((int_t) FR_INVALID_DRIVE);
	}

	status = cDisk_initialize();
	if ((status & STA_NOINIT) != 0) {
		return ((int_t) FR_NOT_READY);
	}

	result = f_mount(&fatfs_volume, "0:", 1);
	return ((int_t) result);
}

int_t
eF_getfree(const char *Path, uint32_t *Clusters)
{
	FATFS *fs;
	DWORD free_clusters;
	FRESULT result;

	free_clusters = 0U;
	result = f_getfree(Path, &free_clusters, &fs);
	if (Clusters != 0) {
		*Clusters = (uint32_t) free_clusters;
	}
	return ((int_t) result);
}
