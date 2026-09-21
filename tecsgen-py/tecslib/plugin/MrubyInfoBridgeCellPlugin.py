# -*- coding: utf-8 -*-
#
#  MrubyInfoBridgeCellPlugin.rb の Python 移植

from tecslib.core.componentobj.namespace import Namespace
from tecslib.core.syntaxobj.cdlstring import CDLString
from tecslib.plugin.CellPlugin import CellPlugin


class MrubyInfoBridgeCellPlugin(CellPlugin):

    def __init__(self, cell, option):
        super().__init__(cell, option)
        self.cell = cell
        self.plugin_arg_str = CDLString.remove_dquote(option)
        self.plugin_arg_list = {}

    @classmethod
    def gen_post_code(cls, file):
        file.print("/* '{}' post code */\n".format(cls.__name__))
        cls.gen_signature_cdl(file, Namespace.get_root())

    @classmethod
    def gen_signature_cdl(cls, file, namespace):
        for sig in namespace.get_signature_list():
            if "nMrubyInfo::" in str(sig.get_namespace_path()):
                pass
            else:
                file.print('    generate( MrubyInfoBridgeSignaturePlugin, {}, "auto_exclude=true" );\n'.format(
                    sig.get_namespace_path()))
        for ns in namespace.get_namespace_list():
            cls.gen_signature_cdl(file, ns)
