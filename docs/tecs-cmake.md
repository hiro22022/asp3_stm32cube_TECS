# TECS + CMake ビルド

本リポジトリは asp3_core（TECSレス・Python cfg）を submodule のまま保ち、
TECS ジェネレータと CDL／セル実装を外側に置いて CMake から呼び出す。

## 方針

tecsgen が出す `Makefile.tecsgen` は CMake では使わない。
configure 時に tecsgen を実行し、同時に出す `CMakeLists.tecsgen.cmake`
（ソース一覧マニフェスト）を `include()` する。

```
sample1.cdl
  → ruby tecsgen.rb -R -g <build>/generated
  → generated/CMakeLists.tecsgen.cmake
  → generated/tecsgen.cfg          （cfg pass 1 の入力）
  → generated/*_tecsgen.c
cmake --build
  → cfg.py pass 1/2 → リンク
```

CDL の変更は `CMAKE_CONFIGURE_DEPENDS` で再 configure される。

## ホスト依存

- 既存: CMake, Ninja, Python 3, arm-none-eabi-gcc, STM32CubeMX 生成物
- **追加: Ruby**（tecsgen）

```bash
ruby --version    # 2.7 以降を想定
```

## ビルド（STM32N6570-DK）

非 TECS（現行どおり）:

```bash
cd stm32n6570_dk/sample1/FSBL
cmake --preset Debug
cmake --build build/Debug
```

TECS:

```bash
cd stm32n6570_dk/sample1/FSBL
cmake --preset Debug -DASP3_ENABLE_TECS=ON
cmake --build build/Debug
```

起動は非 TECS と同じく SRAM ロード＋OpenOCD（[build-and-run.md](build-and-run.md) §4）。

## ビルド（NUCLEO-H563ZI）

非 TECS（現行どおり）:

```bash
cd nucleo_h563zi/sample1
cmake --preset Debug
cmake --build build/Debug
```

TECS:

```bash
cd nucleo_h563zi/sample1
cmake --preset Debug -DASP3_ENABLE_TECS=ON
cmake --build build/Debug
```

`add_subdirectory(asp3_core)` の前に本物の `generated/tecsgen.cfg` を置くため、
asp3_core の非 TECS スタブは上書きされない。

## asp3_core への依頼パッチ

`TOPPERS_OMIT_TECS` は asp3_core の `CMakeLists.txt` が無条件定義している。
TECS 時は `initialize_tecs()` が必要になる。

本リポジトリでは submodule を直接編集せず、
[patches/asp3_core_ASP3_OMIT_TECS.patch](patches/asp3_core_ASP3_OMIT_TECS.patch)
を asp3_core 側へ適用する想定（既定 ON＝現行互換）。

未適用でも `asp3_tecs_clear_omit_tecs()` が `asp3` / `cfg1_out`
ターゲットから定義を取り除くワークアラウンドを使う。

## 検証状況

| 項目 | 結果 |
|---|---|
| tecsgen → `CMakeLists.tecsgen.cmake` / `tecsgen.cfg` | STM32N6570-DK の configure でマニフェストと `tecsgen.cfg` を生成 |
| `ASP3_ENABLE_TECS=OFF`（STM32N6570-DK） | `N6570DK_FSBL.elf` リンク成功（既存の非 TECS 経路） |
| `ASP3_ENABLE_TECS=ON`（STM32N6570-DK） | `N6570DK_FSBL.elf` リンク成功。`initialize_tecs` / `tUsart` / `syslog_wri_log` / `serial_opn_por` を確認。実機シリアルは未実施 |
| NUCLEO-H563ZI の ELF / 実機 | このワークスペースには H5 の CubeMX 生成物が無いため未実施 |
