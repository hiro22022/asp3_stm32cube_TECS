# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/componentobj/compositecelltypejoin.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

from tecslib.core.syntaxobj.node import BDNode
from tecslib.core.toplevel import dbgPrint, dbgPrintf


# CLASS: CompositeCelltype 用の Join
# REM:   CompositeCelltype が export するもの
class CompositeCelltypeJoin(BDNode):
    # @export_name:: string     :  CompositeCelltype が export する名前（呼び口、受け口、属性）
    # @internal_cell_name:: string : CompositeCelltype 内部のセルの名前
    # @internal_cell_elem_name:: string : CompositeCelltype 内部のセルの呼び口、受け口、属性の名前
    # @cell : Cell : Cell::  internal cell  : CompositeCelltyep 内部のセル（in_compositeセル）
    # @port_decl:: Port | Decl
    # @b_pseudo: bool :

    def __init__(self, export_name, internal_cell_name,
                 internal_cell_elem_name, cell, port_decl):
        super().__init__()
        self.export_name = export_name
        self.internal_cell_name = internal_cell_name
        self.internal_cell_elem_name = internal_cell_elem_name
        self.cell = cell
        self.port_decl = port_decl

    #=== CompositeCelltypeJoin# CompositeCelltypeJoin の対象セルか？
    #cell::  Cell 対象かどうかチェックするセル
    #
    #     CompositeCelltypeJoin と cell の名前が一致するかチェックする
    #     port_decl が指定された場合は、現状使われていない
    def match(self, cell, port_decl=None):

        #debug
        if port_decl:
            dbgPrint("match?")
            dbgPrintf("  @cell:      %-20s      %08x\n", self.cell.get_name(), id(self.cell))
            dbgPrintf("  @port_decl: %-20s      %08x\n", self.port_decl.get_name(), id(self.port_decl))
            dbgPrintf("  cell:       %-20s      %08x\n", cell.get_name(), id(cell))
            dbgPrintf("  port_decl:  %-20s      %08x\n", port_decl.get_name(), id(port_decl))
            dbgPrint("  cell_name: {}={} cell_elem_name: {}={}\n".format(
                type(cell.get_name()), cell.get_name(),
                type(port_decl.get_name()), port_decl.get_name()))
            dbgPrint("  @cell_name: {}={} cell_elem_name: {}={}\n".format(
                type(self.cell.get_name()), self.cell.get_name(),
                type(self.port_decl.get_name()), self.port_decl.get_name()))

        #    if @cell.equal?( cell ) && ( port_decl == nil || @port_decl.equal?( port_decl ) ) then
        # なぜ port_decl が一致しなければならなかったか忘れた。
        # recursive_composite で名前の一致に変更   060917
        if (self.cell.get_name() == cell.get_name()
                and (port_decl is None or self.port_decl.get_name() == port_decl.get_name())):
            return True
        else:
            return False

    def check_dup_init(self):
        if self.get_port_type() != "CALL":
            return

        if self.cell.get_join_list().get_item(self.internal_cell_elem_name):
            self.cdl_error("S1131 '$1.$2' has duplicate initializer",
                           self.internal_cell_name, self.internal_cell_elem_name)

    def get_name(self):
        return self.export_name

    def get_cell_name(self):
        return self.internal_cell_name

    def get_cell(self):
        return self.cell

    def get_cell_elem_name(self):
        return self.internal_cell_elem_name

    # @port_decl が Port の場合のみ呼び出してよい
    def get_port_type(self):
        if self.port_decl:
            return self.port_decl.get_port_type()

    # @port_decl が Port の場合のみ呼び出してよい
    def get_port_decl(self):
        return self.port_decl

    #=== CompositeCelltypeJoin#get_allocator_instance
    def get_allocator_instance(self):
        from tecslib.core.componentobj.port import Port
        if type(self.port_decl) is Port:
            return self.port_decl.get_allocator_instance()
        elif self.port_decl:
            raise Exception("CompositeCelltypeJoin#get_allocator_instance: not port")
        else:
            return None

    # @port_decl が Port の場合のみ呼び出してよい
    def is_require(self):
        if self.port_decl:
            return self.port_decl.is_require()

    # @port_decl が Port の場合のみ呼び出してよい
    def is_allocator_port(self):
        if self.port_decl:
            return self.port_decl.is_allocator_port()

    # @port_decl が Port の場合のみ呼び出してよい
    def is_optional(self):
        if self.port_decl:
            return self.port_decl.is_optional()

    #=== CompositeCelltypeJoin# 右辺が Decl ならば初期化子（式）を返す
    # このメソッドは Cell の check_join から初期値チェックのために呼び出される
    #=== CompositeCelltypeJoin# get_initializer
    def get_initializer(self):
        from tecslib.core.syntaxobj.decl import Decl
        if type(self.port_decl) is Decl:
            return self.port_decl.get_initializer()

    def get_size_is(self):
        from tecslib.core.syntaxobj.decl import Decl
        if type(self.port_decl) is Decl:
            return self.port_decl.get_size_is()

    #=== CompositeCelltypeJoin# 配列サイズを得る
    #RETURN:: nil: not array, "[]": 大きさ指定なし, Integer: 大きさ指定あり
    def get_array_size(self):
        return self.port_decl.get_array_size()

    #=== CompositeCelltypeJoin# signature を得る
    # @port_decl が Port の時のみ呼び出してもよい
    def get_signature(self):
        return self.port_decl.get_signature()

    #=== CompositeCelltypeJoin# get_type
    def get_type(self):
        from tecslib.core.syntaxobj.decl import Decl
        if type(self.port_decl) is Decl:
            return self.port_decl.get_type()

    #=== CompositeCelltypeJoin# get_choice_list
    def get_choice_list(self):
        from tecslib.core.syntaxobj.decl import Decl
        if type(self.port_decl) is Decl:
            return self.port_decl.get_choice_list()

    def show_tree(self, indent):
        print("  " * indent, end="")
        print("CompositeCelltypeJoin: export_name: {} {}".format(self.export_name, self))
        print("  " * (indent + 1), end="")
        print("internal_cell_name: {}".format(self.internal_cell_name))
        print("  " * (indent + 1), end="")
        print("internal_cell_elem_name: {}".format(self.internal_cell_elem_name))
        if self.port_decl:
            self.port_decl.show_tree(indent + 1)
