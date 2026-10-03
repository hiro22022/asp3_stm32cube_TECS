/**
 * STM32N6570-DK CN13 microSD（SDMMC2、ポーリング）。
 * FatFs の diskio と、非 TECS ビルドの SD_DEMO_TASK から使う。
 * TECS セルはここでは作らない。
 */
#ifndef BOARD_SD_H
#define BOARD_SD_H

#include <stdint.h>

int board_sd_is_present(void);
int board_sd_is_ready(void);
int board_sd_init(void);
int board_sd_get_info(uint32_t *block_count, uint32_t *block_size);
int board_sd_read(uint8_t *buf, uint32_t block, uint32_t count);
int board_sd_write(const uint8_t *buf, uint32_t block, uint32_t count);
int board_sd_sync(void);

void board_sd_demo_task(intptr_t exinf);

#endif /* BOARD_SD_H */
