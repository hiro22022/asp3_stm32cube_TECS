# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/componentobj/factory.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

from tecslib.core.syntaxobj.node import BDNode
from tecslib.rubylib.symbol import Sym


class Factory(BDNode):
    # @name:: string
    # @file_name:: string
    # @format:: string
    # @arg_list:: Expression の elements と同じ形式 [ [:IDENTIFIER, String], ... ]
    # @f_celltype:: bool : true: celltype factory, false: cell factory

    _f_celltype = False

    def __init__(self, name, file_name, format, arg_list):
        super().__init__()
        self.f_celltype = Factory._f_celltype

        if name == Sym("write"):
            # write 関数
            self.name = name

            # write 関数の第一引数：出力先ファイル名
            # 式を評価する（通常単一の文字列であるから、単一の文字列が返される）
            self.file_name = file_name.eval_const(None).val  # file_name : Expression
            if type(self.file_name) is not str:
                # 文字列定数ではなかった
                self.cdl_error("S1132 $1: 1st parameter is not string(file name)", self.name)
                self.file_name = None

            # write 関数の第二引数：フォーマット文字列
            self.format = format.eval_const(None).val     # format : Expression
            # 式を評価する（通常単一の文字列であるから、単一の文字列が返される）
            if type(self.format) is not str:
                # 文字列定数ではなかった
                self.cdl_error("S1133 $1: 2nd parameter is not string(fromat)", self.name)
                self.format = None

            # 第三引数以降を引数リストとする mikan 引数のチェック
            self.arg_list = arg_list

        else:
            self.cdl_error("S1134 $1: unknown factory function", name)

        from tecslib.core.componentobj.celltype import Celltype
        Celltype.new_factory(self)

    def check_arg(self, celltype):
        if not self.arg_list:
            return

        if self.f_celltype:
            self.cdl_error("S1135 celltype factory can't have parameter(s)")
            return

        from tecslib.core.syntaxobj.decl import Decl

        for elements in self.arg_list:

            if elements[0] == "IDENTIFIER":  #1
                obj = celltype.find(elements[1])
                if obj is None:
                    self.cdl_error("S1136 '$1': not found", elements[1])
                elif type(obj) is not Decl or obj.get_kind() != "ATTRIBUTE":
                    self.cdl_error("S1137 '$1': not attribute", elements[1])
            elif elements[0] == "STRING_LITERAL":
                pass
            else:
                self.cdl_error("S1138 internal error Factory.check_arg()")

    @classmethod
    def set_f_celltype(cls, f_celltype):
        cls._f_celltype = f_celltype

    def get_f_celltype(self):
        return self.f_celltype

    def get_name(self):
        return self.name

    def get_file_name(self):
        return self.file_name

    def get_format(self):
        return self.format

    def get_arg_list(self):
        return self.arg_list

    def show_tree(self, indent):
        print("  " * indent, end="")
        print("Factory: name: {}".format(self.name))
        if self.arg_list:
            print("  " * (indent + 1), end="")
            print("argument(s):")
            for l in self.arg_list:
                print("  " * (indent + 2), end="")
                print("\"{}\"\n".format(l), end="")
