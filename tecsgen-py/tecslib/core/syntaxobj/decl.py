# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/syntaxobj/decl.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

from tecslib.core.syntaxobj.node import BDNode
from tecslib.rubylib.rb import to_s
from tecslib.rubylib.symbol import Sym


#=== 宣言
# @kind で示される各種の宣言
class Decl(BDNode):

    # @identifer:: String
    # @global_name:: String | None : String(@kind=TYPEDEF||CONSTANT), None(@kind=その他)
    #                set_kind にて設定される
    # @type:: ArrayType, FuncType, PtrType, IntType, StructType
    #         VoidType, FloatType, DefinedType, BoolType
    # @initializer:: constant_expression, mikan { initlist }
    # @kind:: VAR, ATTRIBUTE, PARAMETER, TYPEDEF, CONSTANT, MEMBER, FUNCHEAD(signatureの関数定義)
    # @b_referenced:: bool
    #
    # 以下は、@kind が VAR, ATTRIBUTE のときに有効
    # @rw:: bool     # 古い文法では attr に指定可能だった（消すには generate の修正も必要）
    # @omit:: bool
    # @choice_list:: [String]  attr 初期値の選択肢
    # 以下は、@kind が VAR, ATTRIBUTE, MEMBER のときに有効
    # @size_is:: Expression or None unless specified
    # 以下は、@kind が MEMBER のときに有効
    # @count_is:: Expression or None unless specified
    #             attr, var の場合、count_is は指定できない
    # @string:: Expression, -1 (length not specified) or None (not specified)
    #
    # mikan  ParamDecl だけ別に設けたが、MemberDecl, AttrDecl なども分けるべきか(？)

    def __init__(self, identifier):
        super().__init__()
        self.identifier = identifier
        self.rw = False
        self.omit = False
        self.size_is = None
        self.count_is = None
        self.string = None
        self.choice_list = None
        self.b_referenced = False
        self.type = None
        self.kind = None
        self.initializer = None
        self.global_name = None

    def set_initializer(self, initializer):
        self.initializer = initializer

    def get_initializer(self):
        return self.initializer

    def is_function(self):
        from tecslib.core.types import FuncType
        return type(self.type) is FuncType

    #== Decl の意味的誤りをチェックする
    def check(self):
        from tecslib.core.types import ArrayType
        from tecslib.core.ctypes import CArrayType

        # 構造体タグチェック（ポインタ型から構造体が参照されている場合は、タグの存在をチェックしない）
        self.type.check_struct_tag(self.kind)

        # 型のチェックを行う
        res = self.type.check()
        if res:
            self.cdl_error("S2002 $1: $2", self.identifier, res)

        # 不要の初期化子をチェックする
        if self.initializer:
            if self.kind in ("PARAMETER", "TYPEDEF", "MEMBER", "FUNCHEAD"):
                self.cdl_error("S2003 $1: $2 cannot have initializer",
                               self.identifier, str(self.kind).lower())
            elif self.kind in ("VAR", "ATTRIBUTE", "CONSTANT"):
                # ここでは代入可能かどうか、チェックしない
                # VAR, ATTRIBUTE, CONSTANT はそれぞれでチェックする
                pass
            else:
                raise Exception("unknown kind in Delc::check")

        if isinstance(self.type, ArrayType) and self.type.get_subscript() is None and self.omit is False:
            if self.kind == "ATTRIBUTE":
                self.cdl_error("S2004 $1: array subscript must be specified or omit", self.identifier)
            elif self.kind == "VAR" or self.kind == "MEMBER":
                if type(self.type) is CArrayType and self.kind == "MEMBER":
                    self.cdl_info("I9999 $1: array without subscript might not be handled", self.identifier)
                else:
                    self.cdl_error("S2005 $1: array subscript must be specified", self.identifier)

        return None

    #== ポインタレベルを得る
    # 戻り値：
    #   非ポインタ変数   = 0
    #   ポインタ変数     = 1
    #   二重ポインタ変数 = 2
    def get_ptr_level(self):
        from tecslib.core.types import DefinedType, PtrType

        level = 0
        type_ = self.type
        while True:
            if isinstance(type_, PtrType):
                level += 1
                type_ = type_.get_referto()
                # mikan ポインタの添数あり配列のポインタレベルは０でよい？
            elif isinstance(type_, DefinedType):
                type_ = type_.get_type()
            else:
                break
        return level

    def get_name(self):
        return self.identifier

    def get_global_name(self):
        return self.global_name

    def set_type(self, type_):
        if not self.type:
            self.type = type_
        else:
            self.type.set_type(type_)             # 葉に設定

    def get_type(self):
        return self.type

    def get_identifier(self):
        return self.identifier

    # STAGE: B
    def set_kind(self, kind):
        from tecslib.core.componentobj.namespace import Namespace

        self.kind = kind
        if kind in ("TYPEDEF", "CONSTANT"):
            if str(Namespace.get_global_name()) == "":
                self.global_name = self.identifier
            else:
                self.global_name = Sym("{}_{}".format(Namespace.get_global_name(), self.identifier))
        else:
            self.global_name = None

    def get_kind(self):
        return self.kind

    def set_specifier_list(self, spec_list):
        for spec in spec_list:
            if spec[0] == "RW":
                self.rw = True
            elif spec[0] == "OMIT":
                self.omit = True
            elif spec[0] == "SIZE_IS":
                self.size_is = spec[1]
            elif spec[0] == "COUNT_IS":
                self.count_is = spec[1]
            elif spec[0] == "STRING":
                self.string = spec[1]
            elif spec[0] == "CHOICE":
                self.choice_list = spec[1]
            else:
                raise Exception("Unknown specifier {}".format(spec[0]))

        if self.size_is or self.count_is or self.string:
            self.type.set_scs(self.size_is, self.count_is, self.string, None, False)

    def is_rw(self):
        return self.rw

    def is_omit(self):
        return self.omit

    def get_size_is(self):
        return self.size_is

    def get_count_is(self):
        return self.count_is

    def get_string(self):
        return self.string

    def get_choice_list(self):
        return self.choice_list

    def referenced(self):
        self.b_referenced = True

    def is_referenced(self):
        return self.b_referenced

    def is_type(self, type_):
        from tecslib.core.types import DefinedType

        t = self.type
        while True:
            if isinstance(t, type_):
                return True
            elif isinstance(t, DefinedType):
                t = t.get_type()
            else:
                return False

    def is_const(self):
        from tecslib.core.types import DefinedType

        type_ = self.type
        while True:
            if type_.is_const():
                return True
            elif isinstance(type_, DefinedType):
                type_ = type_.get_type()
            else:
                return False

    #=== Decl# print_flowinfo
    def print_flowinfo(self, file):
        if self.kind == "VAR":
            file.write("{} ".format(self.identifier))

    def show_tree(self, indent):
        print("  " * indent, end="")
        print("Declarator: name: {} kind: {} global_name: {} {}".format(
            self.identifier, self.kind, to_s(self.global_name), self.locale_str()))
        print("  " * (indent + 1), end="")
        print("type:")
        self.type.show_tree(indent + 2)
        if self.initializer:
            print("  " * (indent + 1), end="")
            print("initializer:")
            self.initializer.show_tree(indent + 2)
        else:
            print("  " * (indent + 1), end="")
            print("initializer: no")
        print("  " * (indent + 1), end="")
        print("size_is: {}, count_is: {}, string: {} referenced: {} ".format(
            to_s(self.size_is), to_s(self.count_is), to_s(self.string), to_s(self.b_referenced)))
