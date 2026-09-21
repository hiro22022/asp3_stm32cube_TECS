# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2014 by TOPPERS Project
#
#   このファイルは tecsgen (Ruby 版) の tecslib/plugin/TransparentMarshalerPlugin.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．
#
#   $Id: TransparentMarshalerPlugin.rb 2952 2018-05-07 10:19:07Z okuma-top $
#++

#== TransparentMarshaler
# TransparentRPC 用のマーシャラ、アンマーシャラセルタイプを生成するシグニチャプラグイン

from tecslib.plugin.SignaturePlugin import SignaturePlugin
from tecslib.plugin.lib.GenTransparentMarshaler import GenTransparentMarshaler
from tecslib.plugin.lib.GenParamCopy import GenParamCopy
from tecslib.rubylib.symbol import Sym


class TransparentMarshalerPlugin(GenParamCopy, GenTransparentMarshaler, SignaturePlugin):

    TransparentMarshalerPluginArgProc = {}

    def __init__(self, signature, option):
        super().__init__(signature, option)
        self.b_noClientSemaphore = False
        self.noServerChannelOpenerCode = True
        self.initialize_transparent_marshaler(signature.get_name())

        self.plugin_arg_check_proc_tab = TransparentMarshalerPlugin.TransparentMarshalerPluginArgProc
        self.parse_plugin_arg()
        # check_PPAllocator
        if self.signature.need_PPAllocator(True):
            self.PPAllocatorSize = 1    # PPAllocatorの必要性有のために設定 (サイズは使われない)
            necessity = "Necessary"
        else:
            necessity = "Unnecessary"

        print("TransparentMarshalerPlugin: signature={}, PPAllocator={}\n".format(
            signature.get_namespace_path(), necessity))

    def gen_cdl_file(self, file):
        self.gen_marshaler_celltype()
        file.print("import( \"{}\" );\n".format(self.marshaler_celltype_file_name))

    def subst_name(self, val):
        return Sym("_")
        # return nil
