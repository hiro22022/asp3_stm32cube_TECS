# -*- coding: utf-8 -*-
#
#  MrubyBridgeSignaturePluginModule.rb の Python 移植

from tecslib.core.types import IntType, FloatType
from tecslib.core.ctypes import CIntType, CFloatType
from tecslib.rubylib.symbol import Sym


def _set_ignoreUnsigned(obj, rhs):
    obj.set_ignoreUnsigned(rhs)


def _set_include(obj, rhs):
    obj.set_include(rhs)


def _set_exclude(obj, rhs):
    obj.set_exclude(rhs)


def _set_auto_exclude(obj, rhs):
    obj.set_auto_exclude(rhs)


MrubyBridgePluginArgProc = {
    "ignoreUnsigned": _set_ignoreUnsigned,
    "include": _set_include,
    "exclude": _set_exclude,
    "auto_exclude": _set_auto_exclude,
}


class MrubyBridgeSignaturePluginModule(object):

    MrubyBridgePluginArgProc = MrubyBridgePluginArgProc

    celltypes = {}
    init_celltypes = {}
    struct_list = {}
    ptr_list = {}
    VM_list = {}
    VM_celltypes = {}
    VM_struct_list = {}
    VM_ptr_list = {}
    b_post_coded = False

    TYPE_MAP = {
        Sym("char_t"): [Sym("char_t"), "Char", Sym("Char"), Sym("INT")],
        Sym("uchar_t"): [Sym("uchar_t"), "UChar", Sym("Char"), Sym("INT")],
        Sym("schar_t"): [Sym("schar_t"), "SChar", Sym("Char"), Sym("INT")],
        Sym("bool_t"): [Sym("bool_t"), "Bool", Sym("Bool"), Sym("BOOL")],
        Sym("int8_t"): [Sym("int8_t"), "Int8", Sym("Int"), Sym("INT")],
        Sym("int16_t"): [Sym("int16_t"), "Int16", Sym("Int"), Sym("INT")],
        Sym("int32_t"): [Sym("int32_t"), "Int32", Sym("Int"), Sym("INT")],
        Sym("int64_t"): [Sym("int64_t"), "Int64", Sym("Int"), Sym("INT")],
        Sym("uint8_t"): [Sym("uint8_t"), "UInt8", Sym("Int"), Sym("INT")],
        Sym("uint16_t"): [Sym("uint16_t"), "UInt16", Sym("Int"), Sym("INT")],
        Sym("uint32_t"): [Sym("uint32_t"), "UInt32", Sym("Int"), Sym("INT")],
        Sym("uint64_t"): [Sym("uint64_t"), "UInt64", Sym("Int"), Sym("INT")],
        Sym("int"): [Sym("int"), "Int", Sym("Int"), Sym("INT")],
        Sym("char"): [Sym("char"), "Char", Sym("Char"), Sym("INT")],
        Sym("short"): [Sym("short"), "Short", Sym("Int"), Sym("INT")],
        Sym("long"): [Sym("long"), "Long", Sym("Int"), Sym("INT")],
        Sym("unsigned char"): [Sym("uchar_t"), "UChar", Sym("Char"), Sym("INT")],
        Sym("unsigned int"): [Sym("unsigned int"), "UInt", Sym("Int"), Sym("INT")],
        Sym("unsigned short"): [Sym("unsigned short"), "UShort", Sym("Int"), Sym("INT")],
        Sym("unsigned long"): [Sym("unsigned long"), "ULong", Sym("Int"), Sym("INT")],
        Sym("signed char"): [Sym("schar_t"), "SChar", Sym("Char"), Sym("INT")],
        Sym("signed int"): [Sym("int"), "Int", Sym("Int"), Sym("INT")],
        Sym("signed short"): [Sym("short"), "Short", Sym("Int"), Sym("INT")],
        Sym("signed long"): [Sym("long"), "Long", Sym("Int"), Sym("INT")],
        Sym("float32_t"): [Sym("float32_t"), "Float32", Sym("Float"), Sym("FLOAT")],
        Sym("double64_t"): [Sym("double64_t"), "Double64", Sym("Float"), Sym("FLOAT")],
        Sym("float"): [Sym("float"), "Float32", Sym("Float"), Sym("FLOAT")],
        Sym("double"): [Sym("double"), "Double64", Sym("Float"), Sym("FLOAT")],
    }

    def gen_preamble_ptr(self, file, b_singleton, ct_name, global_ct_name):
        tment = MrubyBridgeSignaturePluginModule.ptr_list[ct_name]
        file.print("\n  GET_SET_{2}( {0}, {1} )\n  POINTER_CLASS( {0}, {1} )\n".format(
            tment[1], tment[0], tment[3]))

    def gen_preamble_struct(self, file, b_singleton, ct_name, global_ct_name):
        tag = ct_name
        structType = MrubyBridgeSignaturePluginModule.struct_list[tag]
        file.print("""
  /* struct {0} */
  STRUCT_CLASS( {0} )
""".format(tag))
        for d in structType.get_members_decl().get_items():
            type_obj = d.get_type().get_original_type()
            if isinstance(type_obj, (IntType, CIntType)):
                bit_size = type_obj.get_bit_size()
                if bit_size in (-11, -1):
                    tType = "Char"
                    ttype = "char"
                elif bit_size == -2:
                    tType = "Short"
                    ttype = "short"
                elif bit_size == -3:
                    tType = "Int"
                    ttype = "int"
                elif bit_size == -4:
                    tType = "Long"
                    ttype = "long"
                elif bit_size == -5:
                    tType = "IntPtr"
                    ttype = "intptr"
                elif bit_size in (8, 16, 32, 64):
                    tType = "Int{}".format(bit_size)
                    ttype = "int{}".format(bit_size)
                else:
                    raise RuntimeError(
                        "MrubyBridgeSignaturePlugin: MrubyBridgeSignaturePlugin:"
                        " cannot handle bit_size {}".format(bit_size))
                file.print("MEMBER_GET_SET_INT( {}, {}, {}, {} )\n".format(
                    tag, d.get_name(), tType, ttype))
            elif isinstance(type_obj, (FloatType, CFloatType)):
                file.print("MEMBER_GET_SET_FLOAT( {}, {} )\n".format(tag, d.get_name()))
            else:
                raise RuntimeError(
                    "MrubyBridgeSignaturePlugin: MrubyBridgeSignaturePlugin:"
                    " cannot handle type")

    def gen_ep_func_body_ptr(self, file, b_singleton, ct_name, global_ct_name, sig_name, ep_name,
                             func_name, func_global_name, func_type, params):
        t = MrubyBridgeSignaturePluginModule.ptr_list[ct_name]
        type = t[1]
        file.print("""  struct RClass *a;                                /* MBP710 */

  a = mrb_define_class_under(mrb, TECS, "{0}Pointer", mrb->object_class);
  MRB_SET_INSTANCE_TT(a, MRB_TT_DATA);

  mrb_define_method(mrb, a, "initialize",      {0}Pointer_initialize,   MRB_ARGS_REQ(1));
  mrb_define_method(mrb, a, "[]",              {0}Pointer_aget,         MRB_ARGS_REQ(1));
  mrb_define_method(mrb, a, "value",           {0}Pointer_get_val,      MRB_ARGS_NONE());
  mrb_define_method(mrb, a, "[]=",             {0}Pointer_aset,         MRB_ARGS_REQ(2));
  mrb_define_method(mrb, a, "value=",          {0}Pointer_set_val,      MRB_ARGS_REQ(1));
  mrb_define_method(mrb, a, "size",            {0}Pointer_size,         MRB_ARGS_NONE());
  mrb_define_method(mrb, a, "length",          {0}Pointer_size,         MRB_ARGS_NONE());
""".format(type))

        if t[2] == Sym("Char"):
            file.print("""  mrb_define_method(mrb, a, "to_s",            CharPointer_to_s, MRB_ARGS_NONE());
  mrb_define_method(mrb, a, "from_s",          CharPointer_from_s, MRB_ARGS_REQ(1));
""")

    def gen_ep_func_body_struct(self, file, b_singleton, ct_name, global_ct_name, sig_name, ep_name,
                                func_name, func_global_name, func_type, params):
        tag = ct_name
        structType = MrubyBridgeSignaturePluginModule.struct_list[tag]
        file.print("""    struct RClass *a;                                /* MBP720 */

    a = mrb_define_class_under(mrb, TECS, "Struct{}", mrb->object_class);
    MRB_SET_INSTANCE_TT(a, MRB_TT_DATA);

    mrb_define_method(mrb, a, "initialize", Struct_{}_initialize, MRB_ARGS_NONE());
""".format(tag, tag))
        for d in structType.get_members_decl().get_items():
            file.print("  STRUCT_INIT_MEMBER( {}, {} )\n".format(tag, d.get_name()))

    def ptrMrb2C(self, file, type_, param):
        ttype = type_.get_type().get_original_type()
        tment = self.get_type_map_ent(ttype)
        tstr = tment[1]
        if param.get_size():
            sz_str = str(param.get_size())
        elif param.get_string():
            sz_str = str(param.get_string())
        else:
            sz_str = "1"
        if ttype.get_original_type().get_type_str() != param.get_type().get_type().get_type_str():
            cast_str = "({})".format(param.get_type().get_type_str())
        else:
            cast_str = ""
        modify = ""
        if param.get_direction() in (Sym("OUT"), Sym("INOUT")):
            if tstr in ("Char", "SChar", "UChar"):
                modify = "Mod"
        if param.is_nullable():
            nullable = "Nullable"
        else:
            nullable = ""
        file.print("\t{} = CheckAndGet{}Pointer{}{}( mrb, mrb_{}, {} );\n".format(
            param.get_name(), tstr, modify, nullable, param.get_name(), sz_str))

    def get_celltype_name(self):
        return self.celltype_name

    def set_ignoreUnsigned(self, rhs):
        if rhs == "true" or rhs is None:
            self.b_ignoreUnsigned = True

    def set_include(self, rhs):
        funcs = rhs.split(',')
        for rhs_func in funcs:
            found = False
            rhs_func = rhs_func.replace(' ', '')
            for a in self.signature.get_function_head_array():
                if Sym(rhs_func) == a.get_name():
                    found = True
            if found is False:
                self.cdl_error("MRB1009 include function '$1' not found in signagture '$2'", rhs, self.signature.get_name())
            else:
                self.includes.append(Sym(rhs_func))

    def set_exclude(self, rhs):
        funcs = rhs.split(',')
        for rhs_func in funcs:
            rhs_func = rhs_func.replace(' ', '')
            func_head = self.signature.get_function_head(Sym(rhs_func))
            if func_head is False:
                self.cdl_error("MRB1010 exclude function '$1' not found in signagture '$2", rhs, self.signature.get_name())
            else:
                self.excludes.append(Sym(rhs_func))

    def set_auto_exclude(self, rhs):
        if rhs == "false":
            self.b_auto_exclude = False
        elif rhs == "true":
            self.b_auto_exclude = True
        else:
            self.cdl_warning("MRB9999 auto_exclude: unknown rhs value ignored. specify true or false")
