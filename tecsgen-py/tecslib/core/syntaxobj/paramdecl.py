# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/syntaxobj/paramdecl.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

from tecslib.core.syntaxobj.node import BDNode


# 関数パラメータの宣言
class ParamDecl(BDNode):

    # @declarator:: Decl:  Token, ArrayType, FuncType, PtrType
    # @direction:: IN, OUT, INOUT, SEND, RECEIVE
    # @size:: Expr   (size_is 引数)
    # @count:: Expr   (count_is 引数)
    # @max:: Expr (size_is の第二引数)
    # @b_nullable:: Bool : nullable
    # @string:: Expr or -1(if size not specified) （string 引数）
    # @allocator:: Signature of allocator
    # @b_ref:: bool : size_is, count_is, string_is 引数として参照されている
    #
    # 1. 関数型でないこと
    # 2. ２次元以上の配列であって最も内側以外の添数があること
    # 3. in, out, ..., size_is, count_is, ... の重複指定がないこと
    # 4. ポインタレベルが適切なこと

    def __init__(self, declarator, specifier, param_specifier):
        from tecslib.core.componentobj.namespace import Namespace
        from tecslib.core.componentobj.signature import Signature
        from tecslib.core.types import DefinedType, PtrType, StructType

        super().__init__()
        self.declarator = declarator
        self.declarator.set_owner(self)  # Decl (ParamDecl)
        self.declarator.set_type(specifier)
        self.param_specifier = param_specifier
        self.b_ref = False
        self.b_nullable = False
        self.direction = None
        self.size = None
        self.count = None
        self.string = None
        self.max = None
        self.allocator = None

        if self.declarator.is_function():               # (1)
            self.cdl_error("S2006 \'$1\' function", self.get_name())
            return

        res = self.declarator.check()
        if res:                                         # (2)
            self.cdl_error("S2007 \'$1\' $2", self.get_name(), res)
            return

        for i in self.param_specifier:
            if i[0] in ("IN", "OUT", "INOUT", "SEND", "RECEIVE"):   # (3)
                if self.direction is None:
                    self.direction = i[0]
                elif i[0] == self.direction:
                    self.cdl_warning("W3001 $1: duplicate", i[0])
                    continue
                else:
                    self.cdl_error("S2008 $1: inconsitent with previous one", i[0])
                    continue

                if i[0] in ("SEND", "RECEIVE"):
                    self.allocator = Namespace.find(i[1])   #1
                    if type(self.allocator) is not Signature:
                        self.cdl_error("S2009 $1: not found or not signature", i[1])
                        continue
                    elif not self.allocator.is_allocator():
                        # cdl_error( "S2010 $1: not allocator signature" , i[1] )
                        pass

            elif i[0] == "SIZE_IS":
                if self.size:
                    self.cdl_error("S2011 size_is duplicate")
                else:
                    self.size = i[1]
            elif i[0] == "COUNT_IS":
                if self.count:
                    self.cdl_error("S2012 count_is duplicate")
                else:
                    self.count = i[1]
            elif i[0] == "STRING":
                if self.string:
                    self.cdl_error("S2013 string duplicate")
                elif i[1]:
                    self.string = i[1]
                else:
                    self.string = -1
            elif i[0] == "MAX_IS":
                # max_is は、内部的なもの bnf.y.rb 参照
                # size_is で重複チェックされる
                self.max = i[1]
            elif i[0] == "NULLABLE":
                self.b_nullable = True

        if self.direction is None:
            self.cdl_error("S2014 No direction specified. [in/out/inout/send/receive]")

        if (self.direction == "OUT" or self.direction == "INOUT") and self.string == -1:
            self.cdl_warning("W3002 $1: this string might cause buffer over run", self.get_name())

        # mikan ポインタの配列（添数有）のレベルが０
        ptr_level = self.declarator.get_ptr_level()

        #----  set req_level, min_level & max_level  ----#
        if not (self.size or self.count or self.string):    # (4)
            req_level = 1
        elif (self.size or self.count) and self.string:
            req_level = 2
        else:
            req_level = 1

        if self.direction == "RECEIVE":
            req_level += 1
        min_level = req_level
        max_level = req_level

        # IN without pointer specifier can be non-pointer type
        if self.direction == "IN" and not (self.size or self.count or self.string):
            min_level = 0

        # if size_is specified and pointer refer to struct, max_level increase
        if self.size:
            type_ = self.declarator.get_type().get_original_type()
            while isinstance(type_, PtrType):
                type_ = type_.get_referto().get_original_type()
            if isinstance(type_, StructType):
                max_level += 1
        #----  end req_level & max_level    ----#

        if ptr_level < min_level:
            self.cdl_error("S2014 $1 need pointer or more pointer", self.declarator.get_identifier())
        elif ptr_level > max_level:
            # note: 構文解析段階で実行のため get_current 可
            if Signature.get_current() is None or Signature.get_current().is_deviate() is False:
                self.cdl_warning("W3003 $1 pointer level mismatch", self.declarator.get_identifier())

        type_ = self.declarator.get_type()
        while isinstance(type_, DefinedType):
            type_ = type_.get_original_type()

        if ptr_level > 0:
            # size_is, count_is, string をセット
            if self.direction == "RECEIVE" and ptr_level > 1:
                type_.get_type().set_scs(self.size, self.count, self.string, self.max, self.b_nullable)
            else:
                type_.set_scs(self.size, self.count, self.string, self.max, self.b_nullable)

            # ポインタが指している先のデータ型を得る
            i = 0
            t2 = type_
            while i < ptr_level:
                t2 = t2.get_referto()
                while isinstance(t2, DefinedType):
                    t2 = t2.get_original_type()
                i += 1

            # const 修飾が適切かチェック
            if self.direction == "IN":
                if not t2.is_const():
                    self.cdl_error("S2015 '$1' must be const for \'in\' parameter $2",
                                   self.get_name(), type_.__class__.__name__)
            else:
                if t2.is_const() and Signature.get_current().is_deviate() is False:
                    self.cdl_error("S2016 '$1' can not be const for $2 parameter",
                                   self.get_name(), self.direction)
        else:
            # 非ポインタタイプ
            if self.size is not None or self.count is not None or self.string is not None \
                    or self.max is not None or self.b_nullable:
                type_.set_scs(self.size, self.count, self.string, self.max, self.b_nullable)

    def check_struct_tag(self, kind):
        self.declarator.get_type().check_struct_tag("PARAMETER")

    def get_name(self):
        return self.declarator.get_name()

    def get_size(self):
        return self.size

    def get_count(self):
        return self.count

    def get_string(self):
        return self.string

    def get_max(self):
        return self.max

    def clear_max(self):
        self.max = None
        self.declarator.get_type().clear_max()

    def is_nullable(self):
        return self.b_nullable

    def get_type(self):
        return self.declarator.get_type()

    def get_direction(self):
        return self.direction

    def get_declarator(self):
        return self.declarator

    def get_allocator(self):
        return self.allocator

    def referenced(self):
        self.b_ref = True

    def is_referenced(self):
        return self.b_ref

    #=== PPAllocator が必要か
    # Transparent RPC の場合 in で size_is, count_is, string のいずれかが指定されている場合 oneway では PPAllocator が必要
    # Transparent PC で oneway かどうかは、ここでは判断しないので別途判断が必要
    # Opaque RPC の場合 size_is, count_is, string のいずれかが指定されている場合、PPAllocator が必要
    def need_PPAllocator(self, b_opaque=False):
        from tecslib.core.types import PtrType

        if not b_opaque:
            if self.direction == "IN" and isinstance(
                    self.declarator.get_type().get_original_type(), PtrType):
                return True
        else:
            if self.direction in ("IN", "OUT", "INOUT") and isinstance(
                    self.declarator.get_type().get_original_type(), PtrType):
                return True
        return False

    def show_tree(self, indent):
        print("  " * indent, end="")
        print("ParamDecl: direction: {} {}".format(self.direction, self.locale_str()))
        self.declarator.show_tree(indent + 1)
        if self.size:
            print("  " * (indent + 1), end="")
            print("size:")
            self.size.show_tree(indent + 2)
        if self.count:
            print("  " * (indent + 1), end="")
            print("count:")
            self.count.show_tree(indent + 2)
        if self.string:
            print("  " * (indent + 1), end="")
            print("string:")
            if self.string == -1:
                print("  " * (indent + 2), end="")
                print("size is not specified")
            else:
                self.string.show_tree(indent + 2)
        if self.allocator:
            print("  " * (indent + 1), end="")
            print("allocator: signature: {}".format(self.allocator.get_name()))
