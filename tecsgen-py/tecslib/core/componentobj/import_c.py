# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/componentobj/import_c.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

import os
import re
import subprocess

from tecslib.core import globals as G
from tecslib.core.componentobj.import_ import Importable
from tecslib.core.syntaxobj.cdlstring import CDLString
from tecslib.core.syntaxobj.node import Node
from tecslib.core.toplevel import print_exception
from tecslib.rubylib.rb import to_s


class Import_C(Node, Importable):

    # ヘッダの名前文字列のリスト
    header_list = {}
    header_list2 = []
    define_list = {}

    #=== Import_C# import_C の生成（ヘッダファイルを取込む）
    #header:: Token : import_C の第一引数文字列リテラルトークン
    #define:: Token : import_C の第二引数文字列リテラルトークン
    def __init__(self, header, define=None):
        super().__init__()
        # ヘッダファイル名文字列から前後の "" を取り除く
        # header = header.to_s.gsub( /\A"(.*)"\z/, '\1' )
        header = CDLString.remove_dquote(to_s(header))

        def_opt = None
        if define:
            # 前後の "" を取り除く
            # def_opt = define.to_s.gsub( /\A"(.*)/, '\1' )
            # def_opt.sub!( /(.*)"\z/, '\1' )
            def_opt = CDLString.remove_dquote(to_s(define))

            # "," を -D に置き換え
            def_opt = re.sub(r',', " -D ", def_opt)

            # 先頭に -D を挿入 # mikan 不適切な define 入力があった場合、CPP 時にエラー
            def_opt = re.sub(r'^', "-D ", def_opt)

        # コマンドライン指定された DEFINE
        for define in G.define:
            if G.IN_EXERB:
                q = ""
            else:
                if re.search(r"'", define):
                    q = '"'
                else:
                    q = "'"
            def_opt = "{} -D {}{}{}".format(to_s(def_opt), q, define, q)

        header_path = self.find_file(header)

        #    include_opt = ""
        #    found = False
        #    header_path = ""
        #    $import_path.each{ |path|
        #      include_opt = "#{include_opt} -I #{path}"
        #      if found == false then
        #        begin
        #          # ファイルの stat を取ってみる(なければ例外発生)
        #          File.stat( "#{path}/#{header}" )
        #
        #          # cdl を見つかったファイルパスに再設定
        #          header_path = "#{path}/#{header}"
        #          found = true
        #        rescue => evar
        #          found = false
        #          # print_exception( evar )
        #        end
        #      end
        #    }
        #
        #    if found == false then
        if header_path is None:
            self.cdl_error("S1142 $1 not found in search path", header)
            return

        include_opt = ""
        if self.get_base_dir():
            base = self.get_base_dir() + "/"
        else:
            base = ""
        for path in G.import_path:
            include_opt = "{} -I {}{}".format(include_opt, base, path)

        # 読込み済み？
        if Import_C.header_list.get(header):
            # 第二引数 define が以前と異なる
            if to_s(Import_C.define_list.get(header)) != to_s(define):
                self.cdl_error("S1143 import_C: arg2: mismatch with previous one")
            # いずれにせよ読み込まない
            return

        # ヘッダのリストを記録
        Import_C.header_list[header] = header_path
        Import_C.header_list2.append(header)
        Import_C.define_list[header] = define

        if G.verbose:
            print("import_C header={}, define={}\n".format(header_path, define), end="")

        tmp_C = None
        file = None
        try:
            tmp_C = "{}/tmp_C_src.c".format(G.gen)
            file = open(tmp_C, "w")
        except Exception as evar:
            self.cdl_error("S1144 $1: temporary C source: open error", tmp_C)
            print_exception(evar)

        try:
            self.print_defines(file)

            file.write("#include \"{}\"\n".format(header))
        except Exception as evar:
            self.cdl_error("S1145 $1: temporary C source: writing error", tmp_C)
            print_exception(evar)
        finally:
            if file:
                file.close()

        # CPP 出力用 tmp ファイル名
        tmp_header = re.sub(r'/', "_", header)
        tmp_header = "{}/tmp_{}".format(G.gen, tmp_header)

        # CPP コマンドラインを作成
        cmd = "{} {} {} {}".format(G.cpp, to_s(def_opt), include_opt, tmp_C)

        try:
            if G.verbose:
                print("CPP: {}\n".format(cmd))

            # プリプロセッサコマンドを pipe として開く
            # cmd は cygwin/Linux では bash(sh) 経由で実行される
            # Exerb 版では cmd.exe 経由で実行される
            # この差は引き数の (), $, % などシェルの特別な文字の評価に現れるので注意
            cpp = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
            try:
                tmp_file = None
                enc = G.Ruby19_File_Encode
                if enc in ("ASCII-8BIT", "BINARY", "binary"):
                    enc = "latin-1"
                tmp_file = open(tmp_header, "w", encoding=enc)
                for line in cpp.stdout:
                    line = line.decode(enc)
                    line = re.sub(r'^#(.*)$', r'/* \1 */', line)
                    tmp_file.write(line)
            except Exception as evar:
                self.cdl_error("S1146 $1: error occured while CPP(C-PreProcesor), please check C-compiler path or command line options", header)
                print_exception(evar)
            finally:
                if tmp_file:    # mikan File.open に失敗した時 tmp_file == nil は保証されている ?
                    tmp_file.close()
                cpp.stdout.close()
                cpp.wait()
        except Exception as evar:
            self.cdl_error("S1147 $1: popen for CPP（C-PreProcessor） failed, check C-compiler path or command line ooptions", header)
            print_exception(evar)

        # C 言語のパーサインスタンスを生成
        from tecslib.core.c_parser import C_parser
        c_parser = C_parser()

        # tmp_header をパース
        c_parser.parse([tmp_header])

        # 終期化　パーサスタックを戻す
        c_parser.finalize()

    def print_defines(self, file):
        if not getattr(G, 'b_no_gcc_extension_support', None):

            file.write("""
#ifndef TECS_NO_GCC_EXTENSION_SUPPORT

/*
 * these extension can be eliminated also by spefcifying option
 * --no-gcc-extension-support for tecsgen.
 */
#ifdef __GNUC__

#ifndef __attribute__
#define __attribute__(x)
#endif

#ifndef __extension__
#define __extension__
#endif

#ifndef __builtin_va_list
#define __builtin_va_list va_list
#endif

#if 0
#ifndef __asm__
#define __asm__(x)
#endif
#endif /* 0 */

#ifndef restrict
#define restrict
#endif

#endif /* ifdef __GNUC__ */
#endif /* TECS_NO_GCC_EXTENSION_SUPPORT */
""")

        file.write("""#ifndef NO_TECSGEN_VA_LIST
/* va_list is not supported in C_parser.y.rb */
typedef struct { int dummy; } va_list;
#endif /* NO_TECSGEN_VA_LIST */

""")

    @classmethod
    def get_header_list(cls):
        return cls.header_list

    @classmethod
    def get_header_list2(cls):
        return cls.header_list2
