/*
 *  TECS セル属性用のターゲット定数（NUCLEO-H563ZI）
 */

#ifndef TOPPERS_TARGET_TECS_H
#define TOPPERS_TARGET_TECS_H

/*
 *  CubeMX 生成後は CMSIS の USART3_* を使う。tecsgen 単体（Drivers 未生成）
 *  ではフォールバック定数で import_C を通す。
 */
#if defined(__has_include)
# if __has_include("stm32h5xx.h")
#  include "stm32h5xx.h"
# endif
#endif

#ifndef USART3_BASE
#define USART3_BASE		0x40004800UL
#endif
#ifndef USART3_IRQn
#define USART3_IRQn		59
#endif

#ifndef USART_BASE
#define USART_BASE		USART3_BASE
#endif

#ifndef USART_INTNO
#define USART_INTNO		(USART3_IRQn + 16)
#endif

#ifndef BPS_SETTING
#define BPS_SETTING		115200
#endif

#endif /* TOPPERS_TARGET_TECS_H */
