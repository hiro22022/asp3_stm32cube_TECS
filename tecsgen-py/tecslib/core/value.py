# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/value.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

from tecslib.core.syntaxobj.node import Node
from tecslib.rubylib.rb import to_s


#= BaseVal 整数、浮動小数などの値を扱うクラスの基底クラス
#
# TECS の CDL で扱う値は、以下に分類される
# ・整数
# ・浮動小数
# ・文字列
# ・ブール値
# 集成型（構造体、配列）と C_EXP はここでは扱わない
#
# このクラスで定義済みの演算子は、エラーとなる
# 型により演算可能な場合、演算子をオーバーライドする
#
class BaseVal(Node):
    def __str__(self):
        # Ruby の "#{val}" / "%s" は to_s を呼ぶ
        return self.to_s()

    def __invert__(self):   # ~@
        self.unsupport("~")

    def __neg__(self):      # -@
        self.unsupport("unary -")

    def __pos__(self):      # +@
        self.unsupport("unary +")

    def not_(self):         # not # ! val
        self.unsupport("!")

    def __mul__(self, val):
        self.unsupport("*")

    def __truediv__(self, val):
        self.unsupport("/")

    def __mod__(self, val):
        self.unsupport("%")

    def __add__(self, val):
        self.unsupport("+")

    def __sub__(self, val):
        self.unsupport("-")

    def __lshift__(self, val):
        self.unsupport("<<")

    def __rshift__(self, val):
        self.unsupport(">>")

    def __gt__(self, val):
        self.unsupport(">")

    def __lt__(self, val):
        self.unsupport("<")

    def __ge__(self, val):
        self.unsupport(">=")

    def __le__(self, val):
        self.unsupport("<=")

    def eq(self, val):      # == val
        self.unsupport("==")

    def neq(self, val):     # != val
        self.unsupport("!=")

    def __and__(self, val):
        self.unsupport("&")

    def __xor__(self, val):
        self.unsupport("^")

    def __or__(self, val):
        self.unsupport("|")

    def lAND(self, val):    # && val
        self.unsupport("&&")

    def lOR(self, val):     # || val
        self.unsupport("||")

    def cast(self, type_):
        self.unsupport("CAST")

    def unsupport(self, op):
        self.cdl_error("V1001 $1: unable for $2", op, self.__class__)

    def to_s(self):
        raise Exception("to_s not overridden")

    def to_b(self):
        self.cdl_error("V1002 $1: cannot cast to bool (implicitly)", self.__class__)
        return False

    def to_i(self):
        self.cdl_error("V1003 $1: cannot cast to integer (implicitly)", self.__class__)
        return 1

    def to_f(self):
        self.cdl_error("V1004 $1: cannot cast to float (implicitly)", self.__class__)
        return 1.0


#= Pointer 値 (IntegerVal の Pointer 版)
#
# ポインタ値は、CDL で直接生成されることはない
# 整数値のキャスト演算により生成される
class PointerVal(BaseVal):
    # @int_val:: IntegerVal: IntegerVal でなくてはならない
    # @ptr_type:: PtrType: ポインタの指す先の型
    # Ruby 未初期化の @val (nil) を参照できるようにする
    val = None

    def __init__(self, int_val, ptr_type):
        super().__init__()
        self.int_val = int_val
        self.ptr_type = ptr_type

    # === ポインタの指す先の型を得る
    # PointerVal 専用のメソッド
    def get_type(self):
        return self.ptr_type

    def cast(self, type_):
        from tecslib.core.types import FloatType, IntType, PtrType

        t = type_.get_original_type()   # typedef の元を得る
        if isinstance(t, IntType):
            val = t.check_and_clip(self.int_val, "IntType")
            return IntegerVal(val)
        elif isinstance(t, FloatType):
            self.cdl_error("V1005 Cannot cast pointer to float")
            return FloatVal(self.int_val)
        elif isinstance(t, PtrType):
            return PointerVal(self.int_val, type_)
        else:
            self.cdl_error("V1006 pointer value cannot cast to $1", type_.__class__)
            return None

    def to_s(self):
        if isinstance(self.int_val, IntegerVal):
            n = self.int_val.val
        else:
            n = self.int_val
        return "({}{}){}".format(
            self.ptr_type.get_type_str(),
            self.ptr_type.get_type_str_post(),
            ("0x%X" % n))

    def to_b(self):
        self.cdl_error("V1007 convert pointer value to bool")
        return False

    def to_i(self):
        self.cdl_error("V1008 convert pointer value to integer without cast")
        # @val.to_i   # Ruby: 未初期化 @val は nil
        if self.val is None:
            return 0
        return self.val.to_i()


#= IntegerVal: 整数値を扱うクラス
class IntegerVal(BaseVal):
    # @val:: Integer: value
    # @str:: string: literal
    # @sign:: Symbol: :SIGNED | :UNSIGNED
    # @size:: Symbol: :NORMAL | :SHORT | :LONG | :LONGLONG

    def __init__(self, val, str_=None, sign="SIGNED", size="NORMAL"):
        super().__init__()
        if val is True or val is False:
            self.val = int(val)
        elif hasattr(val, "to_i"):
            self.val = val.to_i()
        else:
            self.val = int(val)
        self.str = str_
        self.sign = sign
        self.size = size

    def __invert__(self):   # ~@
        return IntegerVal(~self.val)

    def __neg__(self):      # -@
        return IntegerVal(-self.val)

    def __pos__(self):      # +@
        return self

    def not_(self):         # not # !
        return BoolVal(self.to_b())

    def __mul__(self, val):
        if isinstance(val, FloatVal):
            return FloatVal(self.val * val.to_f())
        else:
            return IntegerVal(self.val * val.to_i())

    def __truediv__(self, val):
        if isinstance(val, FloatVal):
            v2 = val.to_f()   # to_f を2回評価しない
            if v2 == 0.0:
                self.cdl_error("V1009 / : divieded by zero")
                return FloatVal(1.0)
            return FloatVal(float(self.val) / v2)
        else:
            v2 = val.to_i()   # to_i を2回評価しない
            if v2 == 0:
                self.cdl_error("V1010 / : divieded by zero")
                return IntegerVal(1)
            return IntegerVal(self.val // v2)

    def __mod__(self, val):
        if isinstance(val, FloatVal):
            v2 = val.to_f()   # to_f を2回評価しない
            if v2 == 0.0:
                self.cdl_error("V1011 % : divieded by zero")
                return FloatVal(1.0)
            return FloatVal(float(self.val) % v2)
        else:
            v2 = val.to_i()   # to_i を2回評価しない
            if v2 == 0:
                self.cdl_error("V1012 % : divieded by zero")
                return IntegerVal(1)
            return IntegerVal(self.val % v2)

    def __add__(self, val):
        if isinstance(val, FloatVal):
            return FloatVal(self.val + val.to_f())
        else:
            return IntegerVal(self.val + val.to_i())

    def __sub__(self, val):
        if isinstance(val, FloatVal):
            return FloatVal(self.val - val.to_f())
        else:
            return IntegerVal(self.val - val.to_i())

    def __lshift__(self, val):
        return IntegerVal(self.val << val.to_i())

    def __rshift__(self, val):
        return IntegerVal(self.val >> val.to_i())

    def __gt__(self, val):
        if isinstance(val, FloatVal):
            return BoolVal(self.val > val.to_f())
        else:
            return BoolVal(self.val > val.to_i())

    def __lt__(self, val):
        if isinstance(val, FloatVal):
            return BoolVal(self.val < val.to_f())
        else:
            return BoolVal(self.val < val.to_i())

    def __ge__(self, val):
        if isinstance(val, FloatVal):
            return BoolVal(self.val >= val.to_f())
        else:
            return BoolVal(self.val >= val.to_i())

    def __le__(self, val):
        if isinstance(val, FloatVal):
            return BoolVal(self.val <= val.to_f())
        else:
            return BoolVal(self.val <= val.to_i())

    def eq(self, val):      # == val
        if isinstance(val, FloatVal):
            return BoolVal(self.val == val.to_f())
        else:
            return BoolVal(self.val == val.to_i())

    def neq(self, val):     # != val
        if isinstance(val, FloatVal):
            return BoolVal(self.val != val.to_f())
        else:
            return BoolVal(self.val != val.to_i())

    def __and__(self, val):
        return IntegerVal(self.val & val.to_i())

    def __xor__(self, val):
        return IntegerVal(self.val ^ val.to_i())

    def __or__(self, val):
        return IntegerVal(self.val | val.to_i())

    def lAND(self, val):    # && val
        return BoolVal(self.to_b() and val.to_b())

    def lOR(self, val):     # || val
        return BoolVal(self.to_b() or val.to_b())

    def cast(self, type_):
        from tecslib.core.types import BoolType, FloatType, IntType, PtrType

        t = type_.get_original_type()   # typedef の元を得る
        if isinstance(t, IntType):
            val = t.check_and_clip(self.val, "IntType")
            return IntegerVal(val)
        elif isinstance(t, FloatType):
            return FloatVal(self.val)
        elif isinstance(t, PtrType):
            return PointerVal(self.val, type_)
        elif isinstance(t, BoolType):
            return BoolVal(self.to_b())
        else:
            self.cdl_error("V1013 integer value cannot cast to $1", type_.__class__)
            return None

    def to_s(self):
        if self.str:
            return self.str
        else:
            return str(self.val)

    def to_b(self):
        return self.val != 0

    def to_i(self):
        return self.val

    def to_f(self):
        return float(self.val)


#= BoolVal: bool 値を扱うクラス
class BoolVal(BaseVal):
    # @val:: bool: true, false

    def __init__(self, val):
        super().__init__()
        if val is True or val is False:
            self.val = val
        elif val.to_i() != 0:
            self.val = True
        else:
            self.val = False
        # raise "No boolean val" if val != true && val != false

    def not_(self):         # not # ! val
        return BoolVal(not self.val)

    def eq(self, val):      # == val
        if isinstance(val, BoolVal):
            return BoolVal(self.to_i() == val.to_i())
        else:
            self.cdl_error("V1014 comparing bool value with \'$1\'", val.__class__)
            return BoolVal(False)

    def neq(self, val):     # != val
        if isinstance(val, BoolVal):
            return BoolVal(self.to_i() != val.to_i())
        else:
            self.cdl_error("V1015 comparing bool value with \'$1\'", val.__class__)
            return BoolVal(False)

    def lAND(self, val):    # && val
        return BoolVal(self.to_b() and val.to_b())

    def lOR(self, val):     # || val
        return BoolVal(self.to_b() or val.to_b())

    def cast(self, type_):
        from tecslib.core.types import BoolType, FloatType, IntType

        t = type_.get_original_type()   # typedef の元を得る
        if self.val:
            val = 1
        else:
            val = 0
        if isinstance(t, IntType):
            return IntegerVal(val)
        elif isinstance(t, FloatType):
            return FloatVal(val)
        elif isinstance(t, BoolType):
            return self
        else:
            self.cdl_error("V1016 bool value cannot cast to $1", type_.__class__)
            return None

    def to_s(self):
        if self.val:
            return "true"
        else:
            return "false"

    def to_b(self):
        return self.val

    def to_i(self):
        if self.val is False:
            return 0
        return 1

    def to_f(self):
        if self.val is False:
            return 0.0
        return 1.0


#= FloatVal: 実数値を扱うクラス
class FloatVal(BaseVal):
    # @val:: Float
    def __init__(self, val):
        super().__init__()
        self.val = float(val.to_f() if hasattr(val, "to_f") and callable(val.to_f) else val)

    def __neg__(self):      # -@
        return FloatVal(-self.val)

    def __pos__(self):      # +@
        return self

    def __mul__(self, val):
        return FloatVal(self.val * val.to_f())

    def __truediv__(self, val):
        v2 = val.to_f()   # to_f を2回評価しない
        if v2 == 0.0:
            self.cdl_error("V1017 / : divieded by zero")
            return FloatVal(1.0)
        return FloatVal(self.val / v2)

    def __mod__(self, val):
        v2 = val.to_f()   # to_f を2回評価しない
        if v2 == 0.0:
            self.cdl_error("V1018 % : divieded by zero")
            return FloatVal(1.0)
        return FloatVal(self.val % v2)

    def __add__(self, val):
        return FloatVal(self.val + val.to_f())

    def __sub__(self, val):
        return FloatVal(self.val - val.to_f())

    def __gt__(self, val):
        return BoolVal(self.val > val.to_f())

    def __lt__(self, val):
        return BoolVal(self.val < val.to_f())

    def __ge__(self, val):
        return BoolVal(self.val >= val.to_f())

    def __le__(self, val):
        return BoolVal(self.val <= val.to_f())

    def eq(self, val):      # == val
        return BoolVal(self.val == val.to_f())

    def neq(self, val):     # != val
        return BoolVal(self.val != val.to_f())

    def cast(self, type_):
        from tecslib.core.types import FloatType, IntType

        t = type_.get_original_type()   # typedef の元を得る
        if isinstance(t, IntType):
            val = t.check_and_clip(self.val, "FloatType")
            return IntegerVal(val)
        elif isinstance(t, FloatType):
            return self
        else:
            self.cdl_error("V1019 floating value cannot cast to $1", type_)
            return self

    def to_b(self):
        self.cdl_error("V1020 convert floating value to bool without cast")
        return int(self.val)

    def to_i(self):
        self.cdl_error("V1021 convert floating value to integer without cast")
        return int(self.val)

    def to_s(self):
        return str(self.val)

    def to_f(self):
        return self.val


#= 文字列リテラルを扱うクラス
class StringVal(BaseVal):
    # @str:: Token:
    # @specifier:: Symbol: :WIDE, :NORMAL

    def __init__(self, str_, spec="NORMAL"):
        super().__init__()
        self.str = str_
        self.specifier = spec   # mikan L"str" wide 文字列未対応

    # ===
    #
    # string の cast はできない mikan ポインタ型への cast はできるべき
    def cast(self, type_):
        from tecslib.core.types import FloatType, IntType, PtrType

        t = type_.get_original_type()   # typedef の元を得る
        if isinstance(t, IntType):
            self.cdl_error("V1022 string cannot cast to integer")
        elif isinstance(t, FloatType):
            self.cdl_error("V1023 string cannot cast to float")
        elif isinstance(t, PtrType):
            self.cdl_error("V1024 string cannot cast to pointer")
        else:
            self.cdl_error("V1025 string cannot cast to $1", type_)

    def to_s(self):
        if hasattr(self.str, "to_s"):
            return self.str.to_s()
        return to_s(self.str)

    @property
    def val(self):
        # Ruby の def val; @str.to_s; end 相当（属性アクセスと揃える）
        return self.to_s()
