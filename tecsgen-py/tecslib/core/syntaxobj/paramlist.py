# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/syntaxobj/paramlist.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

from tecslib.core.syntaxobj.namedlist import NamedList
from tecslib.core.syntaxobj.node import BDNode


# 関数パラメータリスト
class ParamList(BDNode):
    # @param_list:: NamedList : item: ParamDecl

    def __init__(self, paramdecl):
        super().__init__()
        self.param_list = NamedList(paramdecl, "parameter")
        for pd in self.param_list.get_items():
            pd.set_owner(self)   # ParamDecl

    def add_param(self, paramdecl):
        if paramdecl is None:    # 既にエラー
            return

        self.param_list.add_item(paramdecl)
        paramdecl.set_owner(self)   # ParamDecl

    def get_items(self):
        return self.param_list.get_items()

    #=== size_is, count_is, string の引数の式をチェック
    # 変数は前方参照可能なため、関数頭部の構文解釈が終わった後にチェックする
    def check_param(self):
        from tecslib.core.types import IntType, VoidType

        for i in self.param_list.get_items():
            if i is None:                       # i == None : エラー時
                continue

            # Ruby では if 節の中で代入された局所変数も nil として参照できる
            val = None
            val2 = None

            if type(i.get_type()) is VoidType:
                # 単一の void 型はここにはこない
                self.cdl_error("S2027 '$1' parameter cannot be void type", i.get_name())

            size = i.get_size()                 # Expression
            if size:
                val = size.eval_const(self.param_list)
                if val is None:                 # 定数式でないか？
                    # mikan 変数を含む式：単一の変数のみ OK
                    type_ = size.get_type(self.param_list)
                    if not isinstance(type_, IntType):
                        self.cdl_error("S2017 size_is argument is not integer type")
                    else:
                        size.check_dir_for_param(self.param_list, i.get_direction(), "size_is")
                else:
                    if val != int(val):
                        self.cdl_error("S2018 \'$1\' size_is parameter not integer",
                                       i.get_declarator().get_identifier())
                    elif val <= 0:
                        self.cdl_error("S2019 \'$1\' size_is parameter negative or zero",
                                       i.get_declarator().get_identifier())

            max_ = i.get_max()
            if max_:
                val2 = max_.eval_const(self.param_list)
                if val2 is None:
                    self.cdl_error("S2028 '$1' max (size_is 2nd parameter) not constant", i.get_name())
                elif val2 != int(val2) or val2 <= 0:
                    self.cdl_error("S2029 '$1' max (size_is 2nd parameter) negative or zero, or not integer",
                                   i.get_name())

            if val is not None and val2 is not None:
                if val < val2:
                    self.cdl_warning("W3005 '$1' size_is always lower than max. max is ignored",
                                     i.get_name())
                    i.clear_max()
                else:
                    self.cdl_error("S2030 '$1' both size_is and max are const. size_is larger than max",
                                   i.get_name())

            count = i.get_count()               # Expression
            if count:
                val = count.eval_const(self.param_list)
                if val is None:                 # 定数式でないか？
                    # mikan 変数を含む式：単一の変数のみ OK
                    type_ = count.get_type(self.param_list)
                    if not isinstance(type_, IntType):
                        self.cdl_error("S2020 count_is argument is not integer type")
                    else:
                        count.check_dir_for_param(self.param_list, i.get_direction(), "count_is")
                else:
                    if val != int(val):
                        self.cdl_error("S2021 \'$1\' count_is parameter not integer",
                                       i.get_declarator().get_identifier())
                    elif val <= 0:
                        self.cdl_error("S2022 \'$1\' count_is parameter negative or zero",
                                       i.get_declarator().get_identifier())

            string = i.get_string()             # Expression
            if string != -1 and string:
                val = string.eval_const(self.param_list)
                if val is None:                 # 定数式でないか？
                    # mikan 変数を含む式：単一の変数のみ OK
                    type_ = string.get_type(self.param_list)
                    if not isinstance(type_, IntType):
                        self.cdl_error("S2023 string argument is not integer type")
                    else:
                        string.check_dir_for_param(self.param_list, i.get_direction(), "string")
                else:
                    if val != int(val):
                        self.cdl_error("S2024 \'$1\' string parameter not integer",
                                       i.get_declarator().get_identifier())
                    elif val <= 0:
                        self.cdl_error("S2025 \'$1\' string parameter negative or zero",
                                       i.get_declarator().get_identifier())

    def check_struct_tag(self, kind):
        for p in self.param_list.get_items():
            p.check_struct_tag(kind)

    #=== Push Pop Allocator が必要か？
    # Transparent RPC の場合 (oneway かつ) in の配列(size_is, count_is, string のいずれかで修飾）がある
    def need_PPAllocator(self, b_opaque=False):
        for i in self.param_list.get_items():
            if i.need_PPAllocator(b_opaque):
                return True
        return False

    def find(self, name):
        return self.param_list.get_item(name)

    #== ParamList# 文字列化
    #b_name:: Bool: パラメータ名を含める
    def to_str(self, b_name):
        string = "("
        delim = ""
        for paramdecl in self.param_list.get_items():
            decl = paramdecl.get_declarator()
            string += delim + str(decl.get_type())
            if b_name:
                string += " " + str(decl.get_name())
            string += decl.get_type_post()
            delim = ", "
        string += ")"
        return string

    def show_tree(self, indent):
        print("  " * indent, end="")
        print("ParamList: {}".format(self.locale_str()))
        self.param_list.show_tree(indent + 1)
