# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/messages.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

import re

from tecslib.core import globals as G
from tecslib.rubylib import kconv as kconv_lib
from tecslib.rubylib.kconv import Kconv


#== TECS の生成する各国語化必要な文字列
# 現状、エラーメッセージは英語のみ
# 生成ファイルのコメントとして出力される文字列
class TECSMsg:

    # Ruby 版の @@error_message など．tecslib/messages/*.py が設定する
    error_message = {}
    warning_message = {}
    info_message = {}
    comment = {}

    #=== TECSMsg#生成するヘッダやテンプレートなどに含めるコメントの取得
    # CDL の文字コードに合わせて、文字コード変換を行う
    @classmethod
    def get(cls, msg):
        string = cls.comment[msg]
        if G.KCONV_TECSGEN == G.KCONV_CDL or G.KCONV_CDL == Kconv.BINARY:
            return string
        return kconv_lib.kconv(string, G.KCONV_CDL, G.KCONV_TECSGEN)

    #=== TECSMsg#ローカライズされたエラーメッセージを得る
    #body::String   : "S0001 error message body"  の形式
    # S0001 の部分が使用される
    # Generator.error2 から呼び出される
    @classmethod
    def get_error_message(cls, body):
        return cls._get_message(cls.error_message, body)

    #=== TECSMsg#ローカライズされたウォーニングメッセージを得る
    # Generator.warning2 から呼び出される
    @classmethod
    def get_warning_message(cls, body):
        return cls._get_message(cls.warning_message, body)

    #=== TECSMsg#ローカライズされた情報メッセージを得る
    # Generator.info2 から呼び出される
    @classmethod
    def get_info_message(cls, body):
        return cls._get_message(cls.info_message, body)

    @classmethod
    def _get_message(cls, table, body):
        m = re.match(r"^[A-Z0-9]+", body)   # メッセージ番号を取り出す
        num = m.group(0) if m else None
        msg = table.get(num) if num else None
        if msg is None:
            return body
        return num + " " + msg
