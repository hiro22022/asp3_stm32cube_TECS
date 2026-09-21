# -*- coding: utf-8 -*-
#
#  CppIfGenPlugin.rb (MultiPlugin) の Python 移植

from tecslib.plugin.MultiPlugin import MultiPlugin


class CppIfGenPlugin(MultiPlugin):

    @classmethod
    def get_plugin(cls, superClass):
        from tecslib.plugin.SignaturePlugin import SignaturePlugin
        from tecslib.plugin.CelltypePlugin import CelltypePlugin
        from tecslib.plugin.CellPlugin import CellPlugin

        if issubclass(superClass, SignaturePlugin):
            return None
        if issubclass(superClass, CelltypePlugin):
            from tecslib.plugin.CppIfGenCelltypePlugin import CppIfGenCelltypePlugin
            return CppIfGenCelltypePlugin
        if issubclass(superClass, CellPlugin):
            from tecslib.plugin.CppIfGenCellPlugin import CppIfGenCellPlugin
            return CppIfGenCellPlugin
        return None
