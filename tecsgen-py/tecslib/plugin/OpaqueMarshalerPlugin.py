# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#
#   このファイルは tecsgen (Ruby 版) の tecslib/plugin/OpaqueMarshalerPlugin.rb を
#   Python へ移植したものである．
#
#   $Id: OpaqueMarshalerPlugin.rb 3159 2020-07-05 10:25:24Z okuma-top $
#++

#== OpaqueMarshaler
# OpaqueRPC 用のマーシャラ、アンマーシャラセルタイプを生成するシグニチャプラグイン

from tecslib.plugin.SignaturePlugin import SignaturePlugin
from tecslib.plugin.lib.GenOpaqueMarshaler import GenOpaqueMarshaler
from tecslib.plugin.lib.GenParamCopy import GenParamCopy
from tecslib.rubylib.symbol import Sym


class OpaqueMarshalerPlugin(GenParamCopy, GenOpaqueMarshaler, SignaturePlugin):

    OpaqueMarshalerPluginArgProc = {}

    def __init__(self, signature, option):
        super().__init__(signature, option)
        self.b_noClientSemaphore = False
        self.noServerChannelOpenerCode = True
        self.initialize_opaque_marshaler()

        self.plugin_arg_check_proc_tab = OpaqueMarshalerPlugin.OpaqueMarshalerPluginArgProc
        self.parse_plugin_arg()
        if self.signature.need_PPAllocator(True):
            self.PPAllocatorSize = 1
            necessity = "Necessary"
        else:
            necessity = "Unnecessary"

        print("OpaqueMarshalerPlugin: signature={}, PPAllocator={}\n".format(
            signature.get_namespace_path(), necessity))

    def gen_cdl_file(self, file):
        self.gen_marshaler_celltype()
        file.print("import( \"{}\" );\n".format(self.marshaler_celltype_file_name))

    def subst_name(self, val):
        return Sym("_")
