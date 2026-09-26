# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/componentobj/reversejoin.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

from tecslib.core.syntaxobj.node import BDNode


#== 逆結合
class ReverseJoin(BDNode):
    #@ep_name:: Symbol
    #@ep_subscript:: Expression or nil
    #@cell_nsp: NamespacePath
    #@cp_name:: Symbol
    #@cp_subscript:: Expression or nil
    def __init__(self, ep_name, ep_subscript, cell_nsp, cp_name, cp_subscript=None):
        super().__init__()
        self.ep_name = ep_name
        self.ep_subscript = ep_subscript
        self.cell_nsp = cell_nsp
        self.cp_name = cp_name
        self.cp_subscript = cp_subscript

    def get_name(self):
        return self.ep_name

    def get_rhs_cell_and_port(self):
        return [self.ep_subscript, self.cell_nsp, self.cp_name, self.cp_subscript]
