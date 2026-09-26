# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   このファイルは tecsgen (Ruby 版) の tecslib/plugin/TECSInfoCompoPlugin.rb を
#   Python へ移植したものである．
#

from tecslib.core import globals as G
from tecslib.core.componentobj.import_ import Import
from tecslib.core.componentobj.join import Join
from tecslib.core.componentobj.namespacepath import NamespacePath
from tecslib.core.expression import Expression
from tecslib.core.plugin import CFile
from tecslib.plugin.CompositePlugin import CompositePlugin
from tecslib.rubylib.symbol import Sym


class TECSInfoCompoPlugin(CompositePlugin):

    cell_list = []

    def __init__(self, celltype, option):
        super().__init__(celltype, option)
        if G.unopt_entry is False:
            self.cdl_info("TIF0001 forcely set --unoptimize-entry by TECSInfoPlugin (by importing TECSInfo.cdl)")
            G.unopt_entry = True

    def new_cell(self, cell):
        TECSInfoCompoPlugin.cell_list.append(cell)

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

        if cell.get_join_list().get_item(Sym("cTECSInfo")) is None:
            nsp = NamespacePath(Sym("rTECSInfo"), False)
            nsp.append_bang(Sym("TECSInfoSub"))
            rhs = Expression.create_cell_join_expression(nsp, None, Sym("eTECSInfo"))
            join = Join(Sym("cTECSInfo"), None, rhs)
            cell.new_join_inst(join)
