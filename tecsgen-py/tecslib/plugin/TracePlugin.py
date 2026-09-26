# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2014 by TOPPERS Project
#
#   このファイルは tecsgen (Ruby 版) の tecslib/plugin/TracePlugin.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．
#
#   $Id: TracePlugin.rb 2952 2018-05-07 10:19:07Z okuma-top $
#

from tecslib.rubylib.symbol import Sym
from tecslib.core import globals as G
from tecslib.core.plugin import CFile

from tecslib.plugin.ThroughPlugin import ThroughPlugin


# プラグイン引数名と処理関数 (Ruby の Proc を Python の関数で代替)

def _trace_set_maxArrayDisplay(obj, rhs):
    obj.set_maxArrayDisplay(rhs)


def _trace_set_cellEntry(obj, rhs):
    obj.set_cellEntry(rhs)


def _trace_set_probeName(obj, rhs):
    obj.set_probeName(rhs)


def _trace_set_displayTime(obj, rhs):
    obj.set_displayTime(rhs)


def _trace_set_kernelCelltype(obj, rhs):
    obj.set_kernelCelltype(rhs)


def _trace_set_syslogCelltype(obj, rhs):
    obj.set_syslogCelltype(rhs)


TracePluginArgProc = {
    "maxArrayDisplay":  _trace_set_maxArrayDisplay,
    "cellEntry":        _trace_set_cellEntry,
    "probeName":        _trace_set_probeName,
    "displayTime":      _trace_set_displayTime,
    "kernelCelltype":   _trace_set_kernelCelltype,
    "syslogCelltype":   _trace_set_syslogCelltype,
}


class TracePlugin(ThroughPlugin):
    #@cellEntry_list::[ "Cell.eEntry", "Cell2.eEntry2", ... ]
    #@b_generate::bool  : true : TracePlugin を生成する必要がある

    #=== TracePlugin の initialize
    #  説明は ThroughPlugin (plugin.rb) を参照
    def __init__(self, cell_name, plugin_arg, next_cell, next_cell_port_name,
                 next_cell_port_subscript, signature, celltype, caller_cell):

        self.maxArrayDisplay = 16
        self.cellEntry_list  = []
        self.probeName       = ""
        self.b_generate      = False
        self.b_displayTime   = False
        self.kernelCelltype  = Sym("tKernel")
        self.syslogCelltype  = Sym("tSysLog")

        super().__init__(cell_name, plugin_arg, next_cell, next_cell_port_name,
                         next_cell_port_subscript, signature, celltype, caller_cell)
        self.plugin_arg_check_proc_tab = TracePluginArgProc
        self.parse_plugin_arg()

        if len(self.cellEntry_list) > 0:
            for ce in self.cellEntry_list:
                if Sym("{}.{}".format(next_cell.get_name(), next_cell_port_name)) == Sym(str(ce)):
                    self.b_generate = True
        else:
            self.b_generate = True

        if self.b_generate == False:
            # 元々呼び出すセルに結合するものとする
            self.entry_port_name = next_cell_port_name
            self.cell_name = next_cell.get_name()

    #===  宣言コードの生成
    #      typedef, signature, celltype など（cell 以外）のコードを生成
    #          重複して生成してはならない（すでに生成されている場合は出力しないこと）
    #file::        FILE       生成するファイル
    def gen_plugin_decl_code(self, file):

        # このセルタイプ（同じシグニチャ）は既に生成されているか？
        if ThroughPlugin.generated_celltype.get(self.ct_name) is None:
            ThroughPlugin.generated_celltype[self.ct_name] = [self]
        else:
            ThroughPlugin.generated_celltype[self.ct_name].append(self)
            return

        file2 = CFile.open("{}/{}.cdl".format(G.gen, self.ct_name), "w")

        send_receive = []
        if self.signature is not None:
            def _each_param(fd, param):
                dir_ = param.get_direction()
                if dir_ in ("SEND", "RECEIVE"):
                    send_receive.append([dir_, fd, param])
            self.signature.each_param(_each_param)

        file2.print("celltype {} {{\n".format(self.ct_name))

        if len(send_receive) > 0:
            file2.print("  [ allocator(\n")
            delim = ""
            for a in send_receive:
                file2.print("{}\t{}.{}<=\t{}.{}.{}".format(
                    delim,
                    a[1].get_name(), a[2].get_name(),
                    self.call_port_name, a[1].get_name(), a[2].get_name()
                ))
                delim = ",\n"
            file2.print("\n  )]\n")

        file2.print("""\
  entry {sig_path} {entry_port_name};
  call  {sig_path} {call_port_name};
  attr{{
    char_t   *probeName_str      = "";
    char_t   *from_str           = "";
  }};
  require  {syslogCelltype}.eSysLog;
  require  {kernelCelltype}.eKernel;
}};
""".format(
            sig_path=self.signature.get_namespace_path(),
            entry_port_name=self.entry_port_name,
            call_port_name=self.call_port_name,
            syslogCelltype=self.syslogCelltype,
            kernelCelltype=self.kernelCelltype,
        ))
        #    char_t   *cell_port_name_str = "";

        file2.close()

        file.print("import( \"{}/{}.cdl\" );\n".format(G.gen, self.ct_name))

    def gen_through_cell_code(self, file):

        self.gen_plugin_decl_code(file)

        if self.b_generate != False:
            nest = self.region.gen_region_str_pre(file)
            indent_str = "  " * nest
            if self.next_cell_port_subscript is not None:
                subscript = "[" + str(self.next_cell_port_subscript) + "]"
            else:
                subscript = ""

            if self.probeName:
                probeName_str = "{}  probeName_str = \"{}: \";\n".format(
                    indent_str, self.probeName)
            else:
                probeName_str = ""
            if self.caller_cell:
                caller_cell_str = "{}  from_str = \"{}\";\n".format(
                    indent_str, self.caller_cell.get_name())
            else:
                caller_cell_str = ""

            file.print("""\
{indent_str}cell {ct_name} {cell_name} {{
{indent_str}  {call_port_name} = {next_cell_path}.{next_cell_port_name}{subscript};
{probeName_str}{caller_cell_str}{indent_str}}};
""".format(
                indent_str=indent_str,
                ct_name=self.ct_name,
                cell_name=self.cell_name,
                call_port_name=self.call_port_name,
                next_cell_path=self.next_cell.get_namespace_path().get_path_str(),
                next_cell_port_name=self.next_cell_port_name,
                subscript=subscript,
                probeName_str=probeName_str,
                caller_cell_str=caller_cell_str,
            ))
            #  cell_port_name_str = "#{@next_cell.get_name}.#{@next_cell_port_name}";
            self.region.gen_region_str_post(file)

    def gen_ep_func_body(self, file, b_singleton, ct_name, global_ct_name, sig_name,
                         ep_name, func_name, func_global_name, func_type, params):

        if not func_type.get_type().is_void():
            file.print("\t{}\tretval;\n".format(func_type.get_type_str()))

        file.print("\tSYSUTM\tutime;\n")

        if not b_singleton:

            file.print("""\
\t{ct_name}_CB *p_cellcb;
\tif( VALID_IDX( idx ) ){{
\t\tp_cellcb = {global_ct_name}_GET_CELLCB(idx);
\t}}else{{
\t\t/* put code here for error */
\t}}

""".format(ct_name=ct_name, global_ct_name=global_ct_name))

        #    p "celltype_name, sig_name, func_name, func_global_name"
        #    p "#{ct_name}, #{sig_name}, #{func_name}, #{func_global_name}"

        file.print("""\
\tgetMicroTime( &utime );
\tsyslog( LOG_INFO, "Enter: %sTime=%d: {next_cell_name}.{next_cell_port_name}.{func_name} calledFrom: %s", ATTR_probeName_str, utime, ATTR_from_str );
""".format(
            next_cell_name=self.next_cell.get_name(),
            next_cell_port_name=self.next_cell_port_name,
            func_name=func_name,
        ))

        self.print_params(params, file, 0, "IN")

        delim = ""
        if not func_type.get_type().is_void():
            file.print("\tretval = ")
        else:
            file.print("\t")

        file.print("{}_{}(".format(self.call_port_name, func_name))

        for param in params:
            file.printf("{} {}".format(delim, param.get_name()))
            delim = ","
        file.print(" );\n")

        if self.next_cell_port_subscript is not None:
            subscript = "[" + str(self.next_cell_port_subscript) + "]"
        else:
            subscript = ""

        file.print("""\
\tgetMicroTime( &utime );
\tsyslog( LOG_INFO, "Leave: %sTime=%d: {next_cell_name}.{next_cell_port_name}{subscript}.{func_name}", ATTR_probeName_str, utime );
""".format(
            next_cell_name=self.next_cell.get_name(),
            next_cell_port_name=self.next_cell_port_name,
            subscript=subscript,
            func_name=func_name,
        ))

        self.print_params(params, file, 0, "OUT")

        if not func_type.get_type().is_void():
            self.print_param("retval", func_type.get_type(), file, 0, "RETURN",
                             func_type.get_type().get_type_str(), None, None)
            file.print("\treturn retval;\n")

    def print_params(self, params, file, nest, direction):
        for param in params:
            dir_ = param.get_direction()
            if direction == "IN":
                if dir_ in ("IN", "INOUT", "SEND"):
                    self.print_param(param.get_name(), param.get_type(), file, nest, dir_,
                                     param.get_type().get_type_str(), None, None)
            else:
                if dir_ in ("OUT", "INOUT"):
                    self.print_param(param.get_name(), param.get_type(), file, nest, dir_,
                                     param.get_type().get_type_str(), None, None)
                elif dir_ == "RECEIVE":
                    outer = "*"
                    outer2 = None
                    self.print_param(param.get_name(), param.get_type().get_referto(), file, nest, dir_,
                                     param.get_type().get_referto().get_type_str(), outer, outer2)

    def print_param(self, name, type, file, nest, direction, type_str, outer, outer2,
                    name_list=None):
        from tecslib.core.types import (DefinedType, VoidType, BoolType, IntType,
                                         FloatType, EnumType, StructType, FuncType,
                                         ArrayType, PtrType)
        indent = "    " * (nest + 1)

        # outer / outer2 の None → 空文字列変換ヘルパー
        def _s(x):
            return "" if x is None else str(x)

        if isinstance(type, DefinedType):
            self.print_param(name, type.get_type(), file, nest, direction, type_str,
                             outer, outer2, name_list)
        elif isinstance(type, VoidType):
            pass
        elif isinstance(type, BoolType):
            file.print("{indent}syslog( LOG_INFO, \"{indent}[{direction}]{type_str} {outer}{name}{outer2} = %d;\", {outer}{name}{outer2} );\n".format(
                indent=indent, direction=direction, type_str=type_str,
                outer=_s(outer), name=name, outer2=_s(outer2)))
        elif isinstance(type, IntType):
            file.print("""\
{indent}if( sizeof({outer}{name}{outer2}) > sizeof(int_t) )
{indent}\tsyslog( LOG_INFO, "{indent}[{direction}]{type_str} {outer}{name}{outer2} = %ld;", (long){outer}{name}{outer2} );
{indent}else
{indent}\tsyslog( LOG_INFO, "{indent}[{direction}]{type_str} {outer}{name}{outer2} = %d;", {outer}{name}{outer2} );
""".format(
                indent=indent, direction=direction, type_str=type_str,
                outer=_s(outer), name=name, outer2=_s(outer2)))
            #      file.print( "#{indent}syslog( LOG_INFO, \"#{indent}[#{direction}]#{type_str} #{outer}#{name}#{outer2} = %ld;\", (long)#{outer}#{name}#{outer2} );\n" )
        elif isinstance(type, FloatType):
            file.print("{indent}syslog( LOG_INFO, \"{indent}[{direction}]{type_str} {outer}{name}{outer2} = %g;\", (double){outer}{name}{outer2} );\n".format(
                indent=indent, direction=direction, type_str=type_str,
                outer=_s(outer), name=name, outer2=_s(outer2)))
        elif isinstance(type, EnumType):  # mikan EnumType
            pass
        elif isinstance(type, StructType):
            members_decl = type.get_members_decl()
            if outer or outer2:
                outer = "({}{}{}).".format(_s(outer), name, _s(outer2))
            else:
                outer = "{}.".format(name)
            for m in members_decl.get_items():
                self.print_param(m.get_name(), m.get_type(), file, nest, direction,
                                 m.get_type().get_type_str(), outer, None, members_decl)
        elif isinstance(type, FuncType):  # mikan FuncType
            pass
        elif isinstance(type, ArrayType):  # mikan ArrayType
            pass
        elif isinstance(type, PtrType):

            se = type.get_size()
            ce = type.get_count()
            max_loop = self.maxArrayDisplay
            loop_count = None
            size = None

            if se is not None:
                loop_count = "((({}>{}) ? {} : ({})))".format(
                    se.to_str(name_list, outer, outer2), max_loop,
                    max_loop, se.to_str(name_list, outer, outer2))
                file.print("{indent}syslog( LOG_INFO, \"{indent}size_is({se_str})=%d\", {se_str} );\n".format(
                    indent=indent, se_str=se.to_str(name_list, outer, outer2)))
                size = se.to_str(name_list, outer, outer2)
            elif ce is not None:
                loop_count = "((({}>{}) ? {} : ({}) ))".format(
                    ce.to_str(name_list, outer, outer2), max_loop,
                    max_loop, ce.to_str(name_list, outer, outer2))
                file.print("{indent}syslog( LOG_INFO, \"{indent}count_is({ce_str})=%d\", {ce_str} );\n".format(
                    indent=indent, ce_str=ce.to_str(name_list, outer, outer2)))
                size = ce.to_str(name_list, outer, outer2)

            # mikan PtrType: string

            referto = type.get_referto()
            type0 = type
            type = referto
            type_str = type.get_type_str()
            if isinstance(type, DefinedType):
                type = type.get_original_type()

            if type0.is_nullable():
                nest += 1
                indent0 = indent
                outer0 = outer
                outer20 = outer2
                indent += "    "
                file.print("{indent0}if( {outer}{name}{outer2} ){{\n".format(
                    indent0=indent0, outer=_s(outer), name=name, outer2=_s(outer2)))

            if loop_count is None:
                if isinstance(type, StructType):
                    members = type.get_members_decl()
                    if outer or outer2:
                        outer = "({}{}{})->".format(_s(outer), name, _s(outer2))
                    else:
                        outer = "{}->"  .format(name)
                    outer2 = None
                    for m in members.get_items():
                        self.print_param(m.get_name(), m.get_type(), file, nest, direction,
                                         m.get_type().get_type_str(), outer, outer2, members)
                elif isinstance(type, FuncType):  # mikan FuncType
                    pass
                elif isinstance(type, ArrayType):  # mikan ArrayType
                    pass
                elif isinstance(type, (BoolType, IntType, FloatType, EnumType, PtrType)):
                    outer = "*{}".format(_s(outer))
                    outer2 = "{}".format(_s(outer2))
                    self.print_param(name, type, file, nest, direction, type_str, outer, outer2)
            else:  # loop_count != nil
                if isinstance(type, (PtrType, StructType)):
                    num_per_loop = 1
                else:
                    num_per_loop = 4

                file.print("""\
{indent}{{
{indent}\tint i__{nest}, loop_count__ = {loop_count};
{indent}\tfor( i__{nest} = 0; i__{nest} < loop_count__; i__{nest}+={num_per_loop} ){{
""".format(indent=indent, nest=nest, loop_count=loop_count, num_per_loop=num_per_loop))

                if isinstance(type, StructType):
                    members = type.get_members_decl()
                    if outer or outer2:
                        outer = "({}{}{})[i__{}].".format(_s(outer), name, _s(outer2), nest)
                    else:
                        outer = "{}[i__{}].".format(name, nest)
                    for m in members.get_items():
                        self.print_param(m.get_name(), m.get_type(), file, nest + 1, direction,
                                         m.get_type().get_type_str(), outer, None, members)
                elif isinstance(type, FuncType):  # mikan FuncType
                    pass
                elif isinstance(type, ArrayType):  # mikan ArrayType
                    pass
                elif isinstance(type, (BoolType, FloatType)):
                    if outer or outer2:
                        outer = "({}"  .format(_s(outer))
                        outer2 = "{})".format(_s(outer2))

                    file.print("""\
{indent}\t\tsyslog( LOG_INFO, "{indent}[{direction}]{type_str} {name}[%d]: %d %d %d %d",
{indent}\t\t\t\ti__{nest}, {outer}{name}{outer2}[i__{nest}], {outer}{name}{outer2}[i__{nest}+1], {outer}{name}{outer2}[i__{nest}+2], {outer}{name}{outer2}[i__{nest}+3] );
""".format(
                        indent=indent, direction=direction, type_str=type_str, name=name,
                        nest=nest, outer=_s(outer), outer2=_s(outer2)))
                elif isinstance(type, IntType):
                    if outer or outer2:
                        outer = "({}"  .format(_s(outer))
                        outer2 = "{})".format(_s(outer2))

                    file.print("""\
{indent}\t\tif( sizeof({outer}{name}{outer2}) > sizeof(int_t) )
{indent}\t\t\tsyslog( LOG_INFO, "{indent}[{direction}]{type_str} {name}[%d]: %02x %02x %02x %02x",
{indent}\t\t\t\t\ti__{nest}, {outer}{name}{outer2}[i__{nest}], {outer}{name}{outer2}[i__{nest}+1], {outer}{name}{outer2}[i__{nest}+2], {outer}{name}{outer2}[i__{nest}+3] );
{indent}\t\telse
{indent}\t\t\tsyslog( LOG_INFO, "{indent}[{direction}]{type_str} {name}[%d]: %02lx %02lx %02lx %02lx",
{indent}\t\t\t\t\ti__{nest}, {outer}{name}{outer2}[i__{nest}], {outer}{name}{outer2}[i__{nest}+1], {outer}{name}{outer2}[i__{nest}+2], {outer}{name}{outer2}[i__{nest}+3] );
""".format(
                        indent=indent, direction=direction, type_str=type_str, name=name,
                        nest=nest, outer=_s(outer), outer2=_s(outer2)))

                elif isinstance(type, PtrType):
                    # type = type.get_referto
                    if outer or outer2:
                        outer = "({}"  .format(_s(outer))
                        outer2 = "{})[ i__{}]".format(_s(outer2), nest)
                    else:
                        outer = ""
                        outer2 = "[i__{}]".format(nest)
                    self.print_param(name, type, file, nest + 1, direction, type_str, outer, outer2)

                file.print("""\
{indent}\t}} /* for ( i__{nest} ) */
{indent}\tif( i__{nest} < {size} )
{indent}\t\tsyslog( LOG_INFO, "{indent}(%d elements are omitted)", {size} - i__{nest} );
{indent}\telse if( i__{nest} > {size} )
{indent}\t\tsyslog( LOG_INFO, "{indent}(last %d elements are void)", i__{nest} - {size} );
{indent}}}
""".format(indent=indent, nest=nest, size=size))
            # loop_count == nil

            if type0.is_nullable():
                file.print("""\
{indent0}}} else {{
{indent0}    syslog( LOG_INFO, "{indent0}[{direction}]{outer0}{name}{outer20} = NULL" );
{indent0}}}
""".format(
                    indent0=indent0, direction=direction,
                    outer0=_s(outer0), name=name, outer20=_s(outer20)))

    def set_maxArrayDisplay(self, rhs):
        self.maxArrayDisplay = rhs

    def set_cellEntry(self, rhs):
        ces = str(rhs).split(",")
        ces = [ce.strip() for ce in ces]
        for ce in ces:
            import re
            if re.match(r'^[A-Za-z_]\w*\.[A-Za-z_]\w*$', ce):
                # OK
                pass
            else:
                self.cdl_error("{}: TracePlugin arg not in \"symbol.symbol\" form".format(ce))
        self.cellEntry_list.extend(ces)

    def set_probeName(self, rhs):
        self.probeName = str(rhs)

    def set_displayTime(self, rhs):
        if str(rhs) == "true":
            self.b_diplayTime = True     # Ruby 版の typo をそのまま保持
        elif str(rhs) == "false":
            self.b_diplayTime = False    # Ruby 版の typo をそのまま保持
        else:
            self.cdl_error("displayTime : {} unsuitable: specify true or false".format(rhs))

    #=== プラグイン引数 tKernel のチェック
    def set_kernelCelltype(self, rhs):
        from tecslib.core.componentobj.namespacepath import NamespacePath
        from tecslib.core.componentobj.namespace import Namespace
        from tecslib.core.componentobj.celltype import Celltype
        from tecslib.core.componentobj.compositecelltype import CompositeCelltype
        self.kernelCelltype = Sym(str(rhs))
        nsp = NamespacePath.analyze(str(self.kernelCelltype))
        obj = Namespace.find(nsp)
        if not (type(obj) is Celltype) and not (type(obj) is CompositeCelltype):
            self.cdl_error("TracePlugin: kernelCelltype '{}' not celltype or not defined".format(rhs))

    #=== プラグイン引数 tSyslog のチェック
    def set_syslogCelltype(self, rhs):
        from tecslib.core.componentobj.namespacepath import NamespacePath
        from tecslib.core.componentobj.namespace import Namespace
        from tecslib.core.componentobj.celltype import Celltype
        from tecslib.core.componentobj.compositecelltype import CompositeCelltype
        self.syslogCelltype = Sym(str(rhs))
        nsp = NamespacePath.analyze(str(self.syslogCelltype))
        obj = Namespace.find(nsp)
        if not (type(obj) is Celltype) and not (type(obj) is CompositeCelltype):
            self.cdl_error("TracePlugin: syslogCelltype '{}' not celltype or not defined".format(rhs))
