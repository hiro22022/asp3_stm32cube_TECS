/*
 *  TECS セル属性用のターゲット定数（STM32N6570-DK）
 *
 *  ST-LINK VCP は USART1（PE5/PE6）。割込み番号は stm32n657xx.h の
 *  USART1_IRQn = 159。Secure 実行時の USART1_BASE は USART1_BASE_S。
 */

#ifndef TOPPERS_TARGET_TECS_H
#define TOPPERS_TARGET_TECS_H

#ifndef TECSGEN
#include "stm32n6xx.h"
#endif

#ifndef USART1_IRQn
#define USART1_IRQn		159
#endif
#ifndef USART1_BASE
#define USART1_BASE		0x52001000UL	/* USART1_BASE_S。実ビルドは CMSIS */
#endif

#ifndef USART_BASE
#define USART_BASE		USART1_BASE
#endif

#ifndef USART_INTNO
#define USART_INTNO		(USART1_IRQn + 16)
#endif

#ifndef BPS_SETTING
#define BPS_SETTING		115200
#endif

#endif /* TOPPERS_TARGET_TECS_H */
