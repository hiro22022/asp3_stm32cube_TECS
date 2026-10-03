/**
 * FatFs diskio glue。物理ドライブ 0 を board_sd のポーリング API に渡す。
 */
#include <stddef.h>

#include "ff.h"
#include "diskio.h"
#include "board_sd.h"

DSTATUS
disk_initialize(BYTE pdrv)
{
	if (pdrv != 0) {
		return STA_NOINIT;
	}
	if (!board_sd_is_present()) {
		return (DSTATUS) (STA_NOINIT | STA_NODISK);
	}
	if (board_sd_init() != 0) {
		return STA_NOINIT;
	}
	return 0;
}

DSTATUS
disk_status(BYTE pdrv)
{
	if (pdrv != 0) {
		return STA_NOINIT;
	}
	if (!board_sd_is_present()) {
		return (DSTATUS) (STA_NOINIT | STA_NODISK);
	}
	if (!board_sd_is_ready()) {
		return STA_NOINIT;
	}
	return 0;
}

DRESULT
disk_read(BYTE pdrv, BYTE *buff, LBA_t sector, UINT count)
{
	if ((pdrv != 0) || (buff == NULL) || (count == 0U)) {
		return RES_PARERR;
	}
	if (board_sd_read(buff, (uint32_t) sector, count) != 0) {
		return RES_ERROR;
	}
	return RES_OK;
}

DRESULT
disk_write(BYTE pdrv, const BYTE *buff, LBA_t sector, UINT count)
{
	if ((pdrv != 0) || (buff == NULL) || (count == 0U)) {
		return RES_PARERR;
	}
	if (board_sd_write(buff, (uint32_t) sector, count) != 0) {
		return RES_ERROR;
	}
	return RES_OK;
}

DRESULT
disk_ioctl(BYTE pdrv, BYTE cmd, void *buff)
{
	uint32_t blocks;
	uint32_t bsize;

	if (pdrv != 0) {
		return RES_PARERR;
	}

	switch (cmd) {
	case CTRL_SYNC:
		return (board_sd_sync() == 0) ? RES_OK : RES_ERROR;
	case GET_SECTOR_COUNT:
		if ((buff == NULL) || (board_sd_get_info(&blocks, NULL) != 0)) {
			return RES_ERROR;
		}
		*(LBA_t *) buff = (LBA_t) blocks;
		return RES_OK;
	case GET_SECTOR_SIZE:
		if ((buff == NULL) || (board_sd_get_info(NULL, &bsize) != 0)) {
			return RES_ERROR;
		}
		*(WORD *) buff = (WORD) bsize;
		return RES_OK;
	case GET_BLOCK_SIZE:
		if (buff == NULL) {
			return RES_PARERR;
		}
		*(DWORD *) buff = 1;
		return RES_OK;
	default:
		return RES_PARERR;
	}
}
