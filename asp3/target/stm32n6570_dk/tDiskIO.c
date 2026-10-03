/*
 *		tDiskIO（物理ドライブ 0）
 *
 *  ff004_tecs の tDiskIO と同じく disk_* を呼ぶ。
 *  データ経路は ff.c → diskio.c → board_sd のまま。
 */

#include "tDiskIO_tecsgen.h"
#include "ff.h"
#include "diskio.h"
#include "board_sd.h"

int_t
eDisk_initialize(void)
{
	return ((int_t) disk_initialize(0));
}

int_t
eDisk_status(void)
{
	return ((int_t) disk_status(0));
}

int_t
eDisk_read(uint8_t *Buffer, uint32_t SectorNumber, uint_t SectorCount)
{
	return ((int_t) disk_read(0, Buffer, (LBA_t) SectorNumber,
							  (UINT) SectorCount));
}

int_t
eDisk_write(const uint8_t *Buffer, uint32_t SectorNumber, uint_t SectorCount)
{
	return ((int_t) disk_write(0, Buffer, (LBA_t) SectorNumber,
							   (UINT) SectorCount));
}

int_t
eDisk_ioctl(uint8_t cmd, void *param)
{
	return ((int_t) disk_ioctl(0, cmd, param));
}

/*
 *  FF_FS_NORTC のため FatFs は get_fattime を呼ばない。
 *  受け口だけ固定の 2026-10-03 を返す。
 */
uint32_t
eDisk_get_fattime(void)
{
	return (((uint32_t) (2026 - 1980) << 25)
			| ((uint32_t) 10 << 21)
			| ((uint32_t) 3 << 16));
}

int_t
eDisk_isPresent(void)
{
	return (board_sd_is_present() ? 1 : 0);
}

int_t
eDisk_getInfo(uint32_t *blockCount, uint32_t *blockSize)
{
	return ((int_t) board_sd_get_info(blockCount, blockSize));
}
