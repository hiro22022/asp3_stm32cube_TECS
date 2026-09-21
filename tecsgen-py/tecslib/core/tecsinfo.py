# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2017-2018 by TOPPERS Project
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/tecsinfo.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．
#
#   $Id: tecsinfo.rb 2850 2018-04-01 12:38:45Z okuma-top $
#

# TECS 情報セルの生成
from tecslib.core.componentobj.cell import Cell
from tecslib.core.componentobj.celltype import Celltype
from tecslib.core.componentobj.namespace import Namespace
from tecslib.core.componentobj.port import Port
from tecslib.core.componentobj.region import Region
from tecslib.core.componentobj.signature import Signature
from tecslib.core.syntaxobj.decl import Decl
from tecslib.core.syntaxobj.funchead import FuncHead
from tecslib.core.syntaxobj.paramdecl import ParamDecl
from tecslib.core.toplevel import dbgPrint
from tecslib.core.types import (
    ArrayType,
    DefinedType,
    DescriptorType,
    FuncType,
    PtrType,
    StructType,
    Type,
)
from tecslib.rubylib.rb import to_s
from tecslib.rubylib.symbol import Sym


class TECSInfo:
    # region は Link root のこと
    @staticmethod
    def print_info(f, region):
        # p "region: "+ region.get_name.to_s
        nest = region.gen_region_str_pre(f)
        indent0 = "    " * nest
        indent = "    " * (nest + 1)
        f.print("""{0}region rTECSInfo {{
""".format(indent0))
        Type.reset_print_info()

        # mikan 全部生成するのではなく、region 下のセルのセルタイプと、そこから参照されるシグニチャ、セルタイプに限定して出力すべき
        # しかし、意味解析後に出力するため、これは容易ではない．最適化とコード生成は、リンクルートごとに行われる．
        Namespace.print_info(f, indent)
        region.get_link_root().print_info(f, indent)

        f.print("\n{}/*** TYPE information cell ***/\n".format(indent))
        Type.print_info_post(f, indent)

        f.print("\n{}/*** TECS information cell ***/\n".format(indent))
        f.print("""{0}cell nTECSInfo::tTECSInfoSub TECSInfoSub {{
{0}    cNamespaceInfo = _RootNamespaceInfo.eNamespaceInfo;
{0}    cRegionInfo    = _LinkRootRegionInfo.eRegionInfo;
{0}}} /* TECSInfoSub */;
{1}}}; /* rTECSInfo */
""".format(indent, indent0))
        region.gen_region_str_post(f)


# === Namespace (tecsinfo.rb class reopen) ===

def _namespace_print_info_ns_sub(self, f, indent):
    # RootRegion と LinkRegion は同じ Region クラスのオブジェクトである
    # 子ネームスペースは Namespace クラスの、子リージョンは Region クラスのオブジェクトである
    # これは、意味解析段階で呼び出されるため、リンクユニットごとに出しわけることができない
    # 出しわけるには、2パスにする必要がある
    if self.name == "::":
        name = "_Root"
    else:
        name = self.global_name
    f.print("\n{}/*** {} namespace information cell ***/\n".format(
        indent, self.get_namespace_path()))
    f.print("""{0}cell nTECSInfo::tNamespaceInfo {1}NamespaceInfo{{
{0}    name = "{2}";
""".format(indent, name, to_s(self.name)))
    if len(self.signature_list) > 0:
        f.print("\n{}    /* SIGNATURE info */\n".format(indent))
    for sig in self.signature_list:
        f.print("""{0}    cSignatureInfo[] = {1}SignatureInfo.eSignatureInfo;
""".format(indent, sig.get_global_name()))
    if len(self.celltype_list) > 0:
        f.print("\n{}    /* CELLTYPE info */\n".format(indent))
    for ct in self.celltype_list:
        if len(ct.get_cell_list()) > 0:
            f.print("""{0}    cCelltypeInfo[] = {1}CelltypeInfo.eCelltypeInfo;
""".format(indent, ct.get_global_name()))
    if len(self.namespace_list) > 0:
        f.print("\n{}    /* NAMESPACE info */\n".format(indent))
    for ns in self.namespace_list:
        if type(ns) is Namespace:   # region を含めない
            f.print("""{0}    cNamespaceInfo[] = {1}NamespaceInfo.eNamespaceInfo;
""".format(indent, ns.get_global_name()))
    f.print("{0}}};   /* cell nTECSInfo::tNamespaceInfo {1}NamespaceInfo */\n".format(indent, name))


def _namespace_print_info_ns(self, f, indent):
    # p "print_info: #{self.get_global_name}"
    self.print_info_ns_sub(f, indent)
    for sig in self.signature_list:
        sig.print_info(f, indent)
    for ct in self.celltype_list:
        if len(ct.get_cell_list()) > 0:
            ct.print_info(f, indent)
    for ns in self.namespace_list:
        if type(ns) is Namespace:   # region を含めない
            ns.print_info_ns(f, indent)


def _namespace_print_info(f, indent):
    Namespace.get_root().print_info_ns(f, indent)


def _namespace_print_struct_define(self, f):
    f.print("\n/***** Offset of members of structures  *****/\n")
    for tag in self.struct_tag_list.get_items():
        # print "sttype: #{tag.get_name} #{sttype}\n"
        for decl in tag.get_members_decl().get_items():
            f.print("#define OFFSET_OF_{:<30}  ({})\n".format(
                "{}_{}".format(tag.get_ID_str(), decl.get_name()),
                "(uint32_t)(intptr_t)&((({}{}*)0)->{})".format(
                    tag.get_type_str(), tag.get_type_str_post(), decl.get_name())))
            f.print("#define PLACE_OF_{:<30}  ({})\n".format(
                "{}_{}".format(tag.get_ID_str(), decl.get_name()),
                "VARDECL_PLACE_STRUCT"))


def _namespace_print_celltype_define_offset(self, f):
    for ct in self.celltype_list:
        if len(ct.get_cell_list()) > 0:
            ct.print_define_offset(f)
    for ns in self.namespace_list:
        if type(ns) is Namespace:   # region を含めない
            ns.print_celltype_define_offset(f)


def _namespace_print_celltype_define(self, f):
    for ct in self.celltype_list:
        if len(ct.get_cell_list()) > 0:
            ct.print_celltype_define(f)
    for ns in self.namespace_list:
        if type(ns) is Namespace:   # region を含めない
            ns.print_celltype_define(f)


def _namespace_print_call_define(self, f):
    for ct in self.celltype_list:
        if len(ct.get_cell_list()) > 0:
            ct.print_call_define(f)
    for ns in self.namespace_list:
        if type(ns) is Namespace:   # region を含めない
            ns.print_call_define(f)


def _namespace_print_entry_define(self, f):
    for ct in self.celltype_list:
        if len(ct.get_cell_list()) > 0:
            ct.print_entry_define(f)
    for ns in self.namespace_list:
        if type(ns) is Namespace:   # region を含めない
            ns.print_entry_define(f)


# === Region ===

def _region_print_info_region_sub(self, f, indent):
    if self.get_link_root() is self:
        name = "_LinkRoot"
    else:
        name = self.global_name
    # p "region:#{get_name}"
    f.print("\n{}/*** {} region information cell ***/\n".format(
        indent, self.get_namespace_path()))
    f.print("""{0}cell nTECSInfo::tRegionInfo {1}RegionInfo{{
{0}    name = "{2}";
""".format(indent, name, to_s(self.name)))
    for cell in self.cell_list:
        # print "cell class="+cell.get_celltype.class.name+", " + cell.get_celltype.get_name.to_s + " 1\n"
        if not cell.exclude_info():
            # print "cell class="+cell.get_celltype.class.name+", " + cell.get_celltype.get_name.to_s + " 2\n"
            f.print("{}    cCellInfo[] = {}CellInfo.eCellInfo;\n".format(
                indent, cell.get_global_name()))
    for region in self.namespace_list:
        if type(region) is Region:
            f.print("{}    cRegionInfo[] = {}RegionInfo.eRegionInfo;\n".format(
                indent, region.get_global_name()))
    f.print("{}}};\n".format(indent))
    for cell in self.cell_list:
        if not cell.exclude_info():
            cell.print_info(f, indent)


def _region_print_info_region(self, f, indent):
    self.print_info_region_sub(f, indent)
    for region in self.namespace_list:
        if type(region) is Region:
            region.print_info_region(f, indent)


def _region_print_info(self, f, indent):
    # p "print_info: #{self.get_global_name}"
    self.print_info_region(f, indent)


def _region_get_region(self, visitor=None):
    if visitor:
        visitor(self)
    for ns in self.namespace_list:
        if type(ns) is Region:
            ns.get_region(visitor)


def _region_print_cell_define_offset(self, f):
    # mikan: Ruby tecsgen 本体にもメソッド定義がなく、tecsinfo.rb からのみ参照される
    pass


def _region_print_cell_define(self, f):
    ct_list = {}
    for cell in self.cell_list:
        if cell.exclude_info_factory():
            continue
        ct_list[cell.get_celltype()] = True
    f.print("#define TOPPERS_CB_TYPE_ONLY\n")
    for ct in ct_list:
        f.print("#include \"{}_tecsgen.h\"\n".format(ct.get_global_name()))
    f.print("\n")
    for cell in self.cell_list:
        if cell.exclude_info_factory():
            continue
        name_array = cell.get_celltype().get_name_array(cell)
        if cell.get_celltype().has_CB():
            cb = "(void*){}".format(name_array[8])
            cb_proto = "extern {}_CB {};\n".format(
                cell.get_celltype().get_global_name(), name_array[4])
        else:
            cb = "0"
            cb_proto = ""
        if cell.get_celltype().has_INIB():
            inib = "(void*)&{}".format(name_array[5])
            inib_proto = "extern {}_INIB {};\n".format(
                cell.get_celltype().get_global_name(), name_array[11])
        else:
            inib = "0"
            inib_proto = ""
        if not cell.exclude_info_factory():
            f.print("{}#define  {}__CBP   {}\n{}#define  {}__INIBP {}\n".format(
                cb_proto, cell.get_global_name(), cb,
                inib_proto, cell.get_global_name(), inib))
    for region in self.namespace_list:
        if type(region) is Region:
            region.print_cell_define(f)


def _region_print_entry_descriptor_define(self, f):
    for cell in self.cell_list:
        if cell.exclude_info_factory():
            continue

        signatures = {}
        for port in cell.get_celltype().get_port_list():
            if port.get_port_type() != "ENTRY":
                continue

            if port.get_signature() not in signatures:
                f.print("#include \"{}_tecsgen.h\"\n".format(port.get_signature().get_global_name()))
                signatures[port.get_signature()] = True
            if cell.get_celltype().get_global_name() == Sym("nTECSInfo_tRawEntryDescriptorInfo"):
                f.print("const struct tag_{}_{}_DES ".format(
                    cell.get_celltype().get_global_name(), port.get_name()))
                f.print("{}_{}_des;\n".format(cell.get_global_name(), port.get_name()))
            else:
                size = port.get_array_size()
                if size is None:
                    size = 1
                elif size == "[]":
                    size = cell.get_entry_port_max_subscript(port)
                if not port.is_omit():
                    if size == 1:
                        f.print("extern struct tag_{}_VDES ".format(
                            port.get_signature().get_global_name()))
                        f.print("{}_{}_des;\n".format(cell.get_global_name(), port.get_name()))
                    else:
                        for i in range(size):
                            f.print("extern struct tag_{}_VDES ".format(
                                port.get_signature().get_global_name()))
                            f.print("{}_{}_des{};\n".format(
                                cell.get_global_name(), port.get_name(), i))
    for region in self.namespace_list:
        if type(region) is Region:
            region.print_entry_descriptor_define(f)


# === Celltype ===

def _celltype_print_info(self, f, indent):
    f.print("""{0}cell nTECSInfo::tCelltypeInfo {1}CelltypeInfo {{
{0}    name             = "{2}";
{0}    b_singleton      = {3};
{0}    b_IDX_is_ID_act  = C_EXP( "{1}__IDX_is_ID_act" );
{0}    sizeOfCB         = C_EXP( "{1}__sizeOfCB" );
{0}    sizeOfINIB       = C_EXP( "{1}__sizeOfINIB" );
{0}    n_cellInLinkUnit = C_EXP( "{1}__NCELLINLINKUNIT" );
{0}    n_cellInSystem   = {4};
""".format(indent, self.global_name, to_s(self.name), to_s(self.singleton), len(self.cell_list)))
    for port in self.port:
        if port.get_port_type() == "ENTRY":
            f.print("{0}    cEntryInfo[]    = {1}_{2}EntryInfo.eEntryInfo;\n".format(
                indent, self.global_name, port.get_name()))
    for port in self.port:
        if port.get_port_type() == "CALL":
            f.print("{0}    cCallInfo[]     = {1}_{2}CallInfo.eCallInfo;\n".format(
                indent, self.global_name, port.get_name()))
    for decl in self.attribute:
        f.print("{0}    cAttrInfo[]     = {1}_{2}VarDeclInfo.eVarDeclInfo;\n".format(
            indent, self.global_name, decl.get_name()))
    for decl in self.var:
        f.print("{0}    cVarInfo[]      = {1}_{2}VarDeclInfo.eVarDeclInfo;\n".format(
            indent, self.global_name, decl.get_name()))
    f.print("{0}}};\n".format(indent))
    for port in self.port:
        if port.get_port_type() == "ENTRY":
            port.print_info(f, self.global_name, indent)
    for port in self.port:
        if port.get_port_type() == "CALL":
            port.print_info(f, self.global_name, indent)
    for decl in self.attribute:
        decl.print_info(f, self.global_name, indent, Sym("DECLTYPE_ATTR"))
    for decl in self.var:
        decl.print_info(f, self.global_name, indent, Sym("DECLTYPE_VAR"))


def _celltype_print_define_offset(self, f):
    # intptr_t に一回キャストするのは 64bit 版を考量してのこと．しかし 32bit としているので 4GB を超える構造体等は扱えない
    if self.n_cell_gen > 0:
        f.print("""

#include "{}_tecsgen.h"
""".format(self.global_name))
        for decl in self.attribute:
            if self.has_INIB():
                inib_cb = "INIB"
            else:
                inib_cb = "CB"
            if not decl.is_omit():
                offset = "(uint32_t)(intptr_t)&((({}_{}*)0)->{})".format(
                    self.global_name, inib_cb, decl.get_name())
                place = inib_cb
            else:
                offset = "0xffffffff"
                place = "NON"
            f.print("#define OFFSET_OF_{:<30}  ({})\n".format(
                "{}_{}".format(self.global_name, decl.get_name()), offset))
            f.print("#define PLACE_OF_{:<30}  VARDECL_PLACE_{}\n".format(
                "{}_{}".format(self.global_name, decl.get_name()), place))
        for decl in self.var:
            if decl.get_size_is() and self.has_INIB():
                inib_cb = "INIB"
            else:
                inib_cb = "CB"
            place = inib_cb
            f.print("#define OFFSET_OF_{:<30}  ({})\n".format(
                "{}_{}".format(self.global_name, decl.get_name()),
                "(uint32_t)(intptr_t)&((({}_{}*)0)->{})".format(
                    self.global_name, inib_cb, decl.get_name())))
            f.print("#define PLACE_OF_{:<30}  VARDECL_PLACE_{}\n".format(
                "{}_{}".format(self.global_name, decl.get_name()), place))
    else:
        f.print("""

// #include "{}_tecsgen.h"   // no cell exist
""".format(self.global_name))
        # 生成されないセルタイプ
        for decl in self.attribute:
            f.print("#define OFFSET_OF_{:<30}  ({})\n".format(
                "{}_{}".format(self.global_name, decl.get_name()), "0xffffffff"))
            f.print("#define PLACE_OF_{:<30}   VARDECL_PLACE_NON\n".format(
                "{}_{}".format(self.global_name, decl.get_name())))
        for decl in self.var:
            f.print("#define OFFSET_OF_{:<30}  ({})\n".format(
                "{}_{}".format(self.global_name, decl.get_name()), "0xffffffff"))
            f.print("#define PLACE_OF_{:<30}   VARDECL_PLACE_NON\n".format(
                "{}_{}".format(self.global_name, decl.get_name())))


def _celltype_print_celltype_define(self, f):
    if self.has_INIB():
        size_INIB = "(sizeof({}_INIB))".format(self.global_name)
    else:
        size_INIB = "(0)"
    if self.has_CB():
        size_CB = "(sizeof({}_CB))".format(self.global_name)
    else:
        size_CB = "(0)"

    if self.n_cell_gen > 0:
        f.print("\n#include \"{}_tecsgen.h\"\n".format(self.global_name))
        f.print("#define {:<50} ({})\n".format(
            "{}__IDX_is_ID_act".format(self.global_name), to_s(self.idx_is_id_act)))
        f.print("#define {:<50} ({})\n".format(
            "{}__sizeOfCB".format(self.global_name), size_CB))
        f.print("#define {:<50} ({})\n".format(
            "{}__sizeOfINIB".format(self.global_name), size_INIB))
        f.print("#define {:<30} ({})\n".format(
            "{}__NCELLINLINKUNIT".format(self.global_name), self.n_cell_gen))
    else:
        f.print("#define {:<50} (false)\n".format(
            "{}__IDX_is_ID_act".format(self.global_name)))
        f.print("#define {:<50} (0)\n".format(
            "{}__sizeOfCB".format(self.global_name)))
        f.print("#define {:<50} (0)\n".format(
            "{}__sizeOfINIB".format(self.global_name)))
        f.print("#define {:<30} ({})\n".format(
            "{}__NCELLINLINKUNIT".format(self.global_name), self.n_cell_gen))


def _celltype_print_call_define(self, f):
    if self.n_cell_gen > 0:
        f.print("""

#include "{}_tecsgen.h"
""".format(self.global_name))
    else:
        f.print("""

// #include "{}_tecsgen.h"   // no cell exist
""".format(self.global_name))
    for port in self.port:
        if port.get_port_type() == "ENTRY":
            continue
        if port.is_omit() or (port.is_VMT_useless() and port.is_cell_unique()) or self.n_cell_gen == 0:
            place = "CALL_PLACE_NON"
        elif port.is_dynamic():
            if port.get_array_size():
                place = "CALL_PLACE_INIB_DES"
            else:
                place = "CALL_PLACE_CB_DES"
        elif not self.has_INIB():
            if port.is_VMT_useless():
                place = "CALL_PLACE_CB_IDX"
            else:
                place = "CALL_PLACE_CB_DES"
        else:
            if port.is_VMT_useless():
                place = "CALL_PLACE_INIB_IDX"
            else:
                place = "CALL_PLACE_INIB_DES"
        if (port.is_VMT_useless() and port.is_cell_unique()) or port.is_omit() or self.n_cell_gen == 0:
            offset = "0xffffffff"
        else:
            if port.is_dynamic() or not self.has_INIB():
                cb_inib = "CB"
            else:
                cb_inib = "INIB"
            offset = "(uint32_t)(intptr_t)&(({}_{}*)0)->{}".format(
                self.global_name, cb_inib, port.get_name())
        array_size = port.get_array_size()
        if array_size == "[]":
            array_size = "0xffffffff"
        elif array_size is None:
            array_size = "0"

        f.print("#define {:<50} ({})\n".format(
            "{}_{}__offset".format(self.global_name, port.get_name()), offset))
        f.print("#define {:<50} ({})\n".format(
            "{}_{}__array_size".format(self.global_name, port.get_name()), array_size))
        f.print("#define {:<50} ({})\n".format(
            "{}_{}__place".format(self.global_name, port.get_name()), place))
        f.print("#define {:<50} ({})\n".format(
            "{}_{}__b_VMT_useless".format(self.global_name, port.get_name()), to_s(port.is_VMT_useless())))
        f.print("#define {:<50} ({})\n".format(
            "{}_{}__b_skelton_useless".format(self.global_name, port.get_name()), to_s(port.is_skelton_useless())))
        f.print("#define {:<50} ({})\n".format(
            "{}_{}__b_cell_unique".format(self.global_name, port.get_name()), to_s(port.is_cell_unique())))


def _celltype_print_entry_define(self, f):
    for port in self.port:
        if port.get_port_type() == "CALL":
            continue
        array_size = port.get_array_size()
        if array_size == "[]":
            array_size = "0xffffffff"
        elif array_size is None:
            array_size = "0"

        f.print("#define {:<50} ({})\n".format(
            "{}_{}__array_size".format(self.global_name, port.get_name()), array_size))


# === Port ===

def _port_print_info(self, f, ct_global, indent):
    if self.signature is None:     # signature not found error in cdl
        return
    if self.port_type == "ENTRY":
        f.print("""{0}cell nTECSInfo::tEntryInfo {1}_{2}EntryInfo{{
{0}    name            = "{2}";
{0}    cSignatureInfo  = {3}SignatureInfo.eSignatureInfo;
{0}    b_inline        = {4};
{0}    array_size      = C_EXP( "{1}_{2}__array_size" );
{0}}};
""".format(indent, ct_global, self.name, self.signature.get_global_name(), to_s(self.b_inline)))
    else:
        f.print("""{0}cell nTECSInfo::tCallInfo {1}_{2}CallInfo{{
{0}    name            = "{2}";
{0}    cSignatureInfo  = {3}SignatureInfo.eSignatureInfo;
{0}    offset            = C_EXP( "{1}_{2}__offset" );
{0}    array_size        = C_EXP( "{1}_{2}__array_size" );
{0}    b_optional        = {4};
{0}    b_omit            = {5};
{0}    b_dynamic         = {6};
{0}    b_ref_desc        = {7};
{0}    b_allocator_port  = {8};
{0}    b_require_port    = {9};
{0}    place             = C_EXP( "{1}_{2}__place" );
{0}    b_VMT_useless     = C_EXP( "{1}_{2}__b_VMT_useless" );
{0}    b_skelton_useless = C_EXP( "{1}_{2}__b_skelton_useless" );
{0}    b_cell_unique     = C_EXP( "{1}_{2}__b_cell_unique" );

{0}}};
""".format(
            indent, ct_global, self.name, self.signature.get_global_name(),
            to_s(self.b_optional), to_s(self.b_omit), to_s(self.b_dynamic), to_s(self.b_ref_desc),
            to_s(self.allocator_port is not None), to_s(self.b_require)))


# === Cell ===

def _cell_print_info(self, f, indent):
    if self.exclude_info():
        return
    f.print("""

{}/*** {} cell information ****/
{}cell nTECSInfo::tCellInfo {}CellInfo {{
{}    name            = "{}";
{}    cbp             = C_EXP( \"{}__CBP\" );
{}    inibp           = C_EXP( \"{}__INIBP\" );
{}    cCelltypeInfo   = {}CelltypeInfo.eCelltypeInfo;
""".format(
        indent, self.global_name, indent, self.global_name,
        indent, to_s(self.name),
        indent, self.global_name,
        indent, self.global_name,
        indent, self.celltype.get_global_name()))
    for port in self.celltype.get_port_list():
        if port.get_port_type() != "ENTRY":
            continue

        f.print("{0}    cRawEntryDescriptor[] = {1}_{2}RawEntryDescriptorInfo.eRawEntryDescriptor;\n".format(
            indent, self.global_name, port.get_name()))
    f.print("{}}};\n".format(indent))

    # RawEntryDescriptorInfo cells
    for port in self.celltype.get_port_list():
        if port.get_port_type() != "ENTRY":
            continue

        size = port.get_array_size()
        if size is None:
            size = 1
        elif size == "[]":
            size = self.entry_array_max_subscript[port]
        if not port.is_omit():
            if size == 1:
                red = 'C_EXP( "&{}_{}_des" )'.format(self.global_name, port.get_name())
            else:
                red = ""
                delim = ""
                for i in range(size):
                    red += "{}C_EXP( \"&{}_{}_des{}\" )".format(
                        delim, self.global_name, port.get_name(), i)
                    delim = ", "
        else:
            red = "(void *)0"
        f.print("""{0}cell nTECSInfo::tRawEntryDescriptorInfo {1}_{2}RawEntryDescriptorInfo {{
{0}   size = {3};
{0}   rawEntryDescriptor = {{ {4} }};
""".format(indent, self.global_name, port.get_name(), size, red))
        f.print("{}}};\n".format(indent))


def _cell_exclude_info(self):
    # print "exclude_info?: name=" + get_name.to_s
    if self.celltype is None or \
       self.is_of_composite() or \
       self.celltype.get_global_name() == Sym("nTECSInfo_tTECSInfoSub") or \
       self.post_code_generated() or \
       self.b_defined is False:
        # print ": true celltype_is_of_composite=#{is_of_composite?} celltype_name=#{@celltype.get_global_name} celltype.need_generate=#{@celltype.need_generate?}\n"
        return True
    else:
        # print ": false\n"
        return False


def _cell_exclude_info_factory(self):
    # print "exclude_info_factory?: name=" + get_name.to_s
    if self.celltype is None or \
       self.is_of_composite() or \
       self.celltype.get_global_name() == Sym("nTECSInfo_tTECSInfoSub") or \
       not self.celltype.need_generate():
        # print ": true celltype_is_of_composite=#{is_of_composite?} celltype_name=#{@celltype.get_global_name} celltype.need_generate=#{@celltype.need_generate?}\n"
        return True
    else:
        # print ": false\n"
        return False


# === Signature ===

def _signature_print_info(self, f, indent):
    f.print("""

{}/*** {} signature information ****/
{}cell nTECSInfo::tSignatureInfo {}SignatureInfo {{
{}    name            = "{}";
""".format(
        indent, self.global_name, indent, self.global_name,
        indent, to_s(self.name)))
    for fh in self.function_head_list.get_items():
        f.print("{0}    cFunctionInfo[] = {1}_{2}FunctionInfo.eFunctionInfo;\n".format(
            indent, self.global_name, fh.get_name()))
    f.print("{0}}};\n".format(indent))
    for fh in self.function_head_list.get_items():
        fh.print_info(f, indent)


# === FuncHead ===

def _funchead_print_info(self, f, indent):
    sig_name = self.get_owner().get_global_name()
    func_name = self.get_name()
    f.print("""{0}cell nTECSInfo::tFunctionInfo {1}_{2}FunctionInfo {{
{0}    name            = "{2}";
{0}    bOneway         = {3};
""".format(indent, sig_name, func_name, to_s(self.is_oneway())))
    for param in self.get_paramlist().get_items():
        f.print("{0}    cParamInfo[]    = {1}_{2}_{3}ParamInfo.eParamInfo;\n".format(
            indent, sig_name, func_name, param.get_name()))
    f.print("{0}    cReturnTypeInfo = {1}TypeInfo.eTypeInfo;\n{0}}};\n".format(
        indent, self.get_return_type().get_ID_str()))
    for param in self.get_paramlist().get_items():
        dbgPrint("param_list {}, {}, {}\n".format(sig_name, func_name, param.get_name()))
        param.print_info(f, sig_name, func_name, self.get_paramlist(), indent)
    self.get_return_type().print_info(f, indent)


# === ParamDecl ===

def _paramdecl_print_info(self, f, signature_global_name, func_name, paramdecl_list, indent):
    if self.size:
        size = "\"{}\"".format(self.size.get_rpn(paramdecl_list))
    else:
        size = "(char_t*)0"
    if self.count:
        count = "\"{}\"".format(self.count.get_rpn(paramdecl_list))
    else:
        count = "(char_t*)0"
    if self.string:
        if self.string == -1:
            string = '""'
        else:
            string = "\"{}\"".format(self.string.get_rpn(paramdecl_list))
    else:
        string = "(char_t*)0"
    f.print("""{0}cell nTECSInfo::tParamInfo {1}_{2}_{3}ParamInfo {{
{0}    name            = "{3}";
{0}    dir             = PARAM_DIR_{4};
{0}    sizeIsExpr      = {5};
{0}    countIsExpr     = {6};
{0}    stringExpr      = {7};
{0}    cTypeInfo       = {8}TypeInfo.eTypeInfo;
{0}}};
""".format(
        indent, signature_global_name, func_name, self.get_name(), self.direction,
        size, count, string, self.get_type().get_ID_str()))
    self.get_type().print_info(f, indent)


# === Decl ===

def _decl_print_info(self, f, parent_ID_str, indent, decl_type):
    if self.size_is:
        size = "\"mikan\""
    else:
        size = "(char_t*)0"
    f.print("""{0}cell nTECSInfo::tVarDeclInfo {1}_{2}VarDeclInfo {{
{0}    name            = "{2}";
{0}    sizeIsExpr      = {3};
{0}    declType        = {4};
{0}    offset          = C_EXP( "OFFSET_OF_{1}_{2}" );
{0}    place           = C_EXP( "PLACE_OF_{1}_{2}" );
{0}    cTypeInfo       = {5}TypeInfo.eTypeInfo;
{0}}};
""".format(
        indent, parent_ID_str, self.get_name(), size, decl_type, self.get_type().get_ID_str()))
    self.get_type().print_info(f, indent)


# === Type ===

_typeinfo_printed = {}


def _type_reset_print_info():
    global _typeinfo_printed
    _typeinfo_printed = {}


def _type_print_info(self, f, indent):
    # Type の info は、最後にまとめて出力するので、ここでは記録するだけ
    global _typeinfo_printed
    id_str = self.get_ID_str()
    if id_str in _typeinfo_printed:
        return
    # p "ID Str: #{get_ID_str}"
    _typeinfo_printed[id_str] = self
    if isinstance(self, PtrType):
        self.get_referto().print_info(f, indent)
    elif isinstance(self, ArrayType):
        self.get_type().print_info(f, indent)
    elif isinstance(self, DefinedType):
        self.get_type().print_info(f, indent)
    elif isinstance(self, StructType):
        for decl in self.get_members_decl().get_items():
            decl.print_info(f, self.get_ID_str(), indent, Sym("DECLTYPE_STMEMBER"))


def _tecsinfo_type_kind_name(type_obj):
    # Ruby: superclass == Type ? class.name : superclass.name
    # Python C* types use (CType, IntType) MI; walk MRO for the direct Type subclass.
    cls = type_obj.__class__
    if cls.__bases__ and cls.__bases__[0] is Type:
        return cls.__name__
    for c in cls.__mro__[1:]:
        if c is Type:
            break
        if Type in c.__bases__:
            return c.__name__
    return cls.__name__


def _type_print_info_post_one(self, f, indent):
    type_name = _tecsinfo_type_kind_name(self)
    # p "type: #{type_name}, #{self.class.name}"

    # p "class=#{self.class.name} size=#{bit_size}"
    f.print("""{0}cell nTECSInfo::t{1}Info {2}TypeInfo{{
{0}    name           = "{3}{4}";
{0}    typeKind       = TECSTypeKind_{1};
""".format(
        indent, type_name, self.get_ID_str(),
        self.get_type_str(), self.get_type_str_post()))
    if type_name != "FuncType":
        f.print("""{0}    size           = C_EXP( "sizeof({1}{2})" );
{0}    b_const        = {3};
{0}    b_volatile     = {4};
""".format(
            indent, self.get_type_str(), self.get_type_str_post(),
            to_s(self.is_const()), to_s(self.is_volatile())))

    if isinstance(self, PtrType):
        f.print("{0}    cTypeInfo        = {1}TypeInfo.eTypeInfo;\n".format(
            indent, self.get_referto().get_ID_str()))
    elif isinstance(self, ArrayType):
        f.print("{0}    cTypeInfo        = {1}TypeInfo.eTypeInfo;\n".format(
            indent, self.get_type().get_ID_str()))
    elif isinstance(self, DefinedType):
        f.print("{0}    cTypeInfo        = {1}TypeInfo.eTypeInfo;\n".format(
            indent, self.get_type().get_ID_str()))
    elif isinstance(self, StructType):
        for decl in self.get_members_decl().get_items():
            f.print("{0}    cVarDeclInfo[] = {1}_{2}VarDeclInfo.eVarDeclInfo;\n".format(
                indent, self.get_ID_str(), decl.get_name()))
    elif isinstance(self, DescriptorType):
        f.print("{0}    cSignatureInfo   = {1}SignatureInfo.eSignatureInfo;\n".format(
            indent, self.get_signature().get_global_name()))

    f.print("{0}}};\n".format(indent))


def _type_get_ID_str(self):
    # puts "get_ID_str: #{self.class.name}"
    if isinstance(self, PtrType):
        str_ = self.get_referto().get_ID_str() + "_Ptr_"
    elif isinstance(self, ArrayType):
        if self.get_subscript():
            str_ = self.get_type().get_ID_str() + "_Array" + str(self.get_subscript().eval_const(None)) + "_"
        else:
            str_ = self.get_type().get_ID_str() + "_Array" + "_"
    elif isinstance(self, StructType):
        str_ = "struct {}".format(self.tag)
    elif isinstance(self, DescriptorType):
        str_ = "Descriptor_of_" + to_s(self.get_signature().get_global_name())
    elif isinstance(self, FuncType):
        str_ = "function_" + self.get_type().get_ID_str()
        for param in self.get_paramlist().get_items():
            str_ += "__" + param.get_declarator().get_type().get_ID_str()
    else:
        str_ = self.get_type_str() + self.get_type_str_post()
    # p "before: #{str}"
    str_ = str_.replace(" ", "__")
    # p "after: #{str}"
    return str_


def _type_print_info_post(f, indent):
    for type_ in _typeinfo_printed.values():
        _type_print_info_post_one(type_, f, indent)


# --- assign methods (Ruby class reopen) ---
Namespace.print_info_ns_sub = _namespace_print_info_ns_sub
Namespace.print_info_ns = _namespace_print_info_ns
Namespace.print_info = _namespace_print_info
Namespace.print_struct_define = _namespace_print_struct_define
Namespace.print_celltype_define_offset = _namespace_print_celltype_define_offset
Namespace.print_celltype_define = _namespace_print_celltype_define
Namespace.print_call_define = _namespace_print_call_define
Namespace.print_entry_define = _namespace_print_entry_define

Region.print_info_region_sub = _region_print_info_region_sub
Region.print_info_region = _region_print_info_region
Region.print_info = _region_print_info
Region.get_region = _region_get_region
Region.print_cell_define_offset = _region_print_cell_define_offset
Region.print_cell_define = _region_print_cell_define
Region.print_entry_descriptor_define = _region_print_entry_descriptor_define

Celltype.print_info = _celltype_print_info
Celltype.print_define_offset = _celltype_print_define_offset
Celltype.print_celltype_define = _celltype_print_celltype_define
Celltype.print_call_define = _celltype_print_call_define
Celltype.print_entry_define = _celltype_print_entry_define

Port.print_info = _port_print_info

Cell.print_info = _cell_print_info
Cell.exclude_info = _cell_exclude_info
Cell.exclude_info_factory = _cell_exclude_info_factory

Signature.print_info = _signature_print_info

FuncHead.print_info = _funchead_print_info

ParamDecl.print_info = _paramdecl_print_info

Decl.print_info = _decl_print_info

Type.reset_print_info = _type_reset_print_info
Type.print_info = _type_print_info
Type.print_info_post = _type_print_info_post
Type.get_ID_str = _type_get_ID_str
Type.print_info_post_one = _type_print_info_post_one
