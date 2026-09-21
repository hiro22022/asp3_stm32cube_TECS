# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2014 by TOPPERS Project TECS-WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/plugin/ATK1ResourcePlugin.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．
#
#   $Id: ATK1ResourcePlugin.rb 2955 2018-05-07 10:23:26Z okuma-top $
#

import re

from tecslib.core import globals as G
from tecslib.core.plugin import CFile
from tecslib.plugin.CelltypePlugin import CelltypePlugin
from tecslib.rubylib.rb import to_s
from tecslib.rubylib.symbol import Sym


def _strip_dq(s):
    return re.sub(r'^"(.*)"$', r"\1", to_s(s))


class ATK1ResourcePlugin(CelltypePlugin):

    def __init__(self, celltype, option):
        super().__init__(celltype, option)

    def new_cell(self, cell):
        pass

    def gen_factory(self, file):
        file2 = CFile.open("{}/RESOURCE_tecsgen.oil".format(G.gen), "w")
        file3 = CFile.open(
            "{}/{}_factory.{}".format(G.gen, to_s(self.celltype.get_name()), G.h_suffix),
            "w",
        )

        for cell in self.celltype.get_cell_list():
            if not cell.is_generate():
                continue

            if to_s(cell.get_name()) == "RES_SCHEDULER":
                cell.set_specified_id(1)
            else:
                file3.print("DeclareResource( {} );\n".format(to_s(cell.get_name())))
                file2.print("\tRESOURCE {} {{\n".format(to_s(cell.get_name())))

                join = cell.get_join_list().get_item(Sym("property"))
                if join:
                    str_ = _strip_dq(join.get_rhs())
                    if str_ == "LINKED":
                        file2.print("\t\tRESOURCEPROPERTY = {} {{\n".format(str_))
                        join2 = cell.get_join_list().get_item(Sym("linkedResource"))
                        str2 = _strip_dq(join2.get_rhs())
                        file2.print("\t\t\tLINKEDRESOURCE = {};\n".format(str2))
                        file2.print("\t\t};\n")
                    else:
                        file2.print("\t\tRESOURCEPROPERTY = {};\n".format(str_))

                file2.print("\t};\n")
                file2.print("\n")

        file2.close()
        file3.close()
