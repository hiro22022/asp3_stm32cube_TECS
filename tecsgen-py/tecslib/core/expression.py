# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/expression.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

import copy
import sys

from tecslib.core.syntaxobj.node import Node
from tecslib.core.toplevel import dbgPrint


class Expression(Node):
#  @elements   # array
# @b_in_C:Bool : import_C 内の式
# @b_checked:Bool : 式はチェックされている

    MAX_NEST_LEVEL = 64    # 簡易のループ検出（参照のネストを 64 まで許可する）

    def __init__(self, elements, locale=None):
        super().__init__()
        if locale:
            self.locale = locale

        self.elements = elements
        from tecslib.core.bnf import Generator
        self.b_in_C = Generator.parsing_C()
        self.b_checked = False

    def print(self):
        # puts "expr: #{@elements}"
        print("expr_string: {}".format(self.to_s()))

    #=== Expression# to_s
    # C 言語ソース向きの文字列を生成 (globa_name)
    def to_s(self):
        return self.elements_to_s(self.elements)

    def __str__(self):
        return self.to_s()

    #=== Expression# to_str
    # C 言語ソース向きの文字列を生成 (globa_name)
    def to_str(self, name_list, pre, post):
        # Ruby の "#{pre}#{name}#{post}" では nil が空文字になる
        return self.elements_to_s(self.elements, name_list, pre or "", post or "")

    #=== Expression#to_CDL_str
    # CDL 表現の文字列を生成
    def to_CDL_str(self):
        return self.to_s()

    #=== 定数式として評価する(トライしてみる)
    #
    # このメソッドは、定数式を評価する
    # ・attribute, var の初期化子
    # ・size_is, count_is 引数
    # ・配列の添数
    #
    # name_list(NamedList|Nil): 式から参照可能なリスト．
    # NamedList の要素は  size_is, count_is の引数評価の場合 ParamDecl (関数仮引数)
    #
    # name_list2(NamedList|Nil) : NamedList の要素は Decl (attribute, var) である．省略時 nil
    #
    # RETURN: 評価した定数．評価できなかった場合は nil を返す
    #
    # 型は get_type で、評価する（定数として求められないときに使用できる）
    # Array を返すのは attr{ int *a = {1, 2, 3}; int *b = a; }; の b の右辺を評価した場合

    def eval_const(self, name_list, name_list2=None):
        val = self.elements_eval_const(self.elements, name_list, name_list2, 0)
        self.b_checked = True
        from tecslib.core.value import BoolVal, FloatVal, IntegerVal, PointerVal
        if isinstance(val, IntegerVal):
            return val.to_i()
        elif isinstance(val, FloatVal):
            return val.to_f()
        elif isinstance(val, BoolVal):
            return val.to_i()
        elif isinstance(val, PointerVal):
            return val.to_i()           # mikan エラー V1008 が発生してしまう
            # elsif val.kind_of? EnumVal then
            # enum mikan
        else:
            # C_EXP, Array または nil ：そのまま返す
            return val

    #=== 定数式として評価する2(トライしてみる)
    #
    # IntegerVal, FloatVal をそのまま返す（eval_const では Integer, Float に変換）
    def eval_const2(self, name_list, name_list2=None, nest=0):
        val = self.elements_eval_const(self.elements, name_list, name_list2, nest)
        return val

    #=== 式の型を評価する
    #
    # eval_const で値が得られない場合、型を導出可能であれば型を得る
    # param を含んだ式は定数値を求められないが、型を得ることはできる
    # 未定義変数を含んだ型は、得ることができない (ダミー型定義が返る)
    def get_type(self, namedList):        # 名前空間の NamedList を指定
        return self.elements_get_type(self.elements, namedList)

    def check_dir_for_param(self, namedList, dir, spec):
        self.elements_check_dir_for_param(self.elements, namedList, dir, spec)

    def get_elements(self):
        return self.elements

    def show_tree(self, indent):
        # mikan override してしまった print を呼出す方法がわからないのでこうした
        str_ = ""
        str_ += "  " * indent
        print("{}{}".format(str_, self.to_s()))

## private

    #=== 式を文字列に変換
    #name_list:: attribute (Celltype::@attribute_list), struct の @member_list を仮定している
    def elements_to_s(self, elements, name_list=None, pre=None, post=None):
        from tecslib.core.bnf import Token
        if type(elements) is Token:
            return elements.to_s()    # OP_DOT, OP_REF の右辺

        tag = elements[0]
        if tag == "IDENTIFIER":
            nsp = elements[1]
            # if nsp.is_name_only? && name_list && name_list.get_item( nsp.get_name ) then
            if nsp.is_name_only() and name_list and name_list.get_item(nsp.get_name()):
                return "{}{}{}".format(pre, nsp.get_name(), post)
            else:
                # return  elements[1].get_global_name
                return nsp.get_path_str()
        elif tag in ("INTEGER_CONSTANT", "FLOATING_CONSTANT", "OCTAL_CONSTANT", "HEX_CONSTANT",
                     "CHARACTER_LITERAL", "STRING_LITERAL_LIST", "BOOL_CONSTANT"):
            return elements[1].to_s()
        elif tag == "PARENTHESES":
            return "({})".format(self.elements_to_s(elements[1], name_list, pre, post))
        elif tag == "OP_SUBSC":
            return "{}[{}]".format(self.elements_to_s(elements[1], name_list, pre, post), elements[2].to_s())
        elif tag == "OP_DOT":
            return "{}.{}".format(self.elements_to_s(elements[1], name_list, pre, post),
                                  self.elements_to_s(elements[2], name_list, pre, post))
        elif tag == "OP_REF":
            return "{}->{}".format(self.elements_to_s(elements[1], name_list, pre, post),
                                   self.elements_to_s(elements[2], name_list, pre, post))
        elif tag == "OP_SIZEOF_EXPR":
            return "sizeof({})".format(self.elements_to_s(elements[1], name_list, pre, post))
        elif tag == "OP_SIZEOF_TYPE":
            return "sizeof({}) mikan".format(elements[1])
        elif tag == "OP_U_AMP":
            return "&{}".format(self.elements_to_s(elements[1], name_list, pre, post))
        elif tag == "OP_U_ASTER":
            return "*{}".format(self.elements_to_s(elements[1], name_list, pre, post))
        elif tag == "OP_U_PLUS":
            return "+{}".format(self.elements_to_s(elements[1], name_list, pre, post))
        elif tag == "OP_U_MINUS":
            return "-{}".format(self.elements_to_s(elements[1], name_list, pre, post))
        elif tag == "OP_U_TILDE":
            return "~{}".format(self.elements_to_s(elements[1], name_list, pre, post))
        elif tag == "OP_U_EXCLAM":
            return "!{}".format(self.elements_to_s(elements[1], name_list, pre, post))
        elif tag == "CAST":
            return "({}){}".format(elements[1].get_type_str(),
                                   self.elements_to_s(elements[2], name_list, pre, post))
        elif tag == "OP_MULT":
            return "{}*{}".format(self.elements_to_s(elements[1], name_list, pre, post),
                                  self.elements_to_s(elements[2], name_list, pre, post))
        elif tag == "OP_DIV":
            return "{}/{}".format(self.elements_to_s(elements[1], name_list, pre, post),
                                  self.elements_to_s(elements[2], name_list, pre, post))
        elif tag == "OP_REMAIN":
            return "{}%{}".format(self.elements_to_s(elements[1], name_list, pre, post),
                                  self.elements_to_s(elements[2], name_list, pre, post))
        elif tag == "OP_ADD":
            return "{}+{}".format(self.elements_to_s(elements[1], name_list, pre, post),
                                  self.elements_to_s(elements[2], name_list, pre, post))
        elif tag == "OP_SUB":
            return "{}-{}".format(self.elements_to_s(elements[1], name_list, pre, post),
                                  self.elements_to_s(elements[2], name_list, pre, post))
        elif tag == "OP_LSFT":
            return "{}<<{}".format(self.elements_to_s(elements[1], name_list, pre, post),
                                   self.elements_to_s(elements[2], name_list, pre, post))
        elif tag == "OP_RSFT":
            return "{}>>{}".format(self.elements_to_s(elements[1], name_list, pre, post),
                                   self.elements_to_s(elements[2], name_list, pre, post))
        elif tag == "OP_LT":
            return "{}<{}".format(self.elements_to_s(elements[1], name_list, pre, post),
                                  self.elements_to_s(elements[2], name_list, pre, post))
        elif tag == "OP_GT":
            return "{}>{}".format(self.elements_to_s(elements[1], name_list, pre, post),
                                  self.elements_to_s(elements[2], name_list, pre, post))
        elif tag == "OP_LE":
            return "{}<={}".format(self.elements_to_s(elements[1], name_list, pre, post),
                                   self.elements_to_s(elements[2], name_list, pre, post))
        elif tag == "OP_GE":
            return "{}>={}".format(self.elements_to_s(elements[1], name_list, pre, post),
                                   self.elements_to_s(elements[2], name_list, pre, post))
        elif tag == "OP_EQ":
            return "{}=={}".format(self.elements_to_s(elements[1], name_list, pre, post),
                                   self.elements_to_s(elements[2], name_list, pre, post))
        elif tag == "OP_NE":
            return "{}!={}".format(self.elements_to_s(elements[1], name_list, pre, post),
                                   self.elements_to_s(elements[2], name_list, pre, post))
        elif tag == "OP_AND":
            return "{}&{}".format(self.elements_to_s(elements[1], name_list, pre, post),
                                  self.elements_to_s(elements[2], name_list, pre, post))
        elif tag == "OP_EOR":
            return "{}^{}".format(self.elements_to_s(elements[1], name_list, pre, post),
                                  self.elements_to_s(elements[2], name_list, pre, post))
        elif tag == "OP_OR":
            return "{}|{}".format(self.elements_to_s(elements[1], name_list, pre, post),
                                  self.elements_to_s(elements[2], name_list, pre, post))
        elif tag == "OP_LAND":
            return "{}&&{}".format(self.elements_to_s(elements[1], name_list, pre, post),
                                   self.elements_to_s(elements[2], name_list, pre, post))
        elif tag == "OP_LOR":
            return "{}||{}".format(self.elements_to_s(elements[1], name_list, pre, post),
                                   self.elements_to_s(elements[2], name_list, pre, post))
        elif tag == "OP_CEX":
            return "{}?{}:{}".format(self.elements_to_s(elements[1], name_list, pre, post),
                                     self.elements_to_s(elements[2], name_list, pre, post),
                                     self.elements_to_s(elements[3], name_list, pre, post))
        else:
            raise Exception("Unknown expression element: {}. try -t and please report".format(elements[0]))
        return ""

    #=== Expression# 逆ポーランド文字列化
    #param_list:: ParamlList  関数の引数リスト
    def get_rpn(self, param_list=None, name_list2=None):
        return self.elements_rpn(self.elements, param_list, name_list2)

    #=== Expression# 逆ポーランド文字列化 (private)
    #name_list:: ParamlList  関数の引数リスト
    def elements_rpn(self, elements, name_list=None, name_list2=None):
        from tecslib.core.bnf import Token
        if type(elements) is Token:
            print("rpn: {}\n".format(elements.to_s()))
            return elements.to_s()    # OP_DOT, OP_REF の右辺

        tag = elements[0]
        if tag == "IDENTIFIER":
            nsp = elements[1]
            #if nsp.is_name_only? && name_list && name_list.find( nsp.get_name ) then
            if nsp.is_name_only():
                count = 0
                # p "search: #{nsp.get_name}"
                for nm in name_list.get_items():
                    # p "    : #{nm.get_name} #{nsp.get_name.class} #{nm.get_name.class}"
                    if nsp.get_name() == nm.get_name():
                        return " ${}".format(count)
                    count += 1
                raise Exception("not found parameter")
            else:
                # return  elements[1].get_global_name
                raise Exception("not unexpected parameter")
        elif tag in ("INTEGER_CONSTANT", "FLOATING_CONSTANT", "OCTAL_CONSTANT", "HEX_CONSTANT",
                     "CHARACTER_LITERAL", "STRING_LITERAL_LIST", "BOOL_CONSTANT"):
            return elements[1].to_s()
        elif tag == "PARENTHESES":
            return self.elements_rpn(elements[1], name_list, name_list2)
        elif tag == "OP_SUBSC":
            return (self.elements_rpn(elements[1], name_list, name_list2) + " "
                    + self.elements_rpn(elements[1], "", name_list, name_list2) + " []")
        elif tag == "OP_DOT":
            return self.elements_rpn(elements[1], name_list, name_list2) + " ."
        elif tag == "OP_REF":
            return self.elements_rpn(elements[1], name_list, name_list2) + " ->"
        elif tag == "OP_SIZEOF_EXPR":
            return self.elements_rpn(elements[1], name_list, name_list2) + " #s"
        elif tag == "OP_SIZEOF_TYPE":
            return self.elements_rpn(elements[1], name_list, name_list2) + " #S"
        elif tag == "OP_U_AMP":
            return self.elements_rpn(elements[1], name_list, name_list2) + " #&"
        elif tag == "OP_U_ASTER":
            return self.elements_rpn(elements[1], name_list, name_list2) + " #*"
        elif tag == "OP_U_PLUS":
            return self.elements_rpn(elements[1], name_list, name_list2) + " #+"
        elif tag == "OP_U_MINUS":
            return self.elements_rpn(elements[1], name_list, name_list2) + " #-"
        elif tag == "OP_U_TILDE":
            return self.elements_rpn(elements[1], name_list, name_list2) + " #~"
        elif tag == "OP_U_EXCLAM":
            return self.elements_rpn(elements[1], name_list, name_list2) + " #!"
        elif tag == "CAST":
            return (self.elements_rpn(elements[1], name_list, name_list2) + " #("
                    + self.elements_rpn(elements[2], "", name_list, name_list2) + ")")
        elif tag == "OP_MULT":
            return (self.elements_rpn(elements[1], name_list, name_list2) + " "
                    + self.elements_rpn(elements[2], "", name_list, name_list2) + " *")
        elif tag == "OP_DIV":
            return (self.elements_rpn(elements[1], name_list, name_list2) + " "
                    + self.elements_rpn(elements[2], "", name_list, name_list2) + " /")
        elif tag == "OP_REMAIN":
            return (self.elements_rpn(elements[1], name_list, name_list2) + " "
                    + self.elements_rpn(elements[2], "", name_list, name_list2) + " %")
        elif tag == "OP_ADD":
            return (self.elements_rpn(elements[1], name_list, name_list2) + " "
                    + self.elements_rpn(elements[2], "", name_list, name_list2) + " +")
        elif tag == "OP_SUB":
            return (self.elements_rpn(elements[1], name_list, name_list2) + " "
                    + self.elements_rpn(elements[2], "", name_list, name_list2) + " -")
        elif tag == "OP_LSFT":
            return (self.elements_rpn(elements[1], name_list, name_list2) + " "
                    + self.elements_rpn(elements[2], "", name_list, name_list2) + " <<")
        elif tag == "OP_RSFT":
            return (self.elements_rpn(elements[1], name_list, name_list2) + " "
                    + self.elements_rpn(elements[2], "", name_list, name_list2) + " >>")
        elif tag == "OP_LT":
            return (self.elements_rpn(elements[1], name_list, name_list2) + " "
                    + self.elements_rpn(elements[2], "", name_list, name_list2) + " <")
        elif tag == "OP_GT":
            return (self.elements_rpn(elements[1], name_list, name_list2) + " "
                    + self.elements_rpn(elements[2], "", name_list, name_list2) + " >")
        elif tag == "OP_LE":
            return (self.elements_rpn(elements[1], name_list, name_list2) + " "
                    + self.elements_rpn(elements[2], "", name_list, name_list2) + " <=")
        elif tag == "OP_GE":
            return (self.elements_rpn(elements[1], name_list, name_list2) + " "
                    + self.elements_rpn(elements[2], "", name_list, name_list2) + " >=")
        elif tag == "OP_EQ":
            return (self.elements_rpn(elements[1], name_list, name_list2) + " "
                    + self.elements_rpn(elements[2], "", name_list, name_list2) + " ==")
        elif tag == "OP_NE":
            return (self.elements_rpn(elements[1], name_list, name_list2) + " "
                    + self.elements_rpn(elements[2], "", name_list, name_list2) + " !=")
        elif tag == "OP_AND":
            return (self.elements_rpn(elements[1], name_list, name_list2) + " "
                    + self.elements_rpn(elements[2], "", name_list, name_list2) + " &")
        elif tag == "OP_EOR":
            return (self.elements_rpn(elements[1], name_list, name_list2) + " "
                    + self.elements_rpn(elements[2], "", name_list, name_list2) + " ^")
        elif tag == "OP_OR":
            return (self.elements_rpn(elements[1], name_list, name_list2) + " "
                    + self.elements_rpn(elements[2], "", name_list, name_list2) + " |")
        elif tag == "OP_LAND":
            return (self.elements_rpn(elements[1], name_list, name_list2) + " "
                    + self.elements_rpn(elements[2], "", name_list, name_list2) + " &&")
        elif tag == "OP_LOR":
            return (self.elements_rpn(elements[1], name_list, name_list2) + " "
                    + self.elements_rpn(elements[2], "", name_list, name_list2) + " ||")
        elif tag == "OP_CEX":
            return (self.elements_rpn(elements[1], name_list, name_list2) + " "
                    + self.elements_rpn(elements[2], name_list, name_list2) + " "
                    + self.elements_rpn(elements[3], name_list, name_list2) + " ?:")
        else:
            raise Exception("Unknown expression element: {}. try -t and please report".format(elements[0]))
        return ""

    # 定数式(elements)を評価する
    #
    # このメソッドは Expression クラスのメソッドである必要はない（関数化できる）
    #
    # elements は式の要素
    #
    # name_list, name_list2 は eval_const を参照
    #
    # RETURN: 評価した定数、評価できなかった場合は nil を返す

    def elements_eval_const(self, elements, name_list, name_list2=None, nest=None):
        from tecslib.core.componentobj.join import Join
        from tecslib.core.componentobj.namespace import Namespace
        from tecslib.core.syntaxobj.decl import Decl
        from tecslib.core.syntaxobj.paramdecl import ParamDecl
        from tecslib.core.types import BoolType
        from tecslib.core.value import BoolVal, FloatVal, IntegerVal, StringVal

        object = None
        tag = elements[0]
        if tag == "IDENTIFIER":
            nsp = elements[1]

            # #809 の修正しかけ (別の問題が解決しきれていない)
            # nest += 1     # 参照がループになっていないかのチェック
            #               # mikan 本当にループしているかどうかではなく、単純に多数の参照を繰り返していることで判定している
            # if nest > MAX_NEST_LEVEL then
            #   cdl_error( "E9999: '$1' too many reference (maybe loop) max=$1" , nsp.to_s, MAX_NEST_LEVEL )
            #   return
            # end
            if nsp.is_name_only():
                if name_list:
                    object = name_list.get_item(nsp.get_name())

                if object is None and name_list2:
                    object = name_list2.get_item(nsp.get_name())

            # 見つからなければ定数定義から探す
            if object is None:
                object = Namespace.find(nsp)# mikan namespace の対応 #1

# この実装は、もう少し整理されるべき
# これが呼出されるのは、以下の場合
#   ・attribute, var の右辺式の評価
#   ・size_is 引数の評価：関数パラメータの場合とattribute, var の場合がある
# 以下のエラーチェックでは、これらがごっちゃになって誤りを検出しようとしている

            # IDENTIFIER は見つからなかった？
            if object is None:
                self.cdl_error("E1001 $1: not found", nsp.get_path_str())
                # raise  "E1001"  # bug trap
                return None
            elif type(object) is Join:
                # Join の場合： cell の中の attribute, var, call のどれかが見つかった
                # Decl (attribute, var) でない？
                if type(object.get_definition()) is not Decl:
                    self.cdl_error("E1002 $1: not constant (port)", nsp.get_path_str())
                    return None
                return object.get_rhs().eval_const2(name_list, name_list2, nest)
            elif type(object) is not Decl:
                # Decl でない場合： 定数でもない
                if type(object) is not ParamDecl:
                                                      # mikan paramdecl は無視する
                                                      # ParamList から呼ばれたとき
                    self.cdl_error("E1003 $1: not constant", nsp.get_path_str())
                else:
                    # ParamDecl
                    object.referenced()
                return None
            else: # Decl
                object.referenced()
                if object.get_initializer() is None:
                    # 初期化子の存在しない変数   # mikan ここへくるのは、通常ありえないはず（未検証）
                    return IntegerVal(0)
                else:
                    # Decl の右辺の評価
                    # mikan size_is 引数に現れる変数の型が適切かのチェックする
                    init = object.get_initializer()
                    if type(init) is Expression or type(init) is C_EXP:
                        return init.eval_const2(name_list, name_list2, nest)
                    else:
                        # Array の場合
                        return init
        elif tag == "BOOL_CONSTANT":
            if type(elements[1]) is bool and elements[1] is True:
                return BoolVal(True)
            elif type(elements[1]) is bool and elements[1] is False:
                return BoolVal(False)
            else:
                raise Exception("BOOL constant error")
        elif tag == "INTEGER_CONSTANT":
            return IntegerVal(elements[1].val)
        elif tag == "FLOATING_CONSTANT":
            return FloatVal(elements[1].val)
        elif tag == "OCTAL_CONSTANT":
            return IntegerVal(int(elements[1].val, 8), elements[1].val)
        elif tag == "HEX_CONSTANT":
            return IntegerVal(int(elements[1].val, 16), elements[1].val)
        elif tag == "CHARACTER_LITERAL":
            str_ = elements[1].val.replace("'", "")
#2.0      if str.jlength == 1
            len_ = len(str_)
            if len_ == 1:
                sum_ = 0
                # Ruby の String#each_byte 相当。ファイル文字コードのバイト列で評価する
                # (Shift_JIS 等で Unicode 化した後に latin-1 へ再符号化すると失敗する)
                from tecslib.core import globals as G
                enc = G.Ruby19_File_Encode
                if enc == "Shift_JIS":
                    byte_enc = "cp932"
                elif enc in ("ASCII-8BIT", "BINARY", "binary"):
                    byte_enc = "latin-1"
                else:
                    byte_enc = enc
                for b in str_.encode(byte_enc, "surrogateescape"):
                    sum_ = sum_ * 256 + b
                return IntegerVal(sum_, elements[1].val)
            else:
#2.0        if str[0] == 92 then
                if len(str_) > 0 and (str_[0] == chr(92) or str_[0] == "\\"):
                    if len(str_) > 1:
                        case1 = str_[1]
                        if case1 == chr(48) or case1 == "0":  # '0'
                            return IntegerVal(0, elements[1].val)
                        elif case1 == chr(110) or case1 == "n":  # 'n'
                            return IntegerVal(10, elements[1].val)
                        elif case1 == chr(114) or case1 == "r":  # 'r'
                            return IntegerVal(13, elements[1].val)
                        elif case1 == chr(116) or case1 == "t":  # 't'
                            return IntegerVal(15, elements[1].val)
                        elif case1 == chr(92) or case1 == '\\':  # '\\'
                            return IntegerVal(92, elements[1].val)
#2.0      printf( "c=%c\n", str[1] )
            if len(str_) > 1:
                sys.stdout.write("len={} c={}\n".format(len_, str_[1]))
            else:
                sys.stdout.write("len={} c=\n".format(len_))
            raise Exception()
        elif tag == "STRING_LITERAL_LIST":
            return StringVal(elements[1])
        elif tag == "PARENTHESES":
            return self.elements_eval_const(elements[1], name_list, name_list2, nest)
        elif tag == "OP_SUBSC":
            self.cdl_error("E1004 cannot evaluate \'[]\' operator")
            return None
        elif tag == "OP_DOT":
            self.cdl_error("E1005 cannot evaluate \'.\' operator")
            return None
        elif tag == "OP_REF":
            self.cdl_error("E1006 cannot evaluate \'->\' operator")
            return None
        elif tag == "OP_SIZEOF_EXPR":
            if not self.b_checked:
                if self.b_in_C:
                    self.cdl_info("I9999 cannot evaluate \'sizeof\' operator. this might causes later error.")
                else:
                    self.cdl_error("E1007 cannot evaluate \'sizeof\' operator")
            return None
        elif tag == "OP_SIZEOF_TYPE":
            if not self.b_checked:
                if self.b_in_C:
                    self.cdl_info("I9999 cannot evaluate \'sizeof\' operator. this might causes later error.")
                else:
                    self.cdl_error("E1008 cannot evaluate \'sizeof\' operator")
            return None
        elif tag == "OP_U_AMP":
            self.cdl_error("E1009 cannot evaluate \'&\' operator")
            return None
        elif tag == "OP_U_ASTER":
            # cdl_error( "E1010 cannot evaluate \'*\' operator"  )
            val = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            if not self.evaluable(val):
                return None
            return val
        elif tag == "OP_U_PLUS":
            val = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            if not self.evaluable(val):
                return None
            if hasattr(val, "__pos__"):
                return +val
            else:
                self.cdl_error("E1011 cannot evaluate unary + for $1", val.__class__)
                return None
        elif tag == "OP_U_MINUS":
            val = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            if not self.evaluable(val):
                return None
            if hasattr(val, "__neg__"):
                return -val
            else:
                return None
        elif tag == "OP_U_TILDE":
            val = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            if not self.evaluable(val):
                return None
# p "val.respond_to?( \"-@\" )=#{val.respond_to?( "-@" )} #{val.class}"
# p "val.respond_to?( \"~@\" )=#{val.respond_to?( "~@" )}"
#2.0      if val.respond_to?( "~@" ) then  # Ruby 1.9, 2.0 preview 版では例外が発生してしまう
            if isinstance(val, IntegerVal):
                return ~val
            else:
                return None
        elif tag == "OP_U_EXCLAM":
            val = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            if not self.evaluable(val):
                return None
            val = val.cast(BoolType())
            if hasattr(val, "not_"):
                return val.not_()
            else:
                return None
            return None
        elif tag == "CAST":
            val = self.elements_eval_const(elements[2], name_list, name_list2, nest)
            # return nil if val == nil
            if not self.evaluable(val):
                return None
            return val.cast(elements[1])
        elif tag == "OP_MULT":
            lhs = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            rhs = self.elements_eval_const(elements[2], name_list, name_list2, nest)
            # return nil if( rhs == nil || lhs == nil )
            if not self.evaluable(rhs, lhs):
                return None
            return lhs * rhs
        elif tag == "OP_DIV":
            lhs = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            rhs = self.elements_eval_const(elements[2], name_list, name_list2, nest)
            # return nil if( rhs == nil || lhs == nil )
            if not self.evaluable(rhs, lhs):
                return None
            return lhs / rhs
        elif tag == "OP_REMAIN":
            lhs = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            rhs = self.elements_eval_const(elements[2], name_list, name_list2, nest)
            # return nil if( rhs == nil || lhs == nil )
            if not self.evaluable(rhs, lhs):
                return None
            return lhs % rhs
        elif tag == "OP_ADD":
            lhs = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            rhs = self.elements_eval_const(elements[2], name_list, name_list2, nest)
            # return nil if( rhs == nil || lhs == nil )
            if not self.evaluable(rhs, lhs):
                return None
            return lhs + rhs
        elif tag == "OP_SUB":
            lhs = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            rhs = self.elements_eval_const(elements[2], name_list, name_list2, nest)
            # return nil if( rhs == nil || lhs == nil )
            if not self.evaluable(rhs, lhs):
                return None
            return lhs - rhs
        elif tag == "OP_LSFT":
            lhs = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            rhs = self.elements_eval_const(elements[2], name_list, name_list2, nest)
            # return nil if( rhs == nil || lhs == nil )
            if not self.evaluable(rhs, lhs):
                return None
            return lhs << rhs
        elif tag == "OP_RSFT":
            lhs = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            rhs = self.elements_eval_const(elements[2], name_list, name_list2, nest)
            # return nil if( rhs == nil || lhs == nil )
            if not self.evaluable(rhs, lhs):
                return None
            return lhs >> rhs
        elif tag == "OP_LT":
            lhs = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            rhs = self.elements_eval_const(elements[2], name_list, name_list2, nest)
            # return nil if( rhs == nil || lhs == nil )
            if not self.evaluable(rhs, lhs):
                return None
            return lhs < rhs
        elif tag == "OP_GT":
            lhs = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            rhs = self.elements_eval_const(elements[2], name_list, name_list2, nest)
            # return nil if( rhs == nil || lhs == nil )
            if not self.evaluable(rhs, lhs):
                return None
            return lhs > rhs
        elif tag == "OP_LE":
            lhs = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            rhs = self.elements_eval_const(elements[2], name_list, name_list2, nest)
            # return nil if( rhs == nil || lhs == nil )
            if not self.evaluable(rhs, lhs):
                return None
            return lhs <= rhs
        elif tag == "OP_GE":
            lhs = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            rhs = self.elements_eval_const(elements[2], name_list, name_list2, nest)
            # return nil if( rhs == nil || lhs == nil )
            if not self.evaluable(rhs, lhs):
                return None
            return lhs >= rhs
        elif tag == "OP_EQ":
            lhs = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            rhs = self.elements_eval_const(elements[2], name_list, name_list2, nest)
            # return nil if( rhs == nil || lhs == nil )
            if not self.evaluable(rhs, lhs):
                return None
            return lhs.eq(rhs)
        elif tag == "OP_NE":
            lhs = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            rhs = self.elements_eval_const(elements[2], name_list, name_list2, nest)
            # return nil if( rhs == nil || lhs == nil )
            if not self.evaluable(rhs, lhs):
                return None
            return lhs.neq(rhs)
        elif tag == "OP_AND":
            lhs = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            rhs = self.elements_eval_const(elements[2], name_list, name_list2, nest)
            # return nil if( rhs == nil || lhs == nil )
            if not self.evaluable(rhs, lhs):
                return None
            return lhs & rhs
        elif tag == "OP_EOR":
            lhs = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            rhs = self.elements_eval_const(elements[2], name_list, name_list2, nest)
            # return nil if( rhs == nil || lhs == nil )
            if not self.evaluable(rhs, lhs):
                return None
            return lhs ^ rhs
        elif tag == "OP_OR":
            lhs = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            rhs = self.elements_eval_const(elements[2], name_list, name_list2, nest)
            # return nil if( rhs == nil || lhs == nil )
            if not self.evaluable(rhs, lhs):
                return None
            return lhs | rhs
        elif tag == "OP_LAND":
            lhs = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            rhs = self.elements_eval_const(elements[2], name_list, name_list2, nest)
            # return nil if( rhs == nil || lhs == nil )
            if not self.evaluable(rhs, lhs):
                return None
            return lhs.lAND(rhs)
        elif tag == "OP_LOR":
            lhs = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            rhs = self.elements_eval_const(elements[2], name_list, name_list2, nest)
            # return nil if( rhs == nil || lhs == nil )
            if not self.evaluable(rhs, lhs):
                return None
            return lhs.lOR(rhs)
        elif tag == "OP_CEX":
            lhs = self.elements_eval_const(elements[1], name_list, name_list2, nest)
            mhs = self.elements_eval_const(elements[2], name_list, name_list2, nest)
            rhs = self.elements_eval_const(elements[3], name_list, name_list2, nest)
            # return nil if( rhs == nil || mhs == nil || lhs == nil )
            if not self.evaluable(rhs, mhs, lhs):
                return None
            if lhs.cast(BoolType()).val:
                return mhs
            else:
                return rhs
        return None

    def elements_get_type(self, elements, namedList):
        from tecslib.core.types import DefinedType
        type_ = self.elements_get_type_sub(elements, namedList)
        # 返された方が DefinedType の場合 元の型を返す
        if isinstance(type_, DefinedType):
            type_ = type_.get_type()
        return type_

    def elements_get_type_sub(self, elements, namedList):
        from tecslib.core.types import BoolType, IntType, PtrType

        paramdecl = None
        tag = elements[0]
        if tag == "IDENTIFIER":
            nsp = elements[1]
            if nsp.is_name_only() and namedList:    #1202
                paramdecl = namedList.get_item(nsp.get_name())
            else:
                paramdecl = None
            if not paramdecl:
                if namedList:                       #1202
                    self.cdl_error("E1012 $1: not found in parameter list", nsp.get_path_str())
                else:
                    # namedList = nil: expression.rb の initializer.get_type( attribute ) から呼ばれた場合
                    # この場合、E1001 が出るので、ここでは出さない
                    dbgPrint("elements_get_type_sub: {} not found (namedList==nil)\n".format(nsp.get_path_str()))
                return IntType(32)        # dummy result
            return paramdecl.get_type()
# mikan get_type
#    when :INTEGER_CONSTANT
#    when :FLOATING_CONSTANT
#    when :OCTAL_CONSTANT
#    when :HEX_CONSTANT
#    when :CHARACTER_LITERAL
#    when :STRING_LITERAL_LIST
#    when :PARENTHESES
#    when :OP_SUBSC
#    when :OP_DOT
#    when :OP_REF
#    when :OP_SIZEOF_EXPR
#    when :OP_SIZEOF_TYPE
#    when :OP_U_AMP
        elif tag == "OP_U_ASTER":
            type_ = self.elements_get_type(elements[1], namedList)
            if not isinstance(type_, PtrType):
                self.cdl_error("E1013 \'*\': operand is not pointer value")
                return IntType(8)    # IntType を返しておく
            return type_.get_referto()

        elif tag in ("OP_U_PLUS", "OP_U_MINUS"):
            # mikan operand が適切な型かチェックしていない
            return self.elements_get_type(elements[1], namedList)

        elif tag in ("OP_ADD", "OP_SUB", "OP_MULT", "OP_DIV", "OP_REMAIN"):
            # mikan operand が適切な型かチェックしていない＆左辺の型を採用している
            return self.elements_get_type(elements[1], namedList)

        elif tag == "OP_U_TILDE":
            # mikan operand が整数かチェックしていない
            return self.elements_get_type(elements[1], namedList)
        elif tag in ("OP_AND", "OP_EOR", "OP_OR", "OP_LSFT", "OP_RSFT"):
            # mikan operand が整数かチェックしていない
            return BoolType()
        elif tag == "OP_U_EXCLAM":
            # mikan operand が整数かチェックしていない
            return BoolType()

        elif tag in ("OP_LT", "OP_GT", "OP_LE", "OP_GE", "OP_EQ", "OP_NE", "OP_LAND", "OP_LOR", "OP_CEX", "CAST"):
            self.cdl_error("E1014 $1: elements_get_type: sorry not supported", elements[0])

        return None

    # 式が size_is, count_is, string の引数である場合の方向のチェック
    def elements_check_dir_for_param(self, elements, namedList, dir, spec):
       # dir ： 元の引数の方向
       # direct: size_is などの引数の変数の方向

        req_direct = None
        tag = elements[0]
        if tag == "IDENTIFIER":
            nsp = elements[1]
            if nsp.is_name_only():
                paramdecl = namedList.get_item(nsp.get_name())
            else:
                paramdecl = None

            if not paramdecl:      # if nil already error in element_get_type
                return

            direct = paramdecl.get_direction()
            judge = False
            if spec == "size_is" or spec == "string":
                if dir in ("IN", "OUT", "INOUT", "SEND"):
                    judge = True if (direct == "IN" or direct == "INOUT") else False
                    req_direct = "in or inout"
                elif dir == "RECEIVE":
                    judge = True if (direct == "OUT" or direct == "INOUT") else False
                    req_direct = "out or inout"

            elif spec == "count_is":
                if dir in ("IN", "SEND"):
                    judge = True if (direct == "IN" or direct == "INOUT") else False
                    req_direct = "in or inout"
                elif dir in ("OUT", "RECEIVE"):     # mikan out で count_is のみ指定されている場合 in でなくてはならない
                    judge = True if (direct == "OUT" or direct == "INOUT") else False
                    req_direct = "out or inout"
                elif dir == "INOUT":
                    judge = True if (direct == "INOUT") else False
                    req_direct = "inout"

            if judge is False:
                self.cdl_error("E1015 \'$1\': direction mismatch for $2, $3 required",
                               nsp.get_path_str(), spec, req_direct)

        elif tag in ("INTEGER_CONSTANT", "FLOATING_CONSTANT", "OCTAL_CONSTANT", "HEX_CONSTANT",
                     "CHARACTER_LITERAL", "STRING_LITERAL_LIST"):
            return True

        # 単項演算子
        elif tag in ("OP_U_ASTER", "OP_SIZEOF_EXPR", "OP_SIZEOF_TYPE", "OP_U_PLUS", "OP_U_MINUS",
                     "OP_U_TILDE", "OP_U_EXCLAM", "CAST", "OP_U_AMP", "PARENTHESES"):
            self.elements_check_dir_for_param(elements[1], namedList, dir, spec)

        # 2項演算子
        elif tag in ("OP_SUBSC", "OP_DOT", "OP_REF", "OP_MULT", "OP_DIV", "OP_REMAIN", "OP_ADD", "OP_SUB",
                     "OP_LSFT", "OP_RSFT", "OP_LT", "OP_GT", "OP_LE", "OP_GE", "OP_EQ", "OP_NE", "OP_AND",
                     "OP_EOR", "OP_OR", "OP_LAND", "OP_LOR"):
            return (self.elements_check_dir_for_param(elements[1], namedList, dir, spec)
                    and self.elements_check_dir_for_param(elements[2], namedList, dir, spec))

        # 3項演算子
        elif tag == "OP_CEX":
            return (self.elements_check_dir_for_param(elements[1], namedList, dir, spec)
                    and self.elements_check_dir_for_param(elements[2], namedList, dir, spec)
                    and self.elements_check_dir_for_param(elements[3], namedList, dir, spec))

        else:
            self.cdl_error("E1016 $1: elements_check_dir_for_param: sorry not supported", elements[0])

    #Express# get_allocator_rhs_elem
    #alloc_type::Symbol  :NORMAL_ALLOC|:INTERNAL_ALLOC|:RELAY_ALLOC
    #式がアロケータ指定子の右辺として妥当かチェックし、正しければ分解した値を返す
    #return:
    #  :NORMAL_ALLOC      [ cell_nsp, ep_name ]               # rhs = cell_nsp.ep_name    ex) Alloc.eAlloc
    #  :INTERNAL_ALLOC    [ ep_name ]                         # rhs = ep_name             ex) eAlloc
    #  :RELAY_ALLOC       [ cp_name, func_name, param_name ]  # rhs = cp_name.func_name.param_name
    def get_allocator_rhs_elements(self, alloc_type):
        from tecslib.core.bnf import Token
        ele = self.elements
        if alloc_type == "NORMAL_ALLOC":
            if ele[0] != "OP_DOT" or ele[1][0] != "IDENTIFIER":   #1
                self.cdl_error("E1017 $1: rhs not \'Cell.ePort\' form", str(ele[0]))
                return None
            cell_nsp = ele[1][1]
            port_name = ele[2].val
            return [cell_nsp, port_name]
        elif alloc_type == "INTERNAL_ALLOC":
            if ele[0] == "IDENTIFIER":
                if ele[1].is_name_only():
                    return [ele[1].get_path()[0]]  # mikan a::b
                else:
                    self.cdl_error("E1018 $1: namespace cannot be specified", ele[1].to_s())
            else:
                self.cdl_error("E1019 $1: rhs not in 'allocator_entry_port' form", ele[1].to_s())
        elif alloc_type == "RELAY_ALLOC":
            if (ele[0] != "OP_DOT"
                    or ele[1][0] != "OP_DOT" or ele[1][1][0] != "IDENTIFIER" or not ele[1][1][1].is_name_only()
                    or type(ele[1][2]) is not Token or type(ele[2]) is not Token):   #1
                self.cdl_error("E1020 rhs not in 'call_port.func.param' form ($1)", str(ele[0]))   # S1086
            func_name = ele[1][2]
            cp_name = ele[1][1][1].get_name()
            param_name = ele[2].to_sym()
            return [cp_name, func_name, param_name]
        return None

    #Expression#Expression のクローンを作成する
    def clone_for_composite(self):
        cl = copy.copy(self)
        elements = self.clone_elements(self.elements)
        cl.set_elements(elements)
        return cl

    #Expression#elements のクローンを作成
    #elements::Array
    # このメソッドは、Array のディープコピーを行う
    def clone_elements(self, elements):
        elements = copy.copy(elements)
        for i, ele in enumerate(elements):
            if type(ele) is list:
                elements[i] = self.clone_elements(ele)
        return elements

    def set_elements(self, elements):
        self.elements = elements

    #=== Expression#セル結合の式を解析する
    # Cell.eEntry  => [ :OP_DOT, [ :IDENTIFIER, token ], token ]
    # Cell.eEntry[expression] => [ :OP_SUBSC, [ :OP_DOT, [ :IDENTIFIER, token ], token ], expression ]
    # Return: [ NamespacePath(cell_name), Integer(subscript) or nil, Token(port_name)]
    def analyze_cell_join_expression(self):
        # 右辺の Expression の要素を取り出す
        elements = self.elements
        if elements[0] == "OP_SUBSC":  # 右辺：受け口配列？
            # elements = [ :OP_SUBSC, [ :OP_DOT, [ :IDENTIFIER, token ], token ], expression ]
            subscript = elements[2].eval_const(None)  # 受け口配列の添数
            elements = elements[1]          # mikan 配列だった場合
        else:
            subscript = None

        # elements = [ :OP_DOT, [ :IDENTIFIER, token ], token ]
        if elements[0] != "OP_DOT" or elements[1][0] != "IDENTIFIER":   #1
            return None

        nsp = elements[1][1]         # NamespacePath
        port_name = elements[2].val

        return [nsp, subscript, port_name]

    #=== Expression# セルへの結合の式を生成する
    #nsp:: NamespacePath
    #subscript:: Integer
    #port_name:: Symbol
    # analyze_cell_join_expression と対になっている
    @classmethod
    def create_cell_join_expression(cls, nsp, subscript, port_name, locale=None):
        from tecslib.core.bnf import Token
        from tecslib.rubylib.symbol import Sym
        if not isinstance(port_name, Sym):
            raise Exception("port_name: not Symbol")

        if subscript:
            elements = ["OP_SUBSC", ["OP_DOT", ["IDENTIFIER", nsp],
                                     Token(port_name, None, None, None)],
                        cls.create_integer_constant(subscript, locale)]
        else:
            elements = ["OP_DOT", ["IDENTIFIER", nsp], Token(port_name, None, None, None)]
        return Expression(elements, locale)

    #=== Expression#整数定数の式を生成する
    #val:: Integer : 値： 整数
    @classmethod
    def create_integer_constant(cls, val, locale=None):
        from tecslib.core.bnf import Token
        if val != int(val) or val < 0:
            raise Exception("create_integer_constant: not integer or negative: {}".format(val))
        return Expression(["INTEGER_CONSTANT", Token(val, None, None, None)], locale)

    #=== Expression#単一の識別子の式を解析する
    # Identifier  => [ :IDENTIFIER, token ]
    # Return: NamespacePath(Identifier)
    def analyze_single_identifier(self):
        # 右辺の Expression の要素を取り出す
        elements = self.elements
        if elements[0] == "IDENTIFIER":
            return elements[1]
        else:
            return None

    #=== Expression#
    #nsp:: NamespacePath :  参照するもの識別子
    @classmethod
    def create_single_identifier(cls, nsp, locale):
        from tecslib.core.componentobj.namespacepath import NamespacePath
        if type(nsp) is not NamespacePath:
            raise Exception("create_single_identifier: not NamespacePath: {}".format(nsp.to_s()))
        return Expression(["IDENTIFIER", nsp])

    #=== 評価可能かチェックする
    #*v:: 可変個引数（任意の型）
    # すべてが BaseVal の子クラス（値）であれば、評価可能と判断する
    def evaluable(self, *v):
        from tecslib.core.value import BaseVal
        for val in v:
            if not isinstance(val, BaseVal):
                return False
        return True

    # private :elements_to_s, :elements_eval_const,  :elements_get_type


class C_EXP(Node):
# @c_exp_string : string

    #c_exp_string::String
    #b_renew::Bool  : true なら C_EXP の clone 作成（エスケープ処理等をしない）
    def __init__(self, c_exp_string, b_renew=False):
        from tecslib.core.syntaxobj.cdlstring import CDLString
        if b_renew:
            self.c_exp_string = c_exp_string
        else:
            # 前後の " を取り除く
            # str = c_exp_string.to_s.sub( /^\"(.*)\"$/, "\\1" )
            from tecslib.rubylib.rb import to_s
            str_ = CDLString.remove_dquote(to_s(c_exp_string))
            self.c_exp_string = CDLString.escape(str_)

    #=== composite 用に C_EXP を clone する
    #ct_name::
    #cell_name::
    # composite の attribute に現れる C_EXP を文字列置換して生成しなおす．
    # この文字列置換は、意味解釈段階で行う．
    # 他の C_EXP の文字列置換は、コード生成段階で行う．
    def clone_for_composite(self, ct_name, cell_name, locale):
        dbgPrint("C_EXP: {} {} {}\n".format(ct_name, cell_name, self.c_exp_string))

        self.locale = locale
        import re

        def _sub(pat, repl, s):
            return re.sub(pat, lambda m: m.group(1) + str(repl), s)

        str_ = _sub(r'(^|[^\$])\$ct\$', ct_name, self.c_exp_string)
        str_ = _sub(r'(^|[^\$])\$cell\$', cell_name, str_)
        str_ = _sub(r'(^|[^\$])\$id\$', "{}_{}".format(ct_name, cell_name), str_)
        return C_EXP(str_, True)

    def get_c_exp_string(self):
        return self.c_exp_string

    #=== C_EXP を評価する
    # C_EXP の引き数文字列を返す
    # 本来 C_EXP は eval_const する対象ではないが、便宜上 eval_const で対応
    def eval_const(self, name_list, name_list2=None):
        return self

    def eval_const2(self, name_list, name_list2=None, nest=None):
        return self

    def to_s(self):
        return self.c_exp_string

    def __str__(self):
        return self.to_s()

    def to_CDL_str(self):
        return 'C_EXP( "{}" )'.format(self.to_s())

    def show_tree(self, indent):
        print("  " * indent, end="")
        print("C_EXP: {}".format(self.c_exp_string))
