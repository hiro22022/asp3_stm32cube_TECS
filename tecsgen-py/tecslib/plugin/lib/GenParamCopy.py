# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   このファイルは tecsgen (Ruby 版) の tecslib/plugin/lib/GenParamCopy.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．
#
#   $Id: GenParamCopy.rb 3176 2020-10-25 08:07:05Z okuma-top $
#

from tecslib.core.expression import Expression
from tecslib.core.types import (
    DefinedType, BoolType, IntType, FloatType, PtrType, StructType,
    VoidType, EnumType, FuncType, ArrayType,
)


#= ParamCopy
#
# パラメータコピーするマーシャラ／アンマーシャラコードを生成するメソッド print_param を提供する．
# RPCPlugin, OpaqueRPCPlugin に include される．
# RPCPlugin (トランスペアレント) では、oneway 関数で in のポインタ引数の場合に限って print_param が用いられる．
#
class GenParamCopy:

    #=== 引数の転送コードを生成
    def print_param(self, name, type, file, nest, dir, outer, outer2, b_marshal, b_get,
                    alloc_cp=None, alloc_cp_extra=None, name_list=None):
        if isinstance(type.get_original_type(), ArrayType) and b_get and dir != "OUT":
            indent = "\t" * nest
            subsc = type.get_subscript()
            if subsc is None:
                raise Exception("Unsubscripted Array Not Supported")
            else:
                size_str = subsc.to_str(name_list, outer, outer2)
                file.print("""\
/* (GenParamCopy0001) */
{indent}if((ercd_={alloc_cp}(sizeof({tstr}{tpost})*({size_str}),(void **)&{outer}{name}{outer2}{alloc_cp_extra}))!=E_OK)\t/* GenParamCopy 1 */
{indent}	goto error_reset;
""".format(
                    indent=indent, alloc_cp=alloc_cp,
                    tstr=type.get_type().get_type_str(), tpost=type.get_type().get_type_str_post(),
                    size_str=size_str, outer=outer or "", name=name, outer2=outer2 or "",
                    alloc_cp_extra=alloc_cp_extra or ""))
                if (dir == "SEND" or dir == "RECEIVE") and type.get_type().has_pointer():
                    file.print("""\
{indent}memset( (void *){outer}{name}{outer2}{alloc_cp_extra}, 0, sizeof({tstr}{tpost})*({size_str}));   /* GenParamCopy Alloc1 */
""".format(
                        indent=indent, outer=outer or "", name=name, outer2=outer2 or "",
                        alloc_cp_extra=alloc_cp_extra or "",
                        tstr=type.get_type().get_type_str(), tpost=type.get_type().get_type_str_post(),
                        size_str=size_str))
        self.print_param0(name, type, file, nest, dir, outer, outer2, b_marshal, b_get,
                          alloc_cp, alloc_cp_extra, name_list)

    def print_param0(self, name, type, file, nest, dir, outer, outer2, b_marshal, b_get,
                     alloc_cp=None, alloc_cp_extra=None, name_list=None):
        indent = "\t" * nest

        if isinstance(type, DefinedType):
            self.print_param0(name, type.get_type(), file, nest, dir, outer, outer2,
                              b_marshal, b_get, alloc_cp, alloc_cp_extra)
        elif isinstance(type, (BoolType, IntType, FloatType)):
            if isinstance(type, BoolType):
                type_str = "Bool"
            elif isinstance(type, IntType):
                bit_size = type.get_bit_size()
                sign = type.get_sign()
                if sign == "UNSIGNED":
                    signC = "U"
                elif sign == "SIGNED":
                    if bit_size == -1 or bit_size == -11:
                        signC = "S"
                    else:
                        signC = ""
                else:
                    signC = ""

                if bit_size == -1 or bit_size == -11:
                    type_str = "{}Char".format(signC)
                elif bit_size == -2:
                    type_str = "{}Short".format(signC)
                elif bit_size == -3:
                    type_str = "{}Int".format(signC)
                elif bit_size == -4:
                    type_str = "{}Long".format(signC)
                elif bit_size == -5:
                    type_str = "Intptr"
                elif bit_size in (8, 16, 32, 64, 128):
                    type_str = "{}Int{}".format(signC, bit_size)
                else:
                    raise Exception("unknown bit_size '{}' for int type ".format(bit_size))
            elif isinstance(type, FloatType):
                bit_size = type.get_bit_size()
                if bit_size == 32:
                    type_str = "Float32"
                else:
                    type_str = "Double64"

            o = outer or ""
            o2 = outer2 or ""
            if b_get:
                file.print(indent)
                file.print("/* (GenParamCopy0101) */\n")
                file.print(indent)
                file.print("if( ( ercd_ = cTDR_get{}( &({}{}{}) ) ) != E_OK )\t/* GenParamCopy 2 */\n".format(
                    type_str, o, name, o2))
                file.print(indent)
                file.print("	goto error_reset;\n")
            else:
                file.print(indent)
                file.print("/* (GenParamCopy0102) */\n")
                file.print(indent)
                file.print("if( ( ercd_ = cTDR_put{}( {}{}{} ) ) != E_OK )\t/* GenParamCopy 3 */\n".format(
                    type_str, o, name, o2))
                file.print(indent)
                file.print("	goto error_reset;\n")

        elif isinstance(type, PtrType):
            count = type.get_count()
            size = type.get_size()
            string = type.get_string()
            o = outer or ""
            o2 = outer2 or ""
            if count or size or string:
                nest = self.print_nullable_pre(name, type, file, nest, dir, outer, outer2, b_marshal, b_get)
                indent = "\t" * nest
                loop_counter_type = IntType(32)
                file.print("{indent}{{\t/* GenParamCopy0103 */\n".format(indent=indent))
                file.print("{}\t{}  i__{}, length__{};\n".format(
                    indent, loop_counter_type.get_type_str(), nest, nest))

                if size or count:
                    if size:
                        size_str = size.to_str(name_list, o, o2)
                    if count:
                        count_str = count.to_str(name_list, o, o2)
                    else:
                        count_str = size_str
                    file.print("{}\tlength__{} = {};\t/* GenParamCopy0104 */\n".format(indent, nest, count_str))

                    if b_get and type.get_max() is not None and not (
                            (dir == "INOUT" or dir == "OUT") and alloc_cp is None):
                        file.print("{}\tif( length__{} > {} ){{\t/* GenParamCopy0105 max check 1 */\n".format(
                            indent, nest, type.get_max().to_s()))
                        file.print("{indent}\t\tercd_ = E_PAR;\n".format(indent=indent))
                        file.print("{indent}\t\tgoto error_reset;\n".format(indent=indent))
                        file.print("{indent}\t}}\n".format(indent=indent))

                else:
                    bit_size = type.get_type().get_bit_size()
                    if bit_size == -1:
                        b_size = 8
                    elif bit_size in (8, 16, 32, 64):
                        b_size = bit_size
                    else:
                        self.cdl_error(
                            "R9999 $1: string specifier cannot be specified to '$2' in current implementation",
                            name, type.get_type().get_type_str() + type.get_type().get_type_str_post())
                    if not b_get:
                        if isinstance(string, Expression):
                            len_ = string.to_str(name_list, o, o2)
                            file.print("{}\tlength__{} = STRNLEN{}({}{}{},({})-1)+1;\t/* GenParamCopy0106 */\n".format(
                                indent, nest, b_size, o, name, o2, len_))
                            file.print("{}\tif( length__{} < {}) length__{} += 1;\n".format(
                                indent, nest, len_, nest))
                        else:
                            file.print("{}\tlength__{} = STRLEN{}({}{}{})+1;\t/* GenParamCopy0107 */\n".format(
                                indent, nest, b_size, o, name, o2))
                        size_str = "length__{}".format(nest)
                    else:
                        if dir == "INOUT":
                            if isinstance(string, Expression):
                                len_ = string.to_str(name_list, o, o2)
                                size_str = "{}".format(len_)
                            else:
                                raise Exception("unsuscripted string used for inout parameter {}".format(name))
                        else:
                            size_str = "length__{}".format(nest)
                    self.print_param0("length__{}".format(nest), loop_counter_type, file, nest + 1, dir,
                                      None, None, b_marshal, b_get)

                if b_get and dir in ("IN", "INOUT", "SEND", "RECEIVE") and alloc_cp:
                    file.print("""\
{indent} /* (GenParamCopy0108) */
{indent}	if((ercd_={alloc_cp}(sizeof({tstr}{tpost})*({size_str}),(void **)&{o}{name}{o2}{extra}))!=E_OK)\t/* GenParamCopy 8 */
{indent}		goto error_reset;
""".format(
                        indent=indent, alloc_cp=alloc_cp,
                        tstr=type.get_type().get_type_str(), tpost=type.get_type().get_type_str_post(),
                        size_str=size_str, o=o, name=name, o2=o2, extra=alloc_cp_extra or ""))
                    if (dir == "SEND" or dir == "RECEIVE") and type.get_type().has_pointer():
                        file.print("""\
{indent} /* (GenParamCopy0109) */
{indent}	memset( (void *){o}{name}{o2}{extra}, 0, sizeof({tstr}{tpost})*({size_str}) );   /* GenParamCopy Alloc2 */
""".format(
                            indent=indent, o=o, name=name, o2=o2, extra=alloc_cp_extra or "",
                            tstr=type.get_type().get_type_str(), tpost=type.get_type().get_type_str_post(),
                            size_str=size_str))

                file.print("{}\tfor( i__{} = 0; i__{} < length__{}; i__{}++ ){{\t/* GenParamCopy 9 */\n".format(
                    indent, nest, nest, nest, nest))
                self.print_param0(name, type.get_type(), file, nest + 2, dir, outer,
                                  "{}[i__{}]".format(o2, nest), b_marshal, b_get, alloc_cp, alloc_cp_extra)
                file.print("{}\t}}\n".format(indent))
                file.print("{}}}\n".format(indent))

                nest = self.print_nullable_post(name, type, file, nest, dir, outer, outer2, b_marshal, b_get)
                indent = "\t" * nest
            else:
                nest = self.print_nullable_pre(name, type, file, nest, dir, outer, outer2, b_marshal, b_get)
                indent = "\t" * nest

                if b_get and dir in ("IN", "INOUT", "SEND", "RECEIVE") and alloc_cp:
                    file.print("""\
{indent} /* (GenParamCopy0110) */
{indent}if((ercd_={alloc_cp}(sizeof({tstr}{tpost}),(void **)&{o}{name}{o2}{extra}))!=E_OK)\t/* GenParamCopy 10 */
{indent}	 goto error_reset;
""".format(
                        indent=indent, alloc_cp=alloc_cp,
                        tstr=type.get_type().get_type_str(), tpost=type.get_type().get_type_str_post(),
                        o=o, name=name, o2=o2, extra=alloc_cp_extra or ""))
                    if (dir == "SEND" or dir == "RECEIVE") and type.get_type().has_pointer():
                        file.print("""\
{indent} /* (GenParamCopy0111) */
{indent}memset( (void *){o}{name}{o2}{extra}, 0, sizeof({tstr}{tpost}) );   /* GenParamCopy Alloc3 */
""".format(
                            indent=indent, o=o, name=name, o2=o2, extra=alloc_cp_extra or "",
                            tstr=type.get_type().get_type_str(), tpost=type.get_type().get_type_str_post()))

                self.print_param0(name, type.get_type(), file, nest, dir,
                                  "(*{}".format(outer or ""), "{})".format(outer2 or ""),
                                  b_marshal, b_get, alloc_cp, alloc_cp_extra)
                nest = self.print_nullable_post(name, type, file, nest, dir, outer, outer2, b_marshal, b_get)
                indent = "\t" * nest

        elif isinstance(type, StructType):
            members_decl = type.get_members_decl()
            o = outer or ""
            o2 = outer2 or ""
            for m in members_decl.get_items():
                if m.is_referenced():
                    self.print_param0(m.get_name(), m.get_type(), file, nest, dir,
                                      "{}{}{}.".format(o, name, o2), None,
                                      b_marshal, b_get, alloc_cp, alloc_cp_extra, members_decl)
            for m in members_decl.get_items():
                if not m.is_referenced():
                    self.print_param0(m.get_name(), m.get_type(), file, nest, dir,
                                      "{}{}{}.".format(o, name, o2), None,
                                      b_marshal, b_get, alloc_cp, alloc_cp_extra, members_decl)

        elif isinstance(type, VoidType):
            pass
        elif isinstance(type, EnumType):
            pass  # mikan EnumType
        elif isinstance(type, FuncType):
            pass  # mikan FuncType
        elif isinstance(type, ArrayType):
            subsc = type.get_subscript()
            if subsc is None:
                raise Exception("Unsubscripted Array Not Supported")
            else:
                size_str = subsc.to_str(name_list, outer, outer2)
                loop_counter_type = IntType(32)
                file.print("{indent}{{  /* (GenParamCopy0112) */\n".format(indent=indent))
                file.print("{}\t{}  i__{}, length__{} = {};\n".format(
                    indent, loop_counter_type.get_type_str(), nest, nest, size_str))
                file.print("{}\tfor( i__{} = 0; i__{} < length__{}; i__{}++ ){{\n".format(
                    indent, nest, nest, nest, nest))
                o2s = outer2 or ""
                self.print_param0(name, type.get_type(), file, nest + 2, dir, outer,
                                  "{}[i__{}]".format(o2s, nest),
                                  b_marshal, b_get, alloc_cp, alloc_cp_extra)
                file.print("{}\t}}\n".format(indent))
                file.print("{}}}\n".format(indent))

    #=== nullable (pre)
    def print_nullable_pre(self, name, type, file, nest, dir, outer, outer2, b_marshal, b_get):
        if type.is_nullable():
            indent = "\t" * nest
            o = outer or ""
            o2 = outer2 or ""
            if dir == "OUT":
                if b_get:
                    file.print("{}if( {}{}{} ){{\t/* (GenParamCopy0201) Null */\n".format(
                        indent, o, name, o2))
                else:
                    file.print("{}if( ! b_{}_null_ ){{\t/* (GenParamCopy0202) Null */\n".format(
                        indent, name))
                nest += 1
            else:
                if b_get:
                    file.print("{indent}{{\n".format(indent=indent))
                    if not (dir == "INOUT" and b_marshal is True):
                        file.print("""\
{indent} /* (GenParamCopy0203) */
{indent}	int8_t  b_null_;
{indent}	if((ercd_=cTDR_getInt8( &b_null_ )) != E_OK )\t/* GenParamCopy Null 20 */
{indent}		 goto error_reset;
{indent}	if( ! b_null_ ){{
""".format(indent=indent))
                    else:
                        file.print("""\
{indent} /* (GenParamCopy0204) */
{indent}	int8_t  b_null_ = ({o}{name}{o2} == NULL);\t/* GenParamCopy Null 21 */
{indent}	if( ! b_null_ ){{
""".format(indent=indent, o=o, name=name, o2=o2))
                else:
                    file.print("{indent}{{\n".format(indent=indent))
                    file.print("{}\tint8_t  b_null_ = (int8_t)({}{}{} == NULL);\t/* GenParamCopy Null 31 */\n".format(
                        indent, o, name, o2))
                    if not (dir == "INOUT" and b_marshal is False):
                        file.print("""\
{indent} /* (GenParamCopy0205) */
{indent}	if((ercd_=cTDR_putInt8( b_null_ )) != E_OK )\t/* GenParamCopy Null 32 */
{indent}		 goto error_reset;
""".format(indent=indent))
                    file.print("{indent}\tif( ! b_null_ ){{\t/* GenParamCopy Null 33 */\n".format(indent=indent))
                nest += 2
        return nest

    #== nullable (post)
    def print_nullable_post(self, name, type, file, nest, dir, outer, outer2, b_marshal, b_get):
        if type.is_nullable():
            o = outer or ""
            o2 = outer2 or ""
            if dir == "OUT":
                nest -= 1
                indent = "\t" * nest
                file.print("{}}}  /* ! b_{}_null_   (GenParamCopy0301) Null */\n".format(indent, name))
            else:
                nest -= 2
                indent = "\t" * nest
                if b_get:
                    if not (dir == "INOUT" and b_marshal is True):
                        file.print("""\

{indent}	}} else {{ /* null  (GenParamCopy0302) Null */
{indent}		{o}{name}{o2} = NULL;
{indent}	}}  /* ! b_null_ */
""".format(indent=indent, o=o, name=name, o2=o2))
                    else:
                        file.print("{indent}\t}}  /* ! b_null_  (GenParamCopy0303) Null */\n".format(indent=indent))
                else:
                    file.print("{indent}\t}}\t/* (GenParamCopy0304) Null */\n".format(indent=indent))
                file.print("{indent}}}\t/* (GenParamCopy0305) Null */\n".format(indent=indent))
        return nest
