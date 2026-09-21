# -*- coding: utf-8 -*-
#
#  MrubyBridgeCompositePlugin.rb の Python 移植

from tecslib.plugin.CompositePlugin import CompositePlugin
from tecslib.plugin.lib.MrubyBridgeCelltypePluginModule import MrubyBridgeCelltypePluginModule
from tecslib.core.toplevel import dbgPrint


dbgPrint("MrubyBridgeCompositePlugin loaded\n")


class MrubyBridgeCompositePlugin(MrubyBridgeCelltypePluginModule, CompositePlugin):

    @classmethod
    def gen_post_code(cls, file):
        MrubyBridgeCelltypePluginModule.gen_post_code(file)
