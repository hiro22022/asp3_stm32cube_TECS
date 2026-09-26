# -*- coding: utf-8 -*-
#
#  MrubyInfoBridgePlugin.rb の Python 移植

from tecslib.plugin.MultiPlugin import MultiPlugin
from tecslib.core.toplevel import dbgPrint


class MrubyInfoBridgePlugin(MultiPlugin):

    @classmethod
    def get_plugin(cls, superClass):
        from tecslib.plugin.SignaturePlugin import SignaturePlugin
        from tecslib.plugin.CellPlugin import CellPlugin

        if issubclass(superClass, SignaturePlugin):
            dbgPrint("MrubyInfoBridgePlugin: SignaturePlugin\n")
            from tecslib.plugin.MrubyInfoBridgeSignaturePlugin import MrubyInfoBridgeSignaturePlugin
            return MrubyInfoBridgeSignaturePlugin
        if issubclass(superClass, CellPlugin):
            dbgPrint("MrubyInfoBridgePlugin: CellPlugin\n")
            from tecslib.plugin.MrubyInfoBridgeCellPlugin import MrubyInfoBridgeCellPlugin
            return MrubyInfoBridgeCellPlugin
        dbgPrint("MrubyInfoBridgePlugin: unsupported\n")
        return None
