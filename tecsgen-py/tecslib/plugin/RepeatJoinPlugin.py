# -*- coding: utf-8 -*-
#
#  RepeatJoinPlugin.rb の Python 移植

import re

from tecslib.core.componentobj.join import Join
from tecslib.core.componentobj.namespacepath import NamespacePath
from tecslib.core.expression import Expression
from tecslib.plugin.CellPlugin import CellPlugin
from tecslib.rubylib.symbol import Sym


def _set_count(obj, rhs):
    obj.set_count(rhs)


class RepeatJoinPlugin(CellPlugin):

    RepeatJoinPluginArgProc = {
        "count": _set_count,
    }

    def __init__(self, cell, option):
        super().__init__(cell, option)
        print("RepeatJoinPlugin: {}".format(self.cell.get_name()))
        self.plugin_arg_check_proc_tab = RepeatJoinPlugin.RepeatJoinPluginArgProc
        self.parse_plugin_arg()
        self._expand_joins()

    def _expand_joins(self):
        for j in self.cell.get_join_list().get_items():
            ret = j.get_rhs().analyze_cell_join_expression()
            if ret is None:
                continue
            rhs_nsp, rhs_subscript, rhs_port_name = ret
            if j.get_subscript() != 0:
                continue
            rhs_name = str(rhs_nsp.get_name())
            m = re.match(r"(.*[^0-9])([0-9]+)\Z", rhs_name)
            if m:
                b_rhs_name_count = True
                rhs_name_base = m.group(1)
                n_digits = len(m.group(2))
                rhs_count_base = int(m.group(2))
            else:
                b_rhs_name_count = False
                rhs_name_base = rhs_name
                n_digits = 0
                rhs_count_base = 0
            b_rhs_subscript_count = rhs_subscript is not None and rhs_subscript == 0
            count = 1
            while count < self.count:
                count_str = str(count + rhs_count_base)
                if b_rhs_subscript_count:
                    rhs_sub = count
                else:
                    rhs_sub = rhs_subscript
                if b_rhs_name_count:
                    leading_zero = "0" * max(0, n_digits - len(count_str))
                    rhs_name_real = rhs_name_base + leading_zero + count_str
                else:
                    rhs_name_real = rhs_name
                rhs_nsp2 = rhs_nsp.change_name_clone(Sym(rhs_name_real))
                rhs = Expression.create_cell_join_expression(rhs_nsp2, rhs_sub, rhs_port_name)
                j2 = Join(j.get_name(), count, rhs)
                self.cell.new_join_inst(j2)
                count += 1

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
