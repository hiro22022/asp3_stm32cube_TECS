# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#   MultiPlugin.rb の Python 移植

from tecslib.core.syntaxobj.node import Node


class MultiPlugin(Node):

    @classmethod
    def get_plugin(cls, superClass):
        from tecslib.plugin.SignaturePlugin import SignaturePlugin
        from tecslib.plugin.CelltypePlugin import CelltypePlugin
        from tecslib.plugin.CellPlugin import CellPlugin
        from tecslib.plugin.ThroughPlugin import ThroughPlugin

        if superClass is None:
            return None
        if issubclass(superClass, SignaturePlugin) or superClass is SignaturePlugin:
            return SignaturePlugin
        if issubclass(superClass, CelltypePlugin) or superClass is CelltypePlugin:
            return CelltypePlugin
        if issubclass(superClass, CellPlugin) or superClass is CellPlugin:
            return CellPlugin
        if issubclass(superClass, ThroughPlugin) or superClass is ThroughPlugin:
            return ThroughPlugin
        return None
