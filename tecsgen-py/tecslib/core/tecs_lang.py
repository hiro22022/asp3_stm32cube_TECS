# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/tecs_lang.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

import importlib
import re
import sys

from tecslib.core import globals as G
from tecslib.core.toplevel import dbgPrint
from tecslib.rubylib import kconv as kconv_lib
from tecslib.rubylib.kconv import Kconv


#== 言語に関する変数を設定
# メッセージファイルの読み込みも行う (読み込みに失敗した場合、デフォルトの文字コードに変更する)
class TECS_LANG:
    # ハッシュのタグは case insensitive のため、大文字の文字列とする
    CHARSET_ALIAS = {
        "UJIS": "eucJP",
        "UTF-8": "utf8",
        "EUCJP": "eucJP",   # 以下 case insensitive にするため
        "SJIS": "sjis",
        "UTF8": "utf8",
        "ISO8859-1": "iso8859-1",
    }
    LANG_ALIAS = {
        "C": "en_US",
        "EN_US": "en_US",   # 以下 case insensitive にするため
        "JA_JP": "ja_JP",
    }
    SUITABLE_CHARSET = {
        "ja_JP": ["eucJP", "sjis", "utf8"],
        "en_US": ["iso8859-1", "utf8", None],
    }

    #=== LANG のパース
    #lang::String  "ja_JP.eucJP@cjknarrow", "C" など
    #RETURN:: [ "ja_JP", "eucJP", "cjknarrow" ]
    @classmethod
    def parse_lang(cls, lang):
        m = re.match(r"([^\.@]*)(\.([^@]*))?(@(.*))?", lang)

        lang_terri = m.group(1) if m.group(1) else None
        codeset = m.group(3) if m.group(3) else None
        modifier = m.group(5) if m.group(5) else None
        return [lang_terri, codeset, modifier]

    #=== lang, charset の別名解決および妥当性のチェック
    #lang::str    : "en_US", "ja_JP" など
    #charset::str : "eucJP", "utf8" など
    #RETURN:
    #  [ lang, charset, result ]:: result = False の場合 lang, charset は不適切
    @classmethod
    def resolve_alias_and_check(cls, lang, charset):
        key = str(lang).upper()
        ln = cls.LANG_ALIAS[key] if key in cls.LANG_ALIAS else lang

        key = str(charset).upper()
        cs = cls.CHARSET_ALIAS[key] if key in cls.CHARSET_ALIAS else charset

        if ln not in cls.SUITABLE_CHARSET or cs not in cls.SUITABLE_CHARSET[ln]:
            res = False
        else:
            res = True

        return [ln, cs, res]

    #=== 言語、文字コードに関する変数を設定
    # 以下の順にチェックされ、一番最後に設定された値が採用される
    #   ・デフォルト
    #   ・LANG 環境変数
    #   ・TECSGEN_LANG 環境変数
    #   ・TECSGEN_FILE_LANG 環境変数 (ファイルの文字コードのみ)
    #   ・-k オプション (ファイルの文字コードのみ)
    @classmethod
    def set_lang_var(cls):
        import os

        if os.environ.get('LANG'):
            G.LANG_FILE, G.CHARSET_FILE, _dum = cls.parse_lang(os.environ['LANG'])
            G.LANG_CONSOLE = G.LANG_FILE
            G.CHARSET_CONSOLE = G.CHARSET_FILE

        if os.environ.get('TECSGEN_LANG'):
            G.LANG_FILE, G.CHARSET_FILE, _dum = cls.parse_lang(os.environ['TECSGEN_LANG'])
            G.LANG_CONSOLE = G.LANG_FILE
            G.CHARSET_CONSOLE = G.CHARSET_FILE

        if os.environ.get('TECSGEN_FILE_LANG'):
            G.LANG_FILE, G.CHARSET_FILE, _dum = cls.parse_lang(os.environ['TECSGEN_FILE_LANG'])

        cls.set_lang_by_option()

    #=== -k オプションからファイル用の言語、文字コード変数を設定
    @classmethod
    def set_lang_by_option(cls):
        if G.kcode is None:
            return

        code = G.kcode
        if code not in CODE_TYPE_ARRAY:
            print("-k: illegal kcode type {}. ({})".format(code, ", ".join(CODE_TYPE_ARRAY)))
            sys.exit(1)

        if G.kcode == "euc":
            G.CHARSET_FILE = "eucJP"
            G.LANG_FILE = "ja_JP"
        elif G.kcode == "sjis":
            G.CHARSET_FILE = "sjis"
            G.LANG_FILE = "ja_JP"
        elif G.kcode == "utf8":
            G.CHARSET_FILE = "utf8"
            G.LANG_FILE = "ja_JP"
        elif G.kcode == "none":
            G.CHARSET_FILE = None
            G.LANG_FILE = "en_US"

    #=== Kconv クラス用の変数を設定
    # 言語情報から Kconv に関する変数を設定
    @classmethod
    def set_kconv_var(cls):

        # 文字コードの設定
        if G.CHARSET_FILE == "eucJP":
            G.KCONV_CDL = Kconv.EUC
            G.Ruby19_File_Encode = "ASCII-8BIT"
        elif G.CHARSET_FILE == "sjis":
            G.KCONV_CDL = Kconv.SJIS
            G.Ruby19_File_Encode = "Shift_JIS"
        elif G.CHARSET_FILE == "utf8":
            G.KCONV_CDL = Kconv.UTF8
            G.Ruby19_File_Encode = "ASCII-8BIT"
        else:
            G.KCONV_CDL = Kconv.BINARY
            G.Ruby19_File_Encode = "ASCII-8BIT"

        if G.CHARSET_CONSOLE == "eucJP":
            G.KCONV_CONSOLE = Kconv.EUC
        elif G.CHARSET_CONSOLE == "sjis":
            G.KCONV_CONSOLE = Kconv.SJIS
        elif G.CHARSET_CONSOLE == "utf8":
            G.KCONV_CONSOLE = Kconv.UTF8
        else:
            G.KCONV_CONSOLE = Kconv.BINARY

        G.KCONV_TECSGEN = Kconv.UTF8


#####
# G.LANG_FILE        言語 (C は en_US に変換される)
# G.LANG_CONSOLE     言語 (C は en_US に変換される)
# G.CHARSET_FILE     ファイルの文字コード
# G.CHARSET_CONSOLE  コンソール文字コード

# デフォルトの設定（正規化済みのこと）
LANG_FILE_DEFAULT = "en_US"
CHARSET_FILE_DEFAULT = None
LANG_CONSOLE_DEFAULT = "en_US"
CHARSET_CONSOLE_DEFAULT = None

# -k で指定可能なコード
CODE_TYPE_ARRAY = ["euc", "sjis", "none", "utf8"]


#=== メッセージモジュールをロードする
# Ruby 版の require_tecsgen_lib( ..., false ) 相当
#RETURN:: Bool  : True=成功
def _load_message_module(name):
    try:
        importlib.import_module("tecslib.messages." + name)
        return True
    except ImportError:
        return False


def _setup():
    G.LANG_FILE = LANG_FILE_DEFAULT
    G.CHARSET_FILE = CHARSET_FILE_DEFAULT
    G.LANG_CONSOLE = LANG_CONSOLE_DEFAULT
    G.CHARSET_CONSOLE = CHARSET_CONSOLE_DEFAULT

    # 言語を決定する
    TECS_LANG.set_lang_var()

    # 言語、コードのチェックと正規化
    lang_file, charset_file, res = TECS_LANG.resolve_alias_and_check(G.LANG_FILE, G.CHARSET_FILE)
    if res is False:
        lang_file, charset_file = LANG_FILE_DEFAULT, CHARSET_FILE_DEFAULT
    lang_console, charset_console, res = TECS_LANG.resolve_alias_and_check(G.LANG_CONSOLE, G.CHARSET_CONSOLE)
    if res is False:
        lang_console, charset_console = LANG_CONSOLE_DEFAULT, CHARSET_CONSOLE_DEFAULT

    # メッセージモジュールをロード
    if _load_message_module("messages_console_{}".format(lang_console)) is False:
        # TODO(P2): メッセージモジュール未移植のためデフォルトのロード失敗を許容している
        _load_message_module("messages_console_{}".format(LANG_CONSOLE_DEFAULT))
        G.LANG_CONSOLE, G.CHARSET_CONSOLE = LANG_CONSOLE_DEFAULT, CHARSET_CONSOLE_DEFAULT
    else:
        G.LANG_CONSOLE, G.CHARSET_CONSOLE = lang_console, charset_console
    if _load_message_module("messages_file_{}".format(lang_file)) is False:
        _load_message_module("messages_file_{}".format(LANG_FILE_DEFAULT))
        G.LANG_FILE, G.CHARSET_FILE = LANG_FILE_DEFAULT, CHARSET_FILE_DEFAULT
    else:
        G.LANG_FILE, G.CHARSET_FILE = lang_file, charset_file

    # Kconv クラスのための変数を設定
    TECS_LANG.set_kconv_var()

    dbgPrint("LANG_FILE={}.{}, LANG_CONSOLE={}.{}\n".format(
        G.LANG_FILE, G.CHARSET_FILE, G.LANG_CONSOLE, G.CHARSET_CONSOLE))
    dbgPrint("Ruby19_File_Encode={}\n".format(G.Ruby19_File_Encode))


_setup()


#= Console クラス
# 文字コードを変換する
class Console:
    @staticmethod
    def print(string):
        if G.KCONV_CONSOLE == Kconv.BINARY:
            sys.stdout.write(string)
        else:
            sys.stdout.write(kconv_lib.kconv(string, G.KCONV_CONSOLE, G.KCONV_TECSGEN))

    @staticmethod
    def puts(string):
        if G.KCONV_CONSOLE == Kconv.BINARY:
            print(string)
        else:
            print(kconv_lib.kconv(string, G.KCONV_CONSOLE, G.KCONV_TECSGEN))
