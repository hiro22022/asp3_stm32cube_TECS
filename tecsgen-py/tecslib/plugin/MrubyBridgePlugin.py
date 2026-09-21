# -*- coding: utf-8 -*-
#
#  MrubyBridgePlugin.rb の Python 移植

from tecslib.plugin.MultiPlugin import MultiPlugin
from tecslib.core.toplevel import dbgPrint


class MrubyBridgePlugin(MultiPlugin):

    @classmethod
    def get_plugin(cls, superClass):
        from tecslib.plugin.SignaturePlugin import SignaturePlugin
        from tecslib.plugin.CelltypePlugin import CelltypePlugin
        from tecslib.plugin.CompositePlugin import CompositePlugin
        from tecslib.plugin.CellPlugin import CellPlugin

        if issubclass(superClass, SignaturePlugin):
            dbgPrint("MrubyBridgePlugin: SignaturePlugin\n")
            from tecslib.plugin.MrubyBridgeSignaturePlugin import MrubyBridgeSignaturePlugin
            return MrubyBridgeSignaturePlugin
        if issubclass(superClass, CelltypePlugin):
            dbgPrint("MrubyBridgePlugin: CelltypePlugin\n")
            from tecslib.plugin.MrubyBridgeCelltypePlugin import MrubyBridgeCelltypePlugin
            return MrubyBridgeCelltypePlugin
        if issubclass(superClass, CompositePlugin):
            dbgPrint("MrubyBridgePlugin: CompositePlugin\n")
            from tecslib.plugin.MrubyBridgeCompositePlugin import MrubyBridgeCompositePlugin
            return MrubyBridgeCompositePlugin
        if issubclass(superClass, CellPlugin):
            dbgPrint("MrubyBridgePlugin: CellPlugin\n")
            from tecslib.plugin.MrubyBridgeCellPlugin import MrubyBridgeCellPlugin
            return MrubyBridgeCellPlugin
        dbgPrint("MrubyBridgePlugin: unsupported\n")
        return None
