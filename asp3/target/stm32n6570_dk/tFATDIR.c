/*
 *		tFATDIR
 *
 *  同時に開けるディレクトリは 1 つ。
 */

#include "tFATDIR_tecsgen.h"
#include "ff.h"

static DIR fatfs_dir;

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
eF_opendir(const char *DirName)
{
	return ((int_t) f_opendir(&fatfs_dir, DirName));
}

int_t
eF_readdir(FatFileInfo *FileInfo)
{
	FILINFO info;
	FRESULT result;

	result = f_readdir(&fatfs_dir, &info);
	if (result == FR_OK) {
		copy_file_info(FileInfo, &info);
	}
	return ((int_t) result);
}

int_t
eF_closedir(void)
{
	return ((int_t) f_closedir(&fatfs_dir));
}
