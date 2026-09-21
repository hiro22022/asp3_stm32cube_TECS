# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) を Python へ移植したものの一部である．
#   ライセンスは tecsgen.py の冒頭を参照のこと．
#
#= Ruby の Kconv 互換シム
#
# tecsgen は $KCONV_CDL, $KCONV_CONSOLE, $KCONV_TECSGEN で文字コードを保持し，
# String#kconv で変換している．ここでは同じ定数名と変換関数を提供する．

import codecs


class Kconv:
    # Ruby の Kconv の定数に対応する (値は Python の codec 名)
    EUC = "euc_jp"
    SJIS = "cp932"
    UTF8 = "utf-8"
    ASCII = "ascii"
    BINARY = None      # 変換しない


#=== String#kconv 相当
#str::      str
#to::       Kconv の定数 (変換先)
#from_::    Kconv の定数 (変換元)
def kconv(string, to, from_):
    if to is None or from_ is None or to == from_:
        return string
    # Python の str は内部表現が Unicode なので，一旦変換元で符号化し直す
    try:
        raw = string.encode(from_, "replace")
        return raw.decode(from_, "replace").encode(to, "replace").decode(to, "replace")
    except (UnicodeError, LookupError):
        return string


#=== 指定した文字コードでファイルを開くための codec 名を返す
def codec_name(kconv_const):
    if kconv_const is None:
        return "utf-8"
    return codecs.lookup(kconv_const).name
