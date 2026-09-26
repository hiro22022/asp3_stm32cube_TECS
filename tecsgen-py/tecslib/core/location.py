# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/location.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

import tecsgen

from tecslib.rubylib.reopen import reopen

TECSGEN = tecsgen.TECSGEN


#==  Cell_location
# tecscde の位置情報
class Cell_location:

    #=== Cell_location#initialize
    #cell_nspath::NamespacePath
    #x,y,w,h::Expression
    #port_location_list::[ [Symbol(ep_or_cp_name), Symbol(edge_name), Expression(offset)], ... ]
    def __init__(self, cell_nspath, x, y, w, h, port_location_list):
        self.cell_nspath = cell_nspath
        self.x = x.eval_const(None)
        self.y = y.eval_const(None)
        self.w = w.eval_const(None)
        self.h = h.eval_const(None)
        self.port_location_list = port_location_list

        TECSGEN.new_cell_location(self)

    def get_location(self):
        return [self.cell_nspath, self.x, self.y, self.w, self.h, self.port_location_list]


#==  Join_location
# tecscde の位置情報
class Join_location:

    #=== Join_location#initialize
    #cp_cell_nspath::NamespacePath
    #cp_name::Symbol
    #ep_cell_nspath::NamespacePath
    #ep_name::Symbol
    #bar_list::[[Symbol (VBar or HBar), Expression(position mm)], ....]
    def __init__(self, cp_cell_nspath, cp_name, ep_cell_path, ep_name, bar_list):
        self.cp_cell_nspath = cp_cell_nspath
        self.cp_name = cp_name
        self.ep_cell_path = ep_cell_path
        self.ep_name = ep_name
        self.bar_list = bar_list

        TECSGEN.new_join_location(self)

    def get_location(self):
        return [self.cp_cell_nspath, self.cp_name, self.ep_cell_path, self.ep_name, self.bar_list]


@reopen(TECSGEN)
class _:

    # Ruby 版の TECSGEN::Cell_location, TECSGEN::Join_location
    Cell_location = Cell_location
    Join_location = Join_location

    #------ manupulate location information --------#
    @classmethod
    def new_cell_location(cls, cell_location):
        cls._current_tecsgen.new_cell_location_inst(cell_location)

    def new_cell_location_inst(self, cell_location):
        self.cell_location_list.append(cell_location)

    def get_cell_location_list(self):
        return self.cell_location_list

    @classmethod
    def new_join_location(cls, join_location):
        cls._current_tecsgen.new_join_location_inst(join_location)

    def new_join_location_inst(self, join_location):
        self.join_location_list.append(join_location)

    def get_join_location_list(self):
        return self.join_location_list
