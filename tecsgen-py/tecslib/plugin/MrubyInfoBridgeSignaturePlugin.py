# -*- coding: utf-8 -*-
#
#  mruby => TECS bridge (Info variant)
#
#   Copyright (C) 2008-2017 by TOPPERS Project
#
#   このファイルは tecsgen (Ruby 版) の
#   tecslib/plugin/MrubyInfoBridgeSignaturePlugin.rb を Python へ移植したものである．
#
#   $Id: MrubyInfoBridgeSignaturePlugin.rb 3073 2019-05-10 23:18:01Z okuma-top $
#

import re
import sys

from tecslib.core import globals as G
from tecslib.core.bnf import Generator
from tecslib.core.componentobj.namespace import Namespace
from tecslib.core.componentobj.namespacepath import NamespacePath
from tecslib.core.plugin import CFile
from tecslib.core.syntaxobj.cdlstring import CDLString
from tecslib.core.tecsgen import Makefile
from tecslib.core.toplevel import dbgPrint
from tecslib.core.types import BoolType, IntType, FloatType, VoidType, PtrType, StructType
from tecslib.plugin.SignaturePlugin import SignaturePlugin
from tecslib.plugin.lib.MrubyBridgeSignaturePluginModule import (
    MrubyBridgeSignaturePluginModule, MrubyBridgePluginArgProc,
)
from tecslib.rubylib.symbol import Sym

# Module-level Makefile setup (runs at import time, like Ruby class body code)
Makefile.add_ldflag("-lmruby -L$(MRUBYPATH)/lib -lm")
Makefile.add_search_path("$(MRUBYPATH)/include")
Makefile.add_var("MRUBYPATH", "..", "CHANGE this to suitable path")


class MrubyInfoBridgeSignaturePlugin(MrubyBridgeSignaturePluginModule, SignaturePlugin):

    b_no_banner = False  # class-level, separate from MrubyBridgeSignaturePlugin

    def __init__(self, signature, option):
        super().__init__(signature, option)

        if not MrubyInfoBridgeSignaturePlugin.b_no_banner:
            sys.stderr.write(
                "MrubyInfoBridgeSignaturePlugin: version 2.0.0"
                " (Suitable for mruby above ver 1.2.0). \n"
            )
            MrubyInfoBridgeSignaturePlugin.b_no_banner = True

        self.b_ignoreUnsigned = False
        self.includes = []         # function name list
        self.excludes = []         # function name list
        self.struct_list = {}
        self.ptr_list = {}
        self.auto_exclude_list = {}   # function name list
        self.b_auto_exclude = True    # auto_exclude = True by default
        self.b_refused_signature = False  # exclude TECSInfo & mruby bridges

        self.plugin_arg_check_proc_tab = MrubyBridgePluginArgProc
        self.parse_plugin_arg()

        self.celltype_name = Sym("tInfo{}".format(self.signature.get_global_name()))
        self.init_celltype_name = Sym("{}_Initializer".format(self.celltype_name))
        # this variable is sometimes not used. rhs coded directly.
        self.class_name = Sym("Info{}".format(self.signature.get_global_name()))

        self.func_head_array = []
        fh_array = []
        if len(self.includes) > 0 and len(self.excludes) > 0:
            self.cdl_error("MRB1011 both include && exclude are specified")

        sig_path = str(signature.get_namespace_path())
        if sig_path == "::nTECSInfo::sAccessor":
            pass  # accept
        elif sig_path in ("::nMruby::sInitializeBridge",
                          "::nMruby::sInitializeTECSBridge"):
            self.b_refused_signature = True
            return
        elif re.match(r'^::nTECSInfo::', sig_path):
            self.b_refused_signature = True
            return
        # else: accept

        if signature.get_function_head_array() is None:
            return  # 以前に文法エラー発生

        for func_head in signature.get_function_head_array():
            if len(self.includes) > 0:
                if func_head.get_name() in self.includes:
                    dbgPrint(
                        "MrubyInfoBridgePlugin: {} INCLUDED\n".format(func_head.get_name())
                    )
                    fh_array.append(func_head)
                else:
                    dbgPrint(
                        "MrubyInfoBridgePlugin: {} NOT included\n".format(
                            func_head.get_name()
                        )
                    )
            elif len(self.excludes) > 0:
                if func_head.get_name() not in self.excludes:
                    dbgPrint(
                        "MrubyInfoBridgePlugin: {} NOT excluded\n".format(
                            func_head.get_name()
                        )
                    )
                    fh_array.append(func_head)
                else:
                    dbgPrint(
                        "MrubyInfoBridgePlugin: {} EXCLUDED\n".format(func_head.get_name())
                    )
            else:
                fh_array.append(func_head)

        self.check_name_and_return_type(fh_array)
        self.check_parameter_type(fh_array)

        for fh in fh_array:
            if self.auto_exclude_list.get(fh.get_name()) is None:
                self.func_head_array.append(fh)
            else:
                dbgPrint(
                    "MrubyInfoBridgePlugin: auto_exclude {}\n".format(fh.get_name())
                )

        if len(self.func_head_array) == 0:
            self.cdl_warning(
                "MRB1012 '$1' no function remained by exclude",
                self.signature.get_name()
            )

    # === check function name & return type
    def check_name_and_return_type(self, func_head_array):
        b_init = False
        b_init_cell = False
        for func_head in func_head_array:
            if func_head.get_name() == Sym("initialize"):
                self.cdl_warning(
                    "MRW2001 initialize: internally defined. change to initialize_cell in ruby"
                )
                b_init = True
            elif func_head.get_name() == Sym("initialize_cell"):
                b_init_cell = True
            rtype = func_head.get_return_type().get_original_type()
            if isinstance(rtype, (BoolType, IntType, FloatType, VoidType)):
                pass
            else:
                if self.b_auto_exclude:
                    self.cdl_info(
                        "MRI0001 cannot return type $1, $2 automatcally excluded",
                        rtype.get_type_str(), func_head.get_name()
                    )
                    self.auto_exclude_list[func_head.get_name()] = func_head
                else:
                    self.cdl_error("MRB1001 cannot return type $1", rtype.get_type_str())
        if b_init and b_init_cell:
            self.cdl_warning(
                "MRB1002 initialize: internally defined. change to initialize_cell in ruby"
            )

    # === check parameter type
    def check_parameter_type(self, func_head_array):
        for fh in func_head_array:
            for param_decl in fh.get_paramlist().get_items():
                if param_decl.get_direction() in (Sym("SEND"), Sym("RECEIVE")):
                    if self.b_auto_exclude:
                        self.cdl_info(
                            "MRI0002 $1: $2 parameter cannot be used in mruby Bridge,"
                            " $3 automatcally excluded",
                            param_decl.get_name(),
                            str(param_decl.get_direction()).lower(),
                            fh.get_name()
                        )
                        self.auto_exclude_list[fh.get_name()] = fh
                    else:
                        self.cdl_error(
                            "MRB1003 $1: $2 parameter cannot be used in mruby Bridge",
                            param_decl.get_name(),
                            str(param_decl.get_direction()).lower()
                        )

                type_ = param_decl.get_type()
                type_org = type_.get_original_type()
                type_str = type_.get_type_str() + type_.get_type_str_post()

                b_ng = False
                if isinstance(type_org, IntType):
                    bit_size = type_org.get_bit_size()
                    if bit_size in (8, 16, 32, 64):
                        pass
                    elif bit_size in (-1, -2, -3, -4, -11):
                        pass
                    else:
                        b_ng = True
                elif isinstance(type_org, BoolType):
                    pass
                elif isinstance(type_org, FloatType):
                    pass
                elif isinstance(type_org, PtrType):
                    ttype_org = type_org.get_type()
                    ttype = ttype_org.get_original_type()
                    self.register_ptr_type(ttype_org, fh)

                    if str(type_org.get_string()) == "-1":
                        if param_decl.get_direction() in (Sym("OUT"), Sym("INOUT")):
                            if self.b_auto_exclude:
                                self.cdl_info(
                                    "MRB9999 string specifier without length cannot be used"
                                    " for out & inout parameter, $1 automatcally excluded",
                                    fh.get_name()
                                )
                                self.auto_exclude_list[fh.get_name()] = fh
                            else:
                                self.cdl_error(
                                    "MRB9999 string specifier without length cannot be"
                                    " used for out & inout parameter"
                                )

                    if isinstance(ttype, IntType):
                        pass  # bit_size = ttype.get_bit_size()
                    elif isinstance(ttype, FloatType):
                        pass
                    elif isinstance(ttype, BoolType):
                        pass
                    elif isinstance(ttype, StructType):
                        if (type_org.get_size() or type_org.get_string()
                                or type_org.get_count()):
                            if self.b_auto_exclude:
                                self.cdl_info(
                                    "MRI9999 $1: size_is, count_is, string cannot be specified"
                                    " for struct pointer, $2 automatcally excluded",
                                    param_decl.get_name(), fh.get_name()
                                )
                                self.auto_exclude_list[fh.get_name()] = fh
                            else:
                                self.cdl_error(
                                    "MRB1004 $1: size_is, count_is, string cannot be specified"
                                    " for struct pointer",
                                    param_decl.get_name()
                                )
                        self.check_struct_member(ttype_org, fh)
                    else:
                        b_ng = True
                elif isinstance(type_org, StructType):
                    self.check_struct_member(type_org, fh)
                else:
                    b_ng = True

                if b_ng:
                    if self.b_auto_exclude:
                        self.cdl_info(
                            "MRI9999 $1: type $2 cannot be used in mruby Bridge,"
                            " $3 automatcally excluded",
                            param_decl.get_name(), type_str, fh.get_name()
                        )
                        self.auto_exclude_list[fh.get_name()] = fh
                    else:
                        self.cdl_error(
                            "MRB1005 $1: type $2 cannot be used in mruby Bridge",
                            param_decl.get_name(), type_str
                        )

    # === 構造体のメンバーの型のチェック
    def check_struct_member(self, struct_type, fh):
        sttype = struct_type.get_original_type()
        if sttype.get_name() is None:
            if self.b_auto_exclude:
                self.cdl_info(
                    "MRI9999 tagless-struct cannot be handled, $1 automatcally excluded",
                    fh.get_name()
                )
                self.auto_exclude_list[fh.get_name()] = fh
                return
            else:
                self.cdl_error("MRB10007 tagless-struct cannot be handled")
        for d in sttype.get_members_decl().get_items():
            t = d.get_type().get_original_type()
            if isinstance(t, (IntType, FloatType, BoolType)):
                pass
            else:
                if self.b_auto_exclude:
                    self.cdl_info(
                        "MRI9999 $1: type '$2' not allowed for struct member,"
                        " '$3' automatcally excluded",
                        d.get_name(),
                        d.get_type().get_type_str() + d.get_type().get_type_str_post(),
                        fh.get_name()
                    )
                    self.auto_exclude_list[fh.get_name()] = fh
                    return
                else:
                    self.cdl_error(
                        "MRB1006 $1: type '$2' not allowed for struct member",
                        d.get_name(),
                        d.get_type().get_type_str() + d.get_type().get_type_str_post()
                    )
        if self.struct_list.get(sttype.get_name()) is None:
            print("  MrubyInfoBridgePlugin: [struct]   {} => [class] TECS::Struct{}\n".format(
                struct_type.get_type_str(), sttype.get_name()))
            self.struct_list[sttype.get_name()] = sttype

    def register_ptr_type(self, ttype, fh):
        t_org = ttype.get_original_type()
        tment = self.get_type_map_ent(t_org)
        if tment is None:
            return
        ptr_celltype_name = Sym("t{}Pointer".format(tment[1]))
        if MrubyBridgeSignaturePluginModule.ptr_list.get(ptr_celltype_name) is None:
            print("  MrubyInfoBridgePlugin: [pointer]  {}* => [class] TECS::{}Pointer\n".format(
                ttype.get_type_str(), tment[1]))
            MrubyBridgeSignaturePluginModule.ptr_list[ptr_celltype_name] = tment
        if self.ptr_list.get(ptr_celltype_name) is None:
            self.ptr_list[ptr_celltype_name] = tment

    def get_type_map_ent(self, ttype):
        if isinstance(ttype, StructType):
            return None
        tstr = re.sub(r'const ', '', ttype.get_type_str())
        tstr = re.sub(r'volatile ', '', tstr)
        if self.b_ignoreUnsigned:
            tstr = re.sub(r'unsigned ', '', tstr)
            tstr = re.sub(r'uint', 'int', tstr)
            tstr = re.sub(r'[cs]char', 'char', tstr)
        return MrubyBridgeSignaturePluginModule.TYPE_MAP.get(Sym(tstr))

    # === CDL ファイルの生成
    def gen_cdl_file(self, file):
        if self.b_refused_signature:
            return

        # ブリッジセルタイプの生成
        if MrubyBridgeSignaturePluginModule.celltypes.get(self.celltype_name) is None:
            MrubyBridgeSignaturePluginModule.celltypes[self.celltype_name] = [self]
            MrubyBridgeSignaturePluginModule.init_celltypes[self.init_celltype_name] = True

            self.print_msg(
                "  MrubyInfoBridgePlugin: [signature] {} => [class] TECS::{}\n".format(
                    self.signature.get_namespace_path(), self.class_name
                )
            )

            file.print("""\
 /*
  * MrubyInfoBridgeSignaturePlugin:
  *     signature={sig_path}
  *
  *   => celltype=nMrubyInfo::{ct}
  *      (bridge cell 's celltype; generated in this file)
  *      cell nMrubyInfo::{ct} BridgeCellName {{ cTECS = CellName.eEntry; }};
  *        where eEntry's signature must be {sig_path}.
  *      => class=TECS::{cls}
  *         (mruby's class; accessible from your script)
  *          bridge = TECS::{cls}.new("BridgeCellName")
  */
import( <mruby.cdl> );

/****  Ruby => TECS Bridge Celltype (MBP500) ****/
namespace nMrubyInfo{{
    // bridge celltype
    [singleton, idx_is_id,active]   // not actually active, to avoid warning W1002, W1007
    celltype {ct} {{
        [dynamic,optional]
            call {sig_path} cTECS;
        call nTECSInfo::sTECSInfo cTECSInfo;
        [dynamic,optional]
            call nTECSInfo::sEntryInfo cEntryInfo;
        [dynamic,optional]
            call nTECSInfo::sSignatureInfo cSignatureInfo;
        [dynamic,optional]
            call nTECSInfo::sRawEntryDescriptorInfo cRawEntryDescriptorInfo;
        attr {{
            [omit]
            char_t *VMname = "VM";
            [omit]
            char_t *bridgeName = C_EXP( "$cell$" );
        }};
    }};
    // bridge initializer celltype
    celltype {init_ct} {{
        entry nMruby::sInitializeTECSBridge eInitialize;
    }};
}};

// Bridge Cell
cell nMrubyInfo::{ct} MrubyInfoBridge_{gname} {{
  // cTECS = Sample.eEnt;
  cTECSInfo = TECSInfo.eTECSInfo;
  // bridgeName = "Simple";
}};
""".format(
                sig_path=self.signature.get_namespace_path(),
                ct=self.celltype_name,
                cls=self.class_name,
                init_ct=self.init_celltype_name,
                gname=self.signature.get_global_name(),
            ))

            # 構造体セルタイプの生成
            for name, sttype in self.struct_list.items():
                if MrubyBridgeSignaturePluginModule.struct_list.get(name) is None:
                    file.print("""\
namespace nMruby{{
    [singleton]
    celltype {name} {{
        entry nMruby::sInitializeTECSBridge eInitialize;
    }};
}};
""".format(name=name))
                    MrubyBridgeSignaturePluginModule.struct_list[name] = sttype

        else:
            self.cdl_info(
                "MRBW001 MrubyInfoBridgePlugin: signature '$1' duplicate. ignored current one",
                self.signature.get_namespace_path()
            )
            MrubyBridgeSignaturePluginModule.celltypes[self.celltype_name].append(self)

    # === gen_cdl_file で定義したセルタイプに新しいセルが定義された
    def new_cell(self, cell):
        if cell.get_celltype().get_name() != self.celltype_name:
            return

        join = cell.get_join_list().get_item(Sym("VMname"))
        if join:
            vm_name = Sym(CDLString.remove_dquote(str(join.get_rhs())))
        else:
            vm_name = Sym("VM")

        if MrubyBridgeSignaturePluginModule.VM_list.get(vm_name) is None:
            MrubyBridgeSignaturePluginModule.VM_list[vm_name] = True

            initializer_celltype_cdl = "{}/{}_Initializer.cdl".format(
                G.gen, cell.get_name()
            )
            f = CFile.open(initializer_celltype_cdl, "w")

            self.print_msg(
                "  MrubyInfoBridgePlugin: join your VM's cInitialize to"
                " {}_TECSInitializer.eInitialize\n".format(vm_name)
            )

            f.print("""\

  // prototype of TECSInitializer (MBP510)
  cell nMruby::tTECSInitializer {vm_name}_TECSInitializer;
""".format(vm_name=vm_name))
            f.close()

            Generator.parse_class(initializer_celltype_cdl, self)

        if MrubyBridgeSignaturePluginModule.VM_celltypes.get(vm_name):
            vma = MrubyBridgeSignaturePluginModule.VM_celltypes[vm_name]
            if vma.get(self.celltype_name):
                vma[self.celltype_name].append(cell)
            else:
                vma[self.celltype_name] = [cell]
                MrubyBridgeSignaturePluginModule.VM_celltypes[vm_name] = vma
        else:
            vma = {}
            vma[self.celltype_name] = [cell]
            MrubyBridgeSignaturePluginModule.VM_celltypes[vm_name] = vma

        for stname, sttype in self.struct_list.items():
            if MrubyBridgeSignaturePluginModule.VM_struct_list.get(vm_name):
                MrubyBridgeSignaturePluginModule.VM_struct_list[vm_name][
                    sttype.get_name()
                ] = sttype
            else:
                MrubyBridgeSignaturePluginModule.VM_struct_list[vm_name] = {
                    sttype.get_name(): sttype
                }

        for ptr_celltype_name, tment in self.ptr_list.items():
            if MrubyBridgeSignaturePluginModule.VM_ptr_list.get(vm_name):
                MrubyBridgeSignaturePluginModule.VM_ptr_list[vm_name][
                    ptr_celltype_name
                ] = tment
            else:
                MrubyBridgeSignaturePluginModule.VM_ptr_list[vm_name] = {
                    ptr_celltype_name: tment
                }

    # === プラグインが CDL の POST コードを生成
    @classmethod
    def gen_post_code(cls, file):
        dbgPrint("{}: gen_post_code\n".format(cls.__name__))
        cls.gen_post_code_body(file)

    @classmethod
    def gen_post_code_body(cls, file):
        if MrubyBridgeSignaturePluginModule.b_post_coded == False:
            MrubyBridgeSignaturePluginModule.b_post_coded = True
        else:
            return
        dbgPrint("{}: gen_post_code_body\n".format(cls.__name__))

        file.print("\n  // MrubyInfoBridgeSignaturePlugin: MBP601\n")
        for vm_name, instance_list in MrubyBridgeSignaturePluginModule.VM_celltypes.items():
            for celltype_name, array in instance_list.items():
                cell = array[0]
                if cell.get_celltype():
                    ct_name = cell.get_celltype().get_name()
                    if re.match(r'^tInfo', str(ct_name)):
                        info = "Info"
                    else:
                        info = ""
                    file.print(
                        "  cell nMruby{}::{}_Initializer {}_{}_Initializer{{}};\n".format(
                            info, ct_name, vm_name, ct_name
                        )
                    )

        file.print("  // MBP602\n")
        for name, tment in MrubyBridgeSignaturePluginModule.ptr_list.items():
            file.print("  cell nMruby::{} C{} {{}};\n".format(name, name))

        file.print("  // MBP603\n")
        for name, sttype in MrubyBridgeSignaturePluginModule.struct_list.items():
            file.print("  cell nMruby::{} C{} {{}};\n".format(name, name))

        if MrubyBridgeSignaturePluginModule.VM_celltypes is None:
            raise RuntimeError("MrubyInfoBridgeSignaturePlugin: are0")

        for vm_name, instance_list in MrubyBridgeSignaturePluginModule.VM_celltypes.items():
            file.print(
                "  /* === VM name is '{}' === (MBP610) */\n".format(vm_name)
            )
            init_cell_name = "{}_TECSInitializer".format(vm_name)

            file.print(
                "  cell nMruby::tTECSInitializer {} {{\n".format(init_cell_name)
            )

            for celltype_name, array in instance_list.items():
                ct_name = celltype_name
                file.print(
                    "    cInitialize[] = {}_{}_Initializer.eInitialize;\n".format(
                        vm_name, ct_name
                    )
                )
            if MrubyBridgeSignaturePluginModule.VM_ptr_list.get(vm_name):
                for name, tment in MrubyBridgeSignaturePluginModule.VM_ptr_list[vm_name].items():
                    file.print("    cInitialize[] = C{}.eInitialize;\n".format(name))
            if MrubyBridgeSignaturePluginModule.VM_struct_list.get(vm_name):
                for name, sttype in MrubyBridgeSignaturePluginModule.VM_struct_list[
                        vm_name].items():
                    file.print("    cInitialize[] = C{}.eInitialize;\n".format(name))
            file.print("  };")

    ####### 以下コード生成段階 ######

    # === 受け口関数の本体コードを生成
    def gen_ep_func_body(self, file, b_singleton, ct_name, global_ct_name,
                         sig_name, ep_name, func_name, func_global_name,
                         func_type, params):
        if MrubyBridgeSignaturePluginModule.celltypes.get(ct_name):
            self.gen_ep_func_body_bridge(
                file, b_singleton, ct_name, global_ct_name,
                sig_name, ep_name, func_name, func_global_name, func_type, params
            )
        elif MrubyBridgeSignaturePluginModule.init_celltypes.get(ct_name):
            self.gen_ep_func_body_bridge_init(
                file, b_singleton, ct_name, global_ct_name,
                sig_name, ep_name, func_name, func_global_name, func_type, params
            )
        elif MrubyBridgeSignaturePluginModule.ptr_list.get(ct_name):
            self.gen_ep_func_body_ptr(
                file, b_singleton, ct_name, global_ct_name,
                sig_name, ep_name, func_name, func_global_name, func_type, params
            )
        elif MrubyBridgeSignaturePluginModule.struct_list.get(ct_name):
            self.gen_ep_func_body_struct(
                file, b_singleton, ct_name, global_ct_name,
                sig_name, ep_name, func_name, func_global_name, func_type, params
            )
        else:
            raise RuntimeError(
                "MrubyInfoBridgeSignaturePlugin: Unknown {}".format(ct_name)
            )

    def gen_ep_func_body_bridge(self, file, b_singleton, ct_name, global_ct_name,
                                sig_name, ep_name, func_name, func_global_name,
                                func_type, params):
        raise RuntimeError("MrubyInfoBridgeSignaturePlugin: unexpected")

    def gen_ep_func_body_bridge_init(self, file, b_singleton, ct_name, global_ct_name,
                                     sig_name, ep_name, func_name, func_global_name,
                                     func_type, params):
        file.print("""\
    // CELLCB *p_cellcb = GET_CELLCB( idx );  /* no error check */     /* MBP700 */
    struct RClass\t*rc;

    rc = mrb_define_class_under( mrb, TECS, "{cls}", mrb->object_class );
    mrb_define_method( mrb, rc, "initialize", MrubyInfoBridge_{ct}_initialize, MRB_ARGS_REQ(1) );
    MRB_SET_INSTANCE_TT(rc, MRB_TT_DATA);
""".format(cls=self.class_name, ct=self.celltype_name))

        for f in self.func_head_array:
            if not f.is_function():
                continue
            if f.get_name() != Sym("initialize"):
                f_func_name = f.get_name()
            else:
                f_func_name = Sym("initialize_cell")

            n_param = 0
            for param in f.get_paramlist().get_items():
                if param.get_direction() in (Sym("IN"), Sym("INOUT"), Sym("OUT")):
                    n_param += 1
                elif param.get_direction() in (Sym("SEND"), Sym("RECEIVE")):
                    raise RuntimeError("MrubyInfoBridgeSignaturePlugin: send, receive")
            if n_param > 0:
                p_str = "MRB_ARGS_REQ( {} )".format(n_param)
            else:
                p_str = "MRB_ARGS_NONE()"

            file.print(
                '    mrb_define_method( mrb, rc, "{fn}",'
                ' MrubyInfoBridge_{ct}_{fn}, {p_str} );\n'.format(
                    fn=f_func_name, ct=self.celltype_name, p_str=p_str
                )
            )

    # === 受け口関数の preamble (C言語)を生成する
    def gen_preamble(self, file, b_singleton, ct_name, global_ct_name):
        if MrubyBridgeSignaturePluginModule.celltypes.get(ct_name):
            self.gen_preamble_mruby(file, b_singleton, ct_name, global_ct_name)
            self.gen_preamble_instance(file, b_singleton, ct_name, global_ct_name)
            self.gen_preamble_instance_initialize(file, b_singleton, ct_name, global_ct_name)
            self.gen_preamble_bridge_func(file, b_singleton, ct_name, global_ct_name)
        elif MrubyBridgeSignaturePluginModule.init_celltypes.get(ct_name):
            self.gen_preamble_mruby(file, b_singleton, ct_name, global_ct_name)
            self.gen_preamble_instance_proto(file, b_singleton, ct_name, global_ct_name)
        elif MrubyBridgeSignaturePluginModule.ptr_list.get(ct_name):
            self.gen_preamble_ptr(file, b_singleton, ct_name, global_ct_name)
        elif MrubyBridgeSignaturePluginModule.struct_list.get(ct_name):
            self.gen_preamble_struct(file, b_singleton, ct_name, global_ct_name)
        else:
            raise RuntimeError(
                "MrubyInfoBridgeSignaturePlugin: Unknown {}".format(ct_name)
            )

    def gen_preamble_mruby(self, file, b_singleton, ct_name, global_ct_name):
        file.print("""\
/* MBP: MrubyInfoBridgePlugin: MBP000 */
#include "mruby.h"
#include "mruby/class.h"
#include "mruby/data.h"
#include "mruby/string.h"
#include "TECSPointer.h"
#include "TECSStruct.h"
#include "t_syslog.h"
#include "stdlib.h"

#if defined(_WIN32) || defined(__WIN32__) || defined(__CYGWIN__)
#define DLLEXPORT __declspec(dllexport)
#else
#define DLLEXPORT
#endif

#ifndef NULL
#define NULL 0
#endif
""")

    def gen_preamble_instance(self, file, b_singleton, ct_name, global_ct_name):
        # idx_is_id の場合の CB プロトタイプ宣言
        nsp = NamespacePath(Sym("nMrubyInfo"), True)
        nsp.append_bang(ct_name)
        ct = Namespace.find(nsp)
        if ct.idx_is_id_act:
            if ct.has_CB():
                inib_cb = "CB"
            elif ct.has_INIB():
                inib_cb = "INIB"
            else:
                inib_cb = None
            if inib_cb:
                for cell in ct.get_cell_list():
                    if cell.is_generate():
                        name_array = ct.get_name_array(cell)
                        file.print(
                            "extern {}_{} {}_{};\n".format(
                                ct.get_global_name(), inib_cb,
                                cell.get_global_name(), inib_cb
                            )
                        )

        file.print("""\

/* RData MBP001 */
static void 
{ct}_free( mrb_state *mrb, void *p )
{{
    if( p )
        (void)mrb_free( mrb, p );
}}

/* RData MBP002 */
struct mrb_data_type data_type_{ct} =
{{
    "{ct}",
    {ct}_free
}};

/* RData MBP003 */
struct tecs_{ct} {{
    Descriptor( {sig_gname} ) desc;
}};

#ifndef MRUBYINFOBRIDGE_NAME_LEN
#define MRUBYINFOBRIDGE_NAME_LEN  256
#endif
""".format(ct=self.celltype_name, sig_gname=self.signature.get_global_name()))

    def gen_preamble_instance_proto(self, file, b_singleton, ct_name, global_ct_name):
        file.print(
            "//  Prototype MBP400\n"
            "mrb_value  MrubyInfoBridge_{ct}_initialize("
            " mrb_state *mrb, mrb_value self);\n".format(ct=self.celltype_name)
        )

        for f in self.func_head_array:
            if not f.is_function():
                continue
            if f.get_name() != Sym("initialize"):
                f_func_name = f.get_name()
            else:
                f_func_name = Sym("initialize_cell")

            file.print(
                "mrb_value  MrubyInfoBridge_{ct}_{fn}("
                " mrb_state *mrb, mrb_value self );\n".format(
                    ct=self.celltype_name, fn=f_func_name
                )
            )

    def gen_preamble_instance_initialize(self, file, b_singleton, ct_name, global_ct_name):
        file.print("""\

/* MBP100 */
mrb_value
MrubyInfoBridge_{ct}_initialize( mrb_state *mrb, mrb_value self)
{{
    mrb_value\tname;
    struct tecs_{ct} *tecs_desc;
    Descriptor( nTECSInfo_sRawEntryDescriptorInfo ) rawEntryDescDesc;
    Descriptor( nTECSInfo_sEntryInfo ) entryDesc;
    Descriptor( nTECSInfo_sSignatureInfo ) signatureDesc;
    Descriptor( {sig_gname} ) cellEntryDesc;
    char_t   tecs_name[ MRUBYINFOBRIDGE_NAME_LEN ];
    void     *rawDesc;
    char     *p;
    int      subsc;

    /* set DATA_TYPE earlier to avoid SEGV */
    DATA_TYPE( self ) = &data_type_{ct};

    mrb_get_args(mrb, "o", &name );
    if( mrb_type( name ) != MRB_TT_STRING ){{
        mrb_raise(mrb, E_NAME_ERROR, "cell name not string");
    }}
    if( cTECSInfo_findRawEntryDescriptor( RSTRING_PTR( name ), &rawEntryDescDesc, &entryDesc ) != E_OK ){{
         mrb_raise( mrb, E_ARGUMENT_ERROR, "MrubyInfoBridgeSignaturePlugin: path not found" );
    }}
    else{{
#ifdef MRUBYINFOBRIDGEPLUGIN_VERBOSE
         syslog( LOG_NOTICE, "MrubyInfoBridgePlugin: %s: found", RSTRING_PTR( name ) );
#endif /* MRUBYINFOBRIDGEPLUGIN_VERBOSE */
    }}

    // retrieve Signature Name from EntryInfo to check
    cEntryInfo_set_descriptor( entryDesc );
    cEntryInfo_getSignatureInfo( &signatureDesc );
    cSignatureInfo_set_descriptor( signatureDesc );
    cSignatureInfo_getName( tecs_name, MRUBYINFOBRIDGE_NAME_LEN );
    if( strncmp( tecs_name, "{sig_name}", MRUBYINFOBRIDGE_NAME_LEN ) != 0 ){{
         mrb_raise( mrb, E_ARGUMENT_ERROR, "MrubyInfoBridgeSignaturePlugin: signature name mismatch" );
    }}
    else{{
#ifdef MRUBYINFOBRIDGEPLUGIN_VERBOSE
         syslog( LOG_NOTICE, "MrubyInfoBridgePlugin: signature name matched: %s", "{sig_name}" );
#endif /* MRUBYINFOBRIDGEPLUGIN_VERBOSE */
    }}

    /* retrieve entry array suscript if exist */
    for( p = RSTRING_PTR( name ), subsc = 0; *p != 0; p++ ){{
        if( *p == '[' ){{
            p++;
            subsc = atoi( p );
            break;
        }}
    }}

    // retrieve Cell's Entry Descriptor
    cRawEntryDescriptorInfo_set_descriptor( rawEntryDescDesc );
    if( cRawEntryDescriptorInfo_getRawDescriptor( subsc, &rawDesc ) != E_OK ){{
         mrb_raise( mrb, E_ARGUMENT_ERROR, "MrubyInfoBridgeSignaturePlugin: cannot get RawDescriptor (maybe subscript out of range)" );
    }}
    else{{
#ifdef MRUBYINFOBRIDGEPLUGIN_VERBOSE
         syslog( LOG_NOTICE, "MrubyInfoBridgePlugin: got RawDescriptor: %s %d", "{sig_name}", subsc );
#endif /* MRUBYINFOBRIDGEPLUGIN_VERBOSE */
    }}
    cellEntryDesc.vdes = (struct tag_{sig_gname}_VDES *)rawDesc;
  
    tecs_desc = (struct tecs_{ct} *)mrb_malloc(mrb, sizeof(struct tecs_{ct}) );
    tecs_desc->desc = cellEntryDesc;
    DATA_PTR( self ) = (void *)tecs_desc;

    return self;
}}
""".format(
            ct=self.celltype_name,
            sig_gname=self.signature.get_global_name(),
            sig_name=self.signature.get_name(),
        ))

    def gen_preamble_bridge_func(self, file, b_singleton, ct_name, global_ct_name):
        for f in self.func_head_array:
            if not f.is_function():
                continue
            if f.get_name() != Sym("initialize"):
                f_func_name = f.get_name()
            else:
                f_func_name = Sym("initialize_cell")

            ret_type = f.get_return_type()
            ret_type0 = f.get_return_type().get_original_type()
            b_void = ret_type0.is_void()
            plist = f.get_paramlist().get_items()

            file.print("""\

/* bridge function (MBP101) */
mrb_value
MrubyInfoBridge_{ct}_{fn}( mrb_state *mrb, mrb_value self )
{{
  /* cellcbp (MBP105) */
  // CELLCB\t*p_cellcb = ((struct tecs_{self_ct} *)DATA_PTR(self))->cbp;
""".format(ct=ct_name, fn=f_func_name, self_ct=self.celltype_name))

            file.print("\t/* variables for return & parameter (MBP110) */\n")
            if not b_void:
                file.print(
                    "\t{}\tret_val{};\n".format(
                        ret_type.get_type_str(), ret_type.get_type_str_post()
                    )
                )

            arg_str = ""
            n_param = 0
            n_scalar = 0
            n_ptr = 0
            n_struct = 0

            for param in plist:
                if param.get_direction() not in (Sym("IN"), Sym("INOUT"), Sym("OUT")):
                    continue
                type_ = param.get_type().get_original_type()
                if isinstance(type_, IntType):
                    file.print("\tmrb_int\tmrb_{};\n".format(param.get_name()))
                    file.print("\t{}\t{}{};\n".format(
                        param.get_type().get_type_str(),
                        param.get_name(),
                        param.get_type().get_type_str_post()
                    ))
                    arg_str += "i"
                    n_param += 1
                    n_scalar += 1
                elif isinstance(type_, FloatType):
                    file.print("\tmrb_float\tmrb_{};\n".format(param.get_name()))
                    file.print("\t{}\t{}{};\n".format(
                        param.get_type().get_type_str(),
                        param.get_name(),
                        param.get_type().get_type_str_post()
                    ))
                    arg_str += "f"
                    n_param += 1
                    n_scalar += 1
                elif isinstance(type_, BoolType):
                    file.print("\tmrb_value\tmrb_{};\n".format(param.get_name()))
                    file.print("\t{}\t{}{};\n".format(
                        param.get_type().get_type_str(),
                        param.get_name(),
                        param.get_type().get_type_str_post()
                    ))
                    arg_str += "o"
                    n_param += 1
                    n_scalar += 1
                elif isinstance(type_, PtrType):
                    file.print("\tmrb_value\tmrb_{};\n".format(param.get_name()))
                    file.print("\t{}\t{}{};\n".format(
                        param.get_type().get_type_str(),
                        param.get_name(),
                        param.get_type().get_type_str_post()
                    ))
                    arg_str += "o"
                    n_param += 1
                    n_ptr += 1
                elif isinstance(type_, StructType):
                    file.print("\tmrb_value\tmrb_{};\n".format(param.get_name()))
                    file.print("\t{}\t*{}{};\n".format(
                        param.get_type().get_type_str(),
                        param.get_name(),
                        param.get_type().get_type_str_post()
                    ))
                    arg_str += "o"
                    n_param += 1
                    n_struct += 1
                else:
                    raise RuntimeError("MrubyInfoBridgeSignaturePlugin: Unknown type")

            if n_param > 0:
                file.print("\t/* retrieve arguments (MBP111) */\n")
                file.print('\tmrb_get_args(mrb, "{}"'.format(arg_str))
                for param in plist:
                    if param.get_direction() not in (Sym("IN"), Sym("INOUT"), Sym("OUT")):
                        continue
                    file.print(", &mrb_{}".format(param.get_name()))
                file.print(" );\n")

                if n_scalar > 0 or n_struct > 0:
                    file.print("\t/* convert mrb to C (MBP112) */\n")

                for param in plist:
                    if param.get_direction() not in (Sym("IN"), Sym("INOUT"), Sym("OUT")):
                        continue
                    type_ = param.get_type().get_original_type()
                    if isinstance(type_, IntType):
                        ttype = type_.get_original_type()
                        tment = self.get_type_map_ent(ttype)
                        file.print(
                            "\tVALCHECK_{}( mrb, mrb_{} );\n".format(
                                tment[1], param.get_name()
                            )
                        )
                        file.print(
                            "\t{} = ({})mrb_{};\n".format(
                                param.get_name(),
                                param.get_type().get_type_str(),
                                param.get_name()
                            )
                        )
                    elif isinstance(type_, FloatType):
                        file.print(
                            "\t{} = ({})mrb_{};\n".format(
                                param.get_name(),
                                param.get_type().get_type_str(),
                                param.get_name()
                            )
                        )
                    elif isinstance(type_, BoolType):
                        file.print(
                            "\t{} = mrb_test( mrb_{} );\n".format(
                                param.get_name(), param.get_name()
                            )
                        )
                    elif isinstance(type_, PtrType):
                        ttype = type_.get_type().get_original_type()
                        if isinstance(ttype, StructType):
                            file.print(
                                "\tCHECK_STRUCT( {}, mrb_{} );\n".format(
                                    ttype.get_name(), param.get_name()
                                )
                            )
                            file.print(
                                "\t{} = (struct {}*)DATA_PTR(mrb_{});\n".format(
                                    param.get_name(), ttype.get_name(), param.get_name()
                                )
                            )
                        elif isinstance(ttype, (IntType, FloatType, BoolType)):
                            pass  # handled in ptrMrb2C below
                        else:
                            raise RuntimeError(
                                "MrubyInfoBridgeSignaturePlugin: cannot handle type"
                            )
                    elif isinstance(type_, StructType):
                        file.print(
                            "\tCHECK_STRUCT( {}, mrb_{} );\n".format(
                                type_.get_name(), param.get_name()
                            )
                        )
                        file.print(
                            "\t{} = (struct {}*)DATA_PTR(mrb_{});\n".format(
                                param.get_name(), type_.get_name(), param.get_name()
                            )
                        )
                    else:
                        raise RuntimeError(
                            "MrubyInfoBridgeSignaturePlugin: canot treat class"
                        )

                if n_ptr > 0:
                    file.print("\t/* convert mrb to C for pointer types (MBP113) */\n")
                for param in plist:
                    if param.get_direction() not in (Sym("IN"), Sym("INOUT"), Sym("OUT")):
                        continue
                    type_ = param.get_type().get_original_type()
                    if isinstance(type_, PtrType):
                        inner = type_.get_type().get_original_type()
                        if isinstance(inner, StructType):
                            pass  # already handled above
                        elif isinstance(inner, (IntType, FloatType, BoolType)):
                            self.ptrMrb2C(file, type_, param)
                        else:
                            raise RuntimeError(
                                "MrubyInfoBridgeSignaturePlugin: cannot handle type"
                            )

            file.print("""\
\t/* calling target (MBP120) */
  cTECS_set_descriptor( ((struct tecs_{ct} *)DATA_PTR(self))->desc );
""".format(ct=self.celltype_name))
            if not b_void:
                file.print("\tret_val = ")
            else:
                file.print("\t")
            delim = ""
            file.print("cTECS_{} ( ".format(f.get_name()))
            for param in plist:
                if isinstance(param.get_type().get_original_type(), StructType):
                    aster = "*"
                else:
                    aster = ""
                file.print(delim + aster + str(param.get_name()))
                delim = ", "
            file.print(" );\n")

            file.print("\t/* return (MBP130) */\n")
            if isinstance(ret_type0, BoolType):
                file.print(
                    "\treturn ret_val ? mrb_true_value() : mrb_false_value();\n"
                )
            elif isinstance(ret_type0, IntType):
                file.print("\treturn mrb_fixnum_value( ret_val );\n")
            elif isinstance(ret_type0, FloatType):
                file.print("\treturn mrb_float_value( mrb, ret_val );\n")
            elif isinstance(ret_type0, VoidType):
                file.print("\treturn  mrb_nil_value();\n")
            else:
                raise RuntimeError("MrubyInfoBridgeSignaturePlugin: unknown type")

            file.print("}\n")
