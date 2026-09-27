/*
 * _ux_hcd_stm32_request_trans_finish の差し替え版
 * （Middlewares/ST/usbx/common/usbx_stm32_host_controllers/ の同名ファイルはビルドから除外）
 *
 * 元実装は ed->ux_stm32_ed_data が転送バッファと異なり SETUP バッファでもなければ
 * free する。しかしデータ段のないコントロール転送（SET_ADDRESS 等）では、
 * SETUP 段完了後に SETUP バッファが解放されても ed_data がそれを指したまま残り、
 * ステータス段完了時に二重解放（UX_MEMORY_CORRUPTED）となる。
 * trans_prepare が境界合わせ用バッファを確保するのは DMA 有効時だけなので、
 * DMA 無効時は解放対象が存在しない。
 */

#define UX_SOURCE_CODE
#define UX_HCD_STM32_SOURCE_CODE

#include "ux_api.h"
#include "ux_hcd_stm32.h"
#include "ux_host_stack.h"

VOID  _ux_hcd_stm32_request_trans_finish(UX_HCD_STM32 *hcd_stm32, UX_HCD_STM32_ED *ed)
{
UX_TRANSFER *transfer;

    if (ed == UX_NULL)
        return;

    transfer = ed -> ux_stm32_ed_transfer_request;
    if (transfer == UX_NULL)
        return;

    if (ed -> ux_stm32_ed_data == UX_NULL)
        return;

    if (ed -> ux_stm32_ed_data == transfer -> ux_transfer_request_data_pointer)
        return;

    if (hcd_stm32 -> hcd_handle -> Init.dma_enable == 0U)
        return;

    if (ed -> ux_stm32_ed_data == ed -> ux_stm32_ed_setup)
        return;

    if (ed -> ux_stm32_ed_dir)
    {
        _ux_utility_memory_copy(transfer -> ux_transfer_request_data_pointer,
                                ed -> ux_stm32_ed_data,
                                transfer -> ux_transfer_request_actual_length); /* Use case of memcpy is verified. */
    }

    _ux_utility_memory_free(ed -> ux_stm32_ed_data);
    ed -> ux_stm32_ed_data = UX_NULL;
}
