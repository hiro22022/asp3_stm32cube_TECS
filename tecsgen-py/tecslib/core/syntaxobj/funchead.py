# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/syntaxobj/funchead.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

from tecslib.core.syntaxobj.node import BDNode


#== 関数頭部
# signature に登録される関数
class FuncHead(BDNode):
    #  @declarator:: Decl

    def __init__(self, declarator, type_, b_oneway):
        from tecslib.core.componentobj.signature import Signature
        from tecslib.core.types import FuncType, PtrType

        super().__init__()
        declarator.set_type(type_)
        self.declarator = declarator
        self.declarator.set_owner(self)  # Decl (FuncHead)

        if isinstance(self.declarator.get_type(), FuncType):
            if b_oneway:
                self.declarator.get_type().set_oneway(b_oneway)
        self.declarator.get_type().check_struct_tag("FUNCHEAD")

        # check if return type is pointer
        if isinstance(declarator.get_type(), FuncType):
            if isinstance(declarator.get_type().get_type().get_original_type(), PtrType) and \
                    Signature.get_current().is_deviate() is False:
                self.cdl_warning(
                    "W3004 $1 pointer type has returned. specify deviate or stop return pointer",
                    self.declarator.get_identifier())

    def get_declarator(self):
        return self.declarator

    def is_oneway(self):
        if self.declarator.is_function():
            return self.declarator.get_type().is_oneway()
        return False

    def is_function(self):
        return self.declarator.is_function()

    #=== FuncHead# 関数の名前を返す
    def get_name(self):
        return self.declarator.get_name()

    #=== FuncHead# 関数型を返す
    def get_type(self):
        return self.declarator.get_type()

    #=== FuncHead# 関数の戻り値の型を返す
    # types.py に定義されている型
    # 関数ヘッダの定義として不完全な場合 None を返す
    def get_return_type(self):
        if self.is_function():
            return self.declarator.get_type().get_type()
        return None

    #=== FuncHead# 関数の引数のリストを返す
    # ParamList を返す
    # 関数ヘッダの定義として不完全な場合 None を返す
    def get_paramlist(self):
        if self.is_function():
            return self.declarator.get_type().get_paramlist()
        return None

    def show_tree(self, indent):
        print("  " * indent, end="")
        print("FuncHead: {}".format(self.locale_str()))
        self.declarator.show_tree(indent + 1)
