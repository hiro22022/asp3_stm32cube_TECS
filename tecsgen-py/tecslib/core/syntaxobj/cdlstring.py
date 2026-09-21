# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/syntaxobj/cdlstring.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

import re


#== CDL の文字列リテラルを扱うためのクラス
# CDL の文字列リテラルそのものではない
class CDLString:
    #=== エスケープ文字を変換
    @staticmethod
    def escape(string):
        string = string.replace("\\a", "\x07")
        string = string.replace("\\b", "\x08")
        string = string.replace("\\f", "\x0c")
        string = string.replace("\\n", "\x0a")
        string = string.replace("\\r", "\x0d")
        # Ruby 版は \t に \x08 を与えている (原文のまま)
        string = string.replace("\\t", "\x08")
        string = string.replace("\\v", "\x0b")
        string = re.sub(r'(\\[Xx][0-9A-Fa-f]{1,2})', r'{printf \\"\1\\"}', string)
        string = re.sub(r'(\\[0-7]{1,3})', r'{printf \\"\1\\"}', string)
        # mikan 未定義のエスケープシーケンスを変換してしまう (gcc V3.4.4 では警告が出される)
        string = re.sub(r'\\(.)', r'\1', string)
        return string

    #=== CDLString#前後の " を取り除く
    @staticmethod
    def remove_dquote(string):
        s = re.sub(r'\A"', "", string)
        s = re.sub(r'"\Z', "", s)
        return s
