# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/syntaxobj/typedef.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

from tecslib.core.syntaxobj.node import BDNode


class Typedef(BDNode):
    # @declarator:: Decl

    @classmethod
    def new_decl_list(cls, type_spec_qual_list, decl_list):
        for decl in decl_list:
            Typedef(type_spec_qual_list, decl)

    def __init__(self, type_spec_qual_list, decl):
        from tecslib.core.componentobj.namespace import Namespace
        super().__init__()
        decl.set_type(type_spec_qual_list)
        self.declarator = decl
        decl.set_owner(self)    # Decl(Typedef)

        Namespace.new_typedef(self)
        # PLY は typedef の ';' 還元前に次トークンを先読みするため、
        # 直後の宣言で使う新 typedef 名が IDENTIFIER のまま残ることがある
        try:
            from tecslib.core.bnf import upgrade_lookahead_typename
            upgrade_lookahead_typename(self.get_name())
        except Exception:
            pass

    def get_name(self):
        return self.declarator.get_name()

    def get_declarator(self):
        return self.declarator

    def show_tree(self, indent):
        print("  " * indent, end="")
        print("Typedef: {}".format(self.locale_str()))
        self.declarator.show_tree(indent + 1)
