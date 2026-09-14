# STM32N6570-DK — ビルドと実行手順

WSL でビルドし、Windows 側の OpenOCD（CubeIDE 同梱）で AXISRAM2 にロードして実行する手順。

設計・落とし穴の詳細は [docs/porting-n6570dk.md](docs/porting-n6570dk.md)、
他ボードとの比較は [docs/build-and-run.md](docs/build-and-run.md) §4。

---

## 0. 前提（一度だけ）

### ボード

- **BOOT1 = 1-3（development mode）**（BOOT0 は不問）
- 内蔵フラッシュ無し。開発中は **SRAM（AXISRAM2）ロード**で動かす

### リポジトリ

```bash
git clone --recurse-submodules <本リポジトリ>
# 既存 clone:
git submodule update --init --recursive
```

`stm32n6570_dk/sample1/N6570DK.ioc` を STM32CubeMX で開き **GENERATE CODE**
（`Drivers/` 等が無いとビルドできない）。

### 役割分担

| 環境 | 役割 |
|---|---|
| **WSL** | `arm-none-eabi-gcc` でビルド、`readelf` / `objdump` |
| **Windows** | OpenOCD（ST-LINK）でロード＆起動、シリアル受信 |

---

## 1. ビルド（WSL）

```bash
cd stm32n6570_dk/sample1/FSBL

cmake -B build \
  -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_TOOLCHAIN_FILE=../gcc-arm-none-eabi.cmake \
  -G "Unix Makefiles"

cmake --build build
# → build/N6570DK_FSBL.elf
```

Ninja がある場合は `cmake --preset Debug && cmake --build build/Debug` でも可
（成果物パスが `build/Debug/` になる）。

### ビルド後の確認（推奨）

```bash
ELF=build/N6570DK_FSBL.elf

arm-none-eabi-readelf -h "$ELF" | grep Entry
#   Entry point address:  0x34180ef9   ← PC に使う（ビルドごとに変わる）

arm-none-eabi-objdump -s --start-address=0x34180400 --stop-address=0x34180404 "$ELF"
#   34180400 00002034  → リトルエンディアンで MSP = 0x34200000

arm-none-eabi-objdump -d "$ELF" | grep -A1 exc_return_const
#   0xfffffffd であること（Secure。H5 の 0xffffffbc とは逆）

arm-none-eabi-nm "$ELF" | grep _kernel_vector_table
#   下位 10bit が 0（1024 バイト境界）であること
```

| 項目 | 典型値 | 備考 |
|---|---|---|
| VTOR | `0x34180400` | 固定（リンカ配置） |
| MSP | `0x34200000` | objdump の先頭ワードを LE 解釈 |
| PC（Entry） | 例: `0x34180ef9` | **毎回 readelf で確認** |
| `exc_return` | `0xfffffffd` | TrustZone Secure |

---

## 2. Windows 側への配置

例（作業用コピー先）:

```text
C:\cygwin64\home\hiro2\STM32Cube\STM32N6570-DK-honda\
  build\N6570DK_FSBL.elf          ← WSL の build からコピー
  scripts\openocd-n6-windows.cfg  ← リポジトリ scripts/ からコピー
```

WSL パス例:

```text
\\wsl.localhost\Ubuntu\home\hiro22022\TECS_native\asp3_honda\asp3_stm32cube\stm32n6570_dk\sample1\FSBL\build\N6570DK_FSBL.elf
```

---

## 3. 実行（Windows cmd）

### 環境変数（セッションごと、パスは環境に合わせる）

```bat
cd /d C:\cygwin64\home\hiro2\STM32Cube\STM32N6570-DK-honda\build

set "OPENOCD=C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.openocd.win32_2.4.400.202601091506\tools\bin\openocd.exe"
set OSCRIPTS="c:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.debug.openocd_2.3.300.202602021527\resources\openocd\st_scripts"
set "OCFG=C:\cygwin64\home\hiro2\STM32Cube\STM32N6570-DK-honda\scripts\openocd-n6-windows.cfg"
```

`OSCRIPTS` の確認:

```bat
dir "%OSCRIPTS%\interface\stlink-dap.cfg"
```

### ロード＆起動（この環境で確認済み）

**注意点：** pc の値は、ビルドごとに変化する可能性があるため、arm-none-eabi-readelf (上述)で調べて、一致しているか確認すべき！


CubeIDE 同梱 OpenOCD では **`reset halt` すると AXISRAM2 が消える**ため、
Programmer で書いてから reset する方式は使わない。
**OpenOCD だけで reset → load_image → PC 設定 → resume** する。

```bat
"%OPENOCD%" -s "%OSCRIPTS%" -f "%OCFG%" -c "gdb_port disabled" -c "init" -c "reset halt" -c "load_image N6570DK_FSBL.elf" -c "mdw 0x34180400 4" -c "mww 0xE000ED08 0x34180400" -c "reg msp 0x34200000" -c "reg pc 0x34180ef9" -c "reg pc" -c "resume" -c "exit"

TFT 対応版 (pc 変更有)
"%OPENOCD%" -s "%OSCRIPTS%" -f "%OCFG%" -c "gdb_port disabled" -c "init" -c "reset halt" -c "load_image N6570DK_FSBL.elf" -c "mdw 0x34180400 4" -c "mww 0xE000ED08 0x34180400" -c "reg msp 0x34200000" -c "reg pc 0x34180f49" -c "reg pc" -c "resume" -c "exit"

TFT スクロール対応版
 "%OPENOCD%" -s "%OSCRIPTS%" -f "%OCFG%" -c "gdb_port disabled" -c "init" -c "reset halt" -c "load_image N6570DK_FSBL.elf" -c "mdw 0x34180400 4" -c "mww 0xE000ED08 0x34180400" -c "reg msp 0x34200000" -c "reg pc 0x34180f19" -c "reg pc" -c "resume" -c "exit"

T
"%OPENOCD%" -s "%OSCRIPTS%" -f "%OCFG%" -c "gdb_port disabled" -c "init" -c "reset halt" -c "load_image N6570DK_FSBL.elf" -c "mdw 0x34180400 4" -c "mww 0xE000ED08 0x34180400" -c "reg msp 0x34200000" -c "reg pc 0x3418d281" -c "reg pc" -c "resume" -c "exit"
```


`reg pc 0x34180ef9` の値は、§1 の `readelf` 結果に置き換える。

### 成功時のログ目安

```text
..... bytes written at address 0x34180000
0x34180400: 34200000 34180ef9 ........ ........
pc (/32): 0x34180ef9
```

- `mdw` が `00000000` だらけ → イメージ未ロード（失敗）
- `pc` が `0x1800xxxx` → まだブート ROM（PC 未設定）

日常運用では `mdw` / 余分な `reg pc` を省略してよい:

```bat
"%OPENOCD%" -s "%OSCRIPTS%" -f "%OCFG%" -c "gdb_port disabled" -c "init" -c "reset halt" -c "load_image N6570DK_FSBL.elf" -c "mww 0xE000ED08 0x34180400" -c "reg msp 0x34200000" -c "reg pc 0x34180ef9" -c "resume" -c "exit"
```

---

## 4. シリアル確認

- **USART1**（PE5=TX / PE6=RX）、**115200 8N1**
- ST-LINK Virtual COM Port

期待出力（ASP3 sample1）:

```text
TOPPERS/ASP3 Kernel Release ... for STM32N6570-DK(STM32N657X0)
Sample program starts (exinf = 0).
task1 is running (NNN)
```

`r` を送ると task1 → task2 → task3 と切り替わる。

---

## 5. やってはいけないこと / つまずき

| 症状・操作 | 原因 | 対策 |
|---|---|---|
| `STM32_Programmer_CLI ... -g` | `-g` は成功表示でも CPU は ROM 待機のまま | 使わない（本手順の OpenOCD 方式） |
| Programmer `-w` のあと OpenOCD `reset` | **SYSRESETREQ で AXISRAM2 が消える** | `reset halt` の**後に** `load_image` |
| `Can't find interface/stlink-dap.cfg` | OpenOCD の scripts パス未指定 | `-s "%OSCRIPTS%"` |
| `register xPSR not found` | ST OpenOCD / M55 に `xPSR` 名が無い | **設定不要**（Entry の LSB で Thumb） |
| `Wrong connect parameter: foo.elf` | `-w` 忘れ | `-w N6570DK_FSBL.elf` |
| シリアル無出力（起動ログは OK） | ASP3 未リンクの空 `while(1)` | `sta_ker()` 入り ELF を使う |
| OpenOCD が M55 を認識しない | AP 番号違い | `openocd-n6-windows.cfg` の **`-ap-num 1`** |
| 何も動かない | BOOT1 がフラッシュ起動 | **BOOT1 = 1-3** |

### 参考：リポジトリ付属 `scripts/run_n6.sh`

Programmer ロード + **reset なし halt** 向け（素の OpenOCD 0.12.0 想定）。
CubeIDE 同梱 OpenOCD で `halt` が不安定な本環境では、§3 の
`reset halt` + `load_image` を使う。

---

## 6. アプリ差し替え（test_porting 等）

```bash
cd stm32n6570_dk/sample1/FSBL
CORE=$PWD/../../../asp3/asp3_core

cmake -B build/TestPorting \
  -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_TOOLCHAIN_FILE=../gcc-arm-none-eabi.cmake \
  -G "Unix Makefiles" \
  -DASP3_APPLDIR=$CORE/test/porting \
  -DASP3_APPLNAME=test_porting \
  -DASP3_EXTRA_APP_C_FILES=$CORE/test/porting/tap.c

cmake --build build/TestPorting
```

Entry を取り直してから §3 と同様にロードする。

---

## 7. メモリ配置（参考）

| 領域 | アドレス | サイズ |
|---|---|---|
| ROM（vector / text / rodata） | `0x34180400` 起算（イメージ先頭 `0x34180000`） | 255 KB |
| RAM（data / bss / stack） | `0x341C0000` | 256 KB |

どちらも AXISRAM2。先頭 `0x400` はブートヘッダ用。


--------
## clean する方法

オブジェクトだけ消す（再ビルド用）
cd stm32n6570_dk/sample1/FSBL
cmake --build build --target clean
# または
cmake --build build --target clean
make -C build clean でも同じです。CMake の設定（CMakeCache.txt など）は残ります。

ビルド一式を消す（再構成から）
cd stm32n6570_dk/sample1/FSBL
rm -rf build
