#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  TECS Generator
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#--
#   上記著作権者は，以下の(1)〜(4)の条件を満たす場合に限り，本ソフトウェ
#   ア（本ソフトウェアを改変したものを含む．以下同じ）を使用・複製・改
#   変・再配布（以下，利用と呼ぶ）することを無償で許諾する．
#   (1) 本ソフトウェアをソースコードの形で利用する場合には，上記の著作
#       権表示，この利用条件および下記の無保証規定が，そのままの形でソー
#       スコード中に含まれていること．
#   (2) 本ソフトウェアを，ライブラリ形式など，他のソフトウェア開発に使
#       用できる形で再配布する場合には，再配布に伴うドキュメント（利用
#       者マニュアルなど）に，上記の著作権表示，この利用条件および下記
#       の無保証規定を掲載すること．
#   (3) 本ソフトウェアを，機器に組み込むなど，他のソフトウェア開発に使
#       用できない形で再配布する場合には，次のいずれかの条件を満たすこ
#       と．
#     (a) 再配布に伴うドキュメント（利用者マニュアルなど）に，上記の著
#         作権表示，この利用条件および下記の無保証規定を掲載すること．
#     (b) 再配布の形態を，別に定める方法によって，TOPPERSプロジェクトに
#         報告すること．
#   (4) 本ソフトウェアの利用により直接的または間接的に生じるいかなる損
#       害からも，上記著作権者およびTOPPERSプロジェクトを免責すること．
#       また，本ソフトウェアのユーザまたはエンドユーザからのいかなる理
#       由に基づく請求からも，上記著作権者およびTOPPERSプロジェクトを
#       免責すること．
#
#   本ソフトウェアは，無保証で提供されているものである．上記著作権者お
#   よびTOPPERSプロジェクトは，本ソフトウェアに関して，特定の使用目的
#   に対する適合性も含めて，いかなる保証も行わない．また，本ソフトウェ
#   アの利用により直接的または間接的に生じたいかなる損害に関しても，そ
#   の責任を負わない．
#++

#= tecsgen  : TECS のジェネレータ (Python 版)
#
# Ruby 版 tecsgen の tecsgen.rb を Python へ移植したもの．
# 元の tecsgen ジェネレータは TOPPERS プロジェクトの TECS WG により開発されている．
#
# 移植にあたっての相違点
#   ・グローバル変数 $xxx は tecslib/core/globals.py の属性としている
#   ・require_tecsgen_lib によるライブラリ探索は Python の import に置き換えた
#     (-L オプションは受け付けるが探索には使われない)
#   ・トップレベル関数 (dbgPrint, print_report など) は
#     tecslib/core/toplevel.py に置いている
#   ・tecsflow 用の tecsgen.rbdmp (Marshal.dump) は出力しない

import os
import platform
import sys

# 直接 python3 tecsgen.py として起動された場合でも import が通るようにする
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tecslib.core import globals as G              # noqa: E402
from tecslib.core.toplevel import dbgPrint         # noqa: E402
from tecslib.rubylib import optparse as rubyopt    # noqa: E402


#----- class TECSGEN -------#
class TECSGEN:

    _current_tecsgen = None

    @classmethod
    def init(cls, addtional_option_parser=None, no_tecsgen_option=False):
        cls.initialize_global_var()
        if no_tecsgen_option is False:
            cls.analyze_option(addtional_option_parser)
        cls.load_modules()
        if not G.TECSFLOW:
            cls.setup()

        dbgPrint("tecspath: {}, __FILE__={}\n".format(G.tecsgen_base_path, __file__))
        dbgPrint("ARGV(remained): {}, argments={}\n".format(G.ARGV, G.arguments))

    #----- initialize -------#
    def __init__(self):
        self.cell_list = None
        self.cell_list2 = None
        self.celltype_list = None
        self.root_namespace = None

        #--- obsolete ---#   replaced to TOOL_INFO
        self.cell_location_list = []
        self.join_location_list = []

    def run1(self):
        TECSGEN._current_tecsgen = self

        self.syntax_analisys(G.ARGV)
        self.semantics_analisys_1()
        self.semantics_analisys_2()

        from tecslib.core.componentobj.celltype import Celltype
        from tecslib.core.componentobj.cell import Cell

        self.celltype_list = Celltype.get_celltype_list()
        self.cell_list = Cell.get_cell_list()
        self.cell_list2 = Cell.get_cell_list2()

        TECSGEN._current_tecsgen = None

    def run2(self):
        TECSGEN._current_tecsgen = self

        self.optimize_and_generate()
        self.finalize()

        TECSGEN._current_tecsgen = None

    #-----  initialize_global_var -----#
    @classmethod
    def initialize_global_var(cls):
        ### グローバル変数定義 ###
        # 変数の定義そのものは tecslib/core/globals.py にある
        # ここではコマンドライン引数に依存するものだけを設定する
        G.initialize(sys.argv[1:])

    @classmethod
    def analyze_option(cls, additional_option_parser):

        ###  tecsgen コマンドオプション解析  ###
        def define_options(parser):
            parser.banner = "Usage: tecsgen [options] files"

            def opt_D(define):
                G.define.append(define)
            parser.on('-D', '--define=def', 'define cpp symbol for import_C', block=opt_D)

            def opt_G(path):
                if path.startswith("::"):
                    gen_path = path
                else:
                    gen_path = "::" + path
                G.region_list[gen_path] = True
            parser.on('-G', '--generate-region=path', 'generate region', block=opt_G)

            def opt_I(path):
                G.import_path.append(path)
                G.import_path_opt.append(path)
            parser.on('-I', '--import-path=path', 'imoprt/import_C path', block=opt_I)

            def opt_L(path):
                G.library_path.append(path)
            parser.on('-L', '--library-path=path',
                      'path to dir where tecsgen.rb (obsolete, unnecessary to specify -L, those passes are gotten from tecsgen.rb',
                      block=opt_L)

            def opt_R():
                G.ram_initializer = True
            parser.on('-R', '--RAM-initializer',
                      'generate RAM initializer. INITIALIZE_TECS() must be called before running any TECS code.',
                      block=opt_R)

            def opt_U():
                G.unopt = True
            parser.on('-U', '--unoptimize', 'unoptimize', block=opt_U)

            def opt_unoptimize_entry():
                G.unopt_entry = True
            parser.on('--unoptimize-entry', 'unoptimize entry port', block=opt_unoptimize_entry)

            def opt_c(arg):
                G.cpp = arg
                G.b_cpp_specified = True
            parser.on('-c', '--cpp=cpp_cmd',
                      'C pre-processor command used import_C (default: gcc -E -DTECSGEN), you can also specify by environment variable TECS_CPP',
                      block=opt_c)

            def opt_d():
                G.dryrun = True
            parser.on('-d', '--dryrun', 'dryrun', block=opt_d)

            def opt_f():
                G.force_overwrite = True
            parser.on('-f', '--force-overwrite', 'force overwrite all files', block=opt_f)

            def opt_g(directory):
                G.gen = G.gen_base = directory
            parser.on('-g', '--gen=dir', 'generate dir', block=opt_g)

            def opt_i():
                G.idx_is_id = True
            parser.on('-i', '--idx_is_id', 'set idx_is_id to all celltypes', block=opt_i)

            def opt_k(code):
                G.kcode = code
            parser.on('-k', '--kcode=code', 'set kanji code: euc|sjis|none|utf8', block=opt_k)

            #  old_mode は V1.0.C.22 で廃止
            def opt_r():
                G.rom = False
            parser.on('-r', '--ram', 'RAM only', block=opt_r)

            def opt_s():
                G.show_tree = True
            parser.on('-s', '--show-tree', 'show parsing tree', block=opt_s)

            def opt_t():
                G.debug = True
                G.verbose = True
            parser.on('-t', '--generator-debug', 'generator debug', block=opt_t)

            def opt_u():
                G.unique_id = True
            parser.on('-u', '--unique-id', 'assign unique id for each cell', block=opt_u)

            def opt_v():
                G.verbose = True
            parser.on('-v', '--verbose', 'verbose mode', block=opt_v)

            def opt_y():
                G.yydebug = True
            parser.on('-y', '--yydebug', 'yydebug', block=opt_y)

            def opt_no_banner():
                G.no_banner = True
            parser.on('--no-banner', 'not display banner', block=opt_no_banner)

            def opt_version():
                G.print_version = True
            parser.on('--version', 'print version', block=opt_version)

            def opt_unit_test():
                G.unit_test = True
            parser.on('--unit-test', 'unit verification (test tecsgen itself)', block=opt_unit_test)

            def opt_generate_all_template():
                G.generate_all_template = True
            parser.on('--generate-all-template', "generate all celltypes' templates",
                      block=opt_generate_all_template)

            def opt_generate_no_template():
                G.generate_no_template = True
            parser.on('--generate-no-template', 'generate no template', block=opt_generate_no_template)

            def opt_no_default_import_path():
                G.no_default_import_path = True
            parser.on('--no-default-import-path', 'no default import path',
                      block=opt_no_default_import_path)

            def opt_c_suffix(suffix):
                G.c_suffix = suffix
            parser.on('--c-suffix=c', 'C program suffix (default: c)', block=opt_c_suffix)

            def opt_h_suffix(suffix):
                G.h_suffix = suffix
            parser.on('--h-suffix=h', 'C program header suffix (default: h)', block=opt_h_suffix)

            parser.version = "{}".format(G.version)
            parser.release = None
            if additional_option_parser:
                additional_option_parser(parser)
            parser.parse_bang()

        parser = rubyopt.options(G.ARGV, sys.argv[0], define_options)

        if not G.ARGV and not G.print_version and not G.unit_test and not G.TECSFLOW:
            sys.stdout.write(parser.help())
            sys.exit(1)

    @classmethod
    def load_modules(cls):
        ### tecsgen モジュールのロード ####

        #  tecsgen バージョンファイルのロード
        # これを実行するまで tecsgen のバージョンを表示できない
        import tecslib.version  # noqa: F401

        if G.title:
            sys.stderr.write("{} version {} (tecsgen version {})  {}\n".format(
                G.title, G.tool_version, G.version, G.Copyright or ""))
        elif not G.no_banner or G.print_version:
            sys.stderr.write("tecsgen  version {}  {}\n".format(G.version, G.Copyright or ""))
        if G.verbose:
            sys.stderr.write("python {} [{}]\n".format(platform.python_version(), sys.platform))
        if G.print_version and not G.ARGV and not G.TECSFLOW:
            sys.exit()

        # 文字コード決定のため最初に読みこむ
        import tecslib.core.tecs_lang  # noqa: F401

        # TECSGEN クラスの残り (tecslib/core/tecsgen.rb 由来) を読み込む
        import tecslib.core.tecsgen    # noqa: F401

        # Ruby 版の require 順に対応（移植済みから有効化）
        import tecslib.core.bnf  # noqa: F401
        import tecslib.core.optimize  # noqa: F401
        import tecslib.core.generate  # noqa: F401
        import tecslib.core.generate_celltype  # noqa: F401
        import tecslib.core.c_parser  # noqa: F401
        import tecslib.core.tecsinfo  # noqa: F401
        # TODO: tool_info.py, unjoin_plugin.py, plugin/* 本体

        if G.unit_test:
            sys.exit(1)

    @classmethod
    def setup(cls):
        # G.import_path, G.tecspath を調整
        cls.adjust_exerb_path()

        # G.import_path に環境変数 TECSPATH およびその直下を追加
        if G.no_default_import_path is False:
            # TECSPATH および、その直下のディレクトリをパスに追加
            if G.tecspath != ".":
                cls.add_import_path(G.tecspath)
                try:
                    for f in os.listdir(G.tecspath):
                        if os.path.isdir(G.tecspath + '/' + f):
                            cls.add_import_path(G.tecspath + '/' + f)
                except OSError:
                    # 無視
                    pass

        # デフォルト設定
        cls.set_default_config()

        # G.target の設定
        G.target = G.ARGV[0]
        pos = max(G.target.rfind(':'), G.target.rfind('\\'), G.target.rfind('/'))
        if pos >= 0:
            G.target = G.target[pos + 1:]   # ディレクトリ区切りを除いた文字列
        pos = G.target.rfind('.')
        if pos >= 0:
            G.target = G.target[0:pos]      # 拡張子を取り除いた文字列

        # gen ディレクトリの作成
        try:
            if not os.path.isdir(G.gen_base):
                os.mkdir(G.gen_base)
        except OSError:
            print("Cannot mkdir {}. If the path has hierarchy, please create directory by manual.".format(G.gen_base))
            sys.exit(1)

    #=== TECSGEN#get_celltype_list
    def get_celltype_list(self):
        return self.celltype_list

    #=== TECSGEN#get_cell_list
    def get_cell_list(self):
        return self.cell_list

    def get_root_namespace(self):
        return self.root_namespace


# 複数のジェネレータインスタンスを生成することは、可能だが、以下の問題がある
#  クラス変数のリセットを確実に行う必要がある
def main():
    from tecslib.core.toplevel import print_exception

    if G.TECSCDE is not True and G.TECSFLOW is not True:
        try:
            TECSGEN.init()
            tecsgen = TECSGEN()
            tecsgen.run1()
            tecsgen.run2()
        except SystemExit:
            raise
        except Exception as evar:
            print_exception(evar)
            sys.stderr.write("tecsgen: exit because of unrecoverble error.\n")
            sys.stderr.write("   please retry after resolve early error.\n")
            sys.stderr.write("   if no error has occured, please report to TOPPERS TECS WG (users@toppers.jp or com-wg@toppers.jp).\n")
            sys.exit(1)


if __name__ == "__main__":
    # 直接実行された場合，モジュール tecsgen として読み込み直してから実行する
    # (tecslib 側が import tecsgen で同じ TECSGEN クラスを参照できるようにするため)
    import tecsgen as _tecsgen_module

    _tecsgen_module.main()
