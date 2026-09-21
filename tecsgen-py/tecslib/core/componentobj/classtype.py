# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/componentobj/classtype.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

from tecslib.core.plugin_module import PluginModule
from tecslib.core.syntaxobj.node import Node
from tecslib.core.toplevel import dbgPrint
from tecslib.rubylib.symbol import Sym


#== ClassType
#
# region の class を記憶するクラス
class ClassType(Node, PluginModule):
    #@name::Symbol : クラスタイプの名前 ex) FMP, HRMP
    #@region::Region
    #@plugin_name::Symbol : ex) FMPPlugin
    #@option::String : クラス名 | :global (OutOfClass)
    #@plugin::ClassPlugin の子クラス
    #@node_root::Region : node_root となるリージョン

    # ドメインに属する region の Hash
    # class 指定が一度も行われない場合、このリストは空である
    # ルートリージョンは option = "OutOfClass" で登録される (class 指定が無ければ登録されない)
    class_regions = {}  # {:node_root => { :class_type => [ region, ... ] } }

    def __init__(self, region, name, option, node_root):
        super().__init__()
        dbgPrint("ClassType.new: region={} class_name={} option={} node_root={}\n".format(
            region.get_name(), name, option, node_root.get_name()))
        self.name = name
        self.plugin_name = Sym(str(name) + "Plugin")
        from tecslib.core.plugin_module import _import_plugin_class
        ClassPlugin = _import_plugin_class("ClassPlugin")
        self.pluginClass = self.load_plugin(self.plugin_name, ClassPlugin)
        self.region = region
        self.option = option
        self.node_root = node_root

        if ClassType.class_regions.get(node_root) is None:
            ClassType.class_regions[node_root] = {}

        if ClassType.class_regions[node_root].get(name):
            if region not in ClassType.class_regions[node_root][name]:
                ClassType.class_regions[node_root][name].append(region)
        else:
            ClassType.class_regions[node_root][name] = [region]

    def create_class_plugin(self):
        if not getattr(self, "plugin", None):
            dbgPrint("create_class_plugin region={} name={} option={}\n".format(
                self.region.get_name(), self.name, self.option))
            # pluginClass = Object.const_get @plugin_name  # not incompatible with MultiPlugin
            if self.pluginClass is None:
                return
            self.plugin = self.pluginClass(self.region, self.name, self.option)
            self.plugin.set_locale(self.locale)

    def add_through_plugin(self, join, from_region, to_region, through_type):
        # print( "CLASS: add_through_plugin: from=#{from_region.get_name}#{join.get_owner.get_name}.#{join.get_name} to=#{to_region}#{join.get_cell.get_name}.#{join.get_port_name} through_type=#{through_type}\n" )
        return self.plugin.add_through_plugin(join, from_region, to_region, through_type)

    def joinable(self, from_region, to_region, through_type):
        dbgPrint("ClassType.joinable?: from_region={} to_region={} through_type={}\n".format(
            from_region.get_name(), to_region, through_type))
        return self.plugin.joinable(from_region, to_region, through_type)

    def check_class(self, class_name):
        dbgPrint("ClassType#check_class class_name={}\n".format(class_name))
        if getattr(self, "plugin", None) is None or self.plugin.check_class(class_name) == False:
            self.cdl_error("S9999 '$1': invalide class name", class_name)

    def get_name(self):
        return self.name

    def get_plugin(self):
        return self.plugin

    #== ClassType リージョンの Hash を得る
    # class_regions の説明参照
    @classmethod
    def get_class_regions(cls, node_root):
        if cls.class_regions.get(node_root):
            return cls.class_regions[node_root]
        else:
            return {}

    def get_regions(self, node_root):
        return ClassType.class_regions[node_root][self.name]

    def get_option(self):
        dbgPrint("ClassType: get_option: {}\n".format(self.option))
        return self.option

    #== ClassType#ドメイン種別を得る
    def get_kind(self):
        dbgPrint("ClassType#get_kind plugin_name={} plugin={} DomainType={}\n".format(
            self.plugin_name, getattr(self, "plugin", None), self))
        return self.plugin.get_kind()

    def show_tree(self, indent):
        print("  " * (indent + 1), end="")
        print("class: name={} plugin={} option={}".format(self.name, self.plugin_name, self.option))
