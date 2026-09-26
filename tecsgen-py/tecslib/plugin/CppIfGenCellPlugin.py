# -*- coding: utf-8 -*-
#
#  CppIfGenCellPlugin.rb の Python 移植

from tecslib.plugin.CellPlugin import CellPlugin


class CppIfGenCellPlugin(CellPlugin):

    def gen_cdl_file(self, file):
        file.print("""/* apply CppIfGenCelltypePlugin to celltype '{}' (celltype of cell '{}') */
generate( CppIfGenCelltypePlugin, {}, "" ); 

""".format(
            self.cell.get_celltype().get_name(),
            self.cell.get_name(),
            self.cell.get_celltype().get_namespace_path().get_path_str(),
        ))

    @classmethod
    def gen_post_code(cls, file):
        pass
