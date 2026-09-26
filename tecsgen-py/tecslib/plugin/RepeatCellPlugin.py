# -*- coding: utf-8 -*-
#
#  RepeatCellPlugin.rb の Python 移植

import re

from tecslib.core import globals as G
from tecslib.core.componentobj.namespacepath import NamespacePath
from tecslib.core.expression import Expression
from tecslib.plugin.CellPlugin import CellPlugin
from tecslib.rubylib.symbol import Sym


def _set_count(obj, rhs):
    obj.set_count(rhs)


class RepeatCellPlugin(CellPlugin):

    plugin_list = []
    RepeatCellPluginArgProc = {
        "count": _set_count,
    }

    def __init__(self, cell, option):
        super().__init__(cell, option)
        RepeatCellPlugin.plugin_list.append(self)
        print("RepeatCellPlugin: {}".format(self.cell.get_name()))
        self.count = 0
        self.plugin_arg_check_proc_tab = RepeatCellPlugin.RepeatCellPluginArgProc
        self.parse_plugin_arg()

    def gen_cdl_file(self, file):
        if G.verbose:
            print("{}: repeat {} times".format(self.__class__.__name__, self.cell.get_name()))
        nest = self.cell.get_region().gen_region_str_pre(file)
        indent_str = "  " * nest
        m = re.search(r".*[^0-9]([0-9]+)\Z", str(self.cell.get_name()))
        if not m:
            self.cdl_error("{}: {}'s name ends without '0-9'".format(self.__class__.__name__, self.cell.get_name()))
            return
        tail_zero = m.group(1)
        bname = re.sub(r"[0-9]+\Z", "", str(self.cell.get_name()))
        base_count = int(tail_zero)
        count = 1
        num = self.count
        file.print("/*  {} times repeat of '{}' */\n".format(num, self.cell.get_name()))
        while count < num:
            count_str = str(count + base_count)
            if len(tail_zero) > len(count_str):
                leading_zero = "0" * (len(tail_zero) - len(count_str))
            else:
                leading_zero = ""
            cname = bname + leading_zero + count_str
            file.print("{}cell {} {}{{\n".format(indent_str, self.cell.get_celltype().get_name(), cname))
            for j in self.cell.get_join_list().get_items():
                res = j.get_rhs().analyze_cell_join_expression()
                if res:
                    nsp, subscript, port_name = res[0], res[1], res[2]
                else:
                    nsp = j.get_rhs().analyze_single_identifier()
                    if nsp:
                        subscript, port_name = None, None
                    else:
                        file.print("{}  {} = {};\n".format(indent_str, j.get_name(), j.get_rhs()))
                        continue
                rm = re.match(r"(.*[^0-9])([0-9]+)\Z", str(nsp.get_name()))
                if rm:
                    rhs_tail_num = rm.group(2)
                    rhs_name_count = count + int(rhs_tail_num)
                    if len(rhs_tail_num) > len(str(rhs_name_count)):
                        lz = "0" * (len(rhs_tail_num) - len(str(rhs_name_count)))
                    else:
                        lz = ""
                    rhs_cname = rm.group(1) + lz + str(rhs_name_count)
                    nsp = nsp.change_name_clone(Sym(rhs_cname))
                if port_name:
                    if subscript is not None:
                        file.print("{}  {} = {}.{}[{}];\n".format(
                            indent_str, j.get_name(), nsp.get_path_str(), port_name, count + subscript))
                    else:
                        file.print("{}  {} = {}.{};\n".format(
                            indent_str, j.get_name(), nsp.get_path_str(), port_name))
                else:
                    file.print("{}  {} = {};\n".format(indent_str, j.get_name(), nsp.get_path_str()))
            file.print("{}}};\n\n".format(indent_str))
            count += 1
        self.cell.get_region().gen_region_str_post(file)

    def set_count(self, rhs):
        s = str(rhs)
        if re.match(r"\A\d+\Z", s):
            self.count = int(s)
        else:
            nsp = NamespacePath(Sym(s), True)
            expr = Expression.create_single_identifier(nsp, None)
            res = expr.eval_const(None)
            if res is None:
                self.cdl_error("count value ($1): not single identifier or integer number", s)
                self.count = 0
            else:
                self.count = res
