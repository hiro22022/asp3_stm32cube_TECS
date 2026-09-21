# -*- coding: utf-8 -*-
# Celltype コード生成 — generate.rb 1185 行〜相当（mini.cdl 向け手移植＋段階拡張）

import re

import tecsgen
from tecslib.core import globals as G
from tecslib.core.messages import TECSMsg
from tecslib.core.componentobj.celltype import Celltype
from tecslib.core.toplevel import dbgPrint, print_exception
from tecslib.core.componentobj.port import Port
from tecslib.core.componentobj.region import Region
from tecslib.core.expression import C_EXP, Expression
from tecslib.core.syntaxobj.cdlstring import CDLString
from tecslib.core.types import (
    ArrayType,
    BoolType,
    DefinedType,
    DescriptorType,
    EnumType,
    FloatType,
    IntType,
    PtrType,
    StructType,
)
from tecslib.core.generate import (
    AppFile,
    print_note,
    print_indent,
    ifndef_macro_only,
    endif_macro_only,
    ifndef_cb_type_only,
    ifdef_cb_type_only,
    endif_cb_type_only,
    begin_extern_C,
    end_extern_C,
)
from tecslib.rubylib.symbol import Sym
from tecslib.rubylib.reopen import reopen
from tecslib.rubylib.rb import to_s
TECSGEN = tecsgen.TECSGEN


@reopen(Celltype)
class _CelltypeGenerate:

    def generate(self):
        if self.need_generate():
            self.generate_private_header()
            self.generate_factory_header()
            self.generate_cell_code()
            self.generate_template_code()
            self.generate_inline_template_code()
            self.generate_celltype_factory_code()
            self.generate_cell_factory_code()
            self.generate_makefile()
        elif G.generate_all_template:
            self.generate_template_code()
            self.generate_inline_template_code()

    def generate_post(self):
        if not self.need_generate():
            return
        self.generate_private_header_post()
        self.generate_factory_header_post()

    def generate_private_header(self):
        f = AppFile.open("{}/{}_tecsgen.{}".format(G.gen, self.global_name, G.h_suffix))
        print_note(f)
        self.gen_ph_guard(f)
        self.gen_ph_info(f)
        self.gen_ph_include(f)
        ifndef_macro_only(f)
        begin_extern_C(f)
        self.gen_ph_cell_cb_type(f)
        self.gen_ph_INIB_as_CB(f)
        self.gen_ph_extern_cell(f)
        self.gen_ph_typedef_idx(f)
        self.gen_ph_ep_fun_prototype(f)
        end_extern_C(f)
        endif_macro_only(f)
        self.gen_ph_include_cb_type(f)
        if self.n_entry_port_inline == 0:
            ifndef_cb_type_only(f)
        self.gen_ph_base(f)
        self.gen_ph_valid_idx(f)
        if self.n_call_port_array > 0:
            self.gen_ph_n_cp(f)
        if self.n_entry_port_array > 0:
            self.gen_ph_n_ep(f)
        self.gen_ph_test_optional_call_port(f)
        self.gen_ph_get_cellcb(f)
        if self.n_attribute_rw > 0 or self.n_attribute_ro > 0 or self.n_var > 0:
            self.gen_ph_attr_access(f)
        f.print("#ifndef TECSFLOW\n")
        if self.n_call_port > 0:
            self.gen_ph_cp_fun_macro(f, False)
        f.print("#else  /* TECSFLOW */\n")
        if self.n_call_port > 0:
            self.gen_ph_cp_fun_macro(f, True)
        f.print("#endif /* TECSFLOW */\n")
        if self.n_entry_port_inline == 0:
            endif_cb_type_only(f)
        ifndef_macro_only(f)
        begin_extern_C(f)
        self.gen_ph_ep_skel_prototype(f)
        if self.n_entry_port_inline == 0:
            ifndef_cb_type_only(f)
        self.gen_ph_ref_desc_func(f)
        self.gen_ph_set_desc_func(f)
        if self.n_entry_port_inline == 0:
            endif_cb_type_only(f)
        end_extern_C(f)
        endif_macro_only(f)
        if self.n_entry_port_inline == 0:
            ifndef_cb_type_only(f)
        self.gen_ph_valid_idx_abbrev(f)
        self.gen_ph_get_cellcb_abbrev(f)
        if self.n_attribute_rw > 0 or self.n_attribute_ro > 0 or self.n_var > 0:
            self.gen_ph_attr_access_abbrev(f)
        if self.n_call_port > 0:
            self.gen_ph_cp_fun_macro_abbrev(f)
        self.gen_ph_ref_desc_macro_abbrev(f)
        self.gen_ph_set_desc_macro_abbrev(f)
        self.gen_ph_test_optional_call_port_abbrev(f)
        if self.n_entry_port > 0:
            self.gen_ph_ep_fun_macro(f)
        self.gen_ph_foreach_cell(f)
        self.gen_ph_cb_initialize_macro(f)
        self.gen_ph_dealloc_code(f, "")
        self.gen_ph_dealloc_code(f, "_RESET")
        if self.n_entry_port_inline == 0:
            endif_cb_type_only(f)
        f.close()

    def generate_private_header_post(self):
        f = AppFile.open("{}/{}_tecsgen.{}".format(G.gen, self.global_name, G.h_suffix))
        ifndef_macro_only(f)
        self.gen_ph_inline(f)
        endif_macro_only(f)
        if self.n_entry_port_inline > 0:
            ifdef_cb_type_only(f)
            self.gen_ph_undef(f)
            endif_cb_type_only(f)
        self.gen_ph_endif(f)
        f.close()

    def generate_cell_code(self):
        fs = {}
        f = None
        for r in self.domain_class_roots2.keys():
            if r.is_root():
                nsp = ""
            else:
                nsp = "_{}".format(r.get_namespace_path().get_global_name())
            dbgPrint(
                "celltype:{} nsp:{} class_root={} domain_root={}\n".format(
                    self.name,
                    nsp,
                    r.get_class_root().get_namespace_path(),
                    r.get_domain_root().get_namespace_path(),
                )
            )
            fs[r] = AppFile.open("{}/{}{}_tecsgen.{}".format(
                G.gen, self.global_name, nsp, G.c_suffix))
            if r.is_link_root():
                f = fs[r]
        if f is None:
            keys = list(self.domain_class_roots2.keys())
            if len(keys) > 1:
                gn = keys[0].get_link_root().get_up_global_name()
                f = AppFile.open("{}/{}{}_tecsgen.{}".format(
                    G.gen, self.global_name, gn, G.c_suffix))
            else:
                f = fs[keys[0]]
        print_note(f)
        self.gen_cell_private_header(f)
        self.gen_cell_factory_header(f)
        self.gen_cell_ep_des_type(f)
        for r, f2 in fs.items():
            if f == f2:
                continue
            print_note(f2)
            self.gen_cell_private_header(f2)
            self.gen_cell_factory_header(f2)
            self.gen_cell_ep_des_type(f2)
        self.gen_cell_skel_fun(f)
        self.gen_cell_fun_table(f)
        self.gen_cell_var_init(f)
        self.gen_cell_ep_vdes(fs)
        self.gen_cell_ep_vdes_array(fs)
        self.gen_cell_cb_out_init(fs)
        self.gen_cell_cb(fs)
        self.gen_cell_extern_mt(fs)
        self.gen_cell_ep_des(fs)
        self.gen_cell_cb_tab(f)
        if G.ram_initializer:
            self.gen_cell_cb_initialize_code(f)
        for r, f2 in fs.items():
            f2.close()
            if f == f2:
                f = None
        if f:
            f.close()

    def gen_ph_guard(self, f, post="TECSGEN"):
        f.print("#ifndef {}_{}_H\n".format(self.global_name, post))
        f.print("#define {}_{}_H\n\n".format(self.global_name, post))

    def gen_ph_info(self, f):
        yn_multi_domain = "yes" if self.multi_domain() else "no"
        yn_idx_is_id = "yes" if self.idx_is_id else "no"
        yn_idx_is_id_act = "yes" if self.idx_is_id_act else "no"
        yn_singleton = "yes" if self.singleton else "no"
        yn_rom = "yes" if G.rom else "no"
        yn_has_CB = "yes" if self.has_CB() else "no"
        yn_has_INIB = "yes" if self.has_INIB() else "no"
        yn_cb_init = "yes" if self.need_CB_initializer() else "no"
        f.print(
            "/*\n"
            " * celltype          :  {}\n"
            " * global name       :  {}\n"
            " * multi-domain      :  {}\n"
            " * idx_is_id(actual) :  {}({})\n"
            " * singleton         :  {}\n"
            " * has_CB            :  {}\n"
            " * has_INIB          :  {}\n"
            " * rom               :  {}\n"
            " * CB initializer    :  {}\n"
            " */\n\n".format(
                self.name,
                self.global_name,
                yn_multi_domain,
                yn_idx_is_id,
                yn_idx_is_id_act,
                yn_singleton,
                yn_has_CB,
                yn_has_INIB,
                yn_rom,
                yn_cb_init,
            )
        )

    def gen_ph_include(self, f):
        f.printf(TECSMsg.get("IGH_comment"), "#_IGH_#")
        f.print("#include \"global_tecsgen.{}\"\n\n".format(G.h_suffix))
        f.printf(TECSMsg.get("ISH_comment"), "#_ISH_#")
        for p in self.port:
            if p.is_omit():
                continue
            hname = "{}_tecsgen.{}".format(p.get_signature().get_global_name(), G.h_suffix)
            if not self.header_included(hname):
                f.print("#include \"{}\"\n".format(hname))
        f.print("\n")

    def gen_ph_include_cb_type(self, f):
        if not self.b_cp_optimized:
            return
        f.printf(TECSMsg.get("ICT_comment"), "#_ICT_#")
        f.print("#ifndef  TOPPERS_CB_TYPE_ONLY\n")
        f.print("#define  {}_CB_TYPE_ONLY\n".format(self.global_name))
        f.print("#define TOPPERS_CB_TYPE_ONLY\n")
        f.print("#endif  /* TOPPERS_CB_TYPE_ONLY */\n")
        for p in self.port:
            if p.get_port_type() != "CALL":
                continue
            if p.is_omit():
                continue
            if p.is_skelton_useless() or p.is_cell_unique() or p.is_VMT_useless():
                p2 = p.get_real_callee_port()
                if p2:
                    ct = p2.get_celltype()
                    hname = "{}_tecsgen.{}".format(ct.get_global_name(), G.h_suffix)
                    if not self.header_included(hname):
                        f.print("#include \"{}\"\n".format(hname))
        f.print("#ifdef  {}_CB_TYPE_ONLY\n".format(self.global_name))
        f.print("#undef TOPPERS_CB_TYPE_ONLY\n")
        f.print("#endif /* {}_CB_TYPE_ONLY */\n".format(self.global_name))

    def gen_ph_base(self, f):
        if self.singleton:
            return
        f.printf(
            "#define %-20s %10s  /* %s #_NIDB_# */\n",
            "{}_ID_BASE".format(self.global_name),
            "({})".format(self.id_base),
            TECSMsg.get("NIDB_comment"),
        )
        f.printf(
            "#define %-20s %10s  /* %s  #_NCEL_# */\n\n",
            "{}_N_CELL".format(self.global_name),
            "({})".format(self.n_cell_gen),
            TECSMsg.get("NCEL_comment"),
        )

    def gen_ph_valid_idx(self, f):
        if self.singleton:
            return
        f.printf(TECSMsg.get("CVI_comment"), "#_CVI_#")
        if self.idx_is_id_act:
            f.print(
                "#define {}_VALID_IDX(IDX) ({}_ID_BASE <= (IDX) && (IDX) < {}_ID_BASE+{}_N_CELL)\n\n".format(
                    self.global_name,
                    self.global_name,
                    self.global_name,
                    self.global_name,
                )
            )
        else:
            f.print("#define {}_VALID_IDX(IDX) (1)\n\n".format(self.global_name))

    def gen_ph_valid_idx_abbrev(self, f):
        if self.singleton:
            return
        f.printf(TECSMsg.get("CVIA_comment"), "#_CVIA_#")
        f.print("#define VALID_IDX(IDX)  {}_VALID_IDX(IDX)\n\n".format(self.global_name))

    def gen_ph_n_cp(self, f):
        b_comment = False
        for p in self.port:
            if p.get_port_type() != "CALL":
                continue
            if p.is_omit():
                continue
            if p.get_array_size() is None:
                continue
            if not b_comment:
                f.printf(TECSMsg.get("NCPA_comment"), "#_NCPA_#")
                b_comment = True
            if p.get_array_size() != "[]":
                f.print("#define N_CP_{}    ({})\n".format(p.get_name(), p.get_array_size()))
                f.print("#define NCP_{}     ({})\n".format(p.get_name(), p.get_array_size()))
            else:
                if self.singleton:
                    inib = "INIB" if self.has_INIB() else "CB"
                    f.print("#define N_CP_{}  ({}_SINGLE_CELL_{}.n_{})\n".format(
                        p.get_name(), self.global_name, inib, p.get_name()))
                    f.print("#define NCP_{}   ({}_SINGLE_CELL_{}.n_{})\n".format(
                        p.get_name(), self.global_name, inib, p.get_name()))
                else:
                    inib = "->_inib" if (self.has_CB() and self.has_INIB()) else ""
                    f.print("#define N_CP_{}(p_that)  ((p_that){}->n_{})\n".format(
                        p.get_name(), inib, p.get_name()))
                    f.print("#define NCP_{}           (N_CP_{}(p_cellcb))\n".format(
                        p.get_name(), p.get_name()))

    def gen_ph_n_ep(self, f):
        b_comment = False
        for p in self.port:
            if p.get_port_type() != "ENTRY":
                continue
            if p.get_array_size() is None:
                continue
            if not b_comment:
                f.printf(TECSMsg.get("NEPA_comment"), "#_NEPA_#")
                b_comment = True
            if p.get_array_size() != "[]":
                f.print("#define NEP_{}     ({})\n".format(p.get_name(), p.get_array_size()))
            else:
                if self.singleton:
                    inib = "INIB" if self.has_INIB() else "CB"
                    f.print("#define NEP_{}   ({}_SINGLE_CELL_{}.n_{})\n".format(
                        p.get_name(), self.global_name, inib, p.get_name()))
                else:
                    inib = "->_inib" if (self.has_CB() and self.has_INIB()) else ""
                    f.print("#define NEP_{}           ((p_cellcb){}->n_{})\n".format(
                        p.get_name(), inib, p.get_name()))

    def gen_ph_test_optional_call_port(self, f):
        b_comment = False
        if self.singleton:
            inib = "INIB" if self.has_INIB() else "CB"
        else:
            inib = "->_inib" if (self.has_CB() and self.has_INIB()) else ""
        for p in self.port:
            if p.get_port_type() != "CALL":
                continue
            if not p.is_optional():
                continue
            if not b_comment:
                f.printf(TECSMsg.get("TOCP_comment"), "#_TOCP_#")
                b_comment = True
            if self.singleton:
                param = ""
                delim = ""
            else:
                param = "p_that"
                delim = ","
            if p.get_array_size() is not None:
                param = param + delim + "subscript"
            f.print("#define {}_is_{}_joined({}) \\\n".format(
                self.global_name, p.get_name(), param))
            if p.is_omit():
                f.print("   omit  is_{}_joined\n".format(p.get_name()))
                continue
            if not p.is_VMT_useless():
                if p.is_dynamic():
                    inib_tmp = "CB" if self.singleton else ""
                else:
                    inib_tmp = inib
                if p.get_array_size() is None:
                    if self.singleton:
                        f.print("\t  ({}_SINGLE_CELL_{}.{}!=0)\n".format(
                            self.global_name, inib_tmp, p.get_name()))
                    else:
                        f.print("\t  ((p_that){}->{}!=0)\n".format(inib_tmp, p.get_name()))
                else:
                    if self.singleton:
                        f.print("\t  (({}_SINGLE_CELL_{}.{}!=0) \\\n".format(
                            self.global_name, inib_tmp, p.get_name()))
                        f.print("\t  &&({}_SINGLE_CELL_{}.{}[subscript]!=0))\n".format(
                            self.global_name, inib_tmp, p.get_name()))
                    else:
                        f.print("\t  (((p_that){}->{}!=0)\\\n".format(inib_tmp, p.get_name()))
                        f.print("\t  &&((p_that){}->{}[subscript]!=0))\n".format(
                            inib_tmp, p.get_name()))
            else:
                if p.get_real_callee_port():
                    f.print("\t  (1)\n")
                else:
                    f.print("\t  (0)    /* not joined */\n")

    def gen_ph_test_optional_call_port_abbrev(self, f):
        b_comment = False
        for p in self.port:
            if p.get_port_type() != "CALL":
                continue
            if not p.is_optional():
                continue
            if not b_comment:
                f.printf(TECSMsg.get("TOCPA_comment"), "#_TOCPA_#")
                b_comment = True
            if self.singleton:
                param = ""
                delim = ""
            else:
                param = "p_cellcb"
                delim = ","
            if p.get_array_size() is None:
                subscript = ""
            else:
                subscript = "subscript"
                param = param + delim + subscript
            f.print("#define is_{}_joined({})\\\n\t\t{}_is_{}_joined({})\n".format(
                p.get_name(), subscript, self.global_name, p.get_name(), param))

    def gen_ph_get_cellcb(self, f):
        f.printf(TECSMsg.get("GCB_comment"), "#_GCB_#")
        if (not self.has_CB() and not self.has_INIB()) or self.singleton:
            f.print("#define {}_GET_CELLCB(idx) ((void *)0)\n".format(self.global_name))
        elif self.idx_is_id_act:
            f.print(
                "#define {}_GET_CELLCB(idx) ({}_CB_ptab[(idx) - {}_ID_BASE])\n".format(
                    self.global_name, self.global_name, self.global_name
                )
            )
        else:
            f.print("#define {}_GET_CELLCB(idx) (idx)\n".format(self.global_name))

    def gen_ph_get_cellcb_abbrev(self, f):
        f.printf(TECSMsg.get("GCBA_comment"), "#_GCBA_#")
        f.print("#define GET_CELLCB(idx)  {}_GET_CELLCB(idx)\n\n".format(self.global_name))
        f.printf(TECSMsg.get("CCT_comment"), "#_CCT_#")
        f.print("#define CELLCB\t{}_CB\n\n".format(self.global_name))
        f.printf(TECSMsg.get("CTIXA_comment"), "#_CTIXA_#")
        f.print("#define CELLIDX\t{}_IDX\n\n".format(self.global_name))
        if self.name != self.global_name:
            f.print("#define {}_IDX  {}_IDX\n".format(self.name, self.global_name))

    def gen_ph_attr_access(self, f):
        if self.n_attribute_rw > 0 or self.n_attribute_ro > 0:
            f.printf(TECSMsg.get("AAM_comment"), "#_AAM_#")
        for a in self.attribute:
            if a.is_omit():
                continue
            f.print("#define ")
            if self.singleton:
                inib = "INIB" if self.has_INIB() else "CB"
                f.printf("%-20s", "{}_ATTR_{}".format(self.global_name, a.get_name()))
                f.print("\t({}_SINGLE_CELL_{}.{})\n".format(
                    self.global_name, inib, a.get_name()))
            else:
                inib = "->_inib" if (not a.is_rw() and self.has_CB() and self.has_INIB()) else ""
                f.printf("%-20s", "{}_ATTR_{}( p_that )".format(
                    self.global_name, a.get_name()))
                f.print("\t((p_that){}->{})\n".format(inib, a.get_name()))
        f.print("\n")
        for a in self.attribute:
            if a.is_omit():
                continue
            if self.singleton:
                inib = "INIB" if self.has_INIB() else "CB"
            else:
                inib = "->_inib" if (not a.is_rw() and self.has_CB() and self.has_INIB()) else ""
            f.print("#define ")
            if self.singleton:
                f.printf("%-20s", "{}_GET_{}()".format(self.global_name, a.get_name()))
                f.print("\t({}_SINGLE_CELL_{}.{})\n".format(
                    self.global_name, inib, a.get_name()))
            else:
                f.printf("%-20s", "{}_GET_{}(p_that)".format(
                    self.global_name, a.get_name()))
                f.print("\t((p_that){}->{})\n".format(inib, a.get_name()))
            if a.is_rw():
                f.print("#define ")
                if self.singleton:
                    f.printf("%-20s", "{}_SET_{}(val)".format(self.global_name, a.get_name()))
                    f.print("\t({}_SINGLE_CELL_{}.{} = (val))\n".format(
                        self.global_name, inib, a.get_name()))
                else:
                    f.printf("%-20s", "{}_SET_{}(p_that,val)".format(
                        self.global_name, a.get_name()))
                    f.print("\t((p_that){}->{}=(val))\n".format(inib, a.get_name()))
        f.print("\n")
        if self.n_var > 0:
            f.printf(TECSMsg.get("VAM_comment"), "#_VAM_#")
        for v in self.var:
            if v.is_omit():
                continue
            if self.singleton:
                inib = "INIB" if (v.get_size_is() and self.has_INIB()) else "CB"
            else:
                inib = "->_inib" if (v.get_size_is() and self.has_CB() and self.has_INIB()) else ""
            f.print("#define ")
            if self.singleton:
                f.printf("%-20s", "{}_VAR_{}".format(self.global_name, v.get_name()))
                f.print("\t({}_SINGLE_CELL_{}.{})\n".format(
                    self.global_name, inib, v.get_name()))
            else:
                f.printf("%-20s", "{}_VAR_{}(p_that)".format(
                    self.global_name, v.get_name()))
                f.print("\t((p_that){}->{})\n".format(inib, v.get_name()))
        f.print("\n")
        for v in self.var:
            if v.is_omit():
                continue
            f.print("#define ")
            if self.singleton:
                f.printf("%-20s", "{}_GET_{}()".format(self.global_name, v.get_name()))
                f.print("\t({}_SINGLE_CELL_CB.{})\n".format(self.global_name, v.get_name()))
            else:
                f.printf("%-20s", "{}_GET_{}(p_that)".format(
                    self.global_name, v.get_name()))
                f.print("\t((p_that)->{})\n".format(v.get_name()))
            f.print("#define ")
            if self.singleton:
                f.printf("%-20s", "{}_SET_{}(val)".format(self.global_name, v.get_name()))
                f.print("\t({}_SINGLE_CELL_CB.{}=(val))\n".format(
                    self.global_name, v.get_name()))
            else:
                f.printf("%-20s", "{}_SET_{}(p_that,val)".format(
                    self.global_name, v.get_name()))
                f.print("\t((p_that)->{}=(val))\n".format(v.get_name()))
        f.print("\n")

    def gen_ph_attr_access_abbrev(self, f):
        if self.n_attribute_rw > 0 or self.n_attribute_ro > 0:
            f.printf(TECSMsg.get("AAMA_comment"), "#_AAMA_#")
        for a in self.attribute:
            if a.is_omit():
                continue
            f.print("#define ")
            f.printf("%-20s", "ATTR_{}".format(a.get_name()))
            f.print(" {}_ATTR_{}".format(self.global_name, a.get_name()))
            if not self.singleton:
                f.print("( p_cellcb )")
            f.print("\n")
        f.print("\n")
        if self.n_var > 0:
            f.printf(TECSMsg.get("VAMA_comment"), "#_VAMA_#")
        for v in self.var:
            if v.is_omit():
                continue
            f.print("#define ")
            f.printf("%-20s", "VAR_{}".format(v.get_name()))
            f.print(" {}_VAR_{}".format(self.global_name, v.get_name()))
            if not self.singleton:
                f.print("( p_cellcb )")
            f.print("\n")
        f.print("\n")

    def gen_ph_cp_fun_macro(self, f, b_flow):
        if self.n_call_port > 0 and b_flow is False:
            f.printf(TECSMsg.get("CPM_comment"), "#_CPM_#")
        for p in self.port:
            if p.get_port_type() != "CALL":
                continue
            if p.is_omit():
                continue
            for fun in p.get_signature().get_function_head_array():
                if self.singleton:
                    inib = "INIB" if self.has_INIB() else "CB"
                    if p.is_dynamic() and p.get_array_size() is None:
                        inib = "CB"
                else:
                    inib = "->_inib" if (self.has_CB() and self.has_INIB()) else ""
                    if p.is_dynamic() and p.get_array_size() is None:
                        inib = ""
                f.print("#define {}_{}_{}(".format(
                    self.global_name, p.get_name(), fun.get_name()))
                ft = fun.get_declarator().get_type()
                delim = ""
                if not self.singleton:
                    f.print("{} p_that".format(delim))
                    delim = ","
                if p.get_array_size() is not None:
                    f.print("{} subscript".format(delim))
                    delim = ","
                for param in ft.get_paramlist().get_items():
                    f.print("{} {}".format(delim, param.get_name()))
                    delim = ","
                f.print(" ) \\\n")
                subsc = "[subscript]" if p.get_array_size() is not None else ""
                delim = ""
                if b_flow:
                    f.print("\t  (p_that)->{}{}.{}__T( \\\n".format(
                        p.get_name(), subsc, fun.get_name()))
                elif not p.is_VMT_useless():
                    if self.singleton:
                        f.print("\t  {}_SINGLE_CELL_{}.{}".format(
                            self.global_name, inib, p.get_name()))
                    else:
                        f.print("\t  (p_that){}->{}".format(inib, p.get_name()))
                    f.print("{}->VMT->{}__T( \\\n".format(
                        subsc, fun.get_name()))
                else:
                    p2 = p.get_real_callee_port()
                    if p2:
                        ct = p2.get_celltype()
                        if p.is_skelton_useless():
                            f.print("\t  {}_{}_{}( \\\n".format(
                                ct.get_global_name(), p2.get_name(), fun.get_name()))
                        else:
                            f.print("\t  {}_{}_{}_skel( \\\n".format(
                                ct.get_global_name(), p2.get_name(), fun.get_name()))
                    else:
                        rettype = ft.get_type()
                        f.print("\t  (({}{} (*)()".format(
                            rettype.get_type_str(), rettype.get_type_str_post()))
                        f.print(")0)()\n")
                        f.print("\t  /* optional no entry port joined */\n")
                        if not p.is_optional():
                            raise Exception(
                                "unjoined but not optional celltype: {} {}".format(
                                    self.name, p.get_name()))
                b_join = True
                if b_flow:
                    pass
                elif not p.is_skelton_useless() and not p.is_cell_unique():
                    if self.singleton:
                        f.print("\t  {}_SINGLE_CELL_{}.{}{}".format(
                            self.global_name, inib, p.get_name(), subsc))
                        delim = ","
                    else:
                        f.print("\t   (p_that){}->{}{}".format(
                            inib, p.get_name(), subsc))
                        delim = ","
                else:
                    c2 = p.get_real_callee_cell()
                    p2 = p.get_real_callee_port()
                    if p2:
                        ct = p2.get_celltype()
                        if not ct.is_singleton():
                            if ct.has_CB() or ct.has_INIB():
                                if p.is_cell_unique():
                                    name_array = ct.get_name_array(c2)
                                    f.print("\t   {}".format(name_array[7]))
                                else:
                                    f.print("\t   (p_that){}->{}{}".format(
                                        inib, p.get_name(), subsc))
                            else:
                                f.print("\t   ({}_IDX)0".format(ct.get_global_name()))
                            delim = ","
                        else:
                            f.print("\t   ")
                    else:
                        b_join = False
                if b_join:
                    for param in ft.get_paramlist().get_items():
                        f.print("{} ({})".format(delim, param.get_name()))
                        delim = ","
                    f.print(" )\n")
        f.print("\n")

    def gen_ph_cp_fun_macro_abbrev(self, f):
        if self.n_call_port > 0:
            f.printf(TECSMsg.get("CPMA_comment"), "#_CPMA_#")
        for p in self.port:
            if p.get_port_type() != "CALL":
                continue
            for fun in p.get_signature().get_function_head_array():
                if p.is_VMT_useless() and not self.singleton:
                    dummy_p_cell_access_pre = "((void)p_cellcb, "
                    dummy_p_cell_access_post = ")"
                else:
                    dummy_p_cell_access_pre = ""
                    dummy_p_cell_access_post = ""
                if not p.is_require() or p.has_name():
                    f.print("#define {}_{}(".format(p.get_name(), fun.get_name()))
                else:
                    f.print("#define {}(".format(fun.get_name()))
                ft = fun.get_declarator().get_type()
                delim = ""
                if p.get_array_size() is not None:
                    f.print("{} subscript".format(delim))
                    delim = ","
                for param in ft.get_paramlist().get_items():
                    f.print("{} {}".format(delim, param.get_name()))
                    delim = ","
                f.print(" ) \\\n")
                if p.is_omit():
                    f.print("          {}omitted {}_{}(".format(
                        dummy_p_cell_access_pre, p.get_name(), fun.get_name()))
                else:
                    f.print("          {}{}_{}_{}(".format(
                        dummy_p_cell_access_pre, self.global_name,
                        p.get_name(), fun.get_name()))
                ft = fun.get_declarator().get_type()
                delim = ""
                if not self.singleton:
                    f.print("{} p_cellcb".format(delim))
                    delim = ","
                if p.get_array_size() is not None:
                    f.print("{} subscript".format(delim))
                    delim = ","
                for param in ft.get_paramlist().get_items():
                    f.print("{} {}".format(delim, param.get_name()))
                    delim = ","
                f.print(" ){}".format(dummy_p_cell_access_post))
                f.print("\n")
        f.print("\n")

    def gen_ph_ref_desc_func(self, f):
        if self.n_call_port_ref_desc > 0:
            f.printf(TECSMsg.get("CRD_comment"), "#_CRD_#")
        inib = "->_inib" if (self.has_CB() and self.has_INIB()) else ""
        for p in self.port:
            if p.get_port_type() != "CALL":
                continue
            if not p.is_ref_desc():
                continue
            if self.singleton:
                p_that = ""
                p_cellcb = ""
                delim = ""
                if self.has_INIB():
                    cb = "{}_SINGLE_CELL_INIB.".format(self.global_name)
                else:
                    cb = "{}_SINGLE_CELL_CB.".format(self.global_name)
            else:
                p_that = "{}_CB  *p_that".format(self.global_name)
                p_cellcb = "    {}_CB *p_cellcb = p_that;\n".format(self.global_name)
                delim = ", "
                cb = "p_cellcb{}->".format(inib)
            if p.get_array_size() is not None:
                array = "{}int_t  i ".format(delim)
                array2 = "[ i ]"
                assert_ = "    assert( 0 <= i && i < NCP_{} );\n".format(p.get_name())
            else:
                array = ""
                array2 = ""
                assert_ = ""
            sig = p.get_signature().get_global_name()
            f.print(
                "/* [ref_desc] {} */\n"
                "Inline Descriptor( {} )\n"
                "{}_{}_refer_to_descriptor( {}{} )\n"
                "{{\n"
                "    Descriptor( {} )  des;\n"
                "{}    /* cast is ncecessary for removing 'const'  */\n"
                "{}    des.vdes = (struct tag_{}_VDES *){}{}{};\n"
                "    return des;\n"
                "}}\n"
                "\n".format(
                    p.get_name(), sig, self.global_name, p.get_name(), p_that, array,
                    sig, p_cellcb, assert_, sig, cb, p.get_name(), array2))

    def gen_ph_set_desc_func(self, f):
        if self.n_call_port_dynamic > 0:
            f.printf(TECSMsg.get("SDF_comment"), "#_SDF_#")
        for p in self.port:
            if p.get_port_type() != "CALL":
                continue
            if not p.is_dynamic():
                continue
            if self.has_CB() and self.has_INIB() and p.get_array_size() is not None:
                inib = "->_inib"
            else:
                inib = ""
            if self.singleton:
                p_that = ""
                p_that2 = ""
                p_cellcb = ""
                if p.get_array_size() is not None and G.rom:
                    cb = "{}_SINGLE_CELL_INIB.".format(self.global_name)
                else:
                    cb = "{}_SINGLE_CELL_CB.".format(self.global_name)
            else:
                p_that = "{}_CB  *p_that, ".format(self.global_name)
                p_that2 = "{}_CB  *p_that ".format(self.global_name)
                p_cellcb = "    {}_CB *p_cellcb = p_that;\n".format(self.global_name)
                cb = "(p_cellcb)->{}".format(inib)
            if p.get_array_size() is not None:
                array = "int_t  i, "
                array2 = "[ i ]"
                array3 = " int_t  i "
                assert2 = "    assert( 0 <= i && i < NCP_{} );\n".format(p.get_name())
            else:
                array = ""
                array2 = ""
                array3 = ""
                assert2 = ""
            sig = p.get_signature().get_global_name()
            f.print(
                "/* [dynamic] {} */\n"
                "Inline void\n"
                "{}_{}_set_descriptor( {}{}Descriptor( {} ) des )\n"
                "{{\n"
                "{}    assert( des.vdes != NULL );\n"
                "{}    {}{}{} = des.vdes;\n"
                "}}\n"
                "\n".format(
                    p.get_name(), self.global_name, p.get_name(), p_that, array, sig,
                    p_cellcb, assert2, cb, p.get_name(), array2))
            if p.is_optional():
                if p_that2 != "" and array3 != "":
                    delim = ", "
                else:
                    delim = ""
                f.print(
                    "/* [dynamic,optional] {} */\n"
                    "Inline void\n"
                    "{}_{}_unjoin( {}{}{} )\n"
                    "{{\n"
                    "{}    {}{}{} = NULL;\n"
                    "}}\n"
                    "\n".format(
                        p.get_name(), self.global_name, p.get_name(),
                        p_that2, delim, array3, p_cellcb, cb, p.get_name(), array2))

    def gen_ph_ref_desc_macro_abbrev(self, f):
        if self.n_call_port_ref_desc > 0:
            f.printf(TECSMsg.get("CRDA_comment"), "#_CRDA_#")
        for p in self.port:
            if p.get_port_type() != "CALL":
                continue
            if not p.is_ref_desc():
                continue
            if self.singleton:
                p_cellcb = ""
                delim = ""
            else:
                p_cellcb = "p_cellcb"
                delim = ", "
            if p.get_array_size() is not None:
                array = " i "
                array2 = delim + "i"
            else:
                array = ""
                array2 = ""
            f.printf(
                "#define %s_refer_to_descriptor(%s)\\\n"
                "          %s_%s_refer_to_descriptor( %s%s )\n",
                p.get_name(), array, self.global_name, p.get_name(), p_cellcb, array2)
            f.printf(
                "#define %s_ref_desc(%s)\\\n"
                "          %s_refer_to_descriptor(%s)\n",
                p.get_name(), array, p.get_name(), array)
        f.print("\n")

    def gen_ph_set_desc_macro_abbrev(self, f):
        if self.n_call_port_dynamic > 0:
            f.printf(TECSMsg.get("SDMA_comment"), "#_SDMA_#")
        if self.singleton:
            p_cellcb = ""
            delim = ""
        else:
            p_cellcb = "p_cellcb"
            delim = ", "
        for p in self.port:
            if p.get_port_type() != "CALL":
                continue
            if not p.is_dynamic():
                continue
            if p.get_array_size() is not None:
                subsc = "i, "
                subsc2 = "i"
                subsc3 = delim + subsc2
            else:
                subsc = ""
                subsc2 = ""
                subsc3 = ""
            f.printf(
                "#define %s_set_descriptor( %sdesc )\\\n"
                "          %s_%s_set_descriptor( %s%s%sdesc )\n",
                p.get_name(), subsc, self.global_name, p.get_name(), p_cellcb, delim, subsc)
            f.printf(
                "#define %s_unjoin( %s )\\\n"
                "          %s_%s_unjoin( %s%s )\n",
                p.get_name(), subsc2, self.global_name, p.get_name(), p_cellcb, subsc3)
        f.print("\n")

    def gen_ph_ep_fun_macro(self, f):
        if self.n_entry_port > 0:
            f.printf(TECSMsg.get("EPM_comment"), "#_EPM_#")
        for p in self.port:
            if p.get_port_type() != "ENTRY":
                continue
            if p.is_omit():
                continue
            for fun in p.get_signature().get_function_head_array():
                f.printf(
                    "#define %-16s %s\n",
                    "{}_{}".format(p.get_name(), fun.get_name()),
                    "{}_{}_{}".format(self.global_name, p.get_name(), fun.get_name()),
                )
        f.print("\n")

    def gen_ph_typedef_idx(self, f):
        f.printf(TECSMsg.get("CTIX_comment"), "#_CTIX_#")
        if self.idx_is_id_act:
            f.print("typedef ID {}_IDX;\n".format(self.global_name))
        elif self.has_CB():
            f.print("typedef struct tag_{}_CB *{}_IDX;\n".format(
                self.global_name, self.global_name))
        elif self.has_INIB():
            f.print("typedef const struct tag_{}_INIB *{}_IDX;\n".format(
                self.global_name, self.global_name))
        else:
            f.print("typedef int   {}_IDX;\n".format(self.global_name))

    def gen_ph_ep_fun_prototype(self, f):
        if self.n_entry_port > 0:
            f.printf(TECSMsg.get("EPP_comment"), "#_EPP_#")
        for p in self.port:
            if p.get_port_type() != "ENTRY":
                continue
            if p.is_omit():
                continue
            f.print("/* {} */\n".format(p.get_signature().get_global_name()))
            for fun in p.get_signature().get_function_head_array():
                if p.is_inline():
                    f.print("Inline ")
                functype = fun.get_declarator().get_type()
                f.printf("%-12s", functype.get_type_str())
                f.print(" {}_{}_{}(".format(
                    self.global_name, p.get_name(), fun.get_name()))
                if self.singleton:
                    delim = ""
                else:
                    f.print("{}_IDX idx".format(self.global_name))
                    delim = ","
                if p.get_array_size() is not None:
                    f.print("{} int_t subscript".format(delim))
                    delim = ","
                paramlist = functype.get_paramlist()
                if paramlist:
                    items = paramlist.get_items()
                else:
                    items = []
                for param in items:
                    f.print("{} ".format(delim))
                    delim = ","
                    f.print(param.get_type().get_type_str())
                    f.print(" ")
                    f.print(param.get_name())
                    f.print(param.get_type().get_type_str_post())
                f.print(");\n")

    def gen_ph_ep_skel_prototype(self, f):
        if self.n_entry_port > 0:
            f.printf(TECSMsg.get("EPSP_comment"), "#_EPSP_#")
        for p in self.port:
            if p.get_port_type() != "ENTRY":
                continue
            if p.is_omit():
                continue
            if p.is_skelton_useless():
                continue
            f.print("/* {} */\n".format(p.get_name()))
            for fun in p.get_signature().get_function_head_array():
                functype = fun.get_declarator().get_type()
                f.printf("%-14s", functype.get_type_str())
                f.print(" {}_{}_{}_skel(".format(
                    self.global_name, p.get_name(), fun.get_name()))
                f.print(" const struct tag_{}_VDES *epd".format(
                    p.get_signature().get_global_name()))
                delim = ","
                paramlist = functype.get_paramlist()
                if paramlist:
                    items = paramlist.get_items()
                else:
                    items = []
                for param in items:
                    f.print("{} ".format(delim))
                    delim = ","
                    f.print(param.get_type().get_type_str())
                    f.print(" ")
                    f.print(param.get_name())
                    f.print(param.get_type().get_type_str_post())
                f.print(");\n")
        f.print("\n")

    def gen_ph_cell_cb_type(self, f):
        if G.rom:
            if self.has_INIB():
                f.printf(TECSMsg.get("CIP_comment"), "#_CIP_#")
                f.print("typedef const struct tag_{}_INIB {{\n".format(self.global_name))
                self.gen_cell_cb_type_port(f, "INIB")
                self.gen_cell_cb_type_attribute(f, "INIB")
                f.print("}}  {}_INIB;\n".format(self.global_name))
            if self.has_CB():
                f.printf(TECSMsg.get("CCTPA_comment"), "#_CCTPA_#")
                f.print("typedef struct tag_{}_CB {{\n".format(self.global_name))
                if self.has_INIB():
                    f.print("    {}_INIB  *_inib;\n".format(self.global_name))
                self.gen_cell_cb_type_port(f, "CB_DYNAMIC")
                self.gen_cell_cb_type_attribute(f, "CB")
                self.gen_cell_cb_type_var(f)
                f.print("}}  {}_CB;\n".format(self.global_name))
            if not self.has_CB() and not self.has_INIB():
                f.printf(TECSMsg.get("CCDP_comment"), "#_CCDP_#")
                f.print("typedef struct tag_{}_CB {{\n".format(self.global_name))
                f.print("    int  dummy;\n")
                f.print("}} {}_CB;\n".format(self.global_name))
        else:
            f.printf(TECSMsg.get("CCTPO_comment"), "#_CCTPO_#")
            f.print("typedef struct tag_{}_CB {{\n".format(self.global_name))
            self.gen_cell_cb_type_port(f, "CB")
            self.gen_cell_cb_type_attribute(f, "CB")
            self.gen_cell_cb_type_var(f)
            f.print("}}  {}_CB;\n".format(self.global_name))

    def gen_cell_cb_type_attribute(self, f, inib_cb):
        if inib_cb == "INIB" and self.n_attribute_ro > 0:
            f.print("    /* attribute(RO) #_ATO_# */ \n")
        elif inib_cb == "CB":
            if G.rom:
                if self.n_attribute_rw > 0:
                    f.print("    /* attribute(RW) #_ATW_# */ \n")
            else:
                if self.n_attribute_rw > 0 or self.n_attribute_ro > 0:
                    f.print("    /* attribute #_AT_# */ \n")
        from tecslib.core.types import PtrType
        for a in self.attribute:
            if a.is_omit():
                continue
            if inib_cb == "INIB" and a.is_rw():
                continue
            if self.has_INIB() and inib_cb == "CB" and not a.is_rw():
                continue
            if isinstance(a.get_type(), PtrType) and not a.get_type().is_const() and a.get_size_is():
                const_str = "const "
            else:
                const_str = ""
            f.print("    ")
            f.printf("{}{:<14s}".format(const_str, a.get_type().get_type_str()))
            f.print(" {}{};\n".format(a.get_name(), a.get_type().get_type_str_post()))
        for v in self.var:
            if v.is_omit():
                continue
            if v.get_size_is() is None:
                continue
            if G.rom and inib_cb == "CB":
                continue
            f.print("    ")
            f.printf("%-14s", v.get_type().get_type_str())
            f.print(" {}{};\n".format(v.get_name(), v.get_type().get_type_str_post()))

    def gen_cell_cb_type_var(self, f):
        if self.n_var > 0:
            f.print("    /* var #_VA_# */ \n")
        for v in self.var:
            if v.is_omit():
                continue
            if v.get_size_is() is not None:
                continue
            f.print("    ")
            f.printf("%-14s", v.get_type().get_type_str())
            f.print(" {}{};\n".format(v.get_name(), v.get_type().get_type_str_post()))

    def gen_cell_cb_type_port(self, f, inib_cb):
        self.gen_cell_cb_type_call_port(f, inib_cb)
        self.gen_cell_cb_type_entry_port(f, inib_cb)

    def gen_cell_cb_type_call_port(self, f, inib_cb):
        if self.n_call_port > 0:
            f.print("    /* call port #_TCP_# */\n")
        for p in self.port:
            if p.get_port_type() != "CALL":
                continue
            if p.is_omit():
                continue
            if inib_cb == "INIB" and p.is_dynamic() and p.get_array_size() is None and not G.ram_initializer:
                continue
            if inib_cb == "CB_DYNAMIC" and (not p.is_dynamic() or p.get_array_size() is not None):
                continue
            ptr = "*" if p.get_array_size() else ""
            if not p.is_cell_unique():
                const = "" if p.is_dynamic() else "const"
                if inib_cb == "INIB" and p.is_dynamic() and p.get_array_size() is None and G.ram_initializer:
                    init = "_init_"
                    const2 = "const"
                else:
                    init = ""
                    const2 = "const"
                if not p.is_skelton_useless():
                    if inib_cb == "INIB" and p.is_dynamic() and p.get_array_size() is not None and G.ram_initializer:
                        f.print(
                            "    struct tag_{}_VDES {}{}*{}_init_; /* TCP_1 */\n".format(
                                p.get_signature().get_global_name(), ptr, const2, p.get_name()))
                    f.print(
                        "    struct tag_{}_VDES {}{}*{}{}; /* TCP_2 */\n".format(
                            p.get_signature().get_global_name(), ptr, const, p.get_name(), init))
                    if p.get_array_size() == "[]":
                        f.print("    int_t n_{};  /* TCP_3 */\n".format(p.get_name()))
                else:
                    if p.get_real_callee_cell():
                        f.print("    ", end="")
                        p.get_real_callee_cell().get_celltype().gen_ph_idx_type(f)  # noqa: E501
                        f.print(" {} {}{};  /* TCP_4 */\n".format(const, ptr, p.get_name()))
                        if p.get_array_size() == "[]":
                            f.print("    int_t n_{};  /* TCP_5 */\n".format(p.get_name()))

    def gen_cell_cb_type_entry_port(self, f, inib_cb):
        if self.n_entry_port > 0:
            f.print("    /* call port #_NEP_# */ \n")
        for p in self.port:
            if p.get_port_type() == "ENTRY" and p.get_array_size() == "[]":
                f.print("    int_t n_{};\n".format(p.get_name()))

    def gen_ph_idx_type(self, f):
        if self.idx_is_id_act:
            f.print("ID")
        elif self.has_CB():
            f.print("struct tag_{}_CB *".format(self.global_name))
        elif self.has_INIB():
            f.print("const struct tag_{}_INIB *".format(self.global_name))
        else:
            f.print("int")

    def get_name_array(self, cell):
        if self.singleton:
            cell_CB_name = "{}_SINGLE_CELL_CB".format(self.global_name)
            cell_CB_INIT = cell_CB_name
            cell_CB_proto = "{}_SINGLE_CELL_CB".format(self.global_name)
            cell_INIB_name = "{}_SINGLE_CELL_INIB".format(self.global_name)
            cell_INIB_proto = cell_INIB_name
            cell_ID = 0
        else:
            if not self.b_need_ptab:
                index = cell.get_id() - cell.get_celltype().get_id_base()
                cell_CB_name = "{}_CB_tab[{}]".format(self.global_name, index)
                cell_CB_INIT = "{}_{}_CB".format(self.global_name, cell.get_name())
                cell_CB_proto = "{}_CB_tab[]".format(self.global_name)
                cell_INIB_name = "{}_INIB_tab[{}]".format(self.global_name, index)
                cell_INIB_proto = "{}_INIB_tab[]".format(self.global_name)
            else:
                cell_CB_name = "{}_CB".format(cell.get_global_name())
                cell_CB_INIT = cell_CB_name
                cell_CB_proto = cell_CB_name
                cell_INIB_name = "{}_INIB".format(cell.get_global_name())
                cell_INIB_proto = cell_INIB_name
            cell_ID = cell.get_id()
        if self.has_CB():
            cell_CBP = "&{}".format(cell_CB_name)
        elif self.has_INIB():
            cell_CBP = "&{}".format(cell_INIB_name)
        else:
            cell_CBP = "(({}_IDX)0)".format(self.global_name)
        if self.idx_is_id_act:
            cell_IDX = cell_ID
        else:
            cell_IDX = cell_CBP
        name_array = [None] * 12
        name_array[0] = self.name
        name_array[1] = cell.get_name()
        name_array[2] = cell_CB_name
        name_array[3] = cell_CB_INIT
        name_array[4] = cell_CB_proto
        name_array[5] = cell_INIB_name
        name_array[6] = cell_ID
        name_array[7] = cell_IDX
        name_array[8] = cell_CBP
        name_array[9] = self.global_name
        name_array[10] = cell.get_global_name()
        name_array[11] = cell_INIB_proto
        return name_array

    def gen_ph_extern_cell(self, f):
        if self.singleton:
            f.printf(TECSMsg.get("SCP_comment"), "#_SCP_#")
            if self.has_CB():
                f.print("extern  {}_CB  {}_SINGLE_CELL_CB;\n".format(
                    self.global_name, self.global_name))
            if self.has_INIB():
                f.print("extern  {}_INIB  {}_SINGLE_CELL_INIB;\n".format(
                    self.global_name, self.global_name))
            f.print("\n")
        elif self.b_need_ptab:
            f.printf(TECSMsg.get("SCP_comment"), "#_MCPP_#")
            if self.has_CB():
                f.print("extern {}_CB  *const {}_CB_ptab[];\n".format(
                    self.global_name, self.global_name))
                for c in self.ordered_cell_list:
                    if c.is_generate():
                        name_array = self.get_name_array(c)
                        f.print("extern {}_CB  {};\n".format(
                            self.global_name, name_array[4]))
            elif self.has_INIB():
                f.print("extern {}_INIB  *const {}_INIB_ptab[];\n".format(
                    self.global_name, self.global_name))
                for c in self.ordered_cell_list:
                    if c.is_generate():
                        name_array = self.get_name_array(c)
                        f.print("extern {}_INIB  {};\n".format(
                            self.global_name, name_array[11]))
        else:
            f.printf(TECSMsg.get("SCP_comment"), "#_MCPB_#")
            if self.has_CB():
                f.print("extern {}_CB  {}_CB_tab[];\n".format(
                    self.global_name, self.global_name))
            elif self.has_INIB():
                f.print("extern {}_INIB  {}_INIB_tab[];\n".format(
                    self.global_name, self.global_name))

    def gen_ph_INIB_as_CB(self, f):
        if not self.has_CB() and self.has_INIB():
            f.printf(TECSMsg.get("DCI_comment"), "#_DCI_#")
            if self.singleton:
                f.print("#define {}_SINGLE_CELL_CB   {}_SINGLE_CELL_INIB\n".format(
                    self.global_name, self.global_name))
            elif self.b_need_ptab:
                f.print("#define {}_CB_ptab           {}_INIB_ptab\n".format(
                    self.global_name, self.global_name))
            else:
                f.print("#define {}_CB_tab           {}_INIB_tab\n".format(
                    self.global_name, self.global_name))
            f.print("#define {}_CB               {}_INIB\n".format(
                self.global_name, self.global_name))
            f.print("#define tag_{}_CB           tag_{}_INIB\n".format(
                self.global_name, self.global_name))
            f.print("\n")

    def gen_ph_foreach_cell(self, f):
        if self.singleton:
            return
        if self.has_CB() or self.has_INIB():
            if self.need_CB_initializer():
                necessity = ""
            else:
                necessity = "//"
            f.printf(TECSMsg.get("FEC_comment"), "#_FEC_#")
            if self.b_need_ptab:
                amp = ""
                tab = "ptab"
            else:
                amp = "&"
                tab = "tab"
            f.print(
                "#define FOREACH_CELL(i,p_cb)   \\\n"
                "    for( (i) = 0; (i) < {}_N_CELL; (i)++ ){{ \\\n"
                "       {}(p_cb) = {}{}_CB_{}[i];\n\n"
                "#define END_FOREACH_CELL   }}\n\n".format(
                    self.global_name, necessity, amp, self.global_name, tab))
        else:
            f.printf(TECSMsg.get("NFEC_comment"), "#_NFEC_#")
            f.print(
                "#define FOREACH_CELL(i,p_cb)   \\\n"
                "    for((i)=0;(i)<0;(i)++){\n\n"
                "#define END_FOREACH_CELL   }\n\n")

    def gen_ph_cb_initialize_macro(self, f):
        from tecslib.core.types import ArrayType, PtrType, StructType
        from tecslib.core.expression import C_EXP, Expression
        f.printf(TECSMsg.get("CIM_comment"), "#_CIM_#")
        for v in self.var:
            init = v.get_initializer()
            if isinstance(init, list):
                type_ = v.get_type()
                if isinstance(type_, PtrType):
                    t2 = ArrayType(Expression.create_integer_constant(len(init), None))
                    t2.set_type(type_.get_type())
                    type_ = t2
                f.print("extern const {} {}_{}_VAR_INIT{};\n".format(
                    type_.get_type_str(), self.global_name, v.get_name(),
                    type_.get_type_str_post()))
        if self.singleton:
            arg = "()"
            p_that = ""
            that = "{}_SINGLE_CELL_CB.".format(self.global_name)
        else:
            arg = "(p_that)"
            p_that = "(p_that)"
            that = "(p_that)->"
        if self.n_cell_gen > 0 and self.need_CB_initializer():
            b_var_init = False
            f.print("#define INITIALIZE_CB{}".format(arg))
            for v in self.var:
                init = v.get_initializer()
                if init is None:
                    continue
                b_var_init = True
                type_ = v.get_type().get_original_type()
                f.print("\\\n")
                if isinstance(init, list):
                    if isinstance(type_, ArrayType) or isinstance(type_, PtrType):
                        pre = "&"
                        post = "[0]"
                    elif isinstance(type_, StructType):
                        pre = "&"
                        post = ""
                    else:
                        pre = ""
                        post = ""
                    f.print(
                        "\tmemcpy((void*){}{}_VAR_{}{}{}, ".format(
                            pre, self.global_name, v.get_name(), p_that, post))
                    # Ruby: sizeof(#{@global_name}_#{v.get_name}_VAR_INIT)
                    f.print(
                        "(void*){}{}_{}_VAR_INIT{}, sizeof({}_{}_VAR_INIT));".format(
                            pre, self.global_name, v.get_name(), post,
                            self.global_name, v.get_name()))
                elif type(init) is C_EXP:
                    f.print("\t{}{} = {};".format(that, v.get_name(), init.get_c_exp_string()))
                else:
                    pre = "{}_ATTR_".format(self.global_name)
                    if self.singleton:
                        post = ""
                    else:
                        post = p_that
                    f.print("\t{}{} = {};".format(
                        that, v.get_name(), init.to_str(self.name_list, pre, post)))
            b_dyn_port = False
            for p in self.port:
                if p.get_port_type() != "CALL":
                    continue
                if p.is_dynamic() and G.ram_initializer:
                    if p.get_array_size() is None:
                        f.print("\\\n\t{}{} = {}_inib->{}_init_;".format(
                            that, p.get_name(), that, p.get_name()))
                    else:
                        if self.singleton or p.get_array_size() != "[]":
                            p_that_dyn = ""
                        else:
                            p_that_dyn = "(p_that)"
                        if self.singleton:
                            that_dyn = "{}_SINGLE_CELL_INIB.".format(self.global_name)
                        else:
                            that_dyn = "(p_that)->"
                        if self.has_CB():
                            init = "_init->"
                        else:
                            init = ""
                        f.printf("\\\n%-80s\\\n", "     {")
                        f.printf("%-80s\\\n", "        int_t   j;")
                        f.printf("%-80s\\\n",
                                 "        for( j = 0; j < N_CP_{}{}; j++){{".format(
                                     p.get_name(), p_that_dyn))
                        f.printf("%-80s\\\n",
                                 "            {}{}[j] = {}{}{}_init_[j];".format(
                                     that_dyn, p.get_name(), that_dyn, init, p.get_name()))
                        f.printf("%-80s\\\n", "        }")
                        f.printf("%-80s", "       }")
                    b_dyn_port = True
            if b_dyn_port:
                f.print("\n")
            if b_var_init is False and b_dyn_port is False and not self.singleton:
                f.print("\t(void)(p_that);")
            f.print("\n")
            f.print("#define SET_CB_INIB_POINTER(i,p_that)\\\n")
            if self.has_CB() and self.has_INIB():
                if self.singleton:
                    f.print("\t{}_inib = &{}_SINGLE_CELL_INIB;\n\n".format(that, self.global_name))
                elif self.b_need_ptab:
                    f.print("\t{}_inib = {}_INIB_ptab[(i)];\n\n".format(
                        that, self.global_name))
                else:
                    f.print("\t{}_inib = &{}_INIB_tab[(i)];\n\n".format(
                        that, self.global_name))
            else:
                f.print("\t/* empty */\n")

    def gen_ph_dealloc_code(self, f, append_name, b_undef=False):
        #=== send/receive で受け取ったメモリ領域を dealloc するマクロコード
        #f:: File
        #b_undef:: bool : true = #undef コードの生成,  false = #define コードの生成
        b_msg = False
        for p in self.port:
            if p.is_omit():
                continue

            def _each(port, fd, par):
                nonlocal b_msg
                direction = par.get_direction()
                if direction == "SEND":
                    # next if port.get_port_type == :CALL
                    type_ = par.get_declarator().get_type()
                    pre = "("
                    post = ")"
                elif direction == "RECEIVE":
                    # next if port.get_port_type == :ENTRY
                    type_ = par.get_declarator().get_type().get_type()
#          pre = "(*"
#          post = ")"
                    pre = "("
                    post = ")"
                else:
                    return

                #                      ポート名         関数名         パラメータ名
                dealloc_func_name = "{}_{}_{}_dealloc".format(
                    port.get_name(), fd.get_name(), par.get_name())
                dealloc_macro_name = dealloc_func_name.upper()
                name = par.get_name()

                if b_undef is False:
                    if (type_.get_size() or type_.get_count()) and type_.get_type().has_pointer():
                        count_str = "count__"
                        count_str2 = ", count__"
                    else:
                        count_str = None
                        count_str2 = None
                    if not b_msg:
                        f.print("\n")
                        f.printf(TECSMsg.get("DAL_comment"), "#_DAL_#  {}".format(append_name))
                        b_msg = True
                    f.print("#define {}{}({}{})".format(
                        dealloc_macro_name, append_name, name,
                        count_str2 if count_str2 else ""))
                    if append_name == "_RESET":
                        self.gen_dealloc_code_for_type(
                            f, type_, dealloc_func_name, pre, name, post, 0, True, count_str)
                    else:
                        self.gen_dealloc_code_for_type(
                            f, type_, dealloc_func_name, pre, name, post, 0, False, count_str)
                    f.print("\n")
                else:
                    f.print("#undef {}{}\n".format(dealloc_macro_name, append_name))

            p.each_param(_each)

    #=== decl 用の dealloc コードを生成
    #b_reset:: Bool:  リセット用の dealloc コードの生成 (NULL ポインタの場合 dealloc しない)
    # mikan string 修飾されたポインタの先にポインタが来ないと仮定。ポインタ型を持つ構造体の可能性を排除していない
    # このメソッドでは、行を出力する直前に " \\\n" を出力し、行末で改行文字を出力しない
    def gen_dealloc_code_for_type(
            self, f, type_, dealloc_func_name, pre, name, post, level, b_reset, count_str=None):
        type_ = type_.get_original_type()
        indent = "\t" + "  " * (level + 1)
        if not type_.has_pointer():
            return
        elif isinstance(type_, ArrayType):
            if type_.get_type().has_pointer():
                loop_str = "i{}__".format(level)
                count_str = "{}".format(type_.get_subscript().eval_const(None))
                f.print(" \\\n")
                f.print("{}{{ int_t  {};".format(indent, loop_str))
                f.print(" \\\n")
                f.print("{}  for( {} = 0; {} < {}; {}++ ){{ ".format(
                    indent, loop_str, loop_str, count_str, loop_str))

                self.gen_dealloc_code_for_type(
                    f, type_.get_type(), dealloc_func_name, pre, name,
                    "{}[{}]".format(post, loop_str), level + 2, b_reset)

                f.print(" \\\n")
                f.print("{}  }}".format(indent))
                f.print(" \\\n")
                f.print("{}}}".format(indent))
        elif isinstance(type_, StructType):
            members_decl = type_.get_members_decl()
            for md in members_decl.get_items():
                pre2 = pre + str(name) + post + "."
                name2 = md.get_name()
                post2 = ""
                type2 = md.get_type().get_original_type()
                if isinstance(type2, PtrType):   # mikan typedef された型
                    if type2.get_count():
                        count_str = type2.get_count().to_str(members_decl, pre2, post2)
                    elif type2.get_size():
                        count_str = type2.get_size().to_str(members_decl, pre2, post2)
                    else:
                        count_str = None
                else:
                    count_str = None
                self.gen_dealloc_code_for_type(
                    f, md.get_type(), dealloc_func_name, pre2, name2, post2, level, b_reset, count_str)

        elif isinstance(type_, PtrType):

            if b_reset or type_.is_nullable():
                nullable = ""
                if (not b_reset) and type_.is_nullable():
                    nullable = "\t/* nullable */"
                level2 = level + 1
                indent2 = indent + "  "
                f.print(" \\\n")
                f.print("{}if( {}{}{} ){{{}".format(indent, pre, name, post, nullable))
            else:
                level2 = level
                indent2 = indent

            if type_.get_type().has_pointer():
                if count_str:
                    loop_str = "i{}__".format(level)
                    f.print(" \\\n")
                    f.print("{}{{ int_t  {};".format(indent2, loop_str))
                    f.print(" \\\n")
                    f.print("{}  for( {} = 0; {} < {}; {}++ ){{ ".format(
                        indent2, loop_str, loop_str, count_str, loop_str))

                    self.gen_dealloc_code_for_type(
                        f, type_.get_type(), dealloc_func_name, pre, name,
                        "{}[{}]".format(post, loop_str), level2 + 2, b_reset)

                    f.print(" \\\n")
                    f.print("{}  }}".format(indent2))
                    f.print(" \\\n")
                    f.print("{}}}".format(indent2))
                else:
                    self.gen_dealloc_code_for_type(
                        f, type_.get_type(), dealloc_func_name,
                        "(*{}".format(pre), name, "{})".format(post), level2, b_reset)
            f.print(" \\\n")
            f.print("{}{}( {}{}{} ); ".format(indent2, dealloc_func_name, pre, name, post))

            if b_reset or type_.is_nullable():
                f.print(" \\\n")
                f.print("{}}}".format(indent))
        else:
            raise Exception("UnknownType")

    def gen_ph_inline(self, f):
        if self.n_entry_port_inline > 0:
            f.printf(TECSMsg.get("INL_comment"), "#_INL_#")
            f.print("#include \"{}_inline.{}\"\n\n".format(self.global_name, G.h_suffix))

    def gen_ph_undef(self, f):
        f.printf(TECSMsg.get("UDF_comment"), "#_UDF_#")
        f.print("#undef VALID_IDX\n")
        f.print("#undef GET_CELLCB\n")
        f.print("#undef CELLCB\n")
        f.print("#undef CELLIDX\n")
        f.print("#undef {}_IDX\n".format(self.name))
        f.print("#undef FOREACH_CELL\n")
        f.print("#undef END_FOREACH_CELL\n")
        f.print("#undef INITIALIZE_CB\n")
        f.print("#undef SET_CB_INIB_POINTER\n")
        for a in self.attribute:
            f.print("#undef ATTR_{}\n".format(a.get_name()))
            f.print("#undef {}_ATTR_{}\n".format(self.global_name, a.get_name()))
            f.print("#undef {}_GET_{}\n".format(self.global_name, a.get_name()))
        for v in self.var:
            f.print("#undef VAR_{}\n".format(v.get_name()))
            f.print("#undef VAR_{}\n".format(v.get_name()))
            f.print("#undef {}_VAR_{}\n".format(self.global_name, v.get_name()))
            f.print("#undef {}_GET_{}\n".format(self.global_name, v.get_name()))
            f.print("#undef {}_SET_{}\n".format(self.global_name, v.get_name()))
        for p in self.port:
            if p.get_port_type() != "CALL":
                continue
            if p.is_optional():
                f.print("#undef is_{}_joined\n".format(p.get_name()))
            if p.is_omit():
                continue
            for fun in p.get_signature().get_function_head_array():
                f.print("#undef {}_{}_{}\n".format(
                    self.global_name, p.get_name(), fun.get_name()))
                if not p.is_require() or p.has_name():
                    f.print("#undef {}_{}\n".format(p.get_name(), fun.get_name()))
                else:
                    f.print("#undef {}\n".format(fun.get_name()))
            if p.is_dynamic():
                f.print("#undef {}_set_descriptor\n".format(p.get_name()))
                if p.is_optional():
                    f.print("#undef {}_unjoin\n".format(p.get_name()))
            elif p.is_ref_desc():
                f.print("#undef {}_refer_to_descriptor\n".format(p.get_name()))
                f.print("#undef {}_ref_desc\n".format(p.get_name()))
        for p in self.port:
            if p.get_port_type() != "ENTRY":
                continue
            if p.is_omit():
                continue
            for fun in p.get_signature().get_function_head_array():
                f.print("#undef {}_{}\n".format(p.get_name(), fun.get_name()))
            if p.get_array_size() is not None:
                f.print("#undef NEP_{}\n".format(p.get_name()))
        self.gen_ph_dealloc_code(f, "", True)
        self.gen_ph_dealloc_code(f, "_RESET", True)
    def gen_ph_endif(self, f, post="TECSGEN"):
        f.print("#endif /* {}_{}H */\n".format(self.global_name, post))

    def generate_factory_header(self):
        f = AppFile.open("{}/{}_factory.{}".format(G.gen, self.global_name, G.h_suffix))
        f.print("#ifndef {}_FACTORY_H\n".format(self.name))
        f.print("#define {}_FACTORY_H\n".format(self.name))
        f.close()

    def generate_factory_header_post(self):
        f = AppFile.open("{}/{}_factory.{}".format(G.gen, self.global_name, G.h_suffix))
        for generate in self.generate_list:
            if generate[2]:
                generate[2].gen_factory(f)
        f.print("#endif /* {}_FACTORY_H */\n".format(self.name))
        f.close()

    def gen_cell_private_header(self, f):
        f.print("#include \"{}_tecsgen.{}\"\n".format(self.global_name, G.h_suffix))

    def gen_cell_factory_header(self, f):
        f.print("#include \"{}_factory.{}\"\n\n".format(self.global_name, G.h_suffix))

    def gen_cell_ep_des_type(self, f):
        if self.n_entry_port > 0:
            f.printf(TECSMsg.get("EDT_comment"), "#_EDT_#")
        for p in self.port:
            if p.get_port_type() != "ENTRY":
                continue
            if p.is_omit():
                continue
            if p.is_skelton_useless():
                f.print("/* {} : omitted by entry port optimize */\n\n".format(p.get_name()))
                continue
            f.print("/* {} */\n".format(p.get_name()))
            f.print("struct tag_{}_{}_DES {{\n".format(self.global_name, p.get_name()))
            f.print("    const struct tag_{}_VMT *vmt;\n".format(p.get_signature().get_global_name()))
            if self.has_CB() or self.has_INIB():
                f.print("    {}_IDX  idx;\n".format(self.name))
            else:
                f.print("    int           idx;\n")
            if p.get_array_size() is not None:
                f.print("    int_t  subscript;\n")
            f.print("};\n\n")

    def gen_cell_skel_fun(self, f):
        if self.n_entry_port > 0:
            f.printf(TECSMsg.get("EPSF_comment"), "#_EPSF_#")
        for p in self.port:
            if p.get_port_type() != "ENTRY":
                continue
            if p.is_omit():
                continue
            if p.is_skelton_useless():
                f.print("/* {} : omitted by entry port optimize */\n".format(p.get_name()))
                continue
            f.print("/* {} */\n".format(p.get_name()))
            for fun in p.get_signature().get_function_head_array():
                functype = fun.get_declarator().get_type()
                f.printf("%-14s", functype.get_type_str())
                f.print(" {}_{}_{}_skel(".format(
                    self.global_name, p.get_name(), fun.get_name()))
                f.print(" const struct tag_{}_VDES *epd".format(
                    p.get_signature().get_global_name()))
                delim = ","
                paramlist = functype.get_paramlist()
                if paramlist:
                    items = paramlist.get_items()
                else:
                    items = []
                for param in items:
                    f.print("{} ".format(delim))
                    delim = ","
                    f.print(param.get_type().get_type_str())
                    f.print(" ")
                    f.print(param.get_name())
                    f.print(param.get_type().get_type_str_post())
                f.print(")\n")
                f.print("{\n")
                if (not self.singleton) or (p.get_array_size() is not None):
                    f.print("    struct tag_{}_{}_DES *lepd\n".format(
                        self.global_name, p.get_name()))
                    f.print("        = (struct tag_{}_{}_DES *)epd;\n".format(
                        self.global_name, p.get_name()))
                if functype.get_type_str() == "void":
                    f.print("    ")
                else:
                    f.print("    return ")
                f.print("{}_{}_{}(".format(
                    self.global_name, p.get_name(), fun.get_name()))
                if self.singleton:
                    delim = ""
                else:
                    f.print(" lepd->idx")
                    delim = ","
                if p.get_array_size() is not None:
                    f.print("{} lepd->subscript".format(delim))
                    delim = ","
                for param in items:
                    f.print("{} ".format(delim))
                    delim = ","
                    f.print(param.get_name())
                f.print(" );\n")
                f.print("}\n")
        if self.n_entry_port > 0:
            f.print("\n")

    def gen_cell_fun_table(self, f):
        if self.n_entry_port > 0:
            f.printf(TECSMsg.get("EPSFT_comment"), "#_EPSFT_#")
        for p in self.port:
            if p.get_port_type() != "ENTRY":
                continue
            if p.is_omit():
                continue
            if p.is_VMT_useless():
                f.print("/* {} : omitted by entry port optimize */\n".format(p.get_name()))
                continue
            f.print("/* {} */\n".format(p.get_name()))
            f.print("const struct tag_{}_VMT".format(p.get_signature().get_global_name()))
            f.print(" {}_{}_MT_ = {{\n".format(self.global_name, p.get_name()))
            for fun in p.get_signature().get_function_head_array():
                f.print("    {}_{}_{}_skel,\n".format(
                    self.global_name, p.get_name(), fun.get_name()))
            f.print("};\n")
        f.print("\n")

    def gen_cell_var_init(self, f):
        n_init = 0
        for v in self.var:
            init = v.get_initializer()
            if init is not None and type(init) is list:
                n_init += 1
        if n_init == 0:
            return
        f.printf(TECSMsg.get("AVI_comment"), "#_AVI_#")
        for v in self.var:
            init = v.get_initializer()
            if init is None or type(init) is not list:
                continue
            type_ = v.get_type()
            org_type = v.get_type().get_original_type()
            if isinstance(org_type, PtrType):
                t2 = ArrayType(Expression.create_integer_constant(len(init), None))
                t2.set_type(type_.get_type())
                type_ = t2
                org_type = t2
            if len(self.ordered_cell_list) == 0:
                continue
            c = self.ordered_cell_list[0]
            name_array = self.get_name_array(c)
            f.print("const {}\t{}_{}_VAR_INIT{} = ".format(
                type_.get_type_str(),
                self.global_name,
                v.get_name(),
                type_.get_type_str_post(),
            ))
            if isinstance(org_type, StructType):
                str_ = self.gen_cell_cb_init(
                    f, c, name_array, type_, init, v.get_identifier(), 1, True)
            elif isinstance(org_type, (PtrType, ArrayType)):
                str_ = "{ "
                elem_type = org_type.get_type()
                for i in init:
                    str_ += self.gen_cell_cb_init(
                        f, c, name_array, elem_type, i, v.get_identifier(), 1, True)
                    str_ += ", "
                str_ += "}"
            else:
                raise Exception("Unknown Type")
            f.print(str_)
            f.print(";\n")
        f.print("\n")

    def gen_cell_ep_vdes(self, fs):
        if self.n_cell_gen > 0:
            for f in fs.values():
                f.printf(TECSMsg.get("CPEPD_comment"), "#_CPEPD_#")
        for c in self.ordered_cell_list:
            if not c.is_generate():
                continue
            f = fs[c.get_domain_class_root()]
            jl = c.get_join_list()
            for j in jl.get_items():
                definition = j.get_definition()
                if not isinstance(definition, Port):
                    continue
                port = self.find(j.get_name())
                if port.is_cell_unique() or port.is_omit():
                    continue
                am = j.get_array_member2()
                if am:
                    i = 0
                    while i < len(am):
                        j2 = am[i]
                        if j2:
                            if j2.get_rhs_cell().get_celltype() == self:
                                p = j2.get_rhs_port()
                                des_type = "const struct tag_{}_{}_DES".format(
                                    self.global_name, p.get_name())
                            else:
                                des_type = "struct tag_{}_VDES".format(
                                    definition.get_signature().get_global_name())
                            if j2.get_rhs_subscript() is not None:
                                subscript = j2.get_rhs_subscript()
                                f.printf(
                                    "extern %s %s%d;\n",
                                    des_type,
                                    "{}_des".format(j2.get_port_global_name(i)),
                                    subscript,
                                )
                            else:
                                f.printf(
                                    "extern %s %s;\n",
                                    des_type,
                                    "{}_des".format(j2.get_port_global_name(i)),
                                )
                        i += 1
                else:
                    dbgPrint(
                        "me={} callee={} {}\n".format(
                            self.name,
                            j.get_rhs_cell().get_celltype().get_name(),
                            j.get_cell().get_celltype().get_name(),
                        )
                    )
                    if j.get_rhs_cell().get_celltype() == self:
                        p = j.get_rhs_port()
                        des_type = "const struct tag_{}_{}_DES".format(
                            self.global_name, p.get_name())
                    else:
                        des_type = "struct tag_{}_VDES".format(
                            definition.get_signature().get_global_name())
                    if j.get_rhs_subscript() is not None:
                        subscript = j.get_rhs_subscript()
                        f.printf(
                            "extern %s %s%d;\n",
                            des_type,
                            "{}_des".format(j.get_port_global_name()),
                            subscript,
                        )
                    else:
                        f.printf(
                            "extern %s %s;\n",
                            des_type,
                            "{}_des".format(j.get_port_global_name()),
                        )
            f.print("\n")

    def gen_cell_ep_vdes_array(self, fs):
        if self.n_cell_gen > 0:
            for f in fs.values():
                f.printf(TECSMsg.get("CPA_comment"), "#_CPA_#")
        for c in self.ordered_cell_list:
            if not c.is_generate():
                continue
            f = fs[c.get_domain_class_root()]
            jl = c.get_join_list()
            for port in self.port:
                if port.get_port_type() != "CALL":
                    continue
                dbgPrint("gen_cell_ep_vdes_array: {}.{}\n".format(
                    c.get_name(), port.get_name()))
                j = jl.get_item(port.get_name())
                if port.is_cell_unique() or port.is_omit():
                    continue
                b_array = False
                am = None
                if j:
                    am = j.get_array_member2()
                    if am:
                        b_array = True
                else:
                    if port.get_array_size() == "[]":
                        continue
                    elif port.get_array_size() is not None:
                        b_array = True
                if not b_array:
                    continue
                const = "" if (port.is_dynamic() and not G.ram_initializer) else "const "
                init = "_init_" if (port.is_dynamic() and G.ram_initializer) else ""
                if not port.is_skelton_useless():
                    f.printf(
                        "struct %s * %s%s_%s[] = {\n",
                        "tag_{}_VDES".format(port.get_signature().get_global_name()),
                        const,
                        c.get_global_name(),
                        port.get_name() + init,
                    )
                else:
                    f.printf(
                        "%s%s_IDX  %s_%s[] = {\n",
                        const,
                        j.get_rhs_cell().get_celltype().get_global_name(),
                        c.get_global_name(),
                        j.get_name(),
                    )
                if port.get_array_size() == "[]":
                    length = len(am)
                else:
                    length = port.get_array_size()
                i = 0
                while i < length:
                    if am is None:
                        f.print("    0,\n")
                        i += 1
                        continue
                    j2 = am[i]
                    i += 1
                    if j2:
                        if j2.get_rhs_cell().get_celltype() == self:
                            definition = j2.get_definition()
                            des_type_cast = "(struct tag_{}_VDES *)".format(
                                definition.get_signature().get_global_name())
                        else:
                            des_type_cast = ""
                        if j2.get_rhs_subscript() is not None:
                            subscript = j2.get_rhs_subscript()
                            f.printf(
                                "    %s%d,\n",
                                "{}&{}_des".format(
                                    des_type_cast, j2.get_port_global_name()),
                                subscript,
                            )
                        else:
                            if not port.is_skelton_useless():
                                f.printf(
                                    "    %s,\n",
                                    "{}&{}_des".format(
                                        des_type_cast, j2.get_port_global_name()),
                                )
                            else:
                                cell = j2.get_rhs_cell()
                                name_array = cell.get_celltype().get_name_array(cell)
                                f.printf("    {},\n".format(name_array[7]))
                    else:
                        f.print("    0,\n")
                f.print("};\n")
                if port.is_dynamic() and G.ram_initializer:
                    # Ruby: struct %s * %s_%s[ #{length} ];
                    f.printf(
                        "struct %s * %s_%s[ %s ];\n",
                        "tag_{}_VDES".format(port.get_signature().get_global_name()),
                        c.get_global_name(),
                        port.get_name(),
                        length,
                    )
            f.print("\n")

    def gen_cell_cb_out_init(self, fs):
        if self.n_cell_gen == 0:
            return
        for f in fs.values():
            f.printf(TECSMsg.get("AVAI_comment"), "#_AVAI_#")
        for c in self.ordered_cell_list:
            if not c.is_generate():
                continue
            f = fs[c.get_domain_class_root()]
            name_array = self.get_name_array(c)
            ct = c.get_celltype()
            jl = c.get_join_list()
            av_list = ct.get_attribute_list() + ct.get_var_list()
            if len(av_list) == 0:
                continue
            for a in av_list:
                j = jl.get_item(a.get_identifier())
                if j:
                    init = j.get_rhs()
                else:
                    init = a.get_initializer()
                if isinstance(a.get_type(), PtrType) and (
                    (init is not None and type(init) is list) or init is None
                ):
                    ptr_type = a.get_type()
                    size = ptr_type.get_size()
                    if size:
                        sz = size.eval_const(c.get_join_list(), ct.get_name_list())
                        size = Expression.create_integer_constant(sz, None)
                        array_type = ArrayType(size)
                        type_ = a.get_type().get_referto()
                        if not type_.is_const() and a.get_kind() == "ATTRIBUTE":
                            type_.set_qualifier("CONST")
                        array_type.set_type(type_)
                        if a.get_kind() == "ATTRIBUTE":
                            f.print("const ")
                        f.printf(
                            "%s %s_%s_INIT[%d]%s",
                            a.get_type().get_referto().get_type_str(),
                            name_array[3],
                            a.get_identifier(),
                            sz,
                            a.get_type().get_referto().get_type_str_post(),
                        )
                        if not (G.ram_initializer and a.get_kind() == "VAR"):
                            if init:
                                str_ = " = {}".format(
                                    self.gen_cell_cb_init(
                                        f, c, name_array, array_type, init,
                                        a.get_identifier(), 1, True))
                                # Ruby: str.sub( /\}$/, "};\n" ) — 末尾の } のみ
                                str_ = re.sub(r"\}$", "};\n", str_)
                            else:
                                str_ = ";\n"
                            f.print(str_)
                        else:
                            f.print(";\n")

    def gen_cell_cb(self, fs):
        if self.has_INIB():
            if self.n_cell_gen > 0:
                for f in fs.values():
                    f.printf(TECSMsg.get("INIB_comment"), "#_INIB_#")
            if self.singleton:
                for f in fs.values():
                    f.print("{}_INIB {}_SINGLE_CELL_INIB = \n".format(
                        self.global_name, self.global_name))
                indent = 0
            elif not self.b_need_ptab:
                for f in fs.values():
                    f.print("{}_INIB {}_INIB_tab[] = {{\n".format(
                        self.global_name, self.global_name))
                indent = 1
            else:
                indent = 0
            for c in self.ordered_cell_list:
                if not c.is_generate():
                    continue
                f = fs[c.get_domain_class_root()]
                name_array = self.get_name_array(c)
                if not self.singleton:
                    print_indent(f, indent)
                    f.print("/* cell: {}:  {} id={} */\n".format(
                        name_array[2], name_array[1], c.get_id()))
                print_indent(f, indent)
                if self.b_need_ptab:
                    f.print("const {}_INIB {} = ".format(
                        self.global_name, name_array[5]))
                f.print("{\n")
                self.gen_cell_cb_port(c, indent, f, name_array, "INIB")
                self.gen_cell_cb_attribute(c, indent, f, name_array, "INIB")
                if not self.singleton:
                    if self.b_need_ptab:
                        f.print("};\n\n")
                    else:
                        f.print("    },\n")
            if not self.b_need_ptab:
                for f in fs.values():
                    f.print("};\n\n")
        if self.has_CB():
            if self.n_cell_gen > 0:
                for f in fs.values():
                    f.printf(TECSMsg.get("CB_comment"), "#_CB_#")
            if G.ram_initializer is False or G.rom is False:
                if self.singleton:
                    for f in fs.values():
                        f.print("struct tag_{}_CB {}_SINGLE_CELL_CB = \n".format(
                            self.global_name, self.global_name))
                    indent = 0
                elif not self.b_need_ptab:
                    for f in fs.values():
                        f.print("struct tag_{}_CB {}_CB_tab[] = {{\n".format(
                            self.global_name, self.global_name))
                    indent = 1
                else:
                    indent = 0
                for c in self.ordered_cell_list:
                    if not c.is_generate():
                        continue
                    f = fs[c.get_domain_class_root()]
                    name_array = self.get_name_array(c)
                    if not self.singleton:
                        print_indent(f, indent)
                        f.print("/* cell: {}:  {} id={} */\n".format(
                            name_array[2], name_array[1], c.get_id()))
                    print_indent(f, indent)
                    if self.b_need_ptab:
                        f.print("{}_CB {} = ".format(self.global_name, name_array[2]))
                    f.print("{\n")
                    if self.has_INIB():
                        print_indent(f, indent + 1)
                        f.printf("&%-39s /* _inib */\n", "{},".format(name_array[5]))
                    if G.rom is False:
                        self.gen_cell_cb_port(c, indent, f, name_array, "CB_ALL")
                    else:
                        self.gen_cell_cb_port(c, indent, f, name_array, "CB_DYNAMIC")
                    self.gen_cell_cb_attribute(c, indent, f, name_array, "CB")
                    self.gen_cell_cb_var(c, indent, f, name_array)
                    if not self.singleton:
                        if self.b_need_ptab:
                            f.print("};\n\n")
                        else:
                            f.print("    },\n")
                if not self.b_need_ptab:
                    for f in fs.values():
                        f.print("};\n\n")
            else:
                if self.singleton:
                    for f in fs.values():
                        f.print("struct tag_{}_CB {}_SINGLE_CELL_CB;\n".format(
                            self.global_name, self.global_name))
                elif self.b_need_ptab:
                    for c in self.ordered_cell_list:
                        if not c.is_generate():
                            continue
                        f = fs[c.get_domain_class_root()]
                        name_array = self.get_name_array(c)
                        f.print("/* cell: {}:  {} id={} */\n".format(
                            name_array[2], name_array[1], c.get_id()))
                        f.print("{}_CB {} = {{}};\n".format(
                            self.global_name, name_array[2]))
                else:
                    for f in fs.values():
                        f.print("struct tag_{}_CB {}_CB_tab[{}];\n".format(
                            self.global_name, self.global_name, self.n_cell_gen))

    def gen_cell_extern_mt(self, fs):
        for r, f in fs.items():
            if not r.is_link_root():
                for p in self.port:
                    if p.is_omit():
                        continue
                    if p.get_port_type() == "ENTRY" and not p.is_VMT_useless():
                        f.print("extern const struct tag_{}_VMT".format(
                            p.get_signature().get_global_name()))
                        f.print(" {}_{}_MT_;\n".format(
                            self.global_name, p.get_name()))

    def gen_cell_ep_des(self, fs):
        if self.n_cell_gen > 0:
            for f in fs.values():
                f.printf(TECSMsg.get("EPD_comment"), "#_EPD_#")
        index = 0
        for c in self.ordered_cell_list:
            if not c.is_generate():
                continue
            f = fs[c.get_domain_class_root()]
            name_array = self.get_name_array(c)
            port_list = c.get_celltype().get_port_list()
            if len(port_list) == 0:
                index += 1
                continue
            for p in port_list:
                if p.get_port_type() != "ENTRY":
                    continue
                if p.is_omit():
                    continue
                if p.is_skelton_useless():
                    f.print("/* {} : omitted by entry port optimize */\n".format(
                        p.get_name()))
                    continue
                length = p.get_array_size()
                if length == "[]":
                    length = c.get_entry_port_max_subscript(p) + 1
                if length is not None:
                    i = 0
                    while i < length:
                        f.print("extern const struct tag_{}_{}_DES".format(
                            self.global_name, p.get_name()))
                        f.print(" {}_{}_des{};\n".format(
                            c.get_global_name(), p.get_name(), i))
                        f.print("const struct tag_{}_{}_DES".format(
                            self.global_name, p.get_name()))
                        f.print(" {}_{}_des{} = {{\n".format(
                            c.get_global_name(), p.get_name(), i))
                        if p.is_VMT_useless():
                            f.print("    0,\n")
                        else:
                            f.print("    &{}_{}_MT_,\n".format(
                                self.global_name, p.get_name()))
                        if self.idx_is_id_act:
                            f.print("    {},           /* ID */\n".format(c.get_id()))
                        else:
                            if self.has_CB():
                                f.print("    {},      /* CB 1 */\n".format(name_array[8]))
                            elif self.has_INIB():
                                f.print("    &{},      /* INIB 1 */\n".format(name_array[5]))
                            else:
                                f.print("    0,\n")
                        f.print("    {}\n".format(i))
                        f.print("};\n")
                        i += 1
                else:
                    f.print("extern const struct tag_{}_{}_DES".format(
                        self.global_name, p.get_name()))
                    f.print(" {}_{}_des;\n".format(c.get_global_name(), p.get_name()))
                    f.print("const struct tag_{}_{}_DES".format(
                        self.global_name, p.get_name()))
                    f.print(" {}_{}_des = {{\n".format(
                        c.get_global_name(), p.get_name()))
                    if p.is_VMT_useless():
                        f.print("    0,\n")
                    else:
                        f.print("    &{}_{}_MT_,\n".format(
                            self.global_name, p.get_name()))
                    if self.idx_is_id_act:
                        f.print("    {},     /* ID */\n".format(c.get_id()))
                    else:
                        if self.has_CB():
                            f.print("    {},      /* CB 3 */\n".format(name_array[8]))
                        elif self.has_INIB():
                            f.print("    &{},      /* INIB 3 */\n".format(name_array[5]))
                        else:
                            f.print("    0,\n")
                    f.print("};\n")
            index += 1

    def gen_cell_cb_tab(self, f):
        indent = 0
        if not self.b_need_ptab:
            return
        if self.has_INIB() and (G.ram_initializer or not self.has_CB()):
            f.print("/* ID to INIB table #_INTAB_# */\n")
            for c in self.ordered_cell_list:
                if c.is_generate() and c.get_domain_class_root() != Region.get_root():
                    name_array = self.get_name_array(c)
                    print_indent(f, indent + 1)
                    f.print("extern {}_INIB  {};\n".format(
                        self.global_name, name_array[5]))
            f.print("{}_INIB *const {}_INIB_ptab[] ={{\n".format(
                self.global_name, self.global_name))
            for c in self.ordered_cell_list:
                if c.is_generate():
                    name_array = self.get_name_array(c)
                    print_indent(f, indent + 1)
                    f.print("&{},\n".format(name_array[5]))
            f.print("};\n")
        if self.has_CB():
            f.print("/* ID to CB table #_CBTAB_# */\n")
            for c in self.ordered_cell_list:
                if c.is_generate() and c.get_domain_class_root() != Region.get_root():
                    name_array = self.get_name_array(c)
                    print_indent(f, indent + 1)
                    f.print("extern {}_CB  {};\n".format(
                        self.global_name, name_array[2]))
            f.print("{}_CB *const {}_CB_ptab[] ={{\n".format(
                self.global_name, self.global_name))
            for c in self.ordered_cell_list:
                if c.is_generate():
                    name_array = self.get_name_array(c)
                    print_indent(f, indent + 1)
                    f.print("&{},\n".format(name_array[2]))
            f.print("};\n")

    def gen_cell_cb_initialize_code(self, f):
        if not self.need_CB_initializer():
            return
        f.printf(TECSMsg.get("CIC_comment"), "#_CIC_#")
        f.print("void\n{}_CB_initialize()\n{{\n".format(self.global_name))
        if self.singleton:
            f.print(
                "    SET_CB_INIB_POINTER(i,p_cb)\n"
                "    INITIALIZE_CB()\n"
            )
        else:
            f.print(
                "    {}_CB\t*p_cb;\n"
                "    int\t\ti;\n"
                "    FOREACH_CELL(i,p_cb)\n"
                "        SET_CB_INIB_POINTER(i,p_cb)\n"
                "        INITIALIZE_CB(p_cb)\n"
                "    END_FOREACH_CELL\n".format(self.global_name)
            )
        f.print("}\n")

    def get_name_array(self, cell):
        if self.singleton:
            cell_CB_name = "{}_SINGLE_CELL_CB".format(self.global_name)
            cell_CB_INIT = cell_CB_name
            cell_CB_proto = cell_CB_name
            cell_INIB_name = "{}_SINGLE_CELL_INIB".format(self.global_name)
            cell_INIB_proto = cell_INIB_name
            cell_ID = 0
        else:
            if not self.b_need_ptab:
                index = cell.get_id() - cell.get_celltype().get_id_base()
                cell_CB_name = "{}_CB_tab[{}]".format(self.global_name, index)
                cell_CB_INIT = "{}_{}_CB".format(self.global_name, cell.get_name())
                cell_CB_proto = "{}_CB_tab[]".format(self.global_name)
                cell_INIB_name = "{}_INIB_tab[{}]".format(self.global_name, index)
                cell_INIB_proto = "{}_INIB_tab[]".format(self.global_name)
            else:
                cell_CB_name = "{}_CB".format(cell.get_global_name())
                cell_CB_INIT = cell_CB_name
                cell_CB_proto = cell_CB_name
                cell_INIB_name = "{}_INIB".format(cell.get_global_name())
                cell_INIB_proto = cell_INIB_name
            cell_ID = cell.get_id()
        if self.has_CB():
            cell_CBP = "&{}".format(cell_CB_name)
        elif self.has_INIB():
            cell_CBP = "&{}".format(cell_INIB_name)
        else:
            cell_CBP = "(({}_IDX)0)".format(self.global_name)
        if self.idx_is_id_act:
            cell_IDX = cell_ID
        else:
            cell_IDX = cell_CBP
        return [
            self.name,
            cell.get_name(),
            cell_CB_name,
            cell_CB_INIT,
            cell_CB_proto,
            cell_INIB_name,
            cell_ID,
            cell_IDX,
            cell_CBP,
            self.global_name,
            cell.get_global_name(),
            cell_INIB_proto,
        ]

    def subst_name(self, str_, name_array):
        ct = name_array[0]
        cell = name_array[1]
        cb = name_array[2]
        cb_proto = name_array[4]
        id_ = name_array[6]
        idx = name_array[7]
        cbp = name_array[8]
        ct_global = name_array[9]
        cell_global = name_array[10]

        # Ruby の "\\1#{x}" は Python re では \\1 の直後が数字だと
        # グループ参照と誤認される（例: id=1 → "\\11"）。lambda で連結する。
        def _sub(pat, repl, s):
            return re.sub(pat, lambda m: m.group(1) + str(repl), s)

        str_ = _sub(r"(^|[^\$])\$ct\$", ct, str_)
        str_ = _sub(r"(^|[^\$])\$ct_global\$", ct_global, str_)
        if cell:
            str_ = _sub(r"(^|[^\$])\$cell\$", cell, str_)
            str_ = _sub(r"(^|[^\$])\$cb\$", cb, str_)
            str_ = _sub(r"(^|[^\$])\$id\$", "{}_{}".format(ct, cell_global), str_)
            str_ = _sub(r"(^|[^\$])\$cb_proto\$", cb_proto, str_)
            str_ = _sub(r"(^|[^\$])\$ID\$", id_, str_)
            str_ = _sub(r"(^|[^\$])\$idx\$", idx, str_)
            str_ = _sub(r"(^|[^\$])\$cbp\$", cbp, str_)
            str_ = _sub(r"(^|[^\$])\$cell_global\$", cell_global, str_)
        str_ = re.sub(r"\$\$", "$", str_)
        return str_

    def gen_cell_cb_attribute(self, cell, indent, f, name_array, cb_inib):
        jl = cell.get_join_list()
        if cb_inib == "INIB":
            if self.n_attribute_ro == 0 and self.n_var_size_is == 0:
                return
            print_indent(f, indent + 1)
            f.print("/* attribute(RO) */ \n")
        elif G.rom:
            if self.n_attribute_rw == 0:
                return
            print_indent(f, indent + 1)
            f.print("/* attribute(RW) */ \n")
        else:
            if self.n_attribute_rw == 0 and self.n_attribute_ro == 0 and self.n_var_size_is == 0:
                return
            print_indent(f, indent + 1)
            f.print("/* attribute */ \n")
        for a in self.get_attribute_list():
            if a.is_omit():
                continue
            if cb_inib == "INIB" and a.is_rw():
                continue
            elif cb_inib == "CB" and G.rom and not a.is_rw():
                continue
            j = jl.get_item(a.get_identifier())
            if j:
                self.gen_cell_cb_init(
                    f, cell, name_array, a.get_type(), j.get_rhs(),
                    a.get_identifier(), indent + 1)
            elif a.get_initializer():
                self.gen_cell_cb_init(
                    f, cell, name_array, a.get_type(), a.get_initializer(),
                    a.get_identifier(), indent + 1)
            else:
                self.gen_cell_cb_init(
                    f, cell, name_array, a.get_type(), None,
                    a.get_identifier(), indent + 1)
        for v in self.var:
            if v.is_omit() or v.get_size_is() is None:
                continue
            if v.get_initializer() and G.ram_initializer is False:
                self.gen_cell_cb_init(
                    f, cell, name_array, v.get_type(), v.get_initializer(),
                    v.get_identifier(), indent + 1)
            else:
                self.gen_cell_cb_init(
                    f, cell, name_array, v.get_type(), None,
                    v.get_identifier(), indent + 1)

    def gen_cell_cb_var(self, cell, indent, f, name_array):
        if self.n_var - self.n_var_size_is <= 0:
            return
        print_indent(f, indent + 1)
        f.print("/* var */ \n")
        for v in self.get_var_list():
            if v.is_omit() or v.get_size_is():
                continue
            if v.get_initializer() and G.ram_initializer is False:
                self.gen_cell_cb_init(
                    f, cell, name_array, v.get_type(), v.get_initializer(),
                    v.get_identifier(), indent + 1)
            else:
                self.gen_cell_cb_init(
                    f, cell, name_array, v.get_type(), None,
                    v.get_identifier(), indent + 1)

    def gen_cell_cb_port(self, cell, indent, f, name_array, inib_cb="INIB"):
        self.gen_cell_cb_call_port(cell, indent, f, name_array, inib_cb)
        self.gen_cell_cb_entry_port(cell, indent, f, name_array)

    def gen_cell_cb_call_port(self, cell, indent, f, name_array, inib_cb):
        jl = cell.get_join_list()
        n_inib_cp = (
            self.n_call_port - self.n_call_port_omitted_in_CB
            - (0 if G.ram_initializer else (
                self.n_call_port_dynamic - self.n_call_port_array_dynamic))
        )
        if (
            (inib_cb == "INIB" and n_inib_cp > 0)
            or (inib_cb == "CB_ALL" and self.n_call_port > 0)
            or (inib_cb == "CB_DYNAMIC" and (
                self.n_call_port_dynamic - self.n_call_port_array_dynamic) > 0)
        ):
            print_indent(f, indent + 1)
            f.print("/* call port ({}) #_CP_# */ \n".format(inib_cb))
            for p in self.get_port_list():
                if p.get_port_type() != "CALL" or p.is_omit() or p.is_cell_unique():
                    continue
                if inib_cb == "INIB" and p.is_dynamic() and p.get_array_size() is None \
                        and not G.ram_initializer:
                    continue
                if inib_cb == "CB_DYNAMIC" and (
                    not p.is_dynamic() or p.get_array_size() is not None):
                    continue
                j = jl.get_item(p.get_name())
                print_indent(f, indent + 1)
                if j is None:
                    dbgPrint("cell_cb_call_port: {} array size={}\n".format(
                        p.get_name(), p.get_array_size()))
                    if p.get_array_size() is not None:
                        if p.is_dynamic():
                            if inib_cb == "INIB":
                                if G.ram_initializer:
                                    f.printf(
                                        "%-40s /* #_CCP7_# _init_ */\n",
                                        "{}_{}_init_,".format(
                                            cell.get_global_name(), p.get_name()))
                                    print_indent(f, indent + 1)
                                f.printf(
                                    "%-40s /* #_CCP7B_# */\n",
                                    "{}_{},".format(
                                        cell.get_global_name(), p.get_name()))
                            elif G.rom is False:
                                f.printf(
                                    "%-40s /* #_CCP8_# */\n",
                                    "{}_{},".format(
                                        cell.get_global_name(), p.get_name()))
                        else:
                            f.printf("%-40s /* #_CCP9_# */\n", "0,")
                        if p.get_array_size() == "[]":
                            print_indent(f, indent + 1)
                            f.printf(
                                "%-40s /* %s #_CCP6_# */\n",
                                "0,",
                                "length of {} (n_{})".format(p.get_name(), p.get_name()),
                            )
                    else:
                        f.printf("%-40s /* #_CCP5_# */\n", "0,")
                    continue
                am = j.get_array_member2()
                if am:
                    if inib_cb == "INIB" and p.is_dynamic() and p.get_array_size() is not None \
                            and G.ram_initializer:
                        f.printf(
                            "%-40s /* #_CCP3_# _init_ */\n",
                            "{}_{}_init_,".format(cell.get_global_name(), j.get_name()))
                        print_indent(f, indent + 1)
                    f.printf(
                        "%-40s /* #_CCP3B_# */\n",
                        "{}_{},".format(cell.get_global_name(), j.get_name()))
                    if p.get_array_size() == "[]":
                        print_indent(f, indent + 1)
                        f.printf(
                            "%-40s /* %s #_CCP4_# */\n",
                            "{},".format(len(am)),
                            "length of {} (n_{})".format(p.get_name(), p.get_name()),
                        )
                else:
                    if j.get_rhs_cell().get_celltype() == self:
                        definition = j.get_definition()
                        des_type_cast = "(struct tag_{}_VDES *)".format(
                            definition.get_signature().get_global_name())
                    else:
                        des_type_cast = ""
                    init = "_init_" if (p.is_dynamic() and inib_cb == "INIB") else ""
                    if j.get_rhs_subscript() is not None:
                        subscript = j.get_rhs_subscript()
                        f.printf(
                            "%-40s /* %s #_CCP0_# */\n",
                            "{}&{}_des{},".format(
                                des_type_cast, j.get_port_global_name(), subscript),
                            p.get_name() + init,
                        )
                    else:
                        if not p.is_skelton_useless():
                            f.printf(
                                "%-40s /* %s #_CCP1_# */\n",
                                "{}&{}_des,".format(
                                    des_type_cast, j.get_port_global_name()),
                                p.get_name() + init,
                            )
                        else:
                            c = j.get_rhs_cell()
                            ct = c.get_celltype()
                            na = ct.get_name_array(c)
                            if ct.has_INIB() or ct.has_CB():
                                f.printf(
                                    "%-40s /* %s #_CCP2_# */\n",
                                    "{},".format(na[7]),
                                    p.get_name(),
                                )
                            else:
                                f.printf(
                                    "%-40s /* %s #_CCP2B_# */\n",
                                    "0,",
                                    p.get_name(),
                                )

    def gen_cell_cb_entry_port(self, cell, indent, f, name_array):
        if self.n_entry_port == 0:
            return
        print_indent(f, indent + 1)
        f.print("/* entry port #_EP_# */ \n")
        for p in self.port:
            if p.get_port_type() == "ENTRY" and p.get_array_size() == "[]":
                print_indent(f, indent + 1)
                f.printf(
                    "%-40s /*  #_EEP_# */\n",
                    "{},".format(cell.get_entry_port_max_subscript(p) + 1))

    def gen_cell_cb_init(
        self, f, cell, name_array, type_, init, identifier, indent, f_get_str=False
    ):
        cell_CB_INIT = name_array[3]
        while isinstance(type_, DefinedType):
            type_ = type_.get_type()
        if init is None:
            return self._gen_cell_cb_init_default(
                f, cell_CB_INIT, type_, identifier, indent, f_get_str)
        if isinstance(type_, BoolType):
            return self._gen_cell_cb_init_scalar(
                f, cell, name_array, init, identifier, indent, f_get_str)
        if isinstance(type_, IntType):
            return self._gen_cell_cb_init_scalar(
                f, cell, name_array, init, identifier, indent, f_get_str)
        if isinstance(type_, FloatType):
            if f_get_str:
                return to_s(init.eval_const2(cell.get_join_list(), self.name_list))
            print_indent(f, indent)
            f.printf(
                "%-40s /* %s */\n",
                "{},".format(to_s(init.eval_const2(cell.get_join_list(), self.name_list))),
                identifier,
            )
            return None
        if isinstance(type_, EnumType):
            if f_get_str:
                return to_s(init.eval_const2(cell.get_join_list(), self.name_list))
            print_indent(f, indent)
            f.printf(
                "%-40s /* %s */\n",
                "{},".format(to_s(init.eval_const2(cell.get_join_list(), self.name_list))),
                identifier,
            )
            return None
        if isinstance(type_, ArrayType):
            return self._gen_cell_cb_init_array(
                f, cell, name_array, type_, init, identifier, indent, f_get_str)
        if isinstance(type_, StructType):
            return self._gen_cell_cb_init_struct(
                f, cell, name_array, type_, init, identifier, indent, f_get_str)
        if isinstance(type_, PtrType):
            return self._gen_cell_cb_init_ptr(
                f, cell, name_array, type_, init, identifier, indent, f_get_str)
        if isinstance(type_, DescriptorType):
            if f_get_str:
                return "{}"
            print_indent(f, indent)
            f.printf("%-40s /* %s */\n", "{},", identifier)
            return None
        raise Exception("UnknownType")

    def _gen_cell_cb_init_default(
        self, f, cell_CB_INIT, type_, identifier, indent, f_get_str
    ):
        defaults = {
            BoolType: ("false", "false,"),
            IntType: ("0", "0,"),
            FloatType: ("0.0", "0.0,"),
            EnumType: ("0", "0,"),
            ArrayType: ("{}", "{},"),
            StructType: ("{}", "{},"),
            DescriptorType: ("{}", "{},"),
        }
        for cls, (s_str, f_str) in defaults.items():
            if isinstance(type_, cls):
                if f_get_str:
                    return s_str
                print_indent(f, indent)
                f.printf("%-40s /* %s */\n", f_str, identifier)
                return None
        if isinstance(type_, PtrType):
            if type_.get_size():
                val = "{}_{}_INIT".format(cell_CB_INIT, identifier)
                if f_get_str:
                    return val
                print_indent(f, indent)
                f.printf("%-40s /* %s */\n", "{},".format(val), identifier)
            else:
                if f_get_str:
                    return "0"
                print_indent(f, indent)
                f.printf("%-40s /* %s */\n", "0,", identifier)
            return None
        raise Exception("UnknownType")

    def _gen_cell_cb_init_scalar(
        self, f, cell, name_array, init, identifier, indent, f_get_str
    ):
        if type(init) is C_EXP:
            init_str = self.subst_name(init.get_c_exp_string(), name_array)
        else:
            init_str = to_s(init.eval_const2(cell.get_join_list(), self.name_list))
        if f_get_str:
            return init_str
        print_indent(f, indent)
        f.printf("%-40s /* %s */\n", "{},".format(init_str), identifier)
        return None

    def _gen_cell_cb_init_array(
        self, f, cell, name_array, type_, init, identifier, indent, f_get_str
    ):
        if type_.get_subscript():
            length = type_.get_subscript().eval_const(
                cell.get_join_list(), self.name_list)
        else:
            length = len(init)
        at = type_.get_type()
        i = 0
        if f_get_str:
            str_ = "{ "
        else:
            print_indent(f, indent)
            f.print("{\n")
        while i < length:
            if i < len(init) and init[i]:
                if f_get_str:
                    str_ += self.gen_cell_cb_init(
                        f, cell, name_array, at, init[i],
                        "{}[{}]".format(identifier, i), indent + 1, True)
                    str_ += ", "
                else:
                    self.gen_cell_cb_init(
                        f, cell, name_array, at, init[i],
                        "{}[{}]".format(identifier, i), indent + 1, False)
            i += 1
        if f_get_str:
            str_ += "}"
            return str_
        print_indent(f, indent)
        f.print("},\n")
        return None

    def _gen_cell_cb_init_struct(
        self, f, cell, name_array, type_, init, identifier, indent, f_get_str
    ):
        if type(init) is C_EXP:
            init_str = self.subst_name(init.get_c_exp_string(), name_array)
            if f_get_str:
                return init_str
            print_indent(f, indent)
            f.printf("%-40s /* %s */\n", "{},".format(init_str), identifier)
            return None
        decls = type_.get_members_decl().get_items()
        i = 0
        if f_get_str:
            str_ = "{ "
        else:
            print_indent(f, indent)
            f.print("{{                                        /* {} */\n".format(identifier))
        for d in decls:
            if i < len(init) and init[i]:
                if f_get_str:
                    str_ += self.gen_cell_cb_init(
                        f, cell, name_array, d.get_type(), init[i],
                        d.get_identifier(), indent + 1, True)
                    str_ += ", "
                else:
                    self.gen_cell_cb_init(
                        f, cell, name_array, d.get_type(), init[i],
                        d.get_identifier(), indent + 1, False)
            i += 1
        if f_get_str:
            str_ += "}"
            return str_
        print_indent(f, indent)
        f.print("},\n")
        return None

    def _gen_cell_cb_init_ptr(
        self, f, cell, name_array, type_, init, identifier, indent, f_get_str
    ):
        cell_CB_INIT = name_array[3]
        if type(init) is list:
            val = "{}_{}_INIT".format(cell_CB_INIT, identifier)
            if f_get_str:
                return val
            print_indent(f, indent)
            f.printf("%-40s /* %s */\n", "{},".format(val), identifier)
            return None
        if type(init) is C_EXP:
            init_str = self.subst_name(init.get_c_exp_string(), name_array)
            if f_get_str:
                return init_str
            print_indent(f, indent)
            f.printf("%-40s /* %s */\n", "{},".format(init_str), identifier)
            return None
        if f_get_str:
            return to_s(init.eval_const2(cell.get_join_list(), self.name_list))
        print_indent(f, indent)
        f.printf(
            "%-40s /* %s */\n",
            "{},".format(to_s(init.eval_const2(cell.get_join_list(), self.name_list))),
            identifier,
        )
        return None

    def generate_template_code(self):
        if self.is_all_entry_inline():
            return
        if self.b_reuse and not G.generate_all_template:
            return
        if not (self.plugin and self.plugin.gen_ep_func()):
            if G.generate_no_template:
                return
            fname = "{}/{}_templ.{}".format(G.gen, self.global_name, G.c_suffix)
        else:
            fname = "{}/{}.{}".format(G.gen, self.global_name, G.c_suffix)
        f = AppFile.open(fname)
        if not (self.plugin and self.plugin.gen_ep_func()):
            f.printf(TECSMsg.get("template_note"), self.name, self.name)
        else:
            print_note(f, True)
        f.print(TECSMsg.get("preamble_note"))
        self.gen_template_attr_access(f)
        self.gen_template_cp_fun(f)
        f.print(" *\n * #[</PREAMBLE>]# */\n\n")
        f.printf(TECSMsg.get("PAC_comment"), "#_PAC_#")
        self.gen_template_private_header(f)
        if self.plugin:
            self.plugin.gen_preamble(f, self.singleton, self.name, self.global_name)
        self.gen_template_ep_fun(f, False)
        f.print(TECSMsg.get("postamble_note"))
        if self.plugin:
            self.plugin.gen_postamble(f, self.singleton, self.name, self.global_name)
        f.close()

    def gen_template_private_header(self, f):
        f.print("#include \"{}_tecsgen.{}\"\n\n".format(self.global_name, G.h_suffix))
        f.print(
            "#ifndef E_OK\n"
            "#define\tE_OK\t0\t\t/* success */\n"
            "#define\tE_ID\t(-18)\t/* illegal ID */\n"
            "#endif\n\n"
        )

    def gen_template_attr_access(self, f):
        if self.n_attribute_rw > 0 or self.n_attribute_ro > 0 or self.n_var > 0:
            f.printf(TECSMsg.get("CAAM_comment"), "#_CAAM_#")
        for a in self.attribute:
            if a.is_omit():
                continue
            f.printf(
                " * %-16s %-16s %-16s\n",
                a.get_name(),
                "{} {}".format(a.get_type().get_type_str(), a.get_type().get_type_str_post()),
                "ATTR_{}".format(a.get_name()),
            )
        for v in self.var:
            if v.is_omit():
                continue
            f.printf(
                " * %-16s %-16s %-16s\n",
                v.get_name(),
                "{} {}".format(v.get_type().get_type_str(), v.get_type().get_type_str_post()),
                "VAR_{}".format(v.get_name()),
            )

    def gen_template_cp_fun(self, f):
        if self.n_call_port > 0:
            f.print(" *\n")
            f.printf(TECSMsg.get("TCPF_comment"), "#_TCPF_#")

        for p in self.port:
            if p.get_port_type() != "CALL":
                continue

            sig_name = p.get_signature().get_global_name()
            con_tmp = p.get_signature().get_context()
            context = " context:{}".format(con_tmp) if con_tmp else ""

            if p.is_optional():
                optional = " optional:true"
                if p.get_array_size():
                    is_join = " *   bool_t     is_{}_joined(int subscript)        check if joined\n".format(
                        p.get_name())
                else:
                    is_join = " *   bool_t     is_{}_joined()                     check if joined\n".format(
                        p.get_name())
            else:
                optional = ""
                is_join = ""

            omit = " omit:true" if p.is_omit() else ""

            if p.is_allocator_port():
                f.print(
                    " * allocator port for {} port:{} func:{} param: {}\n".format(
                        str(p.get_port_type()).lower(),
                        p.get_allocator_port().get_name(),
                        p.get_allocator_func_decl().get_name(),
                        p.get_allocator_param_decl().get_name(),
                    )
                )
            elif not p.is_require():
                f.print(
                    " * call port: {} signature: {}{}{}{}\n{}".format(
                        p.get_name(), sig_name, context, optional, omit, is_join)
                )
            else:
                f.print(" * require port: signature:{}{}\n".format(sig_name, context))

            for fun in p.get_signature().get_function_head_array():
                ft = fun.get_declarator().get_type()
                f.printf(" *   %-14s ", ft.get_type().get_type_str())
                if (not p.is_require()) or p.has_name():
                    f.print("{}_{}(".format(p.get_name(), fun.get_name()))
                else:
                    f.print("{}(".format(fun.get_name()))
                delim = ""
                if p.get_array_size():
                    f.print("{} subscript".format(delim))
                    delim = ","
                for param in ft.get_paramlist().get_items():
                    f.print("{} {}".format(delim, param.get_type().get_type_str()))
                    f.print(" {}{}".format(
                        param.get_name(), param.get_type().get_type_str_post()))
                    delim = ","
                f.print(" );\n")

            if p.get_array_size():
                f.print(" *       subscript:  0...(NCP_{}-1)\n".format(p.get_name()))

            if p.is_ref_desc():
                subsc = " int_t subscript " if p.get_array_size() else ""
                f.print(" *   [ref_desc]\n")
                f.printf(
                    " *      %-14s %s;\n",
                    "Descriptor( {} )".format(p.get_signature().get_global_name()),
                    "{}_refer_to_descriptor({})".format(p.get_name(), subsc),
                )
                f.printf(
                    " *      %-14s %s;\n",
                    "Descriptor( {} )".format(p.get_signature().get_global_name()),
                    "{}_ref_desc({})      (same as above; abbreviated version)".format(
                        p.get_name(), subsc),
                )
            if p.is_dynamic():
                subsc = "int_t subscript, " if p.get_array_size() else ""
                subsc2 = " int_t subscript" if p.get_array_size() else ""
                if p.is_optional():
                    f.print(" *   [dynamic, optional]\n")
                else:
                    f.print(" *   [dynamic]\n")
                f.printf(
                    " *      %-14s %s;\n",
                    "void",
                    "{}_set_descriptor( {}Descriptor( {} ) desc )".format(
                        p.get_name(), subsc, p.get_signature().get_global_name()),
                )
                if p.is_optional():
                    f.printf(
                        " *      %-14s %s;\n",
                        "void",
                        "{}_unjoin( {} )".format(p.get_name(), subsc2),
                    )

    def gen_template_ep_fun(self, f, b_inline=False):
        if self.n_entry_port > 0:
            f.printf(TECSMsg.get("TEPF_comment"), "#_TEPF_#")
        nCELLIDX = "CELLIDX"
        nCELLCB = "CELLCB"
        nGET_CELLCB = "GET_CELLCB"
        for p in self.port:
            if p.get_port_type() != "ENTRY":
                continue
            if p.is_omit():
                continue
            if b_inline and not p.is_inline():
                continue
            if not b_inline and p.is_inline():
                continue
            ctx = p.get_signature().get_context()
            f.print(
                "/* #[<ENTRY_PORT>]# {}\n"
                " * entry port: {}\n"
                " * signature:  {}\n"
                " * context:    {}\n".format(
                    p.get_name(), p.get_name(), p.get_signature().get_global_name(), ctx)
            )
            if p.get_array_size() is not None:
                f.print(" * entry port array size:  NEP_{}\n".format(p.get_name()))
            f.print(" * #[</ENTRY_PORT>]# */\n\n")
            for fun in p.get_signature().get_function_head_array():
                f.print(
                    "/* #[<ENTRY_FUNC>]# {}_{}\n"
                    " * name:         {}_{}\n"
                    " * global_name:  {}_{}_{}\n"
                    " * oneway:       {}\n"
                    " * #[</ENTRY_FUNC>]# */\n".format(
                        p.get_name(),
                        fun.get_name(),
                        p.get_name(),
                        fun.get_name(),
                        self.global_name,
                        p.get_name(),
                        fun.get_name(),
                        fun.is_oneway(),
                    ).replace("True", "true").replace("False", "false")
                )
                if b_inline:
                    f.print("Inline ")
                functype = fun.get_declarator().get_type()
                f.printf("%s\n", functype.get_type_str())
                f.print("{}_{}(".format(p.get_name(), fun.get_name()))
                if self.singleton:
                    delim = ""
                else:
                    f.print("{} idx".format(nCELLIDX))
                    delim = ", "
                if p.get_array_size() is not None:
                    f.print("{}int_t subscript".format(delim))
                    delim = ", "
                paramlist = functype.get_paramlist()
                if paramlist:
                    items = paramlist.get_items()
                else:
                    items = []
                for param in items:
                    f.print(delim)
                    delim = ", "
                    f.print(param.get_type().get_type_str())
                    f.print(" ")
                    f.print(param.get_name())
                    f.print(param.get_type().get_type_str_post())
                f.print(")\n{\n")
                if self.plugin and self.plugin.gen_ep_func():
                    self.plugin.gen_ep_func_body(
                        f,
                        self.singleton,
                        self.name,
                        self.global_name,
                        p.get_signature().get_global_name(),
                        p.get_name(),
                        fun.get_name(),
                        "{}_{}_{}".format(self.global_name, p.get_name(), fun.get_name()),
                        functype,
                        items,
                    )
                elif not self.singleton:
                    functype_ret = functype.get_type()
                    from tecslib.core.types import DefinedType
                    ret_cd = None
                    if (isinstance(functype_ret, DefinedType)
                            and functype_ret.get_type_str() in ("ER", "ER_UINT")):
                        if not fun.is_oneway():
                            f.print("\tER\t\tercd = E_OK;\n")
                            ret_cd = "return(ercd);"
                        else:
                            ret_cd = "{}\n\treturn(E_OK);".format(
                                TECSMsg.get("oneway_ercd_note"))
                    f.print("\t{}	*p_cellcb = {}(idx);\n\n".format(nCELLCB, nGET_CELLCB))
                    f.printf(TECSMsg.get("TEFB_comment"), "#_TEFB_#")
                    f.printf(
                        "#warning \"'{}_{}' needs to be edited.\"   /* delete this line after edit */\n\n".format(
                            p.get_name(), fun.get_name()
                        )
                    )
                    if ret_cd:
                        f.print("\t{}\n".format(ret_cd))
                f.print("}\n\n")

    def generate_inline_template_code(self):
        if self.n_entry_port_inline == 0:
            return
        if self.b_reuse and not G.generate_all_template:
            return
        if not (self.plugin and self.plugin.gen_ep_func()):
            if G.generate_no_template:
                return
            fname = "{}/{}_inline_templ.{}".format(
                G.gen, self.global_name, G.h_suffix)
        else:
            fname = "{}/{}_inline.{}".format(G.gen, self.global_name, G.h_suffix)
        f = AppFile.open(fname)
        self.gen_ph_guard(f, "INLINE")
        if not (self.plugin and self.plugin.gen_ep_func()):
            f.printf(TECSMsg.get("inline_template_note"), self.name, self.name)
        else:
            print_note(f, True)
        f.print(TECSMsg.get("preamble_note"))
        self.gen_template_attr_access(f)
        self.gen_template_cp_fun(f)
        f.print(" *\n * #[</PREAMBLE>]# */\n\n")
        self.gen_template_ep_fun(f, True)
        f.print(TECSMsg.get("postamble_note"))
        if self.plugin:
            self.plugin.gen_postamble(f, self.singleton, self.name, self.global_name)
        f.print("\n")
        self.gen_ph_endif(f, "INLINE")
        f.close()

    def generate_celltype_factory_code(self):
        for fa in self.ct_factory_list:
            if fa.get_name() != Sym("write"):
                continue
            file_name = CDLString.remove_dquote(fa.get_file_name())
            format_ = CDLString.remove_dquote(fa.get_format())
            format_ = format_.replace("\\\n", "\n")

            def _sub(pat, repl, s):
                return re.sub(pat, lambda m: m.group(1) + str(repl), s)

            file_name = _sub(r"(^|[^\$])\$ct\$", self.name, file_name)
            file_name = _sub(r"(^|[^\$])\$ct_global\$", self.global_name, file_name)
            format_ = _sub(r"(^|[^\$])\$ct\$", self.name, format_)
            format_ = _sub(r"(^|[^\$])\$ct_global\$", self.global_name, format_)
            format_ = format_.replace("$$", "$")
            if not file_name.startswith("/"):
                file_name = "{}/{}".format(G.gen, file_name)
            try:
                cfg_file = AppFile.open(file_name)
                if G.debug:
                    print("'{}' : celltype factory format: ".format(self.name), end="")
                    print(format_)
                fmt = CDLString.escape(format_)
                cfg_file.print(fmt)
                cfg_file.print("\n")
                cfg_file.close()
            except Exception as evar:
                self.cdl_error(
                    "H1004 '$1' : write error while writing factory "
                    "(specify -t to get more info)",
                    file_name,
                )
                print_exception(evar)

    def generate_cell_factory_code(self):
        for c in self.ordered_cell_list:
            if not c.is_generate():
                continue
            name_array = self.get_name_array(c)
            for fa in self.factory_list:
                if fa.get_name() != Sym("write"):
                    continue
                file_name = CDLString.remove_dquote(fa.get_file_name())
                file_name = self.subst_name(file_name, name_array)
                format_ = CDLString.remove_dquote(fa.get_format())
                format_ = format_.replace("\\\n", "\n")
                format_ = self.subst_name(format_, name_array)
                arg_list = fa.get_arg_list()
                if not file_name.startswith("/"):
                    file_name = "{}/{}".format(G.gen, file_name)
                na = []
                if arg_list:
                    for a in arg_list:
                        if a[0] == "STRING_LITERAL":
                            s = CDLString.remove_dquote(a[1])
                            s = self.subst_name(s, name_array)
                            na.append(s)
                        elif a[0] == "IDENTIFIER":
                            param_name = a[1]
                            attr = self.find(param_name)
                            init = attr.get_initializer()
                            j = c.get_join_list().get_item(param_name)
                            if j:
                                init = j.get_rhs()
                            str_ = self.gen_cell_cb_init(
                                None, c, name_array, attr.get_type(), init,
                                attr.get_identifier(), 0, True)
                            str_ = CDLString.remove_dquote(str_)
                            na.append(str_)
                try:
                    cfg_file = AppFile.open(file_name)
                    if G.debug:
                        print("'{}' : factory format: ".format(c.get_name()), end="")
                        print(format_, end=" arg: ")
                        for n in na:
                            print("'{}' ".format(n), end="")
                        print()
                    fmt = CDLString.escape(format_)
                    cfg_file.printf(fmt, *na)
                    cfg_file.print("\n")
                    cfg_file.close()
                except Exception as evar:
                    self.cdl_error(
                        "H1004 '$1' : write error while writing factory "
                        "(specify -t to get more info)",
                        file_name,
                    )
                    print_exception(evar)

    def generate_makefile(self):
        self.generate_makefile_template()
        self.generate_makefile_depend()

    def generate_makefile_template(self):
        if G.generate_no_template:
            return
        f = AppFile.open("{}/Makefile.templ".format(G.gen))
        f.print(
            "$(_TECS_OBJ_DIR){}.o : {}.{}\n"
            "\t$(CC) -c $(CFLAGS) -o $@ $<\n"
            " \n".format(self.global_name, self.global_name, G.c_suffix)
        )
        f.close()

    def generate_makefile_depend(self):
        headers = [
            "$(GEN_DIR)/{}_tecsgen.{}".format(self.global_name, G.h_suffix),
            "$(GEN_DIR)/{}_factory.{}".format(self.global_name, G.h_suffix),
            "$(GEN_DIR)/global_tecsgen.{}".format(G.h_suffix),
        ]
        if self.n_entry_port_inline > 0:
            headers.append("{}_inline.{}".format(self.global_name, G.h_suffix))
        for p in self.port:
            if p.is_omit():
                continue
            headers.append(
                "$(GEN_DIR)/{}_tecsgen.{}".format(p.get_signature().get_global_name(), G.h_suffix)
            )
        headers += self.get_depend_header_list()
        headers.sort()
        from tecslib.rubylib import rb
        headers = rb.uniq(headers)
        headers_str = " ".join(headers)
        f = AppFile.open("{}/Makefile.depend".format(G.gen))
        f.print(
            "# Celltype: {}  #_MDEP_#\n"
            "$(_TECS_OBJ_DIR){}_tecsgen.o : {}_tecsgen.{} {}\n"
            "$(_TECS_OBJ_DIR){}_templ.o : {}_templ.{} {}\n"
            "$(_TECS_OBJ_DIR){}.o : {}.{} {}\n\n".format(
                self.name,
                self.global_name,
                self.global_name,
                G.c_suffix,
                headers_str,
                self.global_name,
                self.global_name,
                G.c_suffix,
                headers_str,
                self.global_name,
                self.global_name,
                G.c_suffix,
                headers_str,
            )
        )
        f.close()

    def get_depend_header_list(self):
        return self.get_depend_header_list_([])

    def get_depend_header_list_(self, celltype_list):
        headers = []
        if self in celltype_list:
            return headers
        celltype_list.append(self)
        for p in self.port:
            if p.get_port_type() != "CALL":
                continue
            if p.is_omit():
                continue
            if p.is_skelton_useless() or p.is_cell_unique() or p.is_VMT_useless():
                p2 = p.get_real_callee_port()
                if p2:
                    ct = p2.get_celltype()
                    headers.append(
                        " $(GEN_DIR)/{}_tecsgen.{}".format(ct.get_global_name(), G.h_suffix)
                    )
                    if p2.is_inline():
                        headers.append(" {}_inline.{}".format(ct.get_global_name(), G.h_suffix))
                    headers += ct.get_depend_header_list_(celltype_list)
        return headers
