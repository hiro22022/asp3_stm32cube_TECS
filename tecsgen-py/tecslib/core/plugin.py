# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/plugin.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

import re

from tecslib.core.syntaxobj.node import Node


def _plugin_arg_proc_silent(obj, rhs):
    obj.set_silent(rhs)


#== Plugin クラス
# ThroughPlugin, SignaturePlugin, CelltypePlugin に include する
class Plugin(Node):
#@error_backlog:: [msg1, msg2, ... ]   @locale が設定される前に発生したエラー

    PluginArgProc = {
        "silent": _plugin_arg_proc_silent,
    }

    def __init__(self):
        super().__init__()
        self.b_silent = False
        self.locale = None       # set_locale が呼び出されるまで nil となる
        self.error_backlog = []

    #=== Plugin#cdl_error
    # set_locale が呼び出されるまで @error_backlog に保存し保留する
    def cdl_error(self, *arg):
        if self.locale:
            from tecslib.core.bnf import Generator
            Generator.error2(self.locale, *arg)
        else:
            self.error_backlog.append(arg)

    #=== locale を設定する
    # Node は initialize で locale を設定するが、plugin は parse とは
    # 異なるタイミング new されるため、locale を再設定する
    # このメソッドを2度呼び出すと @error_backlog のエラーが2度出力されてしまう
    def set_locale(self, locale):
        from tecslib.core.bnf import Generator
        self.locale = locale
        for arg in self.error_backlog:
            Generator.error2(locale, *arg)

### 構文解釈 または 意味解析段階で呼び出されるメソッド ###
# generate 指定子の場合、構文解釈次第(end_of_parseで)呼び出される
# generate 文の場合、出現次第呼び出される
    ### 意味解析段階で呼び出されるメソッド ### <<< コメント誤り (V1.4.2)
    #===  CDL ファイルの生成
    #      typedef, signature, celltype, cell のコードを生成
    #      重複して生成してはならない
    #      すでに生成されている場合は出力しないこと。
    #      もしくは同名の import により、重複を避けること。
    #file::        FILE       生成するファイル
    def gen_cdl_file(self, file):
        pass


### コード生段階で呼び出されるメソッド ###
    #=== プラグインは gen_ep_func を提供するか
    # gen_ep_func 定義   ⇒ テンプレートではない、セルタイプコード(tCelltype.c)を生成 
    # gen_ep_func 未定義 ⇒ テンプレート(tCelltype_templ.c)を生成
    def gen_ep_func(self):
        for cls in self.__class__.__mro__:
            if 'gen_ep_func_body' in cls.__dict__:
                return True
        return False

    #===  受け口関数の本体(C言語)を生成する
    #     プラグインの場合、変更する必要のないセルタイプコードを生成する
    #     このメソッドが未定義であれば、プラグインはセルタイプコードを生成しない (通常通りテンプレートを生成する)
    #      gen_cdl_file の中で生成されたセルタイプに対して呼び出される
    #file::           FILE        出力先ファイル (tCelltype.c)
    #b_singleton::    bool        true if singleton
    #ct_name::        Symbol
    #global_ct_name:: string
    #sig_name::       string
    #ep_name::        string
    #func_name::      string
    #func_global_name:: string
    #func_type::      class derived from Type
#  def gen_ep_func_body( file, b_singleton, ct_name, global_ct_name, sig_name, ep_name, func_name, func_global_name, func_type, params )
#  end

    #===  受け口関数の preamble (C言語)を生成する
    #     必要なら preamble 部に出力する
    #      gen_cdl_file の中でで生成されたセルタイプに対して呼び出される
    #file::           FILE        出力先ファイル
    #b_singleton::    bool        true if singleton
    #ct_name::        Symbol
    #global_ct_name:: string
    def gen_preamble(self, file, b_singleton, ct_name, global_ct_name):
        # デフォルトでは何も出力しない
        pass

    #===  受け口関数の postamble (C言語)を生成する
    #     必要なら postamble 部に出力する
    #      gen_cdl_file の中で生成されたセルタイプに対して呼び出される
    #file::           FILE        出力先ファイル
    #b_singleton::    bool        true if singleton
    #ct_name::        Symbol
    #global_ct_name:: string
    def gen_postamble(self, file, b_singleton, ct_name, global_ct_name):
        # デフォルトでは何も出力しない
        pass

    #=== gen_cdl_file の中で生成されたセルタイプに新しいセルが生成された
    # どのセルタイプかは cell.get_celltype で分かる
    #
    #file::           FILE        出力先ファイル
    #b_singleton::    bool        true if singleton
    #ct_name::        Symbol
    #global_ct_name:: string
    def new_cell(self, cell):
        # デフォルトでは何もしない
        pass

### プラグイン引数の解釈 ###
    def parse_plugin_arg(self):
        arg = self.plugin_arg_str

        # 改行を消す
        arg = re.sub(r'\\\n', '', arg)

        while arg != "":

            # 前の空白読み飛ばす
            m = re.match(r'\A\s*(?:\\\n)*\s*(.*)', arg, re.DOTALL)
            arg = m.group(1)

            #  識別子取得
            m = re.match(r'\A([a-zA-Z_]\w*)', arg)
            if m:
                ident = m.group(0)
                arg = arg[len(ident):]
            else:
                self.cdl_error("P1001 plugin arg: cannot find identifier in $1", arg)
                return

            # 前の空白読み飛ばす
            m = re.match(r'\A\s*(?:\\\n)*\s*(.*)', arg, re.DOTALL)
            arg = m.group(1)

            if re.match(r'=', arg):
                arg = re.sub(r'\A=', '', arg, count=1)
            else:
                self.cdl_error("P1002 plugin arg: expecting \'=\' not \'$1\'", arg)
                return

            # 前の空白読み飛ばす
            m = re.match(r'\A\s*(?:\\\n)*\s*(.*)', arg, re.DOTALL)
            arg = m.group(1)

            # 右辺文字列
            rhs = None
            remain = None
            if re.match(r'\A\\"(.*?)\\"\s*,', arg, re.DOTALL):      # \"  \" で囲まれている場合 (末尾に',' あり)
                m = re.match(r'\A\\"(.*?)\\"\s*,', arg, re.DOTALL)
                rhs = m.group(1)
                remain = arg[m.end():]
            elif re.match(r'\A%(.*?)%\s*,', arg, re.DOTALL):      # %   % で囲まれている場合 (末尾に',' あり)
                m = re.match(r'\A%(.*?)%\s*,', arg, re.DOTALL)
                rhs = m.group(1)
                remain = arg[m.end():]
            elif re.match(r'\A!(.*?)!\s*,', arg, re.DOTALL):    # !  ! で囲まれている場合 (末尾に',' あり)
                m = re.match(r'\A!(.*?)!\s*,', arg, re.DOTALL)
                rhs = m.group(1)
                remain = arg[m.end():]
            elif re.match(r"\A'(.*?)'\s*,", arg, re.DOTALL):    # '  ' で囲まれている場合 (末尾に',' あり)
                m = re.match(r"\A'(.*?)'\s*,", arg, re.DOTALL)
                rhs = m.group(1)
                remain = arg[m.end():]
            elif re.match(r'\A\\"(.*?)\\"\s*,', arg, re.DOTALL):  # || にも [,$] にもできなかった
                m = re.match(r'\A\\"(.*?)\\"\s*,', arg, re.DOTALL)
                rhs = m.group(1)
                remain = arg[m.end():]
            # elsif arg =~ /\A(.*?)\s*$/ then
            elif re.match(r'\A\\"(.*?)\\"\s*\Z', arg, re.DOTALL):      # \"  \" で囲まれている場合
                m = re.match(r'\A\\"(.*?)\\"\s*\Z', arg, re.DOTALL)
                rhs = m.group(1)
                remain = arg[m.end():]
            elif re.match(r'\A%(.*?)%\s*\Z', arg, re.DOTALL):      # %   % で囲まれている場合
                m = re.match(r'\A%(.*?)%\s*\Z', arg, re.DOTALL)
                rhs = m.group(1)
                remain = arg[m.end():]
            elif re.match(r'\A!(.*?)!\s*\Z', arg, re.DOTALL):    # !  ! で囲まれている場合
                m = re.match(r'\A!(.*?)!\s*\Z', arg, re.DOTALL)
                rhs = m.group(1)
                remain = arg[m.end():]
            elif re.match(r"\A'(.*?)'\s*\Z", arg, re.DOTALL):    # '  ' で囲まれている場合
                m = re.match(r"\A'(.*?)'\s*\Z", arg, re.DOTALL)
                rhs = m.group(1)
                remain = arg[m.end():]
            elif re.match(r'\A\\"(.*?)\\"\s*\Z', arg, re.DOTALL):  # || にも [,$] にもできなかった
                m = re.match(r'\A\\"(.*?)\\"\s*\Z', arg, re.DOTALL)
                rhs = m.group(1)
                remain = arg[m.end():]
            elif re.match(r'\A(.*?),', arg, re.DOTALL):
                m = re.match(r'\A(.*?),', arg, re.DOTALL)
                rhs = m.group(1)
                remain = arg[m.end():]
                # 前の空白読み飛ばす
                m2 = re.match(r'\A\s*(.*)\s*\Z', rhs, re.DOTALL)
                rhs = m2.group(1)
            elif re.match(r'\A(.*?)\s*\Z', arg, re.DOTALL):
                m = re.match(r'\A(.*?)\s*\Z', arg, re.DOTALL)
                rhs = m.group(1)
                remain = arg[m.end():]
            else:
                self.cdl_error("P1003 plugin arg: unexpected $1", arg)
                return

            # 0文字の文字列を to_sym すると例外発生するので空白文字とする
            if rhs == "":
                rhs = " "

            arg = remain         # arg の残りの部分
            m = re.match(r'\A\s*(?:\\\n)*\s*(.*)', arg, re.DOTALL)
            arg = m.group(1)      # 前の空白読み飛ばす

            # \ を外す
            rhs = re.sub(r'\\(.)', r'\1', rhs)   # ここで $' が変わることに注意！
            # print "parse_plugin_arg:  #{ident} #{rhs}\n"
            self.plugin_arg_list[ident] = rhs

            self.check_plugin_arg(ident, rhs)
        # @plugin_arg_list.each{|i,r|  print "ident: #{i}  rhs: #{r}\n" }

    #=== プラグイン引数をチェックする
    # @plugin_arg_check_proc_tab に従ってプラグイン引数をチェックすする
    # 古い用法：子クラスでオーバーライドし、引数識別子が正しいかチェックする
    #ident:: string: 引数識別子
    #rhs:: string: 右辺文字列
    def check_plugin_arg(self, ident, rhs):

        from tecslib.core.toplevel import dbgPrint
        dbgPrint("check_plugin_arg: {} {}\n".format(ident, str(rhs)))
        proc = None
        ident_s = str(ident)
        if self.plugin_arg_check_proc_tab:
            proc = self.plugin_arg_check_proc_tab.get(ident_s)
        if proc is None:
            proc = Plugin.PluginArgProc.get(ident_s)
        if callable(proc) and not isinstance(proc, type):
            dbgPrint("calling: {}.{}\n".format(self.__class__.__name__, proc))
            proc(self, rhs)
        else:
            params = ""
            delim = ""
            for j, p in self.plugin_arg_check_proc_tab.items():
                params = "{}{}{}".format(params, delim, j)
                delim = ", "
            self.cdl_error("P1004 $1: unknown plugin argument\'s identifier\n  $2 are acceptible for RPCPlugin.", ident, params)

    #=== プラグインのメッセージ出力
    def print_msg(self, msg):
        if self.b_silent == True:
            return
        print(msg, end="")

    #=== プラグイン引数 silent
    def set_silent(self, rhs):
        if rhs == "true" or rhs is None:
            self.b_silent = True


#== 出力文字列を utf-8 から出力ファイルに convert する
# tecsgen のソースコードは utf-8 で記述されている
# これを、出力ファイルの文字コードに変換して出力する
#
# generate.rb で出力するものは message.rb で変換している
# generate.rb で出力するものは APPFile クラスを使用している
# mikan: CFile で出力したものに factory で追記できない (cdl ファイルの場合、追記できても意味がない)
class CFile:

    @classmethod
    def open(cls, path, mode):
        return CFile(path, mode)

    def __init__(self, path, mode):
        from tecslib.core import globals as G
        # Ruby の "w:ASCII-8BIT" はバイナリ相当で UTF-8 文字列のバイト列をそのまま書く。
        # Python の latin-1 は U+0100 以上を拒否するため、ASCII-8BIT は utf-8 にマップする。
        enc = G.Ruby19_File_Encode
        if enc in ("ASCII-8BIT", "BINARY", "binary"):
            enc = "utf-8"
        self.file = open(path, mode, encoding=enc)

    def print(self, str):
        from tecslib.core import globals as G
        from tecslib.rubylib import kconv as kconv_lib
        from tecslib.rubylib.kconv import Kconv
        if G.KCONV_CONSOLE == Kconv.BINARY:
            self.file.write(str)
        else:
            self.file.write(kconv_lib.kconv(str, G.KCONV_CDL, G.KCONV_TECSGEN))

    def puts(self, str):
        from tecslib.core import globals as G
        from tecslib.rubylib import kconv as kconv_lib
        from tecslib.rubylib.kconv import Kconv
        if G.KCONV_CONSOLE == Kconv.BINARY:
            self.file.write(str)
        else:
            self.file.write(kconv_lib.kconv(str, G.KCONV_CDL, G.KCONV_TECSGEN))
        self.file.write("\n")

    def printf(self, format, *arg):
        from tecslib.core import globals as G
        from tecslib.rubylib import kconv as kconv_lib
        from tecslib.rubylib.kconv import Kconv
        if G.KCONV_CONSOLE == Kconv.BINARY:
            self.file.write(format % arg)
        else:
            self.file.write(kconv_lib.kconv(format % arg, G.KCONV_CDL, G.KCONV_TECSGEN))

    def close(self):
        self.file.close()
