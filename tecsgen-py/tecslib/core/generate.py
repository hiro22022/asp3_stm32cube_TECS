# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/generate.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．
#
#   移植状況: AppFile / MemFile / Namespace#generate / generate_post および
#   ヘッダ生成・Makefile 生成の骨格を含む．Celltype 生成の大半は
#   generate_celltype.py（tools/port_generate.py により Ruby から機械変換）に分離．
#   差分テスト合格のためには generate.rb 残りの手直しが必要（後述）．

import os
import re
import sys

import tecsgen
from tecslib.core import globals as G
from tecslib.core.messages import TECSMsg
from tecslib.core.componentobj.import_ import Import
from tecslib.core.componentobj.import_c import Import_C
from tecslib.core.componentobj.namespace import Namespace
from tecslib.core.componentobj.region import Region
from tecslib.core.componentobj.signature import Signature
from tecslib.core.componentobj.celltype import Celltype
from tecslib.core.componentobj.domaintype import DomainType
from tecslib.core.componentobj.classtype import ClassType
from tecslib.core.syntaxobj.typedef import Typedef
from tecslib.core.types import StructType
from tecslib.core.ctypes import CType
from tecslib.core.toplevel import dbgPrint, print_exception
from tecslib.rubylib.reopen import reopen
from tecslib.rubylib.symbol import Sym
from tecslib.rubylib import rb

TECSGEN = tecsgen.TECSGEN


class _AppFileIO(object):
    """Ruby IO#print / #printf 相当 (AppFile が返すファイルオブジェクト)"""

    def __init__(self, f):
        self.file = f

    def print(self, s="", end=""):
        self.file.write(s)

    def printf(self, fmt, *args):
        # Ruby の IO#printf は "%d" に数字文字列を渡すと整数化する
        coerced = []
        for a in args:
            if isinstance(a, str):
                try:
                    if a.lstrip().startswith(("+", "-")) or a.isdigit() or (
                        len(a) > 1 and a[0] in "+-" and a[1:].isdigit()
                    ):
                        # 整数っぽい文字列のみ（factory の %d 用）
                        coerced.append(int(a, 10))
                        continue
                except ValueError:
                    pass
            coerced.append(a)
        self.file.write(fmt % tuple(coerced))

    def puts(self, s=""):
        self.file.write(s)
        self.file.write("\n")

    def close(self):
        self.file.close()


# Appendable File（追記可能ファイル）
class AppFile(object):
    # 開いたファイルのリスト
    file_name_list = {}

    @classmethod
    def open(cls, name):
        if G.force_overwrite:
            real_name = name
        else:
            real_name = name + ".tmp"

        # Ruby File.open mode ":ASCII-8BIT" → バイナリ相当で UTF-8 バイトをそのまま出力
        if cls.file_name_list.get(name):
            f = open(real_name, "a", encoding="utf-8")
        else:
            f = open(real_name, "w", encoding="utf-8")
            cls.file_name_list[name] = True
        # File クラスのオブジェクトを返す
        return _AppFileIO(f)

    @classmethod
    def update(cls):
        if G.force_overwrite:
            return

        for name, boo in list(cls.file_name_list.items()):
            b_identical = False
            if os.path.isfile(name) and os.access(name, os.R_OK):
                with open(name, "r", encoding="utf-8") as oldf:
                    old_lines = oldf.readlines()
                with open(name + ".tmp", "r", encoding="utf-8") as newf:
                    new_lines = newf.readlines()
                if len(old_lines) == len(new_lines):
                    i = 0
                    length = len(old_lines)
                    while i < length:
                        if old_lines[i] != new_lines[i]:
                            break
                        i += 1
                    if i == length:
                        b_identical = True
            if b_identical == False:
                if G.verbose:
                    print("{} changed".format(name))
                    print("renaming '{}.tmp' => '{}'".format(name, name))
                os.rename(name + ".tmp", name)
            else:
                if G.verbose:
                    print("{} not changed".format(name))
                os.remove(name + ".tmp")


class MemFile(object):
    def __init__(self):
        self.string = ""

    def print(self, str):
        self.string += str

    def get_string(self):
        return self.string


def ifdef_macro_only(f):
    f.print("#ifndef TOPPERS_MACRO_ONLY\n\n")


def ifndef_macro_only(f):
    f.print("#ifndef TOPPERS_MACRO_ONLY\n\n")


def endif_macro_only(f):
    f.print("#endif /* TOPPERS_MACRO_ONLY */\n\n")


def ifndef_cb_type_only(f):
    f.print("#ifndef TOPPERS_CB_TYPE_ONLY\n\n")


def ifdef_cb_type_only(f):
    f.print("#ifdef TOPPERS_CB_TYPE_ONLY\n\n")


def endif_cb_type_only(f):
    f.print("#endif /* TOPPERS_CB_TYPE_ONLY */\n\n")


def begin_extern_C(f):
    f.print("#ifdef __cplusplus\nextern \"C\" {\n#endif /* __cplusplus */\n")


def end_extern_C(f):
    f.print("#ifdef __cplusplus\n}\n#endif /* __cplusplus */\n")


def print_note(f, b_complete=True):
    if b_complete:
        f.print("/*\n")
    else:
        f.print(" *\n")
    f.print(TECSMsg.get("note"))
    if b_complete:
        f.print(" */\n")
    else:
        f.print(" *\n")


def print_Makefile_note(f):
    f.print(TECSMsg.get("Makefile_note"))


def print_indent(f, n):
    f.print("    " * n)


@reopen(Namespace)
class _NamespaceGenerate:
    domain_gen_factory_list = {}
    class_gen_factory_list = {}

    def generate(self):
        dbgPrint("Namespace#generate: generating_region={} namespace={} gen_dir={}\n".format(
            G.generating_region.get_name(), self.name, G.gen))

        try:
            # root namespace ならば makefile を出力する(全セルタイプに関わるものだけ)
            # 先に出力する
            if self.name == "::":
                self.gen_makefile_template()
                self.gen_makefile_tecsgen()
                self.gen_cmake_tecsgen()
                if G.generating_region.get_n_cells() == 0:
                    dbgPrint("only makefile_template {}\n".format(self.name))
                    return

            # global_tecsgen.h (typedef, struct, const) の生成
            self.gen_global_header()

            # signature のコードを生成
            for s in self.signature_list:
                s.generate()

            # celltype のコードを生成
            for t in self.celltype_list:
                t.generate()

            # サブネームスペースのコードを生成
            for n in self.namespace_list:
                n.generate()

            # ドメインプラグインの gen_factory は、諸々のコードの出た後で呼び出す V1.8
            if type(self) is Region:
                if self.get_domain_type() is not None:
                    if Namespace.domain_gen_factory_list.get(G.generating_region) is None:
                        Namespace.domain_gen_factory_list[G.generating_region] = self
                        self.get_domain_type().gen_factory(G.generating_region)
                if self.get_class_type() is not None:
                    if Namespace.class_gen_factory_list.get(G.generating_region) is None:
                        Namespace.class_gen_factory_list[G.generating_region] = self
                        self.get_class_type().gen_factory(G.generating_region)

        except Exception as evar:
            # もしスタックトレースが出るまでい時間がかかるようならば、次をコメントアウトしてみるべし
            self.cdl_error("H1001 tecsgen: fatal internal error during code generation")
            print_exception(evar)

    def generate_post(self):
        if G.generating_region.get_n_cells() == 0:
            return

        try:
            # global_tecsgen.h (typedef, struct, const) の終わりのガードコード生成
            self.gen_global_header_post()

            # signature のコードを生成
            for s in self.signature_list:
                s.generate_post()

            # celltype のコードを生成
            for t in self.celltype_list:
                t.generate_post()

            # サブネームスペースのコードを生成
            for n in self.namespace_list:
                n.generate_post()

        except Exception as evar:
            self.cdl_error("H1002 tecsgen: fatal internal error during post code generation")
            print_exception(evar)

    def gen_global_header(self):
        dbgPrint("gen_global_header region={} $generating_region={}\n".format(
            self.name, G.generating_region.get_name()))
        # global_tecs.h の生成
        f = AppFile.open("{}/global_tecsgen.{}".format(G.gen, G.h_suffix))

        if self.name == "::":
            print_note(f)

            # ガードコードを出力
            f.print("#ifndef GLOBAL_TECSGEN_H\n#define GLOBAL_TECSGEN_H\n\n")

            # import_C で指定されたヘッダファイルの #include を出力
            if len(Import_C.get_header_list2()) > 0:
                # ヘッダ include の出力
                f.printf(TECSMsg.get("IMP_comment"), "#_IMP_#")
                for h in Import_C.get_header_list2():
                    f.printf("#include \"%s\"\n", h)
                f.printf("/**/\n\n")

            ifndef_macro_only(f)

        # typedef, struct, enum を生成
        for d in self.decl_list:
            # d は Typedef, StructType, EnumType のいずれか
            if type(d) is Typedef:
                # Typedef の場合、declarator の @type が　CType でないか
                if not isinstance(d.get_declarator().get_type(), CType):
                    d.gen_gh(f)
            elif not isinstance(d, CType):
                # CType ではない (StructType または EnumType)
                d.gen_gh(f)

        if self.name == "::":
            if G.ram_initializer:
                b_inline_only_or_proc = lambda ct: ct.need_CB_initializer()
                self.gen_celltype_names(f, "extern void ", "_CB_initialize();\n", True, b_inline_only_or_proc)
                self.gen_celltype_names(f, "extern void ", "_CB_initialize();\n", False, b_inline_only_or_proc)
                f.print("\n#define INITIALIZE_TECS() \\\n")
                self.gen_celltype_names(f, "\t", "_CB_initialize();\\\n", True, b_inline_only_or_proc)
                self.gen_celltype_names(f, "\t", "_CB_initialize();\\\n", False, b_inline_only_or_proc)
                f.print("/* INITIALIZE_TECS terminator */\n\n")
            else:
                f.print("\n#define INITIALIZE_TECS() \n")
            f.print("#define INITIALZE_TECSGEN() INITIALIZE_TECS()  /* for backward compatibility */\n\n")

            f.print("/* Descriptor for dynamic join */\n")
            f.print("#define Descriptor( signature_global_name )  DynDesc__ ## signature_global_name\n")
            f.print("#define is_descriptor_unjoined( desc )  ((desc).vdes==NULL)\n\n")
            endif_macro_only(f)

        # const を生成  mikan
        for d in self.const_decl_list:
            f.printf("#define %-14s ((%s%s)%s)\n",
                     d.get_global_name(),
                     d.get_type().get_type_str(),
                     d.get_type().get_type_str_post(),
                     d.get_initializer().eval_const2(None))

        f.close()

    def gen_global_header_post(self):
        # global_tecs.h を開く
        f = AppFile.open("{}/global_tecsgen.{}".format(G.gen, G.h_suffix))

        if self.name == "::":
            f.print("\n#endif /* GLOBAL_TECSGEN_H */\n")

        f.close()

    #=== Makefile.tecsgen, Makefile.templ, CMakeLists.tecsgen.cmake の出力
    # 全セルタイプ名を出力する部分を出力
    #    （本メソッドは root namespace に対して呼出す）
    #     個々のセルタイプのメークルールは Celltype クラスで出力
    def gen_makefile(self):
        self.gen_makefile_template()
        self.gen_makefile_tecsgen()
        self.gen_cmake_tecsgen()

    def gen_makefile_template(self):
        dbgPrint("gen_makefile_template: region={} generating_region={} gen={}\n".format(
            self.name, G.generating_region.get_name(), G.gen))

        if G.generate_no_template:
            return

        ### Makefile.templ の生成
        f = AppFile.open("{}/Makefile.templ".format(G.gen))
        print_Makefile_note(f)

        # Makefile の変数の出力
        f.printf(TECSMsg.get("MVAR_comment"), "#_MVAR_#")
        f.print("# fixed variable (unchangeable by config or plugin)\n")

        # TARGET の出力 (第一引数 $target に region 名および .exe を付加)
        target = G.target
        if G.generating_region != Namespace.root_namespace:
            # 子 region のリンクターゲットの場合
            target += "-{}".format(G.generating_region.get_global_name())

        f.print("TARGET_BASE = {}\n".format(target))

        if G.generating_region == Namespace.root_namespace:
            f.print("BASE_DIR = .\n")
            vpath_lead = ""
        else:
            f.print("BASE_DIR = ..\n")
            vpath_lead = "../"

        f.print("GEN_DIR = $(BASE_DIR)/{}\n".format(G.gen))

        f.print("INCLUDES =")
        search_path = G.import_path + TECSGEN.Makefile.get_search_path()
        for path in search_path:
            if TECSGEN.is_absolute_path(path):
                f.print(TECSGEN.subst_tecspath(" -I {}".format(path)))
            else:
                f.print(" -I $(BASE_DIR)/{}".format(path))
        f.print(" -I $(GEN_DIR)\n")
        f.print("DEFINES =")
        for define in G.define:
            f.print(" -D {}".format(define))
        f.print("\n\n")
        f.printf("# end of fixed variable (unchangeable by config or plugin)\n")

        vpath_add = ""
        for path in search_path:
            if path != ".":
                if TECSGEN.is_absolute_path(path):
                    vpath_add += " " + TECSGEN.subst_tecspath(path)
                else:
                    vpath_add += " " + vpath_lead + path
        objs_add = ""
        for obj in TECSGEN.Makefile.get_objs():
            objs_add += " " + obj
        var_add = ""
        for var in TECSGEN.Makefile.get_vars():
            var_add += "#" + rb.to_s(TECSGEN.Makefile.get_var_comment(var)) + "\n"
            var_add += var + " =" + " " + rb.to_s(TECSGEN.Makefile.get_var_val(var)) + "\n\n"
        pre_tecsgen_target = ""
        for t in TECSGEN.Makefile.get_pre_tecsgen_target():
            pre_tecsgen_target += " " + t
        post_tecsgen_target = ""
        for t in TECSGEN.Makefile.get_post_tecsgen_target():
            post_tecsgen_target += " " + t

        f.print("""{var_add}

# Pre-tecsgen target
PRE_TECSGEN_TARGET ={pre_tecsgen_target}

# Post-tecsgen target
POST_TECSGEN_TARGET ={post_tecsgen_target}

# vpath for C sources and headers
vpath %.{c_suffix} $(SRC_DIR) $(GEN_DIR) {vpath_add}
vpath %.{h_suffix} $(SRC_DIR) $(GEN_DIR) {vpath_add}

# Other objects (out of tecsgen)
OTHER_OBJS ={objs_add}                      # Add objects out of tecs care.
# OTHER_OBJS = $(_TECS_OBJ_DIR)vasyslog.o
""".format(
            var_add=var_add,
            pre_tecsgen_target=pre_tecsgen_target,
            post_tecsgen_target=post_tecsgen_target,
            c_suffix=G.c_suffix,
            h_suffix=G.h_suffix,
            vpath_add=vpath_add,
            objs_add=objs_add,
        ))

        # make ルールの出力
        f.printf(TECSMsg.get("MRUL_comment"), "#_MRUL_#")

        f.print("""allall: tecs
\tmake all     # in order to include generated Makefile.tecsgen & Makefile.depend

""")

        if G.generating_region.get_n_cells() != 0:
            all_target = "$(TARGET)"
        else:
            all_target = ""

        if G.generating_region == Namespace.root_namespace:
            if len(Region.get_link_roots()) > 1:
                all_target += " sub_regions"
            timestamp = " $(TIMESTAMP)"
        else:
            timestamp = ""

        f.print("all : {}\n\n".format(all_target))
        f.printf(TECSMsg.get("MDEP_comment"), "#_MDEP_#")
        f.print("-include $(GEN_DIR)/Makefile.tecsgen\n")
        if G.generating_region.get_n_cells() != 0:
            # Makefile.depend の include
            f.print("-include $(GEN_DIR)/Makefile.depend\n\n")

            f.print("$(TARGET) :{} $(CELLTYPE_COBJS) $(TECSGEN_COBJS) $(PLUGIN_COBJS) $(OTHER_OBJS)\n".format(timestamp))
            f.print("\t$(LD) -o $(TARGET) $(TECSGEN_COBJS) $(CELLTYPE_COBJS) $(PLUGIN_COBJS) $(OTHER_OBJS) $(LDFLAGS)\n\n")

        if len(Region.get_link_roots()) > 1 and G.generating_region == Namespace.root_namespace:
            f.print("\nsub_regions:$(TIMESTAMP)\n")
            for region in Region.get_link_roots():
                if region.get_global_name() != "":  # Root region: この Makefile 自身
                    f.print("\tcd {}; make all\n".format(region.get_global_name()))
            f.print("\n")

        # clean: ターゲット
        f.print("clean :\n")
        if G.generating_region == Namespace.root_namespace:
            for region in Region.get_link_roots():
                if region.get_global_name() != "":  # Root region: この Makefile 自身
                    f.print("\tcd {}; make clean\n".format(region.get_global_name()))
        f.print("\trm -f $(CELLTYPE_COBJS) $(TECSGEN_COBJS) $(PLUGIN_COBJS) $(OTHER_OBJS) $(TARGET) {}\n".format(timestamp))
        if G.generating_region == Namespace.root_namespace:
            f.print("\trm -rf $(GEN_DIR)\n")
        f.print("\n")

        # tecs: ターゲット
        if G.generating_region == Namespace.root_namespace:
            f.print("tecs : $(PRE_TECSGEN_TARGET) $(TIMESTAMP) $(POST_TECSGEN_TARGET)\n\n")
            f.print("$(TIMESTAMP) : $(TECS_IMPORTS)\n")
            f.print("\t$(TECSGEN) {}\n\n".format(TECSGEN.subst_tecspath(G.arguments, True)))
        else:
            f.print("tecs:\n")
            f.print("\t@echo \"run 'make tecs' in root region\"\n\n")

        # tecsflow:, tcflow ターゲット
        if G.generating_region.get_n_cells() != 0 or G.generating_region == Namespace.root_namespace:
            f.print("#####  TECSFlow targets  #####\n")

        if len(Region.get_link_roots()) > 1 and G.generating_region == Namespace.root_namespace:
            tecsflow_target = "tecsflow_sub"
            if G.generating_region.get_n_cells() > 0:
                f.print("tecsflow: tecs tecsflow_sub\n")
            else:
                f.print("tecsflow:\n")
            for region in Region.get_link_roots():
                if region.get_n_cells() > 0:
                    f.print("\tcd {}; make tecsflow\n".format(region.get_global_name()))
            f.print("\n")
        else:
            tecsflow_target = "tecsflow"

        if G.generating_region.get_n_cells() != 0:
            f.print("{} : $(GEN_DIR)/tecsgen.rbdmp tcflow\n".format(tecsflow_target))
            f.print("\ttecsflow -g $(GEN_DIR)\n\n")
            f.print("tecsflow_u : $(GEN_DIR)/tecsgen.rbdmp tcflow\n")
            f.print("\ttecsflow -g $(GEN_DIR) -U\n\n")
            f.print("$(GEN_DIR)/tecsgen.rbdmp : tecs\n\n")
            f.print("tcflow : tecs\n")
            f.print("\tmake tcflow_exec\n\n")
            f.print("tcflow_exec : $(GEN_DIR)/tcflow.rbdmp\n")
            f.print("$(GEN_DIR)/tcflow.rbdmp : $(CELLTYPE_SRCS) $(PLUGIN_CELLTYPE_SRCS)\n")
            f.print("\ttcflow -g $(GEN_DIR) -c '$(CC) -E -DTECSFLOW $(CFLAGS) -I ./' $^\n")
            f.print("\t# add -DTECSGEN if many errors occur, especially in case using cygwin, linux\n")

        if G.generating_region.get_n_cells() != 0 or G.generating_region == Namespace.root_namespace:
            f.print("#####  end TECSFlow targets  #####\n\n")

        # generic %.o : %.c
        f.print("# generic target for objs\n")
        f.print("$(_TECS_OBJ_DIR)%.o : %.{}\n".format(G.c_suffix))
        f.print("\t$(CC) -c $(CFLAGS) -o $@ $<\n\n")

        lines = TECSGEN.Makefile.get_lines()
        if len(lines) > 0:
            f.print("# additional lines\n")
            for line in lines:
                f.print(line)
            f.print("# end additional lines\n\n")

        f.close()

    def gen_makefile_tecsgen(self):
        ### Makefile.tecsgen の生成
        f = AppFile.open("{}/Makefile.tecsgen".format(G.gen))

        f.print("""# generated automatically by tecsgen.
# This file is not intended to modify.
#
# Makefile variables below are defined.
#  TECS_IMPORT_CDLS          .cdl files improted by import statement
#  SIGNATURE_HEADERS         .h files of signature
#  CELLTYPE_TECSGEN_HEADERS  .h files of celltype
#  CELLTYPE_FACTORY_HEADERS  .h files of celltype's factory
#  TECS_HEADERS              summary of .h files above
#  TECS_INLINE_HEADERS       .h files of celltype inline header
#  PLUGIN_INLINE_HEADERS     .h files of plugin generated inline header
#
#  TECS_COBJS                .o files of TECS
#                            = $(TECSGEN_COBJS)+$(PLUGIN_COBJS)+$(CELLTYPE_COBJS)
#                            = $(TECS_KERNEL_COBJS)+$(TECS_USER_COBJS)+$(TECS_OUTOFDOMAIN_COBJS)
#                            = $(TECSGEN_domain_COBJS)+$(PLUGIN_domain_COBJS)+$(CELLTYPE_domain_COBJS) for each domain
#
#  TECSGEN_COBJS             .o files of celltype_tecsgen.c
#  CELLTYPE_COBJS            .o files of celltype.c (celltype code)
#  PLUGIN_COBJS              .o files of plugin generated .c files
#
#  TECSGEN_SRCS              .c files of celltype_tecsgen.c
#  CELLTYPE_SRCS             .c files of celltype.c (celltype code)
#  PLUGIN_SRCS               .c files of plugin generated
#  PLUGIN_CELLTYPE_SRCS      .c files of plugin generated celltype.c (celltype code)
#  PLUGIN_TECSGEN_SRCS       .c files of plugin generated celltype_tecsgen.c
#
# Variables for domain (These are defined if domain is specified)
#  TECS_DOMAINS             domain names
#  TECS_KERNEL_COBJS        .o files of kernel domain (tecsgen, celltype, plugin)
#  TECS_USER_COBJS          .o files of user domain (tecsgen, celltype, plugin)
#  TECS_OUTOFDOMAIN_COBJS   .o files of OutOfDomain (tecsgen, celltype, plugin)
#  TECSGEN_domain_COBJS     .o files of celltype_tecsgen.c files for each domain
#  PLUGIN_domain_COBJS      .o files of plugin generated .c files for each domain
#  CELLTYPE_domain_COBJS    .o files of celltype.c files for each domain
#  TECSGEN_domain_SRCS      .c files of celltype_domain_tecsgen.c
#  PLUGIN_domain_SRCS       .c files of plugin generated .c files for each domain
#  CELLTYPE_domain_SRCS     .c files of celltype.c files for each domain

""")

        f.print("TECS_IMPORT_CDLS =")
        for cdl_expand_path, imp in Import.get_list().items():
            path = imp.get_cdl_path()
            if TECSGEN.is_absolute_path(path):
                path = TECSGEN.subst_tecspath(path)
            f.print(" ")
            f.print(path)
        f.print("\n")
        f.print("TECS_IMPORT_HEADERS =")
        for header, path in Import_C.get_header_list().items():
            if TECSGEN.is_absolute_path(path):
                path = TECSGEN.subst_tecspath(path)
            f.print(" ")
            f.print(path)
        f.print("\n")
        f.print("TECS_IMPORTS = $(TECS_IMPORT_CDLS) $(TECS_IMPORT_HEADERS)\n\n")

        f.print("SIGNATURE_HEADERS = \\\n")
        if G.generating_region.get_n_cells() != 0:
            for s in self.signature_list:
                f.print("\t$(GEN_DIR)/{}_tecsgen.{} \\\n".format(s.get_global_name(), G.h_suffix))
        f.print("# SIGNATURE_HEADERS terminator\n\n")

        def b_inline_only_or_proc(ct):
            return True

        f.print("CELLTYPE_TECSGEN_HEADERS = \\\n")
        self.gen_celltype_names(f, "\t$(GEN_DIR)/", "_tecsgen.h \\\n", True, b_inline_only_or_proc)
        self.gen_celltype_names(f, "\t$(GEN_DIR)/", "_tecsgen.h \\\n", False, b_inline_only_or_proc)
        f.print("# CELLTYPE_TECSGEN_HEADERS terminator\n\n")
        f.print("CELLTYPE_FACTORY_HEADERS = \\\n")
        self.gen_celltype_names(f, "\t$(GEN_DIR)/", "_factory.h \\\n", True, b_inline_only_or_proc)
        self.gen_celltype_names(f, "\t$(GEN_DIR)/", "_factory.h \\\n", False, b_inline_only_or_proc)
        f.print("# CELLTYPE_FACTORY_HEADERS terminator\n\n")
        f.print("# TECS_HEADERS:  headers generated by tecsgen\n")
        f.print("TECS_HEADERS = $(SIGNATURE_HEADERS) $(CELLTYPE_TECSGEN_HEADERS) $(CELLTYPE_FACTORY_HEADERS)\n\n")
        b_inline_only_or_proc = True
        f.print("TECS_INLINE_HEADERS = \\\n")
        self.gen_celltype_names(f, "\t", "_tecsgen.h \\\n", False, b_inline_only_or_proc)
        f.print("# TECS_INLINE_HEADERS terminator\n\n")
        f.print("PLUGIN_INLINE_HEADERS = \\\n")
        self.gen_celltype_names(f, "\t", "_tecsgen.h \\\n", True, b_inline_only_or_proc)
        f.print("# PLUGIN_INLINE_HEADERS terminator\n\n")

        ### set domain variables ###
        domain_type = None
        domain_regions = None
        dct = Celltype.get_domain_class_roots_total()
        # Ruby: .keys は空 Hash でも [] を返す（nil ではない）。
        # [][0] => nil となり has_domain? が true になる点まで合わせる。
        if dct is None:
            domain_regions = [G.generating_region]
        else:
            domain_regions = list(dct.keys())
        if G.debug:
            dbgPrint("domain_regions: ")
            for dr in domain_regions:
                dbgPrint("{} ".format(dr.get_name()))
            dbgPrint("\n")

        def has_domain():
            first = domain_regions[0] if domain_regions else None
            if len(domain_regions) > 1 or first != G.generating_region:
                return True
            return False

        def decide_domain_name(region):
            if region.is_root():
                if has_domain():
                    return "_Root_"
                return ""
            if has_domain():
                return "_{}".format(region.get_namespace_path().get_global_name())
            return ""

        f.print("# TECS_COBJS: all objects of TECS, include both user written code and tecsgen automatically generated code\n")
        f.print("TECS_COBJS = $(TECSGEN_COBJS) $(PLUGIN_COBJS) $(CELLTYPE_COBJS)\n\n")

        ### in case domain is used ###
        if has_domain():
            f.print("# TECS_DOMAINS: list of domain names (names of 'domain' spacified region)\n")
            f.print("TECS_DOMAINS = ")
            for r in domain_regions:
                if r.get_domain_root().get_domain_type() and \
                   r.get_domain_root().get_domain_type().get_option() != "OutOfDomain":
                    f.print(" {}".format(r.get_namespace_path().get_global_name()))
            f.print("\n")
            f.print("TECS_CLASS = ")
            for r in domain_regions:
                if r.get_class_root().get_class_type() and \
                   r.get_class_root().get_class_type().get_option() != "OutOfDomain":
                    f.print(" {}".format(r.get_namespace_path().get_global_name()))
            f.print("\n\n")

            f.print("# TECS_KERNEL_COBJS: objects belong to kernel domain\n")
            f.print("TECS_KERNEL_COBJS = \\\n")
            for r in domain_regions:
                if r.get_domain_root().get_domain_type() and \
                   r.get_domain_root().get_domain_type().get_kind() == Sym("kernel"):
                    nsp = decide_domain_name(r)
                    f.print("\t$(TECSGEN{}_COBJS) \\\n".format(nsp))
                    f.print("\t$(PLUGIN{}_COBJS) \\\n".format(nsp))
                    f.print("\t$(CELLTYPE{}_COBJS) \\\n".format(nsp))
            f.print("# TECS_KERNEL_COBJS terminator\n\n")

            f.print("# TECS_USER_COBJS: objects belong to user domain\n")
            f.print("TECS_USER_COBJS = \\\n")
            for r in domain_regions:
                if r.get_domain_root().get_domain_type() and \
                   r.get_domain_root().get_domain_type().get_kind() == Sym("user"):
                    nsp = decide_domain_name(r)
                    f.print("\t$(TECSGEN{}_COBJS) \\\n".format(nsp))
                    f.print("\t$(PLUGIN{}_COBJS) \\\n".format(nsp))
                    f.print("\t$(CELLTYPE{}_COBJS) \\\n".format(nsp))
            f.print("# TECS_USER_COBJS terminator\n\n")

            f.print("# TECS_OUTOFDOMAIN_COBJS: objects belong to OutOfDomain\n")
            f.print("TECS_OUTOFDOMAIN_COBJS = \\\n")
            for r in domain_regions:
                if r.get_domain_root().get_domain_type() and \
                   r.get_domain_root().get_domain_type().get_kind() == Sym("OutOfDomain"):
                    nsp = decide_domain_name(r)
                    f.print("\t$(TECSGEN{}_COBJS) \\\n".format(nsp))
                    f.print("\t$(PLUGIN{}_COBJS) \\\n".format(nsp))
                    f.print("\t$(CELLTYPE{}_COBJS) \\\n".format(nsp))
            f.print("# TECS_OUTOFDOMAIN_COBJS terminator\n\n")

            f.print("# TECSGEN_COBJS: objects from sources which are automatically generated by tecsgen\n")
            f.print("TECSGEN_COBJS = \\\n")
            for r in domain_regions:
                nsp = decide_domain_name(r)
                f.print("\t$(TECSGEN{}_COBJS) \\\n".format(nsp))
            f.print("# TECSGEN_COBJS terminator\n\n")

            f.print("# PLUGIN_COBJS: objects from sources which are automatically generated by plugin(s)\n")
            f.print("PLUGIN_COBJS = \\\n")
            for r in domain_regions:
                nsp = decide_domain_name(r)
                f.print("\t$(PLUGIN{}_COBJS) \\\n".format(nsp))
            f.print("# PLUGIN_COBJS terminator\n\n")

            f.print("CELLTYPE_COBJS = \\\n")
            for r in domain_regions:
                nsp = decide_domain_name(r)
                f.print("\t$(CELLTYPE{}_COBJS) \\\n".format(nsp))
            f.print("# CELLTYPE_COBJS terminator\n\n")

            f.print("TECSGEN_SRCS = \\\n")
            for r in domain_regions:
                nsp = decide_domain_name(r)
                f.print("\t$(TECSGEN{}_SRCS) \\\n".format(nsp))
            f.print("# TECSGEN_SRCS terminator\n\n")

            f.print("PLUGIN_SRCS = \\\n")
            for r in domain_regions:
                nsp = decide_domain_name(r)
                f.print("\t$(PLUGIN{}_SRCS) \\\n".format(nsp))
            f.print("# PLUGIN#_SRCS terminator\n\n")

        ###
        f.print("# TECSGEN_COBJS: objects from sources which are automatically generated by tecsgen\n")
        for r in domain_regions:
            nsp = decide_domain_name(r)
            f.print("TECSGEN{}_COBJS = \\\n".format(nsp))
            self.gen_celltype_names_domain(f, "\t$(_TECS_OBJ_DIR)", "_tecsgen.o \\\n", domain_type, r, False)
            f.print("# TECSGEN{}_COBJS terminator\n\n".format(nsp))

        f.print("# PLUGIN_COBJS: objects from sources which are automatically generated by plugin(s)\n")
        for r in domain_regions:
            nsp = decide_domain_name(r)
            f.print("PLUGIN{}_COBJS = \\\n".format(nsp))
            self.gen_celltype_names_domain(f, "\t$(_TECS_OBJ_DIR)", "_tecsgen.o \\\n", domain_type, r, True)
            self.gen_celltype_names_domain2(f, "\t$(_TECS_OBJ_DIR)", ".o \\\n", domain_type, r, True, False)
            f.print("# PLUGIN{}_COBJS terminator\n\n".format(nsp))

        f.print("# CELLTYPE_COBJS: objects of celltype code written by user\n")
        for r in domain_regions:
            nsp = decide_domain_name(r)
            f.print("CELLTYPE{}_COBJS = \\\n".format(nsp))
            self.gen_celltype_names_domain2(f, "\t$(_TECS_OBJ_DIR)", ".o \\\n", domain_type, r, False, False)
            f.print("# CELLTYPE{}_COBJS terminator\n\n".format(nsp))

        f.print("# TECSGEN_SRCS: sources automatically generated by tecsgen\n")
        for r in domain_regions:
            nsp = decide_domain_name(r)
            f.print("TECSGEN{}_SRCS = \\\n".format(nsp))
            self.gen_celltype_names_domain(f, "\t$(GEN_DIR)/", "_tecsgen.{} \\\n".format(G.c_suffix), domain_type, r, False)
            f.print("# TECSGEN{}_SRCS terminator\n\n".format(nsp))

        f.print("# PLUGIN_SRCS: sources automatically generated by plugin\n")
        f.print("PLUGIN_CELLTYPE_SRCS = \\\n")
        for r in domain_regions:
            nsp = decide_domain_name(r)
            f.print("  $(PLUGIN{}_CELLTYPE_SRCS)\\\n".format(nsp))
        f.print("# PLUGIN_CELLTYPE_SRCS terminator\n\n")
        f.print("PLUGIN_TECSGEN_SRCS = \\\n")
        for r in domain_regions:
            nsp = decide_domain_name(r)
            f.print("  $(PLUGIN{}_TECSGEN_SRCS)\\\n".format(nsp))
        f.print("# PLUGIN_TECSGEN_SRCS terminator\n\n")
        for r in domain_regions:
            nsp = decide_domain_name(r)
            f.print("PLUGIN{}_SRCS = $(PLUGIN{}_CELLTYPE_SRCS) $(PLUGIN{}_TECSGEN_SRCS)\n\n".format(nsp, nsp, nsp))
            f.print("PLUGIN{}_CELLTYPE_SRCS = \\\n".format(nsp))
            self.gen_celltype_names_domain2(f, "", ".{} \\\n".format(G.c_suffix), domain_type, r, True, False)
            f.print("# PLUGIN{}_CELLTYPE_SRCS terminator\n\n".format(nsp))
            nsp = decide_domain_name(r)
            f.print("PLUGIN{}_TECSGEN_SRCS = \\\n".format(nsp))
            self.gen_celltype_names_domain(f, "", "_tecsgen.{} \\\n".format(G.c_suffix), domain_type, r, True)
            f.print("# PLUGIN{}_TECSGEN_SRCS terminator\n\n".format(nsp))

        f.print("# CELLTYPE_SRCS: sources of celltype code written by user\n")
        f.print("CELLTYPE_SRCS = \\\n")
        self.gen_celltype_names(f, "\t", ".{} \\\n".format(G.c_suffix), False, False)
        f.print("# CELLTYPE_SRCS terminator\n\n")
        f.close()

    def cmake_normalize_path(self, path):
        path = re.sub(r"\s*\\\s*$", "", str(path).strip())
        #  Make 変数は is_absolute_path?（先頭 '$'）より先に CMake 変数へ置換する
        path = (path.replace("$(GEN_DIR)/", "${TECS_GEN_DIR}/")
                    .replace("$(GEN_DIR)", "${TECS_GEN_DIR}")
                    .replace("$(TECSPATH)", "${ASP3_TECSGEN_DIR}/tecs"))
        if path.startswith("${"):
            return path
        if TECSGEN.is_absolute_path(path):
            return TECSGEN.subst_tecspath(path).replace("\\", "/")
        return path

    def cmake_write_list(self, f, varname, items):
        f.print("set({}\n".format(varname))
        for item in rb.uniq(list(items)):
            f.print("    \"{}\"\n".format(self.cmake_normalize_path(item)))
        f.print(")\n\n")

    def collect_celltype_names(self, result, prepend, append, b_plugin, b_inline_only_or_proc=True):
        for ct in self.celltype_list:
            if not ct.need_generate():
                continue
            if b_inline_only_or_proc is False and ct.is_all_entry_inline() and not ct.is_active():
                continue
            if callable(b_inline_only_or_proc) and not b_inline_only_or_proc(ct):
                continue
            if (b_plugin and ct.get_plugin()) or (not b_plugin and not ct.get_plugin()):
                result.append("{}{}{}".format(prepend, ct.get_global_name(), append))
        for ns in self.namespace_list:
            ns.collect_celltype_names(result, prepend, append, b_plugin, b_inline_only_or_proc)

    def collect_celltype_names_domain(self, result, prepend, append, domain_type, region, b_plugin, b_inline_only=True):
        for ct in self.celltype_list:
            if not ct.need_generate():
                continue
            if b_inline_only is False and ct.is_all_entry_inline() and not ct.is_active():
                continue
            if (b_plugin and ct.get_plugin()) or (not b_plugin and not ct.get_plugin()):
                regions = list(ct.get_domain_class_roots2().keys())
                rdr = region
                if rdr in regions:
                    if rdr.is_root():
                        nsp = ""
                    else:
                        nsp = "_{}".format(region.get_namespace_path().get_global_name())
                    result.append("{}{}{}{}".format(prepend, ct.get_global_name(), nsp, append))
                elif rdr.is_link_root():
                    if len(regions) > 1:
                        result.append("{}{}{}{}".format(
                            prepend, ct.get_global_name(), rdr.get_up_global_name(), append))
        for ns in self.namespace_list:
            ns.collect_celltype_names_domain(
                result, prepend, append, domain_type, region, b_plugin, b_inline_only)

    def collect_celltype_names_domain2(self, result, prepend, append, domain_type, region, b_plugin, b_inline_only=True):
        for ct in self.celltype_list:
            if not ct.need_generate():
                continue
            if b_inline_only is False and ct.is_all_entry_inline() and not ct.is_active():
                continue
            if (b_plugin and ct.get_plugin()) or (not b_plugin and not ct.get_plugin()):
                regions = ct.get_domain_class_roots2()
                rdr = region
                if rdr in regions and len(regions) == 1:
                    result.append("{}{}{}".format(prepend, ct.get_global_name(), append))
                elif rdr.is_link_root():
                    if len(regions) > 1:
                        result.append("{}{}{}{}".format(
                            prepend, ct.get_global_name(), rdr.get_up_global_name(), append))
        for ns in self.namespace_list:
            ns.collect_celltype_names_domain2(
                result, prepend, append, domain_type, region, b_plugin, b_inline_only)

    def gen_cmake_tecsgen(self):
        f = AppFile.open("{}/CMakeLists.tecsgen.cmake".format(G.gen))

        f.print("""# generated automatically by tecsgen.
# included by cmake/Asp3Tecs.cmake (TECS_GEN_DIR must be set).

""")

        tecsgen_srcs = []
        plugin_tecsgen_srcs = []
        plugin_celltype_srcs = []
        celltype_srcs = []

        dct = Celltype.get_domain_class_roots_total()
        if dct is None:
            domain_regions = [G.generating_region]
        else:
            domain_regions = list(dct.keys())
        domain_type = None

        for r in domain_regions:
            self.collect_celltype_names_domain(
                tecsgen_srcs, "$(GEN_DIR)/", "_tecsgen.{}".format(G.c_suffix), domain_type, r, False)
            self.collect_celltype_names_domain(
                plugin_tecsgen_srcs, "$(GEN_DIR)/", "_tecsgen.{}".format(G.c_suffix), domain_type, r, True)
            self.collect_celltype_names_domain2(
                plugin_celltype_srcs, "", ".{}".format(G.c_suffix), domain_type, r, True, False)
            self.collect_celltype_names_domain2(
                celltype_srcs, "", ".{}".format(G.c_suffix), domain_type, r, False, False)

        import_cdls = []
        for cdl_expand_path, imp in Import.get_list().items():
            path = imp.get_cdl_path()
            if TECSGEN.is_absolute_path(path):
                path = TECSGEN.subst_tecspath(path)
            import_cdls.append(path)

        search_path = G.import_path + TECSGEN.Makefile.get_search_path()
        include_dirs = []
        for path in search_path:
            if TECSGEN.is_absolute_path(path):
                include_dirs.append(self.cmake_normalize_path(TECSGEN.subst_tecspath(path)))
            elif path == ".":
                include_dirs.append("${ASP3_SRCDIR}")
            else:
                include_dirs.append(
                    self.cmake_normalize_path("$(BASE_DIR)/{}".format(path)).replace(
                        "$(BASE_DIR)", "${ASP3_SRCDIR}"))
        include_dirs.append("${TECS_GEN_DIR}")
        include_dirs += [self.cmake_normalize_path(p) for p in TECSGEN.CMake.get_includes()]

        plugin_sources = TECSGEN.CMake.get_sources()

        self.cmake_write_list(f, "TECS_IMPORT_CDLS", import_cdls)
        self.cmake_write_list(f, "TECS_TECSGEN_SOURCES", tecsgen_srcs)
        self.cmake_write_list(f, "TECS_PLUGIN_TECSGEN_SOURCES", plugin_tecsgen_srcs)
        self.cmake_write_list(f, "TECS_PLUGIN_CELLTYPE_SOURCES", plugin_celltype_srcs)
        self.cmake_write_list(f, "TECS_CELLTYPE_SOURCES", celltype_srcs)
        self.cmake_write_list(f, "TECS_PLUGIN_EXTRA_SOURCES", plugin_sources)
        self.cmake_write_list(f, "TECS_INCLUDE_DIRS", rb.uniq(include_dirs))

        defines = [str(d) for d in G.define] + TECSGEN.CMake.get_defines()
        self.cmake_write_list(f, "TECS_COMPILE_DEFINITIONS", rb.uniq(defines))

        link_options = TECSGEN.CMake.get_link_options()
        if len(link_options) > 0:
            self.cmake_write_list(f, "TECS_LINK_OPTIONS", link_options)

        custom_commands = TECSGEN.CMake.get_custom_commands()
        if len(custom_commands) > 0:
            self.cmake_write_list(f, "TECS_CUSTOM_COMMANDS", custom_commands)

        lines = TECSGEN.CMake.get_lines()
        if len(lines) > 0:
            f.print("# plugin additional cmake lines\n")
            for line in lines:
                f.print(str(line))
                f.print("\n")
            f.print("\n")

        f.close()

    def gen_celltype_names(self, f, prepend, append, b_plugin, b_inline_only_or_proc=True):
        dbgPrint("gen_celltype_names {}\n".format(self.name))

        for ct in self.celltype_list:
            if not ct.need_generate():
                continue
            if b_inline_only_or_proc is False and ct.is_all_entry_inline() and not ct.is_active():
                continue
            # Ruby: Proc が偽ならスキップ。0 も Python では偽なので not で判定する
            # （need_CB_initializer は bool を返すが、他の Proc 互換のため）
            if callable(b_inline_only_or_proc) and not b_inline_only_or_proc(ct):
                continue
            if (b_plugin and ct.get_plugin()) or (not b_plugin and not ct.get_plugin()):
                f.print(" {}{}{}".format(prepend, ct.get_global_name(), append))

        for ns in self.namespace_list:
            ns.gen_celltype_names(f, prepend, append, b_plugin, b_inline_only_or_proc)

    def get_up_global_name(self):
        if self.is_root():
            return ""
        return "_{}".format(self.get_global_name())

    def gen_celltype_names_domain(self, f, prepend, append, domain_type, region, b_plugin, b_inline_only=True):
        dbgPrint("gen_celltype_names namespace={}\n".format(self.name))
        for ct in self.celltype_list:
            if not ct.need_generate():
                continue
            if b_inline_only is False and ct.is_all_entry_inline() and not ct.is_active():
                continue
            if (b_plugin and ct.get_plugin()) or (not b_plugin and not ct.get_plugin()):
                regions = list(ct.get_domain_class_roots2().keys())
                rdr = region
                if rdr in regions:
                    if rdr.is_root():
                        nsp = ""
                    else:
                        nsp = "_{}".format(region.get_namespace_path().get_global_name())
                    f.print(" {}{}{}{}".format(prepend, ct.get_global_name(), nsp, append))
                elif rdr.is_link_root():
                    if len(regions) > 1:
                        f.print(" {}{}{}{}".format(
                            prepend, ct.get_global_name(), rdr.get_up_global_name(), append))
        for ns in self.namespace_list:
            ns.gen_celltype_names_domain(
                f, prepend, append, domain_type, region, b_plugin, b_inline_only)

    def gen_celltype_names_domain2(self, f, prepend, append, domain_type, region, b_plugin, b_inline_only=True):
        dbgPrint("gen_celltype_names {}\n".format(self.name))
        for ct in self.celltype_list:
            if not ct.need_generate():
                continue
            if b_inline_only is False and ct.is_all_entry_inline() and not ct.is_active():
                continue
            if (b_plugin and ct.get_plugin()) or (not b_plugin and not ct.get_plugin()):
                regions = ct.get_domain_class_roots2()
                rdr = region
                if rdr in regions and len(regions) == 1:
                    f.print(" {}{}{}".format(prepend, ct.get_global_name(), append))
                elif rdr.is_link_root():
                    if len(regions) > 1:
                        f.print(" {}{}{}{}".format(
                            prepend, ct.get_global_name(), rdr.get_up_global_name(), append))
        for ns in self.namespace_list:
            ns.gen_celltype_names_domain2(
                f, prepend, append, domain_type, region, b_plugin, b_inline_only)

    def travers_all_signature(self, proc=None):
        for sig in self.signature_list:
            proc(sig)
        for ns in self.namespace_list:
            ns.travers_all_signature_proc(proc)

    def travers_all_signature_proc(self, proc):
        for sig in self.signature_list:
            proc(sig)
        for ns in self.namespace_list:
            ns.travers_all_signature_proc(proc)

    def travers_all_celltype(self, proc=None):
        for ct in self.celltype_list:
            proc(ct)
        for ns in self.namespace_list:
            ns.travers_all_celltype_proc(proc)

    def travers_all_celltype_proc(self, proc):
        for ct in self.celltype_list:
            proc(ct)
        for ns in self.namespace_list:
            ns.travers_all_celltype_proc(proc)


@reopen(Typedef)
class _TypedefGenerate:
    def gen_gh(self, f):
        f.printf("typedef %-14s %s%s;\n",
                 self.declarator.get_type().get_type_str(),
                 self.declarator.get_name(),
                 self.declarator.get_type().get_type_str_post())


@reopen(StructType)
class _StructTypeGenerate:
    def gen_gh(self, f):
        if not self.b_define:
            return
        f.print("struct {} {{\n".format(self.tag))
        for i in self.members_decl.get_items():
            f.printf("                %-14s %s%s;\n",
                     i.get_type().get_type_str(),
                     i.get_name(),
                     i.get_type().get_type_str_post())
        f.print("};\n")


@reopen(Signature)
class _SignatureGenerate:
    def generate(self):
        self.generate_signature_header()

    def generate_post(self):
        self.generate_signature_header_post()

    def generate_signature_header(self):
        dbgPrint("generate_signature_header signature={} generating_region={}\n".format(
            self.name, G.generating_region.get_name()))
        f = AppFile.open("{}/{}_tecsgen.{}".format(G.gen, self.global_name, G.h_suffix))

        print_note(f)
        self.gen_sh_guard(f)
        self.gen_sh_info(f)
        self.gen_sh_include(f)

        ifndef_macro_only(f)
        self.gen_sh_func_tab(f)
        endif_macro_only(f)
        self.gen_sh_func_id(f)

        f.close()

    def generate_signature_header_post(self):
        f = AppFile.open("{}/{}_tecsgen.{}".format(G.gen, self.global_name, G.h_suffix))
        self.gen_sh_endif(f)
        f.close()

    def gen_sh_guard(self, f):
        f.print("#ifndef {}_TECSGEN_H\n".format(self.global_name))
        f.print("#define {}_TECSGEN_H\n\n".format(self.global_name))

    def gen_sh_info(self, f):
        f.print("/*\n * signature   :  {}\n * global name :  {}\n * context     :  {}\n */\n\n".format(
            self.name, self.global_name, self.get_context()))

    def gen_sh_include(self, f):
        dl = self.get_descriptor_list()
        if len(dl) > 0:
            f.printf(TECSMsg.get("SDI_comment"), "#_SDI_#")
            for dt, param in dl.items():
                f.print(
                    "/* pre-typedef incomplete-type to avoid error in case of mutual or cyclic reference */\n"
                    "#ifndef Descriptor_of_{0}_Defined\n"
                    "#define  Descriptor_of_{0}_Defined\n"
                    "typedef struct {{ struct tag_{0}_VDES *vdes; }} Descriptor( {0} );\n"
                    "#endif\n".format(dt.get_global_name()))
            f.print("\n")

    def gen_sh_func_tab(self, f):
        f.printf(TECSMsg.get("SD_comment"), "#_SD_#")
        f.print("struct tag_{}_VDES {{\n".format(self.global_name))
        f.print("    struct tag_{}_VMT *VMT;\n".format(self.global_name))
        f.print("};\n\n")

        f.printf(TECSMsg.get("SFT_comment"), "#_SFT_#")
        f.print("struct tag_{}_VMT {{\n".format(self.global_name))
        for fun in self.get_function_head_array():
            f.print("    ")
            functype = fun.get_declarator().get_type()
            f.printf("%-14s", functype.get_type_str())
            f.print(" (*{}__T)(".format(fun.get_name()))
            if not getattr(self, "singleton", False):
                f.print(" const struct tag_{}_VDES *edp".format(self.global_name))
            paramlist = functype.get_paramlist()
            if paramlist:
                items = paramlist.get_items()
            else:
                items = []
            for param in items:
                f.print(", ")
                f.print(param.get_type().get_type_str())
                f.print(" ")
                f.print(param.get_name())
                f.print(param.get_type().get_type_str_post())
            f.print(" );\n")
        if len(self.get_function_head_array()) == 0:
            f.print("    void   (*dummy__)(void);\n")
        f.print("};\n\n")
        f.printf(TECSMsg.get("SDES_comment"), "#_SDES_#")
        f.print(
            "#ifndef Descriptor_of_{0}_Defined\n"
            "#define  Descriptor_of_{0}_Defined\n"
            "typedef struct {{ struct tag_{0}_VDES *vdes; }} Descriptor( {0} );\n"
            "#endif\n".format(self.global_name))

    def gen_sh_func_id(self, f):
        f.print("/* function id */\n")
        for fun in self.get_function_head_array():
            f.printf("#define\tFUNCID_%-31s (%d)\n",
                     "{}_{}".format(self.global_name, fun.get_name()).upper(),
                     self.get_id_from_func_name(fun.get_name()))
        f.print("\n")

    def gen_sh_endif(self, f):
        f.print("#endif /* {}_TECSGEN_H */\n".format(self.global_name))


@reopen(Region)
class _RegionGenerate:
    def gen_region_str_pre(self, f):
        nest = 1
        while nest < len(self.family_line):
            f.print("  " * (nest - 1))
            f.print("region {} {{\n".format(self.family_line[nest].get_name()))
            nest += 1
        return nest - 1

    def gen_region_str_post(self, f):
        nest = len(self.family_line) - 1
        while nest >= 1:
            f.print("  " * (nest - 1))
            f.print("};\n")
            nest -= 1
        return nest - 1


@reopen(DomainType)
class _DomainTypeGenerate:
    def gen_factory(self, node_root):
        self.plugin.gen_factory(node_root)


@reopen(ClassType)
class _ClassTypeGenerate:
    def gen_factory(self, node_root):
        self.plugin.gen_factory(node_root)


# Celltype 生成（generate.rb の最大部分）— 機械変換＋手直し対象
try:
    import tecslib.core.generate_celltype  # noqa: F401
except SyntaxError:
    pass
