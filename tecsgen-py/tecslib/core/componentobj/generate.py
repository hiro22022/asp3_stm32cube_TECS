# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/componentobj/generate.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

from tecslib.core.plugin_module import PluginModule
from tecslib.core.syntaxobj.node import Node
from tecslib.core.toplevel import dbgPrint


#== generate: signature, celltype, cell へのプラグインのロードと適用
class Generate(Node, PluginModule):
    #@plugin_name:: Symbol
    #@object_nsp:: NamespacePath
    #@option::         String '"', '"' で囲まれている
    #@plugin_object:: Plugin

    def __init__(self, plugin_name, object_nsp, option):
        super().__init__()
        self.plugin_name = plugin_name
        self.object_nsp = object_nsp
        option = str(option)    # option は Token
        self.option = option
        self.plugin_object = None

        dbgPrint("generate: {} {} option={}\n".format(plugin_name, str(object_nsp), option))

        from tecslib.core.componentobj.namespace import Namespace
        from tecslib.core.componentobj.signature import Signature
        from tecslib.core.componentobj.celltype import Celltype
        from tecslib.core.componentobj.compositecelltype import CompositeCelltype
        from tecslib.core.componentobj.cell import Cell

        object = Namespace.find(object_nsp)
        if isinstance(object, (Signature, Celltype, CompositeCelltype, Cell)):
            self.plugin_object = object.apply_plugin(self.plugin_name, self.option)
        elif object:
            # V1.5.0 以前の仕様では、signature のみ可能だった
            #      cdl_error( "S1149 $1 not signature" , signature_nsp )
            self.cdl_error("S9999 generate: '$1' neither signature, celltype nor cell", object_nsp)
            return
        else:
            self.cdl_error("S9999 generate: signature '$1' not found", object_nsp)
