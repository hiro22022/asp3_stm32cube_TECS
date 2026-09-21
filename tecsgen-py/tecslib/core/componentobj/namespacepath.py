# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/componentobj/namespacepath.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

import copy

from tecslib.core.syntaxobj.node import Node
from tecslib.rubylib.symbol import Sym


#== 名前空間パス
class NamespacePath(Node):
    #@b_absolute::Bool
    #@path::[ Symbol,... ]
    #@namespace::Namespace:  b_absolute == False のとき、基点となる namespace

    #=== NamespacePath# initialize
    #ident::Symbol           最初の名前, ただし "::" のみの場合は String
    #b_absolute:Bool         "::" で始まっている場合 True
    #namespace::Namespace    b_absolute = False かつ、構文解釈段階以外で呼び出す場合は、必ず指定すること
    def __init__(self, ident, b_absolute, namespace=None):
        from tecslib.core.componentobj.namespace import Namespace
        super().__init__()

        if ident == "::" and not isinstance(ident, Sym):   # RootNamespace
            self.path = []
            self.b_absolute = True
        else:
            self.path = [ident]
            self.b_absolute = b_absolute

        if namespace:
            self.namespace = namespace
            if b_absolute is True:
                raise Exception("NamespacePath#initialize: naamespace specified for absolute path")
        else:
            if b_absolute is False:
                self.namespace = Namespace.get_current()
            else:
                self.namespace = None

    #=== NamespacePath# append する
    #RETURN self
    # このメソッドは、元の NamespacePath オブジェクトを変形して返す
    def append_bang(self, ident):
        self.path.append(ident)
        return self

    #=== NamespacePath# append する
    # このメソッドは、元の NamespacePath オブジェクトを変形しない
    #RETURN:: 複製した NamespacePath
    def append(self, ident):
        cl = copy.copy(self)
        cl.set_clone()
        cl.append_bang(ident)
        return cl

    def set_clone(self):
        self.path = list(self.path)

    def get_name(self):
        return self.path[len(self.path) - 1]

    #=== NamespacePath#クローンを作成して名前を変更する
    def change_name(self, name):
        cl = copy.copy(self)
        cl.set_clone()
        cl.change_name_no_clone(name)
        return cl

    change_name_clone = change_name

    #=== NamespacePath#名前を変更する
    # このインスタンスを参照するすべてに影響を与えることに注意
    def change_name_no_clone(self, name):
        self.path[len(self.path) - 1] = name
        return None

    #=== NamespacePath:: path 文字列を得る
    # CDL 用の path 文字列を生成
    def __str__(self):
        return self.get_path_str()

    def get_path_str(self):
        first = True
        if self.b_absolute:
            path = "::"
        else:
            path = ""
        for n in self.path:
            if first:
                path = "{}{}".format(path, n)
                first = False
            else:
                path += "::{}".format(n)
        return path

    def is_absolute(self):
        return self.b_absolute

    def is_name_only(self):
        return len(self.path) == 1 and self.b_absolute is False

    #=== NamespacePath:: パスの配列を返す
    # is_absolute True の場合、ルートからのパス
    #             False の場合、base_namespace からの相対
    # ルート namespace の場合、長さ０の配列を返す
    def get_path(self):
        return self.path

    #=== NamespacePath#フルパスの配列を返す
    # 返された配列を書き換えてはならない
    def get_full_path(self):
        if self.b_absolute:
            return self.path
        return list(self.namespace.get_namespace_path().get_full_path()) + self.path

    #=== NamespacePath:: 相対パスのベースとなる namespace
    # is_absolute == False の時のみ有効な値を返す (True なら None)
    def get_base_namespace(self):
        return self.namespace

    #=== NamespacePath:: C 言語グローバル名を得る
    def get_global_name(self):
        if self.b_absolute:
            global_name = ""
        else:
            global_name = self.namespace.get_global_name()

        for n in self.path:
            if global_name != "":
                global_name = "{}_{}".format(global_name, n)
            else:
                global_name = str(n)
        return global_name

    #=== NamespacePath:: 分解して NamespacePath インスタンスを生成する
    #path_str:: String       : namespace または region のパス ex) "::path::A" , "::", "ident"
    #b_force_absolute:: Bool : "::" で始まっていない場合でも絶対パスに扱う
    #
    # NamespacePath は通常構文解析されて作成される
    # このメソッドは、オプションなどで指定される文字列を分解して NamespacePath を生成するのに用いる
    # チェックはゆるい。不適切なパス指定は、不適切な NamespacePath が生成される
    @classmethod
    def analyze(cls, path_str, b_force_absolute=False):

        if path_str == "::":
            return cls("::", True)

        pa = path_str.split("::")
        if pa[0] == "":
            pa.pop(0)
            b_absolute = True
        else:
            if b_force_absolute:
                b_absolute = True
            else:
                b_absolute = False

        if pa and pa[0]:
            nsp = cls(Sym(pa[0]), b_absolute)
        else:
            nsp = cls("::", b_absolute)
        if pa:
            pa.pop(0)

        for a in pa:
            if a:
                nsp.append_bang(Sym(a))
            else:
                nsp.append_bang("::")

        return nsp

    #=== NamespacePath# CDL に出力する際の定義用のパスを出力する
    def print_cdl_decl_path_pre(self, file):
        for i in range(0, len(self.path)):
            file.print("  " * i)
            file.print("namespace {}{{\n".format(self.path[i]))

    def print_cdl_decl_path_post(self, file):
        length = len(self.path) - 1
        for i in range(0, length + 1):
            file.print("  " * (length - i))
            file.print("}\n")
        file.print("\n")
