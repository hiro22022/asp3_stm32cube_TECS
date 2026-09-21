# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/tecsgen.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．
#
#= TECSGEN クラスの残り
#
# Ruby 版ではこのファイルが class TECSGEN を再オープンしてメソッドを追加している．
# Python では @reopen で tecsgen.py の TECSGEN へメソッドを追加する．

import tecsgen

from tecslib.core import globals as G
from tecslib.core.toplevel import dbgPrint
from tecslib.rubylib.reopen import reopen

TECSGEN = tecsgen.TECSGEN


###
#== Makefile.templ の出力内容を追加、変更するための操作
class Makefile:
    # 固定されている変数(add_var で変更できない)
    _fixed_vars = {"INCLUDES": None, "DEFINES": None, "TARGET_BASE": None, "BASE_DIR": None}
    _config_mode = False

    _vars = {}
    _vars_default = {}
    _var_comments = {}
    _var_comments_default = {}

    _objs = []
    _ldflags = ""
    _search_path = []
    _pre_tecsgen_target = []
    _post_tecsgen_target = []
    _lines = []

    #=== OTHER_OBJS に追加する
    @classmethod
    def add_obj(cls, obj):
        cls._objs.append(obj)

    #=== 追加する変数
    # プラグインからは、デフォルト値を変更できる
    # config により
    @classmethod
    def add_var(cls, var, val, comment=None):
        if var in cls._fixed_vars:
            raise Exception("fixed var '{}' cannot be changed".format(var))
        if cls._config_mode:
            cls._vars_default[var] = val
            cls._var_comments_default[var] = comment
        else:
            cls._vars[var] = val
            cls._var_comments[var] = comment

    #=== LDFLAGS に追加する
    @classmethod
    def add_ldflag(cls, ldflag):
        cls._ldflags += " " + ldflag

    #=== サーチパスを追加する
    # CFLAGS, vpath に追加する
    @classmethod
    def add_search_path(cls, path):
        cls._search_path.append(path)

    #=== PRE_TECSGEN_TARGET に追加する
    @classmethod
    def add_pre_tecsgen_target(cls, target):
        # Ruby 版は引数名を取り違えており (pre_tecsgen_target)，呼ぶと例外になる
        cls._pre_tecsgen_target.append(target)

    #=== POST_TECSGEN_TARGET に追加する
    @classmethod
    def add_post_tecsgen_target(cls, target):
        # Ruby 版は引数名を取り違えており (pre_tecsgen_target)，呼ぶと例外になる
        cls._post_tecsgen_target.append(target)

    #=== 追加する行
    @classmethod
    def add_line(cls, line):
        cls._lines.append(str(line) + "\n")

    @classmethod
    def get_objs(cls):      # Array を返す
        return list(dict.fromkeys(cls._objs))

    @classmethod
    def get_vars(cls):      # Array を返す
        return sorted(set(list(cls._vars.keys()) + list(cls._vars_default.keys())))

    @classmethod
    def get_var_val(cls, var):
        return cls._vars[var] if cls._vars.get(var) else cls._vars_default.get(var)

    @classmethod
    def get_var_comment(cls, var):
        return cls._var_comments.get(var)

    @classmethod
    def get_ldflags(cls):   # String を返す
        return cls._ldflags

    @classmethod
    def get_search_path(cls):   # Array を返す
        return list(dict.fromkeys(cls._search_path))

    @classmethod
    def get_pre_tecsgen_target(cls):    # Array を返す
        return list(dict.fromkeys(cls._pre_tecsgen_target))

    @classmethod
    def get_post_tecsgen_target(cls):   # Array を返す
        return list(dict.fromkeys(cls._post_tecsgen_target))

    @classmethod
    def get_lines(cls):     # 付加する行を得る
        return list(dict.fromkeys(cls._lines))

    #=== TECSGEN のデフォルト設定を行う
    # _fixed_vars で定義されている変数は、変更できず、定数定義されている
    @classmethod
    def set_default_config(cls):
        cls.add_var("TARGET", "$(TARGET_BASE).exe", "default target name")
        cls.add_var("TECSGEN", "tecsgen", "default TECS generator")
        cls.add_var("TIMESTAMP", "$(GEN_DIR)/tecsgen.timestamp", "Time Stamp")
        cls.add_var("CC", "gcc", "default C Compiler")
        cls.add_var("CFLAGS", '$(INCLUDES) $(DEFINES) -D  "Inline=static inline"',
                    "default C Compiler options")
        cls.add_var("LD", "gcc", "default Liknker")
        cls.add_var("LDFLAGS", cls._ldflags, "default Liknker Options")
        cls.add_var("SRC_DIR", "$(BASE_DIR)/src", "default source directory")
        cls.add_var("_TECS_OBJ_DIR", "$(GEN_DIR)/", "default relocatable object (.o) directory")


###
#== CMakeLists.tecsgen.cmake の出力内容を追加、変更するための操作
class CMake:
    _sources = []
    _includes = []
    _defines = []
    _link_options = []
    _custom_commands = []
    _lines = []

    @classmethod
    def add_source(cls, src):
        cls._sources.append(str(src))

    @classmethod
    def add_include(cls, path):
        cls._includes.append(str(path))

    @classmethod
    def add_define(cls, define):
        cls._defines.append(str(define))

    @classmethod
    def add_link_option(cls, opt):
        cls._link_options.append(str(opt))

    @classmethod
    def add_custom_command(cls, cmd):
        cls._custom_commands.append(str(cmd))

    @classmethod
    def add_line(cls, line):
        cls._lines.append(str(line))

    @classmethod
    def get_sources(cls):
        return list(dict.fromkeys(cls._sources))

    @classmethod
    def get_includes(cls):
        return list(dict.fromkeys(cls._includes))

    @classmethod
    def get_defines(cls):
        return list(dict.fromkeys(cls._defines))

    @classmethod
    def get_link_options(cls):
        return list(dict.fromkeys(cls._link_options))

    @classmethod
    def get_custom_commands(cls):
        return list(dict.fromkeys(cls._custom_commands))

    @classmethod
    def get_lines(cls):
        return list(dict.fromkeys(cls._lines))

    @classmethod
    def set_default_config(cls):
        cls._sources = []
        cls._includes = []
        cls._defines = []
        cls._link_options = []
        cls._custom_commands = []
        cls._lines = []


@reopen(TECSGEN)
class _:

    # ポストコード生成開始後 True
    _b_post_coded = False

    # Ruby 版の TECSGEN::Makefile / TECSGEN::CMake
    Makefile = Makefile
    CMake = CMake

    #=== import パス (-I) を末尾に追加
    # 既に登録済みであれば、追加しない
    @classmethod
    def add_import_path(cls, path):
        if path not in G.import_path:
            dbgPrint("add_import_path: '{}'\n".format(path))
            G.import_path.append(path)

    #=== EXEB 版のパスの調整
    # 環境変数 TECSPATH が cygwin スタイルだと、exerb 版では扱えない
    # Python 版では EXERB を扱わないので何もしない
    @classmethod
    def adjust_exerb_path(cls):
        return

    #=== $(TECSPATH) への置換
    #path::String   : G.tecspath に一致する部分があれば、 "$(TECSPATH)" に置換
    #b_global::Bool : True なら全て置換。False なら最初の一つだけ置換
    @classmethod
    def subst_tecspath(cls, path, b_global=False):
        substr = "$(TECSPATH)"
        if b_global:
            string = path.replace(G.tecspath, substr)
        else:
            string = path.replace(G.tecspath, substr, 1)
        dbgPrint("subst_tecspath {}, {}\n".format(path, string))
        return string

    #=== path は絶対パスか?
    #path:: String   :
    # '/' または '$' で始まる場合、絶対パスと判定する
    @classmethod
    def is_absolute_path(cls, path):
        pa = path[0:1]
        pa2 = path[0:2]
        if pa == '/' or pa == '$' or (len(pa2) == 2 and pa2[0].isalpha() and pa2[1] == ':'):
            res = True
        else:
            res = False
        dbgPrint("is_absolute( {} ) = {}  {}\n".format(path, res, path[0:1]))
        return res

    #=== tecsgen のデフォルトを設定
    @classmethod
    def set_default_config(cls):
        Makefile.set_default_config()
        CMake.set_default_config()
    @classmethod
    def get_argv(cls):
        return G.ARGV

    @classmethod
    def post_coded(cls):
        return cls._b_post_coded

    #------ TECSGEN CDL analyze and generate ------#

    def syntax_analisys(self, argv):
        from tecslib.core.bnf import Generator
        from tecslib.core.componentobj.import_ import Import
        from tecslib.core.componentobj.region import Region
        from tecslib.core.toplevel import dbgPrint

        # ルートネームスペース (region) を生成
        self.root_namespace = Region("::")

        ####  構文解析 (post コードを除く) ####
        # すべての cdl を import する
        for f in argv:
            dbgPrint("## Import: {}\n".format(f))
            Import(f, False, False)

        # すべての構文解釈が完了したことの報告
        Generator.end_all_parse()
        dbgPrint("## End all parse (except Post Code)\n")

    def semantics_analisys_1(self):
        from tecslib.core import globals as G
        from tecslib.core.componentobj.cell import Cell
        from tecslib.core.componentobj.celltype import Celltype
        from tecslib.core.componentobj.signature import Signature
        from tecslib.core.plugin_module import PluginModule
        from tecslib.core.toplevel import dbgPrint
        from tecslib.core.types import DescriptorType

        ####  意味解析１ (post コードを除く) ####
        dbgPrint("## Creating reverse join \n")
        Cell.create_reverse_join()

        DescriptorType.check_signature()
        Signature.set_descriptor_list()
        Celltype.check_dynamic_join()

        #0 set_definition_join は2回呼び出される（1回目）
        dbgPrint("## Checking all join\n")
        self.root_namespace.set_definition_join()

        ####  post コードの生成と構文解析 ####
        TECSGEN._b_post_coded = True     # ポストコード生成開始後 true
        # 引数がなければ、プラグインのポストコードを出力しない
        if len(G.ARGV) > 0:
            dbgPrint("## Generating Post Code\n")
            # プラグインのポストコードの出力と import
            PluginModule.gen_plugin_post_code()

        ####  意味解析１ (post コード) ####
        dbgPrint("## Creating reverse join (for post code) \n")
        Cell.create_reverse_join()

        dbgPrint("## Checking all join (for cells generated by Post Code\n")
        self.root_namespace.set_definition_join()
        self.root_namespace.set_max_entry_port_inner_cell()

        dbgPrint("## Set require join\n")
        self.root_namespace.set_require_join()

    def semantics_analisys_2(self):
        from tecslib.core.componentobj.cell import Cell
        from tecslib.core.toplevel import dbgPrint

        ####  意味解析２ ####
        Cell.make_cell_list2()
        dbgPrint("## Set fixed join\n")
        Cell.create_reverse_require_join()
        dbgPrint("## Setting port reference count\n")
        self.root_namespace.set_port_reference_count()

        dbgPrint("## Checking all join\n")
        self.root_namespace.check_join()

        dbgPrint("## Checking referenced but undefined cell\n")
        self.root_namespace.check_ref_but_undef()

    def optimize_and_generate(self):
        import os
        import sys

        from tecslib.core import globals as G
        from tecslib.core.bnf import Generator
        from tecslib.core.componentobj.region import Region
        from tecslib.core.toplevel import dbgPrint, print_report

        #### Region link root ごとにオプティマイズおよび生成 ####
        for region in Region.get_link_roots():
            n_cells = region.get_n_cells()

            dbgPrint("{} has {} cells\n".format(region.get_name(), n_cells))
            if G.verbose:
                print("=====================================")
                print("=== Region.path_str: {}".format(
                    region.get_namespace_path().get_path_str()))
                print("=====================================")
            else:
                dbgPrint("Region.path_str: {}\n".format(
                    region.get_namespace_path().get_path_str()))

            if len(G.region_list) > 0:
                path_str = region.get_namespace_path().get_path_str()
                if G.region_list.get(path_str):
                    G.region_list[path_str] = False
                else:
                    continue

            # セルが一つもなければ生成しない
            if region.get_n_cells() == 0:
                if len(G.region_list) > 0:
                    Generator.warning(
                        "W9999 $1: specified to generate but has no cell",
                        region.get_name())
                if region is not self.root_namespace:
                    continue

            G.generating_region = region
            if len(Region.get_link_roots()) > 1:
                if region.get_name() == "::":
                    G.gen = G.gen_base
                else:
                    G.gen = G.gen_base + "/" + str(region.get_global_name())
                    try:
                        if not os.path.isdir(G.gen):
                            os.mkdir(G.gen)
                    except OSError:
                        print("Cannot mkdir {}\n".format(G.gen), end="")
                        sys.exit(1)
            else:
                G.gen = G.gen_base

            dbgPrint("## Unset optimize variables\n")
            self.root_namespace.reset_optimize()   # 最適化をリセットする

            if Generator.get_n_error() == 0:
                dbgPrint("## Set cell id\n")
                self.root_namespace.set_cell_id_and_domain()

                if not G.unopt:
                    dbgPrint("## Optimizing: Link Region={}\n".format(
                        self.root_namespace.get_name()))
                    self.root_namespace.optimize()

            if G.show_tree:
                print("##### show_tree LinkRegion={} #####".format(region.get_name()))
                self.root_namespace.show_tree(0)
                print("##### END       LinkRegion={} #####\n".format(region.get_name()))

            if Generator.get_n_error() != 0:
                print_report()
                sys.exit(1)

            #### コード生成 ####
            try:
                dbgPrint("## Generating: Link Region={}\n".format(
                    self.root_namespace.get_name()))
                self.root_namespace.generate()
                dbgPrint("## Generating Post: Link Region={}\n".format(
                    self.root_namespace.get_name()))
                self.root_namespace.generate_post()
            except Exception:
                Generator.error("G9999 fail to generate")

    def finalize(self):
        import sys

        from tecslib.core import globals as G
        from tecslib.core.bnf import Generator
        from tecslib.core.generate import AppFile
        from tecslib.core.toplevel import dbgPrint, print_exception, print_report

        dbgPrint("## Generating XML\n")

        for region_path_str, val in list(G.region_list.items()):
            if val is True:
                Generator.warning(
                    "W9999 $1: not link root, -G ignored", region_path_str)

        if Generator.get_n_error() == 0:
            try:
                AppFile.update()
            except Exception as evar:
                Generator.error(
                    "G9999 Fail to update. (error occurred while renaming generated files)")
                print_exception(evar)

        print_report()
        if Generator.get_n_error() != 0:
            sys.stderr.write(
                "error occurred while generating. some file can be corrupt in {}\n".format(
                    G.gen_base))
            sys.exit(1)

        open("{}/tecsgen.timestamp".format(G.gen_base), "w").close()
