# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2017-2018 by TOPPERS Project
#
#   このファイルは tecsgen (Ruby 版) の tecslib/plugin/TECSInfoPlugin.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．
#
#   $Id: TECSInfoPlugin.rb 3159 2020-07-05 10:25:24Z okuma-top $
#

from tecslib.core import globals as G
from tecslib.core.toplevel import dbgPrint
from tecslib.rubylib.symbol import Sym

from tecslib.plugin.CelltypePlugin import CelltypePlugin


#== CelltypePlugin for tTECSInfo
class TECSInfoPlugin(CelltypePlugin):

    cell_list = []
    #@celltype::Celltype
    #@plugin_arg_str::String
    #@plugin_arg_list::{argNameString=>argOptionString}
    #@cell_list::[Cell]

    #celltype::     Celltype        セルタイプ（インスタンス）
    def __init__(self, celltype, option):
        super().__init__(celltype, option)
        if G.unopt_entry is False:
            self.cdl_info("TIF0001 forcely set --unoptimize-entry by TECSInfoPlugin (by importing TECSInfo.cdl)")
            G.unopt_entry = True

    #=== 新しいセル
    #cell::        Cell            セル
    #
    # celltype プラグインを指定されたセルタイプのセルが生成された
    # セルタイププラグインに対する新しいセルの報告
    def new_cell(self, cell):
        TECSInfoPlugin.cell_list.append(cell)

        # AppFile は、重ね書きようなので、やめる
        # p "import: cell nTECSInfo::tTECSInfoSub #{cell.get_namespace_path.to_s} under #{cell.get_region.get_name}"
        # cell.show_tree 0
        # TECSInfoSub セルのプロトタイプ宣言
        from tecslib.core.componentobj.import_ import Import

        from tecslib.core.plugin import CFile

        fn = "{}/tmp_{}_TECSInfoSub.cdl".format(G.gen, cell.get_region().get_global_name())
        f = CFile.open(fn, "w")
        f.print("/* prototype declaration of TECSInfoSub */\n")
        nest = cell.get_region().gen_region_str_pre(f)
        indent = "    " * nest
        f.print(
            "{indent}[in_through()]\n"
            "{indent}region rTECSInfo {{\n"
            "{indent}    cell nTECSInfo::tTECSInfoSub TECSInfoSub;\n"
            "{indent}}}; /* rTECSInfo */\n".format(indent=indent))
        cell.get_region().gen_region_str_post(f)
        f.close()
        Import(fn)

        # セルに cTECSInfo の結合があるか？
        if cell.get_join_list().get_item(Sym("cTECSInfo")) is None:
            # cTECSInfo = rTECSInfo::TECSInfosub.eTECSInfo; の追加
            from tecslib.core.componentobj.namespacepath import NamespacePath
            from tecslib.core.expression import Expression
            from tecslib.core.componentobj.join import Join

            nsp = NamespacePath(Sym("rTECSInfo"), False)
            nsp.append_bang(Sym("TECSInfoSub"))
            rhs = Expression.create_cell_join_expression(nsp, None, Sym("eTECSInfo"))
            join = Join(Sym("cTECSInfo"), None, rhs)
            # Ruby Cell#new_join（インスタンス）。classmethod new_join は current_object 経由
            cell.new_join_inst(join)

    #=== tCelltype_factory.h に挿入するコードを生成する
    # file 以外の他のファイルにファクトリコードを生成してもよい
    # セルタイププラグインが指定されたセルタイプのみ呼び出される
    def gen_factory(self, file):
        from tecslib.core.generate import AppFile
        from tecslib.core.componentobj.namespace import Namespace
        from tecslib.core.componentobj.region import Region

        with open("{}/include_all_signature_header.h".format(G.gen), "w", encoding="utf-8") as f:
            f.write(
                "#ifndef include_all_signature_header_h\n"
                "#define include_all_signature_header_h\n\n")
            Namespace.get_root().travers_all_signature(
                lambda sig: f.write("#include \"{}_tecsgen.h\"\n".format(sig.get_global_name())))
            f.write("\n#endif /* include_all_signature_header_h */\n")

        undefs2 = ["INITIALIZE_CB", "FOREACH_CELL", "END_FOREACH_CELL"]
        f = AppFile.open("{}/nTECSInfo_tVarDeclInfo_factory.h".format(G.gen))
        Namespace.get_root().print_struct_define(f)

        undefs = ["VALID_IDX", "GET_CELLCB", "CELLCB", "CELLIDX",
                  "tVarDeclInfo_IDX", "ATTR_name", "ATTR_sizeIsExpr",
                  "ATTR_declType", "ATTR_offset", "FOREACH_CELL"]

        f.print(
            "\n\n/***** Offset of attr & var of celltype  *****/\n"
            "#define TOPPERS_CB_TYPE_ONLY\n\n"
            "/* In case a celltype has 'inline' entry,\n"
            " * some macros are temporally defined\n"
            " * even if TOPPERS_CB_TYPE_ONLY is defined.\n"
            " * To avoid redefinition warning, undef these macros.\n"
            " */\n")
        for u in undefs:
            f.print("#undef {}\n".format(u))
        if G.ram_initializer:
            for u in undefs2:
                f.print("#undef {}\n".format(u))
        Namespace.get_root().print_celltype_define_offset(f)
        f.print(
            "\n\n/* redefine macros */\n"
            "#define tVarDeclInfo_IDX  nTECSInfo_tVarDeclInfo_IDX\n\n")
        if G.ram_initializer:
            f.print(
                "#define FOREACH_CELL(i,p_cb)   { (void)(i);\n"
                "#define END_FOREACH_CELL   }\n"
                "#define INITIALIZE_CB(p_that)   (void)(p_that);\n"
                "#define SET_CB_INIB_POINTER(i,p_that)\n")
        f.close()

        undefs = ["N_CP_cEntryInfo", "NCP_cEntryInfo", "N_CP_cCallInfo", "NCP_cCallInfo",
                  "N_CP_cAttrInfo", "NCP_cAttrInfo", "N_CP_cVarInfo", "NCP_cVarInfo",
                  "VALID_IDX", "GET_CELLCB", "CELLCB", "CELLIDX", "ATTR_name", "ATTR_b_singleton",
                  "ATTR_b_IDX_is_ID_act", "ATTR_sizeOfCB", "ATTR_sizeOfINIB", "ATTR_n_cellInLinUnit",
                  "ATTR_n_cellInSystem", "cEntryInfo_getName", "cEntryInfo_getNameLength",
                  "cEntryInfo_getSignatureInfo", "cEntryInfo_getArraySize", "cEntryInfo_isInline",
                  "cCallInfo_getName", "cCallInfo_getNameLength", "cCallInfo_getSignatureInfo",
                  "cCallInfo_getArraySize", "cCallInfo_getSpecifierInfo", "cCallInfo_getInternalInfo",
                  "cCallInfo_getLocationInfo", "cCallInfo_getOptimizeInfo", "cAttrInfo_getName",
                  "cAttrInfo_getOffset", "cAttrInfo_getTypeInfo", "cAttrInfo_getSizeIsExpr",
                  "cAttrInfo_getSizeIs", "cVarInfo_getName", "cVarInfo_getOffset", "cVarInfo_getTypeInfo",
                  "cVarInfo_getSizeIsExpr", "cVarInfo_getSizeIs", "cEntryInfo_refer_to_descriptor",
                  "cEntryInfo_ref_desc", "cCallInfo_refer_to_descriptor", "cCallInfo_ref_desc",
                  "cAttrInfo_refer_to_descriptor", "cAttrInfo_ref_desc", "cVarInfo_refer_to_descriptor",
                  "cVarInfo_ref_desc", "is_cEntryInfo_joined", "is_cCallInfo_joined",
                  "is_cAttrInfo_joined", "is_cVarInfo_joined", "eCelltypeInfo_getName",
                  "eCelltypeInfo_getNameLength", "eCelltypeInfo_getNAttr", "eCelltypeInfo_getAttrInfo",
                  "eCelltypeInfo_getNVar", "eCelltypeInfo_getVarInfo", "eCelltypeInfo_getNCall",
                  "eCelltypeInfo_getCallInfo", "eCelltypeInfo_getNEntry", "eCelltypeInfo_getEntryInfo",
                  "eCelltypeInfo_isSingleton", "eCelltypeInfo_isIDX_is_ID", "eCelltypeInfo_hasCB",
                  "eCelltypeInfo_hasINIB", "FOREACH_CELL", "END_FOREACH_CELL", "INITIALIZE_CB"]

        f = AppFile.open("{}/nTECSInfo_tCelltypeInfo_factory.h".format(G.gen))
        for u in undefs:
            f.print("#undef {}\n".format(u))
        f.print("#define TOPPERS_CB_TYPE_ONLY\n")
        Namespace.get_root().print_celltype_define(f)
        # FOREACH_CELL を出しなおす
        ct = Namespace.find(["::", Sym("nTECSInfo"), Sym("tCelltypeInfo")])
        ct.gen_ph_foreach_cell(f)
        ct.gen_ph_cb_initialize_macro(f)
        f.print("\n")
        f.close()

        undefs = ["VALID_IDX", "GET_CELLCB", "CELLCB", "CELLIDX",
                  "tCallInfo_IDX", "ATTR_name", "ATTR_offset", "ATTR_b_inCB",
                  "ATTR_b_optional", "ATTR_b_omit", "ATTR_b_dynamic",
                  "ATTR_b_ref_desc", "ATTR_b_allocator_port",
                  "ATTR_b_require_port", "ATTR_b_VMT_useless",
                  "ATTR_b_skelton_useless", "ATTR_b_cell_unique",
                  "cSignatureInfo_getName", "cSignatureInfo_getNameLength",
                  "cSignatureInfo_getNFunction",
                  "cSignatureInfo_getFunctionInfo",
                  "cSignatureInfo_refer_to_descriptor",
                  "cSignatureInfo_ref_desc", "eCallInfo_getName",
                  "eCallInfo_getNameLength", "eCallInfo_getSignatureInfo",
                  "eCallInfo_getArraySize", "eCallInfo_isOptional",
                  "eCallInfo_isDynamic", "eCallInfo_isRefDesc",
                  "eCallInfo_isOmit", "FOREACH_CELL"]

        f = AppFile.open("{}/nTECSInfo_tCallInfo_factory.h".format(G.gen))
        f.print(
            "\n\n/***** Offset of attr & var of celltype  *****/\n"
            "#define TOPPERS_CB_TYPE_ONLY\n\n"
            "/* In case a celltype has 'inline' entry,\n"
            " * some macros are temporally defined\n"
            " * even if TOPPERS_CB_TYPE_ONLY is defined.\n"
            " * To avoid redefinition warning, undef these macros.\n"
            " */\n")
        for u in undefs:
            f.print("#undef {}\n".format(u))
        if G.ram_initializer:
            for u in undefs2:
                f.print("#undef {}\n".format(u))

        Namespace.get_root().print_call_define(f)
        f.print(
            "\n\n/* redefine macros */\n"
            "#define tCallInfo_IDX  nTECSInfo_tCallInfo_IDX\n\n")
        if G.ram_initializer:
            f.print(
                "#define FOREACH_CELL(i,p_cb)   { (void)(i);\n"
                "#define END_FOREACH_CELL   }\n"
                "#define INITIALIZE_CB(p_that)   (void)(p_that);\n"
                "#define SET_CB_INIB_POINTER(i,p_that)\n\n")
        f.close()

        f = AppFile.open("{}/nTECSInfo_tEntryInfo_factory.h".format(G.gen))
        Namespace.get_root().print_entry_define(f)
        f.close()

        undefs = ["GET_CELLCB", "CELLCB", "CELLIDX", "ATTR_name", "INITIALIZE_CB", "FOREACH_CELL"]
        f = AppFile.open("{}/nTECSInfo_tCellInfo_factory.h".format(G.gen))
        for u in undefs:
            f.print("#undef {}\n".format(u))
        Region.get_root().print_cell_define(f)
        # FOREACH_CELL を出しなおす
        ct = Namespace.find(["::", Sym("nTECSInfo"), Sym("tCellInfo")])
        ct.gen_ph_foreach_cell(f)
        ct.gen_ph_cb_initialize_macro(f)
        f.close()

        f = AppFile.open("{}/nTECSInfo_tRawEntryDescriptorInfo_factory.h".format(G.gen))
        Region.get_root().print_entry_descriptor_define(f)
        f.close()

    #=== 後ろの CDL コードを生成
    #プラグインの後ろの CDL コードを生成
    #file:: File:
    @classmethod
    def gen_post_code(cls, file):
        from tecslib.core.bnf import Generator
        from tecslib.core.tecsinfo import TECSInfo

        if Generator.get_n_error() > 0:
            Generator.info("I9999 TECSInfoPlugin does not generate TECSInfo code because of early error")
            return
        # 複数のプラグインの post_code が一つのファイルに含まれるため、以下のような見出しをつけること
        file.print("/*------------ {} post code ------------*/\n".format(cls.__name__))
        for cell in TECSInfoPlugin.cell_list:
            root = cell.get_region()  # .get_link_root
            TECSInfo.print_info(file, root)

    @classmethod
    def get_post_code_priority(cls):
        from tecslib.core.plugin_module import PluginModule
        prio = PluginModule.SIGNATURE_PLUGIN_POST_CODE_PRIORITY + 1000
        dbgPrint("TECSInfoPlugin: get_post_code_priority: {}\n".format(prio))
        return prio
