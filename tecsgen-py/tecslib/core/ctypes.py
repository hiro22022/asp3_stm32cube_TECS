# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/ctypes.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

from tecslib.core.types import (
    ArrayType,
    BoolType,
    DefinedType,
    EnumType,
    FloatType,
    FuncType,
    IntType,
    PtrType,
    StructType,
    VoidType,
)
from tecslib.rubylib.symbol import Sym


# CType は C_parser で定義される型を扱う CIntType, CFloatType などに include するもの
# CIntType は IntType を継承するなど、C の型では TECS の型を継承する
class CType:

    #=== 構文要素 type_specifier が複数指定されている場合に merge する
    # merge は const(CIntType) unsigned(CIntTtype), long(CIntType), などと他の型をマージする
    # const, unsigned, long などは、単体で int (CIntType) 型になりうる
    #
    # mikan C の文法を厳密にはチェックしていない  long struct 等もできてしまう
    def merge(self, another):

        # p "self: #{self.class} kind_of( IntType ): #{self.kind_of?( IntType )}  another: #{another.class}"

        # signed, unsigned が Symbol として来る事は無くなった
        # if another.instance_of? Symbol then
        #   # ここで Symbol は :SIGNED, :UNSIGNED のいずれか
        #
        #   # CIntType か？
        #   if self.instance_of? CIntType then
        #     self.set_sign another
        #     return self
        #   else
        #     cdl_error( "C1001 $1: mismatch, suitable for int types" , another )
        #     return self
        #   end
        # elsif self.instance_of?( CIntType ) && another.instance_of?( CIntType )then
        if type(self) is CIntType and type(another) is CIntType:
            if another.get_bit_size() != -3:
                if self.bit_size == -4 and another.get_bit_size() == -4:
                    self.bit_size = -5  # long long
                else:
                    # self は int 型、another の bit_size が (int 以外であれば)そちらにする
                    # mikan 上記以外で 両方 -3 でなければ、本来エラー
                    self.bit_size = another.get_bit_size()

            if another.get_sign():
                # another で sign が指定されていれば、そちらのものを採用する mikan 矛盾のチェック
                self.sign = another.get_sign()

#      if another.get_qualifier then
#        # another で qualifier が指定されていれば、そちらのものを採用する mikan 矛盾のチェック
#        @qualifier = another.get_qualifier
#      end
            if another.is_const():
                self.b_const = True
            if another.is_volatile():
                self.b_volatile = True

            return self
        elif type(self) is CIntType:
            return another.merge(self)
        elif type(self) is CDefinedType:
            # mikan unsigned などとの merge の不正検出
            if another.is_const():
                self.b_const = True
            if another.is_volatile():
                self.b_volatile = True

#      if self.get_type.get_type_str == another.get_type_str &&
#          self.get_type.get_type_str_post == another.get_type_str_post
#        # p "typedef #{another.get_type_str} #{self.get_type_str}#{another.get_type_str_post} ;"
#      else
#        cdl_error( "C1002 $1 not compatible with previous one $2" , self.get_type_str, another.get_type_str )
#      end
            return self
        elif type(self) is CStructType:
            if another.is_const():
                self.b_const = True
            if another.is_volatile():
                self.b_volatile = True
            return self
        elif type(self) is CFloatType:
            # mikan long double
            #   TECS には long double を表現する手段がない (double80_t を定義すればよいか?)
#      cdl_warning( "C1003 $1 & $2 incompatible (\'long double\' is not supported.). Treated as $3." , self.class, another.class, self.class )
#      cdl_warning( "W9999 $1 & $2 incompatible (\'long double\' is not supported.). Treated as $3." , self.get_type_str, another.get_type_str, self.get_type_str )
            self.to_long()
            return self
        elif type(self) is CVoidType:
            if another.is_const():
                self.b_const = True
            if another.is_volatile():
                self.b_volatile = True
            return self
        else:
            raise Exception("merge: unknown type {}".format(self.__class__.__name__))

    #=== qualifier を設定する
    #     元の Type クラスでは矛盾チェックしない（TECSの本来の文法では重複指定できないため）
    def set_qualifier(self, qual):

        if self.qualifier:
            self.cdl_error("C1004 $1: qualifier redefined. previous one: $2", qual, self.qualifier)
        super().set_qualifier(qual)


class CDefinedType(CType, DefinedType):

    def __init__(self, type_name):
        super().__init__(type_name)
        # サイズが明瞭の C 言語の型について、TECS CDL の組込み型と同等に扱う
        if type_name == Sym("int8_t"):
            self.type = IntType(8)
        elif type_name == Sym("int16_t"):
            self.type = IntType(16)
        elif type_name == Sym("int32_t"):
            self.type = IntType(32)
        elif type_name == Sym("int64_t"):
            self.type = IntType(64)
        elif type_name == Sym("int128_t"):
            self.type = IntType(128)
        elif type_name == Sym("uint8_t"):
            self.type = IntType(8)
            self.type.set_sign("UNSIGNED", True)
        elif type_name == Sym("uint16_t"):
            self.type = IntType(16)
            self.type.set_sign("UNSIGNED", True)
        elif type_name == Sym("uint32_t"):
            self.type = IntType(32)
            self.type.set_sign("UNSIGNED", True)
        elif type_name == Sym("uint64_t"):
            self.type = IntType(64)
            self.type.set_sign("UNSIGNED", True)
        elif type_name == Sym("uint128_t"):
            self.type = IntType(128)
            self.type.set_sign("UNSIGNED", True)


class CVoidType(CType, VoidType):

    pass


class CBoolType(CType, BoolType):

    pass


class CIntType(CType, IntType):

    def __init__(self, bit_size):
        # p super.class   mikan super.class が Symbol だ、なぜ？
        super().__init__(bit_size)

    def set_sign(self, sign, b_uint=False):
        super().set_sign(sign, b_uint)
        # p "CInt: set_sign: #{get_type_str} #{sign}"


class CFloatType(CType, FloatType):

    def __init__(self, bit_size):
        super().__init__(bit_size)

    def to_long(self):
        if self.bit_size != -64:
            self.cdl_warning("W9999 long specified for $1", self.get_type_str())
        else:
            self.bit_size = -128  # @bit_size = -128 : long double


class CEnumType(CType, EnumType):  # mikan

    def __init__(self, bit_size):
        super().__init__(bit_size)


class CStructType(CType, StructType):

    def __init__(self, tag=None):
        super().__init__(tag)


class CFuncType(CType, FuncType):

    def __init__(self, paramlist=None):
        super().__init__(paramlist)


class CArrayType(CType, ArrayType):

    def __init__(self, subscript=None):
        super().__init__(subscript)


class CPtrType(CType, PtrType):

    def __init__(self, referto=None):
        super().__init__(referto)
