/*
 *		tFATFILE
 *
 *  同時に開けるファイルは 1 つ。FIL はセル内の static。
 */

#include "tFATFILE_tecsgen.h"
#include "ff.h"

static FIL fatfs_file;

int_t
eF_open(const char *FileName, uint8_t ModeFlags)
{
	return ((int_t) f_open(&fatfs_file, FileName, ModeFlags));
}

int_t
eF_close(void)
{
	return ((int_t) f_close(&fatfs_file));
}

int_t
eF_read(uint8_t *Buffer, uint_t ByteToRead, uint_t *ByteRead)
{
	UINT nread;
	FRESULT result;

	nread = 0U;
	result = f_read(&fatfs_file, Buffer, (UINT) ByteToRead, &nread);
	if (ByteRead != 0) {
		*ByteRead = (uint_t) nread;
	}
	return ((int_t) result);
}

int_t
eF_write(const uint8_t *Buffer, uint_t ByteToWrite, uint_t *ByteWritten)
{
	UINT nwritten;
	FRESULT result;

	nwritten = 0U;
	result = f_write(&fatfs_file, Buffer, (UINT) ByteToWrite, &nwritten);
	if (ByteWritten != 0) {
		*ByteWritten = (uint_t) nwritten;
	}
	return ((int_t) result);
}

int_t
eF_lseek(uint32_t Offset)
{
	return ((int_t) f_lseek(&fatfs_file, (FSIZE_t) Offset));
}

int_t
eF_sync(void)
{
	return ((int_t) f_sync(&fatfs_file));
}
