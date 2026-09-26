# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecsgen.rb のトップレベル関数を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．
#
#= tecsgen.rb のトップレベル関数
#
# Ruby では tecsgen.rb にトップレベル関数として定義されており，どのファイルからも
# 呼び出せる．Python では循環 import を避けるためこのモジュールに置き，
# 各モジュールは from tecslib.core.toplevel import dbgPrint として使う．

import sys
import traceback

from tecslib.core import globals as G


#=== 例外の表示
#evar:: Exception
def print_exception(evar):
    print("*** Begin Ruby exception message ***")
    print(str(evar))

    if G.debug:
        print("#### stack trace ####")
        traceback.print_exception(type(evar), evar, evar.__traceback__)
    print("*** End Ruby exception message ***")


def dbgPrint(string):
    if G.debug:
        sys.stdout.write(string)


def dbgPrintf(fmt, *param):
    if G.debug:
        sys.stdout.write(fmt % param)


#=== エラーおよび警告のレポート
def print_report():
    from tecslib.core.bnf import Generator

    msg = None

    if Generator.get_n_error() != 0:
        msg = "{} error".format(Generator.get_n_error())
        if Generator.get_n_error() >= 2:
            msg = "{}s".format(msg)

    if Generator.get_n_warning() != 0:
        if msg:
            msg = "{}  ".format(msg)
        else:
            msg = ""
        msg = "{}{} warning".format(msg, Generator.get_n_warning())
        if Generator.get_n_warning() >= 2:
            msg = "{}s".format(msg)

    if msg:
        print(msg)
