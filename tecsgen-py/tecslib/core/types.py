# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/types.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

import copy
import sys

from tecslib.core import globals as G
from tecslib.core.syntaxobj.node import Node
from tecslib.core.toplevel import dbgPrint
from tecslib.rubylib.rb import to_s
from tecslib.rubylib.symbol import Sym


#= HasType: @type を内部に持つ型のためのモジュール
#  @b_cloned::Bool  : true if @type is cloned
#
# このモジュールは DefinedType, PtrType, ArrayType に include される
# 本当は typedef された時の Decl の要素のみ clone すればよいのだが、get_type, get_original_type で
# 取り出されたとき、set_scs, set_qualifier されたときに無条件で clone する (無駄にメモリを使用する)
# ただし、clone するのは一回のみである (二回 clone すると別の型を参照してしまう)
#
# initialize で clone しても、共有されているときに clone されない
#
class HasType:
    def initHasType(self):
        self.b_cloned = False

    #=== HasType# @type をクローンする
    def clone_type(self):
        #    if @b_cloned == false then
        self.type = copy.copy(self.type)
        self.b_cloned = True
        #    end


class Type(Node):
    # @b_const    : bool
    # @b_volatile : bool

    # Ruby では未初期化のインスタンス変数を nil として参照できる．Type#initialize は
    # これらを設定しないため、クラス属性を既定値として置く
    # (@qualifier は CType#set_qualifier が設定し、show_tree が参照する)
    b_const = None
    b_volatile = None
    qualifier = None

    def __init__(self):
        super().__init__()

    def set_qualifier(self, qualifier):
        if qualifier == "CONST":
            #      if @b_const then
            #        cdl_error( "T1001 const duplicate"  )
            #      end
            self.b_const = True
        elif qualifier == "VOLATILE":
            #      if @b_volatile then
            #        cdl_error( "T1002 volatile duplicate"  )
            #      end
            self.b_volatile = True
        else:
            raise Exception("Unknown qualifier {}".format(qualifier))

    def is_const(self):
        if self.b_const:
            return True
        else:
            return False

    def is_volatile(self):
        if self.b_volatile:
            return True
        else:
            return False

    def is_void(self):
        if isinstance(self, DefinedType):
            return self.type.is_void()
        elif isinstance(self, VoidType):
            return True
        else:
            return False

    #=== size_is, count_is, string を設定
    # 派生クラスでオーバーライドする（デフォルトではエラー）
    def set_scs(self, size, count, string, max_=None, b_nullable=False):
        str_ = ""
        delim = ""
        if size:
            str_ = "size_is"
            delim = ", "
        if count:
            str_ = "{}{}count_is".format(str_, delim)
            delim = ", "
        if string:
            str_ = "{}{}string".format(str_, delim)
            delim = ", "
        if b_nullable:
            str_ = "{}{}nullable".format(str_, delim)
            delim = ", "
        self.cdl_error("T1003 $1: unsuitable specifier for $2", str_, self.__class__.__name__)

    def clear_max(self):
        raise Exception("clear_max called: {}".format(self.__class__.__name__))

    def get_type_str(self):
        str_ = ""
        if self.b_const:
            str_ = "{}const ".format(str_)
        if self.b_volatile:
            str_ = "{}volatile ".format(str_)
        return str_

    #=== 型をチェック
    #    正当な型定義かどうか、チェックする
    def check(self):
        # 型に誤りがあれば、エラー文字列を返す
        return None

    #=== struct の tag をチェック
    #    正当な型定義かどうか、チェックする
    #kind:: Decl の @kind を参照
    def check_struct_tag(self, kind):
        # tag が存在しなければエラーを出力する
        # 配列型では、要素の型を再帰的にチェック
        # ポインタ型では、指す先の tag チェックはしない
        # 関数型ではパラメータリストのすべてについて行う
        pass

    #===  初期化可能かチェック
    #     attribute など初期化可能かチェックする（型に対し正当な初期化子が与えられているか）
    #ident::        string                被代入変数命
    #initialize::   Expression, Array of initializer or C_EXP
    #               代入値、C_EXP が与えられるのは IntType の場合のみ
    #kind::         symbol (:ATTRIBUTE, :VAR, :CONSTNAT )
    #attribute::    NameList              kind == :VAR のとき参照できる attribute
    #
    #     locale を第一引数として取るのは、以下の理由による。
    #     このメソッドは、変数への代入が行われる「行」に対して呼び出されるが、
    #     Type クラスのインスタンスは、変数が定義された「行」を記憶している。
    #
    # STAGE: S
    def check_init(self, locale, ident, initializer, kind, attribute=None):
        #
        pass

    #=== const_val を指定の型にキャストする
    # 派生クラスでオーバーライドしていないとエラー
    def cast(self, const_val):
        self.cdl_error("T1004 cannot cast to $1", self.__class__.__name__)

    #=== 型が一致するかのチェック
    # 型名の字面でチェック．
    # typedef された型も字面で一致を見るため、元の型が同じでも型名が異なれば不一致となる
    def equal(self, type2):
        return (self.get_type_str() == type2.get_type_str()) and \
               (self.get_type_str_post() == type2.get_type_str_post())

    #=== bit size を得る
    # IntType, FloatType 以外は0
    def get_bit_size(self):
        return 0

    #=== 元の型を得る
    # typedef された型の場合、その元の型を返す.
    # それ以外は、自分自身を返す．
    # (DefinedType では本メソッドがオーバーライドされる)
    def get_original_type(self):
        return self

    #=== 内部にポインタ型を持つ
    # ポインタ型、またはポインタ型メンバを持つ構造体、または要素がポインタ型を持つ配列
    def has_pointer(self):
        return False

    #=== size_is, count_is, string 指定されたポインタを持つか
    # size_is, count_is, string 指定されたポインタ型、またはそれをメンバに持つ構造体、またはそれをを要素に持つ配列
    def has_sized_pointer(self):
        return False

    #=== 長さ指定のない string を持つ
    # なさ指定のない string 指定されたポインタ型、またはそれをメンバに持つ構造体、またはそれを要素に持つ配列
    def has_unsized_string(self):
        return False

    def show_tree(self, indent):
        print("  " * indent, end="")
        print("const={} volatile={} {}".format(
            to_s(self.b_const), to_s(self.b_volatile), self.locale_str()))
        print("  " * indent, end="")
        print("has_pointer={} has_sized_pointer={} has_unsized_string={}".format(
            to_s(self.has_pointer()), to_s(self.has_sized_pointer()),
            to_s(self.has_unsized_string())))


class DefinedType(Type, HasType):
    #  @type_name::string
    #  @typedef::Typedef
    #  @type:: kind_of Type

    def __init__(self, type_name):
        from tecslib.core.componentobj.namespace import Namespace
        from tecslib.core.syntaxobj.typedef import Typedef

        super().__init__()
        self.type_name = type_name

        # mikan type_name が path になっていないため暫定
        self.typedef = Namespace.find([type_name])  #1

        #    if @type.class != Typedef then
        #      raise NotTypedef
        #    end
        if self.typedef is None:
            self.cdl_error("T1005 \'$1\' not defined", type_name)
        elif type(self.typedef) is not Typedef:
            self.cdl_error("T1006 \'$1\' not type name. expecting type name here", type_name)
        self.type = self.typedef.get_declarator().get_type()
        self.initHasType()

    def get_type(self):
        self.clone_type()
        return self.type

    def get_type_str(self):
        return "{}{}".format(super().get_type_str(), self.type_name)

    def get_type_str_post(self):
        return ""

    def get_size(self):
        return self.type.get_size()

    def is_nullable(self):
        return self.type.is_nullable()

    #=== qualifier(const, volatile) の設定
    def set_qualifier(self, qualifier):
        self.clone_type()
        self.type.set_qualifier(qualifier)
        super().set_qualifier(qualifier)

    def set_scs(self, size, count, string, max_=None, b_nullable=False):
        self.clone_type()
        self.type.set_scs(size, count, string, max_, b_nullable)

    def clear_max(self):
        self.type.clear_max()

    def get_original_type(self):
        self.clone_type()
        return self.type.get_original_type()

    def check(self):    # 意味的誤りがあれば、文字列を返す
        return None     # typedef の段階で意味チェックされている

    def check_init(self, locale, ident, initializer, kind, attribute=None):
        self.get_type().check_init(locale, ident, initializer, kind, attribute)

    #=== 内部にポインタ型を持つ
    # ポインタ型、またはポインタ型メンバを持つ構造体、または要素がポインタ型を持つ配列
    def has_pointer(self):
        return self.type.has_pointer()

    #=== size_is, count_is, string 指定されたポインタを持つか
    # size_is, count_is, string 指定されたポインタ型、またはそれをメンバに持つ構造体、またはそれをを要素に持つ配列
    def has_sized_pointer(self):
        return self.type.has_sized_pointer()

    #=== 長さ指定のない string を持つ
    # なさ指定のない string 指定されたポインタ型、またはそれをメンバに持つ構造体、またはそれを要素に持つ配列
    def has_unsized_string(self):
        return self.type.has_unsized_string()

    def show_tree(self, indent):
        print("  " * indent, end="")
        if self.typedef is None:
            print("DefinedType: {} is missing, const={} volatile={} {}".format(
                self.type_name, to_s(self.b_const), to_s(self.b_volatile), self.locale_str()))
        else:
            print("DefinedType: {}, const={} volatile={}".format(
                self.type_name, to_s(self.b_const), to_s(self.b_volatile)))
        super().show_tree(indent + 1)
        self.typedef.show_tree(indent + 1)
        self.type.show_tree(indent + 1)


class VoidType(Type):

    def check(self):    # 意味的誤りがあれば、文字列を返す
        return None

    def check_init(self, locale, ident, initializer, kind, attribute=None):
        self.cdl_error2(locale, "T1007 $1: void type variable cannot have initializer", ident)

    def get_type_str(self):
        return "{}void".format(super().get_type_str())

    def get_type_str_post(self):
        return ""

    def show_tree(self, indent):
        print("  " * indent, end="")
        print("VoidType {}".format(self.locale_str()))
        super().show_tree(indent + 1)


class BoolType(Type):

    def check(self):    # 意味的誤りがあれば、文字列を返す
        return None

    def get_type_str(self):
        return "{}bool_t".format(super().get_type_str())

    def get_type_str_post(self):
        return ""

    def show_tree(self, indent):
        print("  " * indent, end="")
        print("BoolType {}".format(self.locale_str()))
        super().show_tree(indent + 1)


class IntType(Type):
    #  @bit_size::		-11: char, -1: char_t, -2: short, -3: int, -4: long, -5: long long
    #			8, 16, 32, 64, 128
    #  @sign::		:SIGNED, :UNSIGNED, nil

    def __init__(self, bit_size):
        super().__init__()
        self.bit_size = bit_size
        self.sign = None

    def set_sign(self, sign, b_uint=False):
        if self.sign:
            if self.sign != sign:
                self.cdl_error("T1008 ambigous signed or unsigned")
        elif b_uint is False and self.bit_size > 0:
            if sign == "SIGNED":
                self.cdl_warning("W2001 signed int$1_t: obsolete. use int$2_t",
                                 self.bit_size, self.bit_size)
            else:
                self.cdl_warning("W2002 unsinged int$1_t: obsolete. use uint$2_t",
                                 self.bit_size, self.bit_size)

        self.sign = sign

        if self.sign != "SIGNED" and self.sign != "UNSIGNED":
            raise Exception("set_sign: unknown sign: {}".format(self.sign))

    def check(self):    # 意味的誤りがあれば、文字列を返す
        return None

    def check_init(self, locale, ident, initializer, kind, attribute=None):
        from tecslib.core.bnf import Token
        from tecslib.core.expression import C_EXP, Expression
        from tecslib.core.value import FloatVal, IntegerVal

        val = initializer  # C_EXP, Array
        if type(val) is Expression:
            val = val.eval_const2(None, attribute)
            # 評価の結果 C_EXP や Array となる可能性がある

        if type(val) is Token:    # StringVal 導入により、もはや Token は来ないはず
            # val が Token の場合 == の右辺が String だとエラーを起こす (#198)
            self.cdl_error2(locale, "T1009 $1: $2: not integer", ident, val)
            return
        elif isinstance(val, C_EXP):
            # #192 var が attribute を参照し、attribute の右辺が C_EXP の場合
            # const の右辺が C_EXP の場合も
            return
        elif isinstance(val, FloatVal):
            self.cdl_error2(locale, "T1011 $1: need cast to assign float to integer", ident)
            return
        elif type(val) is list:
            self.cdl_error2(locale, "T1017 $1: unsuitable initializer for scalar type", ident)
            return
        elif val is None:
            self.cdl_error2(locale, "T1010 $1: initializer is not constant", ident)
            return

        if not isinstance(val, IntegerVal):
            self.cdl_error2(locale, "T1012 $1: $2: not integer", ident, val)
            return

        val = val.to_i()
        max_ = self.get_max()
        min_ = self.get_min()
        dbgPrint("sign={} ident={} val={} max={} min={}\n".format(
            to_s(self.sign), to_s(ident), to_s(val), to_s(max_), to_s(min_)))

        if max_ is not None:
            if val > max_:
                if self.sign == "SIGNED" or self.sign is None:
                    self.cdl_error2(locale, "T1013 $1: too large (max=$2)", ident, max_)
                else:
                    self.cdl_error2(locale, "T1016 $1: too large (max=$2)", ident, max_)

        if min_ is not None:
            if val < min_:
                if self.sign == "SIGNED" or self.sign is None:
                    self.cdl_error2(locale, "T1014 $1: too large negative value (min=$2)", ident, min_)
                else:
                    self.cdl_error2(locale, "T1015 $1: negative value for unsigned", ident)

    #=== IntType# 最大値、最小値をチェックしてクリップする
    # キャスト演算を行う
    #in_val:: IntegerVal, FloatVal:  この型にキャストする値
    #from_type:: Symbol:  :IntType, :FloatType  IntType の場合はビット数でクリップ、FloatType の場合は最大値でクリップ
    def check_and_clip(self, in_val, from_type="IntType"):
        bit_size = self.get_bit_size()

        if bit_size == -1:
            bit_size = 8
        # Ruby の Numeric#to_i 相当（FloatVal.cast は @val=float を渡す）
        if hasattr(in_val, "to_i"):
            val = in_val.to_i()
        else:
            val = int(in_val)
        # Ruby では 0 も真であるため、get_max, get_min の真偽は nil かどうかで判定する
        if self.get_max() is not None and val > self.get_max():
            if from_type == "IntType":
                rval = ((1 << bit_size) - 1) & val   # bit 数でクリップ
            else:
                rval = self.get_max()                # 最大値でクリップ (FloatType)
            self.cdl_warning("W2003 $1: too large to cast to $2, clipped($3)",
                             in_val, self.get_type_str(), rval)
        elif self.get_min() is not None and val < self.get_min():
            if from_type == "IntType":
                rval = ((1 << bit_size) - 1) & val
                dbgPrint("check_and_clip: negative={} to unsigned={}  {} bit_size={}\n".format(
                    to_s(in_val), to_s(rval), (1 << bit_size) - 1, bit_size))
            else:
                rval = self.get_min()
            if self.sign == "SIGNED" or self.sign is None:
                self.cdl_warning("W2004 $1: too small to cast to $2, clipped($3)",
                                 in_val, self.get_type_str(), rval)
            else:    # @sign == :UNSIGNED || @sign == nil (char の場合)
                self.cdl_warning("W2005 $1: negative value for unsigned: convert to $2",
                                 in_val, rval)
        else:
            rval = val
        return rval

    def get_min(self):
        if self.sign == "SIGNED" or self.sign is None:
            if self.bit_size == -1:
                bit_sz = 8   # char_t は、有符号に扱う
            else:
                bit_sz = self.bit_size
            if bit_sz in (8, 16, 32, 64, 128):
                return -(1 << (bit_sz - 1))
            else:  # -1, -2, -3, -4, -5, -11
                return None
        else:   # @sign == :UNSIGNED
            return 0

    def get_max(self):
        if self.bit_size == -1:
            if self.sign is None:
                return 255   # char_t は、無符号に扱う
            else:
                bit_sz = 8
        else:
            bit_sz = self.bit_size
        if self.sign == "SIGNED" or self.sign is None:
            if bit_sz in (8, 16, 32, 64, 128):
                return (1 << (bit_sz - 1)) - 1
            else:  # -1, -2, -3, -4, -5, -11
                return None
        else:   # @sign == :UNSIGNED
            if bit_sz in (8, 16, 32, 64, 128):
                return (1 << bit_sz) - 1
            else:  # -2, -3, -4, -5, -11
                return None

    #=== IntType# C 言語における型名（修飾子付き）
    def get_type_str(self):
        str_ = super().get_type_str()

        # NEW_MODE
        if self.sign == "SIGNED":
            sign = ""
            signL = "signed "
        elif self.sign == "UNSIGNED":
            sign = "u"
            signL = "unsigned "
        else:
            sign = ""
            signL = ""

        # p "get_type_str: sign:#{@sign} signL=#{signL}"

        if self.bit_size == -1:        # char_t 型
            if self.sign == "SIGNED":
                sign = "s"
            str_ = "{}{}char_t".format(str_, sign)
        elif self.bit_size == -11:     # char 型(obsolete)
            str_ = "{}{}char".format(str_, signL)
        elif self.bit_size == -2:      # short 型
            str_ = "{}{}short".format(str_, signL)
        elif self.bit_size == -3:      # int 型
            str_ = "{}{}int".format(str_, signL)
        elif self.bit_size == -4:      # long 型
            str_ = "{}{}long".format(str_, signL)
        elif self.bit_size == -5:      # long long 型
            str_ = "{}{}long long".format(str_, signL)
        elif self.bit_size in (8, 16, 32, 64, 128):    # int16, int32, int64, int128 型
            str_ = "{}{}int{}_t".format(str_, sign, self.bit_size)

        return str_

    #=== IntType# C 言語における型名（後置文字列）
    def get_type_str_post(self):
        return ""

    #=== IntType#bit_size を得る
    #    返される値は @bit_size の仕様を参照
    def get_bit_size(self):
        return self.bit_size

    #=== IntType# sign を得る
    # @sign の説明を参照
    def get_sign(self):
        return self.sign

    def show_tree(self, indent):
        print("  " * indent, end="")
        print("{} bit_size={} sign={} const={} volatile={} {}".format(
            self.__class__.__name__, to_s(self.bit_size), to_s(self.sign),
            to_s(self.b_const), to_s(self.b_volatile), self.locale_str()))
        super().show_tree(indent + 1)


class FloatType(Type):
    #  @bit_size::         32, 64, (80), -32, -64, -128

    def __init__(self, bit_size):
        super().__init__()
        self.bit_size = bit_size

    def check(self):    # 意味的誤りがあれば、文字列を返す
        return None

    # mikan Float 型の C_EXP 対応 (generate.rb にも変更必要)
    def check_init(self, locale, ident, initializer, kind, attribute=None):
        from tecslib.core.bnf import Token
        from tecslib.core.expression import C_EXP, Expression
        from tecslib.core.value import FloatVal, IntegerVal

        # 型に対する初期値に誤りがあれば、エラー文字列を返す
        val = initializer
        if type(val) is Expression:
            val = val.eval_const2(None, attribute)
            # 評価の結果 C_EXP や Array となる可能性がある

        if type(val) is Token:
            # val が Token の場合 == の右辺が String だとエラーを起こす
            self.cdl_error2(locale, "T1018 $1: $2: not number", ident, val)
            return
        elif type(val) is list:
            self.cdl_error2(locale, "T1020 $1: unsuitable initializer for scalar type", ident)
            return
        elif type(val) is C_EXP:
            return
        elif val is None:
            self.cdl_error2(locale, "T1019 $1: initializer is not constant", ident)
            return
        elif not isinstance(val, IntegerVal) and not isinstance(val, FloatVal):
            self.cdl_error2(locale, "T1037 $1: not number", ident)
            return
        # else
        #   cdl_error2( locale, "T1020 $1: unsuitable initializer for scalar type" , ident )
        #   return
        # end
        return

    def get_type_str(self):
        str_ = super().get_type_str()

        if self.bit_size == 32:
            str_ = "{}float32_t".format(str_)
        elif self.bit_size == 64:
            str_ = "{}double64_t".format(str_)
        elif self.bit_size == -32:
            str_ = "{}float".format(str_)
        elif self.bit_size == -64:
            str_ = "{}double".format(str_)
        elif self.bit_size == -128:
            str_ = "{}long double".format(str_)
        return str_

    def get_type_str_post(self):
        return ""

    def get_bit_size(self):
        return self.bit_size

    def show_tree(self, indent):
        print("  " * indent, end="")
        print("FloatType bit_size={} qualifier={} {}".format(
            to_s(self.bit_size), to_s(self.qualifier), self.locale_str()))
        super().show_tree(indent + 1)


class EnumType(Type):  # mikan
    #  @bit_size::		-1: enum
    #			8, 16, 32, 64, 128
    #  @element::		[]
    #  @element_val::	[]

    def __init__(self, bit_size):
        super().__init__()
        self.bit_size = bit_size

    def check(self):
        # mikan enum check
        pass

    def show_tree(self, indent):
        print("  " * indent, end="")
        print("EnumType bit_size={} qualifier={} {}".format(
            to_s(self.bit_size), to_s(self.qualifier), self.locale_str()))
        super().show_tree(indent + 1)
        # mikan element


class StructType(Type):
    #  @tag::
    #  @b_define::  true if define, false if refer
    #  @members_decl:: NamedList
    #  @definition:: StructType
    #  @b_has_pointer_member:: bool : メンバにポインタ型がある
    #  @b_has_sized_pointer_member:: bool : メンバにポインタ型がある
    #  @b_has_unsized_string_member:: bool : メンバにポインタ型がある
    #  @b_hasTag:: bool : タグがある
    #  @member_types_symbol:: Symbol : tag が無い時のみ設定 (それ以外では nil)

    structtype_current_stack = []
    structtype_current_sp = -1

    # tag なし struct
    no_struct_tag_num = 0
    no_tag_struct_list = {}

    def __init__(self, tag=None):
        super().__init__()
        self.tag = tag
        if tag:
            self.b_hasTag = True
        else:
            self.b_hasTag = False
        StructType.structtype_current_sp += 1
        # Ruby の配列は範囲外への代入で自動的に伸長する
        while len(StructType.structtype_current_stack) <= StructType.structtype_current_sp:
            StructType.structtype_current_stack.append(None)
        StructType.structtype_current_stack[StructType.structtype_current_sp] = self
        self.b_has_pointer_member = False
        self.b_has_sized_pointer_member = False
        self.b_has_unsized_string_member = False
        self.member_types_symbol = None
        # 以下は Ruby では未初期化 (nil)。set_define にて設定される
        self.b_define = None
        self.members_decl = None
        self.definition = None

    @classmethod
    def set_define(cls, b_define):
        StructType.structtype_current_stack[
            StructType.structtype_current_sp].set_define_inst(b_define)

    def set_define_inst(self, b_define):
        from tecslib.core.componentobj.namespace import Namespace
        from tecslib.core.syntaxobj.namedlist import NamedList

        self.b_define = b_define
        if self.b_define:
            self.members_decl = NamedList(None, "in struct {}".format(to_s(self.tag)))
            # if @tag then    登録タイミングを終わりに変更 V1.0.2.19
            #  Namespace.new_structtype( self )
            # end
        else:
            self.definition = Namespace.find_tag(self.tag)
            # check_struct_tag に移す V1.0.2.19
            # if @definition == nil then
            #  cdl_error( "T1021 \'$1\': struct not defined" , @tag )
            # end

    @classmethod
    def new_member(cls, member_decl):
        StructType.structtype_current_stack[
            StructType.structtype_current_sp].new_member_inst(member_decl)

    def new_member_inst(self, member_decl):
        member_decl.set_owner(self)   # Decl (StructType)
        self.members_decl.add_item(member_decl)
        if member_decl.get_type().has_pointer():
            self.b_has_pointer_member = True
        if member_decl.get_type().has_sized_pointer():
            self.b_has_sized_pointer_member = True
        if member_decl.get_type().has_unsized_string():
            self.b_has_unsized_string_member = True

    def check(self):    # 意味的誤りがあれば、文字列を返す
        return None

    #=== 構造体のタグをチェック
    #  declarator の時点でチェックする
    #kind:: Decl の @kind を参照
    def check_struct_tag(self, kind):
        from tecslib.core.componentobj.namespace import Namespace

        if self.tag is None:
            return

        st = Namespace.find_tag(self.tag)
        if st is None:
            self.cdl_error("T1022 struct $1: not defined", self.tag)

    # mikan Float 型の C_EXP 対応 (generate.rb にも変更必要)
    def check_init(self, locale, ident, initializer, kind, attribute=None):
        from tecslib.core.componentobj.namespace import Namespace
        from tecslib.core.expression import C_EXP, Expression

        st = Namespace.find_tag(self.tag)
        if st is None:
            self.cdl_error2(locale, "T1023 struct $1: not defined", self.tag)
            return

        # 初期化子が式の場合、型（タグ）が一致するかチェック
        if type(initializer) is Expression:
            t = initializer.get_type(attribute)
            # print "Check init #{t.class} #{t.get_name}\n"
            if not isinstance(t, StructType):
                if t:
                    str_ = t.get_type_str()
                else:
                    str_ = "unknown"
                self.cdl_error2(locale, "T1038 $1: initializer type mismatch. '$2' & '$3'",
                                ident, self.get_type_str(), str_)
            elif self.tag != t.get_name():
                self.cdl_error2(locale, "T1039 $1: struct tag mismatch $2 and $3",
                                ident, self.tag, t.get_name())
            initializer = initializer.eval_const(attribute)

        if type(initializer) is list:
            i = 0
            for d in st.get_members_decl().get_items():
                # Ruby の Array は範囲外の添数に対し nil を返す
                if i < len(initializer) and initializer[i]:
                    d.get_type().check_init(
                        locale, "{}.{}".format(ident, d.get_identifier()), initializer[i], kind)
                i += 1
        elif type(initializer) is C_EXP:
            # C_EXP は 無常件に OK
            pass
        else:
            self.cdl_error2(locale, "T1024 $1: unsuitable initializer for struct", ident)

    @classmethod
    def end_of_parse(cls):
        StructType.structtype_current_stack[
            StructType.structtype_current_sp].end_of_parse_inst()
        StructType.structtype_current_sp -= 1

    def end_of_parse_inst(self):
        from tecslib.core.componentobj.namespace import Namespace

        if self.members_decl is None:   # @b_define = false またはメンバーのない構造体（エラー）
            return
        for md in self.members_decl.get_items():
            size = md.get_size_is()
            if size:
                val = size.eval_const(self.members_decl)
                if val is None:
                    type_ = size.get_type(self.members_decl)
                    if not isinstance(type_, IntType):
                        self.cdl_error("T1025 size_is argument is not integer type")
            count = md.get_count_is()
            if count:
                val = count.eval_const(self.members_decl)
                if val is None:
                    type_ = count.get_type(self.members_decl)
                    if not isinstance(type_, IntType):
                        self.cdl_error("T1026 count_is argument is not integer type")
            string = md.get_string()
            if string == -1:
                # 長さ指定なし
                pass
            elif string:
                val = string.eval_const(self.members_decl)
                if val is None:
                    type_ = string.get_type(self.members_decl)
                    if not isinstance(type_, IntType):
                        self.cdl_error("T1027 string argument is not integer type")

        if self.tag is None:
            self.member_types_symbol = self.get_member_types_symbol()
            # print "member_types_symbol = #{get_member_types_symbol}\n"
            if StructType.no_tag_struct_list.get(self.member_types_symbol):
                self.tag = StructType.no_tag_struct_list[self.member_types_symbol]
            else:
                self.tag = Sym("TAG_{}_TECS_internal__".format(StructType.no_struct_tag_num))
                StructType.no_struct_tag_num += 1
                StructType.no_tag_struct_list[self.member_types_symbol] = self.tag
                Namespace.new_structtype(self)
        else:
            if self.b_define:
                Namespace.new_structtype(self)

    def get_name(self):
        return self.tag

    def get_type_str(self):      # mikan struct get_type_str
        str_ = super().get_type_str()

        if self.b_hasTag:
            # typedef struct tag StructType; の形式の場合
            # struct の本体は、別に生成される
            return "{}struct {}".format(str_, to_s(self.tag))

        else:
            # typedef struct { int a; } StructType; の形式の場合
            str_ += "struct {"
            for i in self.members_decl.get_items():
                str_ += "%s %s%s;" % (to_s(i.get_type().get_type_str()),
                                      to_s(i.get_name()),
                                      to_s(i.get_type().get_type_str_post()))
            str_ += "} "

            return str_

    def get_type_str_post(self):
        return ""

    def get_members_decl(self):
        from tecslib.core.componentobj.namespace import Namespace
        from tecslib.core.syntaxobj.namedlist import NamedList

        if self.members_decl:
            return self.members_decl

        st = Namespace.find_tag(self.tag)
        if st:
            return st.get_members_decl()

        # 不完全型の場合。
        # import_C の中では構造体のメンバー定義がないものもありうる.
        # TECS CDL では、構造体メンバーを先に定義する必要があり、ここへは来ないはず。
        # return nil
        return NamedList(None, "in struct {}".format(to_s(self.tag)))

    def has_pointer(self):
        if self.definition:
            return self.definition.has_pointer()
        else:
            return self.b_has_pointer_member

    def has_sized_pointer(self):
        if self.definition:
            return self.definition.has_sized_pointer()
        else:
            return self.b_has_sized_pointer_member

    def has_unsized_string(self):
        if self.definition:
            return self.definition.has_unsized_string()
        else:
            return self.b_has_unsized_string_member

    #=== 同じ構造体かどうかチェックする
    # tag のチェックは行わない
    # すべてのメンバの名前と型が一致することを確認する
    def same(self, another):
        md = another.get_members_decl()
        if self.members_decl is None or md is None:
            return False

        md1 = self.members_decl.get_items()
        md2 = md.get_items()
        if len(md1) != len(md2):
            return False

        i = 0
        while i < len(md1):
            if md1[i].get_name() != md2[i].get_name() or \
                    md1[i].get_type().get_type_str() != md2[i].get_type().get_type_str() or \
                    md1[i].get_type().get_type_str_post() != md2[i].get_type().get_type_str_post():
                return False
            i += 1

        return True

    def get_member_types_symbol(self):
        mts = ''
        for member in self.members_decl.get_items():
            mts += member.get_type().get_type_str() + member.get_type().get_type_str_post() + ';'
        return Sym(mts)

    def show_tree(self, indent):
        print("  " * indent, end="")
        print("StructType tag: {} qualifier={} has_pointer={} {}".format(
            to_s(self.tag), to_s(self.qualifier), to_s(self.b_has_pointer_member),
            self.locale_str()))
        super().show_tree(indent + 1)
        if self.b_define:
            self.members_decl.show_tree(indent + 1)


class FuncType(Type):
    #  @paramlist::  ParamList
    #  @type:: return type : PtrType, ArrayType, FuncType, IntType, FloatType, ...
    #  @b_oneway:: bool: true, false
    #  @has_in:: bool :  has [in] parameter
    #  @has_inout:: bool : has [inout] parameter
    #  @has_out:: bool : has [out] parameter
    #  @has_send:: bool : has [send] parameter
    #  @has_receive:: bool : has [receive] parameter
    #
    # @has_in などは同名のメソッド has_in? があるため、Python では _has_in とする

    def __init__(self, paramlist=None):
        from tecslib.core.syntaxobj.paramlist import ParamList

        super().__init__()

        self.type = None        # Ruby では未初期化 (nil)。set_type にて設定される

        self._has_in = False
        self._has_inout = False
        self._has_out = False
        self._has_send = False
        self._has_receive = False

        self.paramlist = paramlist
        self.b_oneway = False
        if paramlist:
            paramlist.check_param()
        else:
            self.paramlist = ParamList(None)
        self.paramlist.set_owner(self)  # ParamList
        for p in self.paramlist.get_items():
            if p.get_direction() == "IN":
                self._has_in = True
            elif p.get_direction() == "INOUT":
                self._has_inout = True
            elif p.get_direction() == "OUT":
                self._has_out = True
            elif p.get_direction() == "SEND":
                self._has_send = True
            elif p.get_direction() == "RECEIVE":
                self._has_receive = True
            else:
                raise Exception("unkown direction")

    def check(self):    # 意味的誤りがあれば、文字列を返す
        if type(self.type) is ArrayType:    # 配列を返す関数
            return "function returning array"
        elif type(self.type) is FuncType:   # 関数を返す関数
            return "function returning function"
        return self.type.check()   # 関数の return する型のチェック

        # パラメータの型のチェックは ParamList#check_param で行う

    def check_struct_tag(self, kind):
        self.type.check_struct_tag(kind)
        # ParamDecl でもチェックされるので、ここではチェックしない
        # @paramlist.check_struct_tag kind

    def check_init(self, locale, ident, initializer, kind, attribute=None):
        self.cdl_error2(locale, "T1028 $1: cannot initialize function pointer", ident)
        return

    def set_type(self, type_):
        if not self.type:
            self.type = type_
        else:
            self.type.set_type(type_)

    #=== return type を返す
    #
    # return type を返す
    # get_return_type とすべきだった
    def get_type(self):
        return self.type

    def get_type_str(self):
        return self.type.get_type_str()

    def get_type_str_post(self):
        # 型だけを返す (仮引数の名前を含めない)
        return self.paramlist.to_str(False)

    def get_paramlist(self):
        return self.paramlist

    def set_oneway(self, b_oneway):
        self.b_oneway = b_oneway

        if (self.type.get_type_str() != "ER" and self.type.get_type_str() != "void") \
                or self.type.get_type_str_post() != "":
            self.cdl_error("T1029 oneway function cannot return type \'$1$2\', \'void\' or \'ER\' is permitted",
                           self.type.get_type_str(), self.type.get_type_str_post())

        if self.paramlist:
            for p in self.paramlist.get_items():
                if p.get_direction() != "IN" and p.get_direction() != "SEND":
                    self.cdl_error("T1030 oneway function cannot have $1 parameter for \'$2\'",
                                   p.get_direction(), p.get_name())

    def is_oneway(self):
        return self.b_oneway

    #=== Push Pop Allocator が必要か？
    # Transparent RPC の場合 oneway かつ in の配列(size_is, count_is, string のいずれかで修飾）がある
    def need_PPAllocator(self, b_opaque=False):
        if self.b_oneway or b_opaque:
            return self.paramlist.need_PPAllocator(b_opaque)
        else:
            return False

    #=== パラメータが in, inout, out, send, receive を持つか
    def has_in(self):
        return self._has_in

    def has_inout(self):
        return self._has_inout

    def has_out(self):
        return self._has_out

    def has_send(self):
        return self._has_send

    def has_receive(self):
        return self._has_receive

    #=== 入力方向のパラメータを持つか
    def has_inward(self):
        return self._has_in or self._has_inout or self._has_send

    #=== 出力方向のパラメータを持つか
    def has_outward(self):
        return self._has_inout or self._has_out or self._has_receive

    def show_tree(self, indent):
        print("  " * indent, end="")
        if self.b_oneway:
            print("FunctType:  oneway=true {}".format(self.locale_str()))
        else:
            print("FunctType:  oneway=false {}".format(self.locale_str()))
        super().show_tree(indent + 1)
        if self.paramlist:
            self.paramlist.show_tree(indent + 1)
        print("  " * (indent + 1), end="")
        print("return type:")
        self.type.show_tree(indent + 2)


class ArrayType(Type, HasType):
    #  @type:: element type :  ArrayType, FuncType, IntType, FloatType, ...
    #  @subscript:: Expression, nil if '[]'

    def __init__(self, subscript=None):
        super().__init__()
        self.type = None        # Ruby では未初期化 (nil)。set_type にて設定される
        self.subscript = subscript
        self.initHasType()

    def set_type(self, type_):
        if not self.type:
            self.type = type_
        else:
            self.type.set_type(type_)

    #=== Array#qualifier(const, volatile) の設定
    def set_qualifier(self, qualifier):
        self.clone_type()
        self.type.set_qualifier(qualifier)
        super().set_qualifier(qualifier)

    # 配列要素が const なら const
    def is_const(self):
        return self.type.is_const()

    # 配列要素が volatile なら volatile
    def is_volatile(self):
        return self.type.is_volatile()

    def get_type(self):
        return self.type

    def get_subscript(self):
        return self.subscript

    def get_type_str(self):
        return "{}".format(self.type.get_type_str())

    def get_type_str_post(self):
        if self.subscript:
            return "[{}]{}".format(to_s(self.subscript.eval_const(None)),
                                   self.type.get_type_str_post())
        else:
            return "[]{}".format(self.type.get_type_str_post())
        # "[#{@subscript.to_s}]#{@type.get_type_str_post}"

    def check(self):    # 意味的誤りがあれば、文字列を返す
        if type(self.type) is FuncType:         # 関数の配列
            return "array of function"
        elif type(self.type) is ArrayType:      # 添数なし配列の配列
            if not self.type.get_subscript():
                return "subscript not specified"

        return self.type.check()    # 配列要素の型をチェック

    def check_struct_tag(self, kind):
        self.type.check_struct_tag(kind)

    def check_init(self, locale, ident, initializer, kind, attribute=None):
        if type(initializer) is list:
            # 要素数が指定されている場合、初期化要素数をチェック
            if self.subscript:
                n_sub = self.subscript.eval_const(None)
                if n_sub is not None:   # Ruby では 0 も真
                    if len(initializer) > n_sub:
                        self.cdl_error2(locale, "T9999 $1: too many initializer, $2 for $3",
                                        ident, len(initializer), n_sub)
            index = 0
            for i in initializer:
                attribute = None    # Ruby 版は引数の位置で attribute = nil と代入している
                self.type.check_init(locale, "{}[{}]".format(ident, index), i, kind, attribute)
                index += 1
        else:
            self.cdl_error2(locale, "T1031 $1: unsuitable initializer for array", ident)

    def has_pointer(self):
        return self.type.has_pointer()

    def has_sized_pointer(self):
        return self.type.has_sized_pointer()

    def has_unsized_string(self):
        return self.type.has_unsized_string()

    def show_tree(self, indent):
        print("  " * indent, end="")
        print("ArrayType: {}".format(self.locale_str()))
        super().show_tree(indent + 1)
        print("  " * (indent + 1), end="")
        print("type:")
        self.type.show_tree(indent + 2)
        print("  " * (indent + 1), end="")
        print("subscript:")
        if self.subscript:
            self.subscript.show_tree(indent + 2)
        else:
            print("  " * (indent + 2), end="")
            print("no subscript")


class PtrType(Type, HasType):
    #  @type:: refer to : PtrType, FuncType, ArrayType, IntType, FloatType, ...
    #  @size:: Expr, or nil if not specified
    #  @count:: Expr, or nil if not specified
    #  @string:: Expr or -1(if size not specified) （string 引数）, or nil if not specified

    def __init__(self, referto=None):
        super().__init__()
        self.type = referto
        self.size = None
        self.count = None
        self.string = None
        # 以下は Ruby では未初期化 (nil)。set_scs にて設定される
        self.max = None
        self.b_nullable = None
        self.initHasType()

    def set_type(self, type_):
        if not self.type:
            self.type = type_
        else:
            self.type.set_type(type_)   # 枝先の type を設定

    def get_type_str(self):
        if isinstance(self.type, ArrayType) or isinstance(self.type, FuncType):
            parenthes = "("
        else:
            parenthes = ""
        return "{}{}*".format(self.type.get_type_str(), parenthes)

    def get_type_str_post(self):
        if isinstance(self.type, ArrayType) or isinstance(self.type, FuncType):
            parenthes = ")"
        else:
            parenthes = ""
        return "{}{}".format(parenthes, self.type.get_type_str_post())

    def check(self):    # 意味的誤りがあれば、文字列を返す
        if self.type is None:
            return None
        return self.type.check()

    def check_struct_tag(self, kind):
        if kind != "MEMBER":  # 構造体メンバーの場合、ポインタの先の構造体タグをチェックしない
            self.type.check_struct_tag(kind)

    def check_init(self, locale, ident, initializer, kind, attribute=None):
        from tecslib.core.ctypes import CDefinedType
        from tecslib.core.expression import C_EXP, Expression
        from tecslib.core.value import IntegerVal, PointerVal, StringVal

        if type(initializer) is Expression:
            val = initializer.eval_const2(None, attribute)
            if isinstance(val, PointerVal):
                type_ = val.get_type()  # PtrType
                t1 = self
                t2 = type_
                while isinstance(t1, PtrType) and isinstance(t2, PtrType):
                    t1 = t1.get_type()
                    t2 = t2.get_type()
                    if (type(t1) is type(t2)) and (t1.get_bit_size() == t2.get_bit_size()):
                        pass
                    elif (isinstance(t1, CDefinedType) or isinstance(t2, CDefinedType)) \
                            and t1.get_type_str() == t2.get_type_str() \
                            and t1.get_type_str_post() is not None \
                            and t2.get_type_str_post() is not None:
                        # Ruby では "" も真であるため、get_type_str_post は nil かどうかで判定する
                        # int8_t などが、一方は .h に定義されているケース
                        pass
                    else:
                        self.cdl_error2(locale, "T1032 $1: incompatible pointer type", ident)
                        break
            elif isinstance(val, IntegerVal):
                if val.to_i() != 0:
                    self.cdl_error2(locale, "T1033 $1: need cast to assign integer to pointer", ident)
            elif isinstance(val, StringVal):
                # 文字列定数
                # mikan L"wide string"
                if self.type.get_bit_size() != -1 and self.type.get_bit_size() != -11:  # -1: char_t
                    self.cdl_error2(locale, "T1034 $1: unsuitable string constant", ident)
            elif type(val) is list:
                i = 0
                for ini in val:
                    attribute = None    # Ruby 版は引数の位置で attribute = nil と代入している
                    self.type.check_init(locale, "{}[{}]".format(ident, i), ini, kind, attribute)
                    i += 1
            elif type(val) is C_EXP:
                # tecsgen V1.8.RC11 から C_EXP も可とする
                pass
            else:
                self.cdl_error2(locale, "T1035 $1: unsuitable initializer for pointer", ident)
        elif type(initializer) is list:
            if self.size is None and self.count is None:
                self.cdl_error2(locale, "T9999 $1: non-size_is pointer cannot have array initializer",
                                ident)

            i = 0
            for ini in initializer:
                attribute = None    # Ruby 版は引数の位置で attribute = nil と代入している
                self.type.check_init(locale, "{}[{}]".format(ident, i), ini, kind, attribute)
                i += 1
        elif type(initializer) is C_EXP:
            pass

        else:
            self.cdl_error2(locale, "T1036 $1: unsuitable initializer for pointer", ident)

    def get_referto(self):
        self.clone_type()
        return self.type

    def set_scs(self, size, count, string, max_, b_nullable):
        self.size = size
        self.count = count
        self.max = max_
        self.b_nullable = b_nullable

        # string は最も左側の ptr に作用する
        if isinstance(self.type, PtrType):
            # ptr_level が 2 以上であることは ParamDecl#initializer でチェックされる
            self.clone_type()
            self.type.set_scs(None, None, string, None, False)
        elif isinstance(self.type, VoidType) and (size or count or string):
            str_ = ""
            if size:
                str_ = "size_is"
            if count:
                if str_ is not None:    # Ruby では "" も真であるため常に成立する
                    str_ += ", "
                str_ += "count_is"
            if string:
                if str_ is not None:    # Ruby では "" も真であるため常に成立する
                    str_ += ", "
                str_ += "string"

            self.cdl_error("T1040 $1 specified for void pointer type", str_)
        else:
            self.string = string

        if (self.size is not None) and (self.b_nullable is not False):
            self.cdl_error("T9999 size_is & nullable cannot be specified simultaneously. If size is zero, pointer must be null")

    def clear_max(self):
        self.max = None

    def get_size(self):
        return self.size

    def get_count(self):
        return self.count

    def get_string(self):
        return self.string

    #=== PtrType# size_is の最大値
    def get_max(self):
        return self.max

    def is_nullable(self):
        return self.b_nullable

    def get_type(self):
        self.clone_type()
        return self.type

    def has_pointer(self):
        return True

    def has_sized_pointer(self):
        from tecslib.core.expression import Expression
        return self.size is not None or self.count is not None \
            or type(self.string) is Expression or self.type.has_sized_pointer()

    def has_unsized_string(self):
        return self.string == -1 or self.type.has_unsized_string()

    def show_tree(self, indent):
        from tecslib.core.expression import Expression

        print("  " * indent, end="")
        print("PtrType: qualifier={}, nullable={} {}".format(
            to_s(self.qualifier), to_s(self.b_nullable), self.locale_str()))
        super().show_tree(indent + 1)
        print("  " * (indent + 1), end="")
        if self.size:
            print("size={}, ".format(to_s(self.size)), end="")
        else:
            print("size=nil, ", end="")
        if self.max:
            print("max={}, ".format(to_s(self.size)), end="")
        else:
            print("max=nil, ", end="")
        if self.count:
            print("count={}, ".format(to_s(self.count)), end="")
        else:
            print("count=nil, ", end="")
        if self.string:
            if type(self.string) is Expression:
                print("string={}\n".format(to_s(self.string)), end="")
            else:
                print("string=yes\n", end="")
        else:
            print("string=nil\n", end="")

        print("  " * (indent + 1), end="")
        print("type:")
        self.type.show_tree(indent + 2)


#==  DescriptorType クラス
# 動的結合で渡すデスクリプタ型
class DescriptorType(Type):
    # @sinagure_nsp::NamespacePath

    descriptors = {}

    def __init__(self, signature_nsp):
        # Ruby 版は super() を呼んでいないため Node#initialize が実行されず、
        # @locale は nil のままとなる
        self.locale = None
        self.signature_nsp = signature_nsp
        # check_signature ##
        DescriptorType.descriptors[self] = False

    def get_type_str(self):
        return "Descriptor( {} )".format(to_s(self.signature_nsp.get_global_name()))

    def get_type_str_post(self):
        return ""

    def set_qualifier(self, qualifier):
        # 注: Ruby 版は qualfier と綴りを誤っており、実行すると NameError となる
        self.cdl_error("T9999 '$1' cannot be specified for Descriptor", to_s(qualfier))  # noqa: F821

    def check(self):
        pass

    def check_init(self, locale, ident, initializer, kind, attribute=None):
        if kind == "PARAMETER":
            # 引数は初期化できない
            pass
        else:
            self.cdl_error2(locale, "T9999 Descriptor cannot be used for $1", kind)

    @classmethod
    def check_signature(cls):
        for desc, val in DescriptorType.descriptors.items():
            if val is not True:
                desc.check_signature_inst()
                DescriptorType.descriptors[desc] = True

    def check_signature_inst(self):
        from tecslib.core.componentobj.namespace import Namespace
        from tecslib.core.componentobj.signature import Signature

        # p "Desc #{@signature_nsp.to_s}"
        obj = Namespace.find(self.signature_nsp)
        if not isinstance(obj, Signature):
            self.cdl_error("T9999 '$1': not signature or not found", to_s(self.signature_nsp))
        else:
            if obj.has_descriptor():
                # cdl_error( "T9999 '$1': has Descriptor in function parameter", @signature_nsp.to_s )
                pass
            # @signature_nsp = obj.get_namespace_path

    #== DescriptorType#
    def get_signature(self):
        from tecslib.core.componentobj.namespace import Namespace
        return Namespace.find(self.signature_nsp)


# 以下単体テストコード
if G.unit_test:
    print("===== Unit Test: IntType ===== (types.rb)")
    sizes = [8, 16, 32, 64]
    for n in sizes:
        int_ = IntType(n)
        sys.stdout.write("%8s  max: %d  min:%d\n" % (
            "int{}_t".format(n), int_.get_max(), int_.get_min()))
    print("")
