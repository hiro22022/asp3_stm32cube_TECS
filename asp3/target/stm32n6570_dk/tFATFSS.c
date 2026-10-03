/*
 *		tFATFSS（パスを取るサービス関数）
 *
 *  chmod と mkfs は FF_USE_CHMOD / FF_USE_MKFS が 0 のため未リンク。
 */

#include "tFATFSS_tecsgen.h"
#include "ff.h"

static void
copy_file_info(FatFileInfo *dst, const FILINFO *src)
{
	uint_t i;

	if (dst == 0) {
		return;
	}
	dst->fsize = (uint32_t) src->fsize;
	dst->fdate = src->fdate;
	dst->ftime = src->ftime;
	dst->fattrib = src->fattrib;
	for (i = 0U; i < 12U; i++) {
		dst->fname[i] = src->fname[i];
		if (src->fname[i] == '\0') {
			break;
		}
	}
	dst->fname[12] = '\0';
}

int_t
eF_stat(const char *FileName, FatFileInfo *FileInfo)
{
	FILINFO info;
	FRESULT result;

	result = f_stat(FileName, &info);
	if (result == FR_OK) {
		copy_file_info(FileInfo, &info);
	}
	return ((int_t) result);
}

int_t
eF_mkdir(const char *DirName)
{
	return ((int_t) f_mkdir(DirName));
}

int_t
eF_unlink(const char *FileName)
{
	return ((int_t) f_unlink(FileName));
}

int_t
eF_chmod(const char *FileName, uint8_t Attribute, uint8_t AttributeMask)
{
	(void) FileName;
	(void) Attribute;
	(void) AttributeMask;
	return ((int_t) FR_INVALID_PARAMETER);
}

int_t
eF_rename(const char *OldName, const char *NewName)
{
	return ((int_t) f_rename(OldName, NewName));
}

int_t
eF_mkfs(uint8_t Drive, uint8_t PartitioningRule, uint32_t AllocSize)
{
	(void) Drive;
	(void) PartitioningRule;
	(void) AllocSize;
	return ((int_t) FR_INVALID_PARAMETER);
}
