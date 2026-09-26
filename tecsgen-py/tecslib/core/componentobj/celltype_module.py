# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/componentobj/celltypeModule.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

from tecslib.core import globals as G
from tecslib.core.toplevel import print_exception


class CelltypePluginModule:
    #=== Celltype# セルタイププラグイン (generate 指定子)
    def celltype_plugin(self):
        plugin_name = self._generate[0]
        option = self._generate[1]
        plugin_object = self.apply_plugin(plugin_name, option)
        # Ruby の Array#[]= は長さを超えて代入できる
        if len(self._generate) <= 2:
            self._generate.append(plugin_object)
        else:
            self._generate[2] = plugin_object

    #=== Celltype# セルタイププラグインをこのセルタイプに適用
    def apply_plugin(self, plugin_name, option):

        # plClass = load_plugin( plugin_name, CelltypePlugin )
        from tecslib.core.componentobj.celltype import Celltype
        from tecslib.core.componentobj.compositecelltype import CompositeCelltype
        from tecslib.core.plugin_module import _import_plugin_class

        if isinstance(self, Celltype):
            plugin_class = _import_plugin_class("CelltypePlugin")
        elif isinstance(self, CompositeCelltype):
            plugin_class = _import_plugin_class("CompositePlugin")
        else:
            raise Exception("unknown class {}".format(self.__class__.__name__))

        plClass = self.load_plugin(plugin_name, plugin_class)
        if plClass is None:
            return
        if G.verbose:
            print("new celltype plugin: plugin_object = {}.new( {}, {} )\n".format(
                plClass.__name__, self.name, option), end="")

        plugin_object = None
        try:
            plugin_object = plClass(self, option)
            self.generate_list.append([plugin_name, option, plugin_object])
            plugin_object.set_locale(self.locale)
            self.generate_and_parse(plugin_object)
        except Exception as evar:
            self.cdl_error("S1023 $1: fail to new", plugin_name)
            print_exception(evar)

        # 既に存在するセルに new_cell を適用
        for cell in self.cell_list:
            self.apply_plugin_cell(plugin_object, cell)

        return plugin_object

    def apply_plugin_cell(self, plugin, cell):
        try:
            plugin.new_cell(cell)
        except Exception as evar:
            self.cdl_error("S1037 $1: celltype plugin fail to new_cell", plugin.__class__.__name__)
            print_exception(evar)

    def celltype_plugin_new_cell(self, cell):
        for generate in self.generate_list:
            celltype_plugin = generate[2]
            try:
                celltype_plugin.new_cell(cell)
            except Exception as evar:
                self.cdl_error("S1037 $1: celltype plugin fail to new_cell", celltype_plugin.__class__.__name__)
                print_exception(evar)
