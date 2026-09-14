/*
 *		STM32H5 USART 用 簡易SIOドライバ
 *
 *  CubeMX が USART を初期化した後に sta_ker() する前提。open/close では
 *  ボーレート再設定をせず、送受信と割込み許可だけをレジスタで扱う。
 */

#include "stm32h5xx.h"
#include "tUsart_tecsgen.h"

Inline bool_t
usart_getready(CELLCB *p_cellcb)
{
	return (((USART_TypeDef *)ATTR_baseAddress)->ISR & USART_ISR_RXNE_RXFNE) != 0;
}

Inline bool_t
usart_putready(CELLCB *p_cellcb)
{
	return (((USART_TypeDef *)ATTR_baseAddress)->ISR & USART_ISR_TXE_TXFNF) != 0;
}

Inline char
usart_getchar(CELLCB *p_cellcb)
{
	return (char)(((USART_TypeDef *)ATTR_baseAddress)->RDR);
}

Inline void
usart_putchar(CELLCB *p_cellcb, char c)
{
	((USART_TypeDef *)ATTR_baseAddress)->TDR = (uint32_t)(uint8_t)c;
}

void
eSIOPort_open(CELLIDX idx)
{
	CELLCB	*p_cellcb = GET_CELLCB(idx);
	USART_TypeDef *usart = (USART_TypeDef *)ATTR_baseAddress;

	(void)p_cellcb;
	/* CubeMX 初期化済み。送受信と UART 自体は有効にしておく */
	usart->CR1 |= (USART_CR1_RE | USART_CR1_TE | USART_CR1_UE);
}

void
eSIOPort_close(CELLIDX idx)
{
	CELLCB	*p_cellcb = GET_CELLCB(idx);
	USART_TypeDef *usart = (USART_TypeDef *)ATTR_baseAddress;

	(void)p_cellcb;
	usart->CR1 &= ~(USART_CR1_TXEIE_TXFNFIE | USART_CR1_RXNEIE_RXFNEIE);
}

bool_t
eSIOPort_putChar(CELLIDX idx, char c)
{
	CELLCB	*p_cellcb = GET_CELLCB(idx);

	if (usart_putready(p_cellcb)) {
		usart_putchar(p_cellcb, c);
		return (true);
	}
	return (false);
}

int_t
eSIOPort_getChar(CELLIDX idx)
{
	CELLCB	*p_cellcb = GET_CELLCB(idx);

	if (usart_getready(p_cellcb)) {
		return ((int_t)(uint8_t)usart_getchar(p_cellcb));
	}
	return (-1);
}

void
eSIOPort_enableCBR(CELLIDX idx, uint_t cbrtn)
{
	CELLCB		*p_cellcb = GET_CELLCB(idx);
	USART_TypeDef *usart = (USART_TypeDef *)ATTR_baseAddress;

	switch (cbrtn) {
	case SIOSendReady:
		usart->CR1 |= USART_CR1_TXEIE_TXFNFIE;
		break;
	case SIOReceiveReady:
		usart->CR1 |= USART_CR1_RXNEIE_RXFNEIE;
		break;
	}
}

void
eSIOPort_disableCBR(CELLIDX idx, uint_t cbrtn)
{
	CELLCB		*p_cellcb = GET_CELLCB(idx);
	USART_TypeDef *usart = (USART_TypeDef *)ATTR_baseAddress;

	switch (cbrtn) {
	case SIOSendReady:
		usart->CR1 &= ~USART_CR1_TXEIE_TXFNFIE;
		break;
	case SIOReceiveReady:
		usart->CR1 &= ~USART_CR1_RXNEIE_RXFNEIE;
		break;
	}
}

void
eiISR_main(CELLIDX idx)
{
	CELLCB	*p_cellcb = GET_CELLCB(idx);

	if (usart_getready(p_cellcb)) {
		ciSIOCBR_readyReceive();
	}
	if (usart_putready(p_cellcb)) {
		ciSIOCBR_readySend();
	}
}
