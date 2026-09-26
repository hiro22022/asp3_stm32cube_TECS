# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#   CompositePlugin.rb の Python 移植

from tecslib.core.plugin import Plugin
from tecslib.core.syntaxobj.cdlstring import CDLString


class CompositePlugin(Plugin):

    def __init__(self, celltype, option):
        super().__init__()
        self.celltype = celltype
        self.plugin_arg_str = CDLString.remove_dquote(option)
        self.plugin_arg_list = {}

    def new_cell(self, cell):
        pass

    @classmethod
    def gen_post_code(cls, file):
        pass
