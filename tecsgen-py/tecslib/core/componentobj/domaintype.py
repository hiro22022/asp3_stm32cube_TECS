# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/componentobj/domaintype.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

from tecslib.core.plugin_module import PluginModule
from tecslib.core.syntaxobj.node import Node
from tecslib.core.toplevel import dbgPrint
from tecslib.rubylib.symbol import Sym


#== DomainType
#
# region の domain を記憶するクラス
class DomainType(Node, PluginModule):
    #@name::Symbol : ドメインタイプの名前 ex) HRP2, HRP
    #@region::Region
    #@plugin_name::Symbol : ex) HRP2Plugin
    #@option::String : ex) (HRP2) "trusted", "nontrusted", (HRP3) :kernel, :user, :OutOfDomain
    #@plugin::DomainPlugin の子クラス
    #@node_root::Region : node_root となるリージョン

    # ドメインに属する region の Hash
    # domain 指定が一度も行われない場合、このリストは空である
    # ルートリージョンは option = "OutOfDomain" で登録される (domain 指定が無ければ登録されない)
    domain_regions = {}  # { node_root => { :domain_type => [ region, ... ] } }

    def __init__(self, region, name, option, node_root):
        super().__init__()
        self.name = name
        self.plugin_name = Sym(str(name) + "Plugin")
        from tecslib.core.plugin_module import _import_plugin_class
        DomainPlugin = _import_plugin_class("DomainPlugin")
        self.pluginClass = self.load_plugin(self.plugin_name, DomainPlugin)
        self.region = region
        self.option = option
        self.plugin = None
        self.node_root = node_root

        if not DomainType.domain_regions.get(node_root):
            DomainType.domain_regions[node_root] = {}
        if DomainType.domain_regions[node_root].get(name):
            if region not in DomainType.domain_regions[node_root][name]:
                DomainType.domain_regions[node_root][name].append(region)
        else:
            DomainType.domain_regions[node_root][name] = [region]

    def create_domain_plugin(self):
        if not self.plugin:
            # pluginClass = Object.const_get @plugin_name  # not incompatible with MultiPlugin
            dbgPrint("create_domain_plugin: plugin_name={} class={} region={} option={}\n".format(
                self.plugin_name, self.pluginClass.__name__, self.region.get_name(), self.option))
            if self.pluginClass is None:
                return
            self.plugin = self.pluginClass(self.region, self.name, self.option)
            self.plugin.set_locale(self.locale)
            # p "*** plugin_name=#{@plugin_name} plugin=#{@plugin} DomainType=#{self}"

    def add_through_plugin(self, join, from_region, to_region, through_type):
        # print( "DOMAIN: add_through_plugin: from=#{from_region.get_name}#{join.get_owner.get_name}.#{join.get_name} to=#{to_region}#{join.get_cell.get_name}.#{join.get_port_name} through_type=#{through_type}\n" )
        return self.plugin.add_through_plugin(join, from_region, to_region, through_type)

    def joinable(self, from_region, to_region, through_type):
        # print( "DOMAIN: joinable? from_region=#{from_region.get_name} to_region=#{to_region} through_type=#{through_type}\n" )
        return self.plugin.joinable(from_region, to_region, through_type)

    def get_name(self):
        return self.name

    #== DomainType リージョンの Hash を得る
    # domain_regions の説明参照
    @classmethod
    def get_domain_regions(cls, node_root):
        if not cls.domain_regions.get(node_root):
            return {}
        else:
            return cls.domain_regions[node_root]

    def get_regions(self, node_root):
        return DomainType.domain_regions[node_root][self.name]

    def get_option(self):
        return self.option

    #== DomainType#ドメイン種別を得る
    #return::Symbol :kernel, :user, :OutOfDomain
    def get_kind(self):
        dbgPrint("DomainType#get_kind plugin_name={} plugin={} DomainType={}\n".format(
            self.plugin_name, self.plugin, self))
        if self.plugin:
            return self.plugin.get_kind()
        else:
            # domain 指定されていないケース
            return Sym("OutOfDomain")

    def show_tree(self, indent):
        print("  " * (indent + 1), end="")
        print("domain: name={} plugin={} option={}".format(self.name, self.plugin_name, self.option))
