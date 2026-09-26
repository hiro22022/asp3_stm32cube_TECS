# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2023 by TOPPERS Project
#
#   このファイルは tecsgen (Ruby 版) の tecslib/plugin/CppIfGenCelltypePlugin.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．
#

from tecslib.core import globals as G
from tecslib.core.componentobj.namespace import Namespace
from tecslib.core.plugin import CFile
from tecslib.core.syntaxobj.cdlstring import CDLString
from tecslib.core.types import VoidType
from tecslib.plugin.CelltypePlugin import CelltypePlugin


class CppIfGenCelltypePlugin(CelltypePlugin):
    CLASS_NAME_SUFFIX = ""
    b_signature_header_generated = False

    def __init__(self, celltype, option):
        super().__init__(celltype, option)
        self.celltype = celltype
        self.plugin_arg_str = CDLString.remove_dquote(option)
        self.plugin_arg_list = {}
        self.cell_list = []

    def new_cell(self, cell):
        self.cell_list.append(cell)

    @classmethod
    def gen_post_code(cls, file):
        pass

    def gen_factory(self, file):
        ct = self.celltype
        if not ct.is_singleton():
            idx_def = "CPP_{}_IDX idx_".format(ct.get_global_name())
            idx_ini = ":cpp_idx( idx_ )"
            cpp_idx = "cpp_idx"
            idx2 = "cpp_idx.idx"
            idx_ = "idx_"
            delim_ini = ", "
        else:
            idx_def = ""
            idx_ini = ""
            cpp_idx = ""
            idx2 = ""
            idx_ = ""
            delim_ini = ""

        if not CppIfGenCelltypePlugin.b_signature_header_generated:
            CppIfGenCelltypePlugin.b_signature_header_generated = True
            self.gen_namespace_signature_header(Namespace.get_root())

        out = CFile.open("{}/{}_cppif.hpp".format(G.gen, ct.get_global_name()), "w")
        out.print(
            "#ifndef {0}_CPPIF_HPP\n"
            "#define {0}_CPPIF_HPP\n"
            "\n"
            "/*\n"
            " * This file is intended to be included in non-TECS celltype code and in C++ code.\n"
            " */\n"
            '#include "{1}_tecsgen.h"\n'.format(
                ct.get_global_name().upper(), ct.get_global_name()))

        b_gen = False
        for port in ct.get_port_list():
            if port.get_port_type() == "ENTRY":
                out.print('#include "{}_cppif.hpp"\n'.format(
                    port.get_signature().get_global_name()))
                b_gen = True
        if b_gen:
            out.print("\n")

        if not ct.is_singleton():
            out.print(
                "/*\n"
                " * Cell IDX type for Cpp\n"
                " */\n"
                "typedef struct  {{\n"
                "    {0}_IDX idx;\n"
                "}} CPP_{0}_IDX;\n"
                "\n"
                "/*\n"
                " * Cell IDX macros in celltype '{1}'\n"
                " *   type of the macro value is {1}_IDX.\n"
                " *   macro name is (cell name) + \"_IDX\"\n"
                " */\n".format(ct.get_global_name(), ct.get_name()))
            for cell in ct.get_cell_list():
                if not cell.is_generate():
                    continue
                name_array = ct.get_name_array(cell)
                idx_real = name_array[7]
                out.print(
                    "inline CPP_{0}_IDX CPP_{1}_IDX__()\n"
                    "{{\n"
                    "    CPP_{0}_IDX cpp_idx = {{ {2} }};\n"
                    "    return cpp_idx;\n"
                    "}}\n"
                    "#define {1}_IDX  CPP_{1}_IDX__()\n".format(
                        ct.get_global_name(), cell.get_global_name(), idx_real))

        cell_sample = None
        for cell in ct.get_cell_list():
            if cell.is_generate():
                cell_sample = cell
                break
        cell_sample_name = cell_sample.get_name() if cell_sample else "Cell"

        for port in ct.get_port_list():
            if port.get_port_type() != "ENTRY":
                continue
            fha = port.get_signature().get_function_head_array()
            if len(fha) == 0:
                continue
            func_1st = fha[0]
            if not ct.is_singleton():
                cell_idx = "( Cell_IDX );"
                cell_list = ct.get_cell_list()
                first_cell = cell_list[0] if cell_list else None
                if first_cell is not None:
                    cell_idx2 = "({}_IDX);".format(first_cell.get_global_name())
                else:
                    cell_idx2 = "(Cell_IDX);"
            else:
                cell_idx = ";     // don't put empty parenthesis for singleton"
                cell_idx2 = ";"
            out.print(
                "\n"
                "/*-------------- begin: use sample ------------\n"
                " * Define variable for Cell with Cnstructor\n"
                " *   tCelltypeName    CellNameInCpp{0}\n"
                " *   ex) {1}     {2}{3}\n"
                " *\n"
                " * Call member function\n"
                " *   CellNameInCpp.eEntryName.FunctionName( parameters... );\n"
                " *   ex) {2}.{4}.{5}( parameters... );\n"
                " *-------------- end:   use sample ------------*/\n"
                "\n".format(
                    cell_idx, ct.get_global_name(), cell_sample_name, cell_idx2,
                    port.get_name(), func_1st.get_name()))
            break

        out.print(
            "/*\n"
            " * C++ interface code\n"
            " *   This class comes from celltype '{0}'.\n"
            " */\n"
            "class {1} {{\n".format(ct.get_name(), ct.get_global_name()))

        for port in ct.get_port_list():
            if port.get_port_type() != "ENTRY":
                continue
            sig = port.get_signature()
            if port.get_array_size() is not None:
                subsc_def = "int_t subscript_"
                delim = delim_ini
            else:
                subsc_def = ""
                delim = ""
            out.print(
                "    /* class for entry {0} {1} */\n"
                "    class {1}_ : public {0}{{\n"
                "        public : \n"
                "        /* constructor: internal use only */\n"
                "        {1}_({2}{3}{4});\n"
                "        /* destructor */\n"
                "        // ~{1}_();   unnecessary\n"
                "    \n"
                "        /* {5} functions */\n".format(
                    sig.get_global_name(), port.get_name(), idx_def, delim, subsc_def,
                    sig.get_name()))
            for fh in sig.get_function_head_array():
                line = "        {} {}( ".format(
                    fh.get_return_type().get_type_str(), fh.get_name())
                d = ""
                for param in fh.get_paramlist().get_items():
                    line += "{}{} {}{}".format(
                        d,
                        param.get_type().get_type_str(),
                        param.get_name(),
                        param.get_type().get_type_str_post())
                    d = ", "
                line += " );\n"
                out.print(line)
            out.print("\n")
            if not ct.is_singleton():
                out.print(
                    "        private:\n"
                    "        CPP_{}_IDX cpp_idx;\n".format(ct.get_global_name()))
            if port.get_array_size() is not None:
                out.print(
                    "        private:\n"
                    "        int_t  subscript;\n")
            out.print("    };\n")

            if port.get_array_size() is not None:
                out.print(
                    "    class {0}_EA{{\n"
                    "        public : \n"
                    "        /* constructor: internal use only */\n"
                    "        {0}_EA({1});\n"
                    "        /* destructor */\n"
                    "        // ~{0}_();   unnecessary\n"
                    "\n"
                    "        {0}_ operator[]( int_t subscript ) const; \n".format(
                        port.get_name(), idx_def))
                if not ct.is_singleton():
                    out.print(
                        "        private:\n"
                        "        CPP_{}_IDX cpp_idx;\n".format(ct.get_global_name()))
                out.print("    };\n")

        out.print(
            "\n"
            "    /*--------  begin public ----------*/\n"
            "    public:\n"
            "    /* constructor */\n"
            "    {0}( {1} );\n"
            "    /* destructor */\n"
            "    // ~{0}();   unnecessary\n"
            "\n".format(ct.get_name(), idx_def))
        for port in ct.get_port_list():
            if port.get_port_type() != "ENTRY":
                continue
            entry_array = "EA" if port.get_array_size() is not None else ""
            out.print(
                "    /* entry {0} {1} */\n"
                "    {1}_{2} {1}; \n".format(
                    port.get_signature().get_global_name(),
                    port.get_name(),
                    entry_array))
        out.print(
            "    /*--------  end public ----------*/\n"
            "};\n"
            "\n"
            "/*-------------- begin: implementation (I/F code only) ----------------*/\n"
            "/* constructor  */\n")

        out.print("inline    {0}::{0}({1}) : ".format(ct.get_global_name(), idx_def))
        delim = ""
        for port in ct.get_port_list():
            if port.get_port_type() == "ENTRY":
                out.print("{}{}({})".format(delim, port.get_name(), idx_))
                delim = ", "
        out.print("{}\n\n")

        for port in ct.get_port_list():
            if port.get_port_type() != "ENTRY":
                continue
            if port.get_array_size() is not None:
                subsc_def = "int_t subscript_"
                subsc_ini = "subscript(subscript_)"
                if idx_ini == "":
                    subsc_ini = ":" + subsc_ini
                delim = delim_ini
            else:
                subsc_def = ""
                subsc_ini = ""
                delim = ""
            out.print(
                "/* ------------- entry port: {0} ------------------*/\n"
                "/* constructor: internal use only */\n"
                "inline    {1}::{0}_::{0}_( {2}{3}{4} ) {5}{3}{6}{{}}\n"
                "\n"
                "/* entry {0} functions */\n".format(
                    port.get_name(), ct.get_global_name(), idx_def, delim, subsc_def,
                    idx_ini, subsc_ini))

            for fh in port.get_signature().get_function_head_array():
                qual = "{}::{}_::{}".format(
                    ct.get_global_name(), port.get_name(), fh.get_name())
                cr = "\n" if len(qual) >= 32 else ""
                out.print("inline {} {}::{}_::{}( ".format(
                    fh.get_return_type().get_type_str(),
                    ct.get_global_name(),
                    port.get_name(),
                    fh.get_name()))
                d = ""
                for param in fh.get_paramlist().get_items():
                    out.print("{}{} {}{}".format(
                        d,
                        param.get_type().get_type_str(),
                        param.get_name(),
                        param.get_type().get_type_str_post()))
                    d = ", "
                out.print(" ){}{{ ".format(cr))
                if not isinstance(fh.get_return_type(), VoidType):
                    out.print("return ")
                d = delim_ini
                out.print("{}_{}_{}( {}".format(
                    ct.get_global_name(), port.get_name(), fh.get_name(), idx2))
                if port.get_array_size() is not None:
                    out.print("{}subscript".format(d))
                    d = ", "
                for param in fh.get_paramlist().get_items():
                    out.print("{}{}".format(d, param.get_name()))
                    d = ", "
                out.print(" ); }}{}\n".format(cr))

            if port.get_array_size() is not None:
                out.print(
                    "/* constructor for entry array (internal use only)*/\n"
                    "inline  {0}::{1}_EA::{1}_EA( {2} ){3}{{}}\n"
                    "/* operator[] */\n"
                    "inline  {0}::{1}_ {0}::{1}_EA::operator[]( int_t subscript ) const\n"
                    "{{\n"
                    "    /*\n"
                    "     * subscript is not checked here. No way to return error.\n"
                    "     */\n"
                    "    return {0}::{1}_({4}{5}subscript);\n"
                    "}};\n"
                    "\n".format(
                        ct.get_global_name(), port.get_name(), idx_def, idx_ini,
                        cpp_idx, delim_ini))

        ct.gen_ph_undef(out)
        out.print(
            "/*-------------- end: implementation (I/F code only) ----------------*/\n"
            "\n"
            "#endif /* {}_CPPIF_HPP */\n".format(ct.get_global_name().upper()))
        out.close()

    def gen_namespace_signature_header(self, ns):
        for sig in ns.get_signature_list():
            f = CFile.open("{}/{}_cppif.hpp".format(G.gen, sig.get_global_name()), "w")
            guard = "{}_CPPIF_HPP".format(sig.get_global_name().upper())
            f.print(
                "#ifndef {0}\n"
                "#define {0}\n"
                "/*\n"
                " * C++ interface code\n"
                " *   This class comes from signature '{1}{2}'.\n"
                " *   All functions are pure virtual. These are defined in celltype class.\n"
                " */\n"
                " \n"
                " /* */\n"
                " class {3}{2} {{\n"
                "    public:\n".format(
                    guard, sig.get_name(), self.CLASS_NAME_SUFFIX, sig.get_global_name()))
            for fh in sig.get_function_head_array():
                line = "    virtual {} {}( ".format(
                    fh.get_return_type().get_type_str(), fh.get_name())
                delim = ""
                for param in fh.get_paramlist().get_items():
                    line += "{}{} {}{}".format(
                        delim,
                        param.get_type().get_type_str(),
                        param.get_name(),
                        param.get_type().get_type_str_post())
                    delim = ", "
                line += " ) = 0;\n"
                f.print(line)
            f.print(
                "}};\n"
                "\n"
                "#endif /* {} */\n".format(guard))
            f.close()
        for sub in ns.get_namespace_list():
            self.gen_namespace_signature_header(sub)
