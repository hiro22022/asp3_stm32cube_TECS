# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/componentobj/join.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

import copy
import sys

from tecslib.core import globals as G
from tecslib.core.plugin_module import PluginModule
from tecslib.core.syntaxobj.node import BDNode
from tecslib.core.toplevel import dbgPrint, print_exception
from tecslib.rubylib.symbol import Sym


def _ruby_at(lst, idx):
    """Ruby の Array#[] 互換（範囲外は None）"""
    if lst is None or idx < 0 or idx >= len(lst):
        return None
    return lst[idx]


def _ruby_aset(lst, idx, val):
    """Ruby の Array#[]= 互換（自動拡張）"""
    while len(lst) <= idx:
        lst.append(None)
    lst[idx] = val


class Join(BDNode, PluginModule):
# 結合の左辺
# @name:: string : 属性名 or 呼び口名
# @subscript:: nil: not array, -1: subscript not specified, >=0: array_subscript
# @definition:: Port, Decl(attribute or var)
#
# 結合の右辺
# @rhs:: Expression | initializer ( array of Expression | initializer (Expression | C_EXP) )
# available if definition is Port
# @cell_name:: string : 右辺のセルの名前
# @cell:: Cell  : 右辺のセル
# @celltype:: Celltype : 右辺のセルタイプ
# @port_name:: string : 右辺の受け口名
# @port:: Port : 右辺の受け口
# @array_member:: rhs array : available only for first appear in the same name
# @array_member2:: Join array : available only for first appear in the same name
# @rhs_subscript:: nil : not array, >=0: 右辺の添数
#

# @through_list::  @cp_through_list + @region_through_list + @ep_through_list
#  以下の構造を持つ（@cp_through_list の構造は共通）
# @cp_through_list::  呼び口に指定された through
#   [ [plugin_name, cell_name, plugin_arg], [plugin_name2, cell_name2, plugin_arg], ... ]
# @ep_through_list::  受け口に指定された through
#   [ [plugin_name, cell_name, plugin_arg], [plugin_name2, cell_name2, plugin_arg], ... ]
# @region_through_list::  region に指定された through
#   [ [plugin_name, cell_name, plugin_arg, region], [plugin_name2, cell_name2, plugin_arg, region2], ... ]
#
# @through_generated_list:: [Plugin_class object, ...]: @through_list に対応
# @region_through_generated_list:: [Plugin_class object, ...]: @region_through_list に対応
#

    through_count = {}
    plugin_creating_join = None
    start_region = None
    end_region = None
    through_type = None
    region_count = None

    #=== Join# 初期化
    #name:: string: 名前（属性名、呼び口名）
    #subscript:: Nil=非配列, -1="[]", N="[N]"
    #rhs:: Expression: 右辺の式
    def __init__(self, name, subscript, rhs, locale=None):
        from tecslib.core.expression import Expression
        # dbgPrint "Join#new: #{name}, #{subscript} #{rhs.eval_const(nil)}\n"
        dbgPrint("Join#new: {}, {}\n".format(name, subscript))

        super().__init__()
        if locale:
            self.locale = locale

        self.name = name
        if type(subscript) is Expression:
            # mikan 配列添数が整数であることを未チェック
            self.subscript = subscript.eval_const(None)
            if self.subscript is None:
                self.cdl_error("S1099 array subscript not constant")
        else:
            self.subscript = subscript

        self.rhs = rhs
        self.definition = None
        self.cell_name = None
        self.cell = None
        self.celltype = None
        self.port = None
        self.port_name = None
        self.rhs_subscript = None
        self.array_member = None
        self.array_member2 = None

        # 配列要素を設定
        # 本当は、初出の要素のみ設定するのが適当
        # new_join で add_array_member の中で初出要素の array_member に対し設定する
        if self.subscript == -1:
            self.array_member = [self]
            self.array_member2 = [self]
        elif self.subscript is not None:
            self.array_member = []
            self.array_member2 = []
            # Python list は自動拡張しないので必要分を確保
            while len(self.array_member) <= self.subscript:
                self.array_member.append(None)
            while len(self.array_member2) <= self.subscript:
                self.array_member2.append(None)
            self.array_member[self.subscript] = self
            self.array_member2[self.subscript] = self

        self.through_list = []
        self.cp_through_list = []
        self.ep_through_list = []
        self.region_through_list = []
        self.through_generated_list = []
        self.region_through_generated_list = []

    #===  Join# 左辺に対応する celltype の定義を設定するとともにチェックする
    # STAGE:   S
    #
    #     代入可能かチェックする
    #definition:: Decl (attribute,varの時) または Port (callの時) または nil (definition が見つからなかった時)

    def set_definition(self, definition):

        dbgPrint("set_definition: {}.{} = {}\n".format(
            self.owner.get_name(), self.name, definition.__class__.__name__))

        # 二重チェックの防止
        if self.definition:
            # set_definition を個別に行うケースで、二重に行われる可能性がある（異常ではない）
            # 二重に set_definition が実行されると through が二重に適用されてしまう
            # cdl_warning( "W9999 $1, internal error: set_definition duplicate", @name )
            return

        self.definition = definition

        # mikan 左辺値、右辺値の型チェックなど
        from tecslib.core.syntaxobj.decl import Decl
        from tecslib.core.componentobj.port import Port
        if type(self.definition) is Decl:
            self.check_var_init()
        elif type(self.definition) is Port:
            self.check_call_port_init()
            if self.definition.get_port_type() == "CALL":   # :ENTRY ならエラー。無視しない
                self.check_and_gen_through()
                self.create_allocator_join()  # through プラグイン生成した後でないと、挿入前のセルのアロケータを結合してしまう
        elif self.definition is None:
            self.cdl_error("S1117 \'$1\' not in celltype", self.name)
        else:
            raise Exception("UnknownToken")

    #=== Join# 変数の初期化チェック
    def check_var_init(self):
        # attribute, var の場合
        if self.definition.get_kind() == "ATTRIBUTE":
#        check_cell_cb_init( definition.get_type, @rhs )
            # 右辺で初期化可能かチェック
            self.definition.get_type().check_init(
                self.locale, self.definition.get_identifier(), self.rhs, "ATTRIBUTE")
        elif self.definition.get_kind() == "VAR":
            # var は初期化できない
            self.cdl_error("S1100 $1: cannot initialize var", self.name)
        else:
            # Bug trap
            raise Exception("UnknownDeclKind")

    #=== Join# 呼び口の初期化チェック
    def check_call_port_init(self):
        ### Port
        from tecslib.core.componentobj.cell import Cell
        from tecslib.core.componentobj.compositecelltype import CompositeCelltype
        from tecslib.core.componentobj.namespace import Namespace
        from tecslib.core.componentobj.port import Port
        from tecslib.core.expression import Expression
        from tecslib.core.plugin_module import _import_plugin_class

        ThroughPlugin = _import_plugin_class("ThroughPlugin")

        dbgPrint("Join#check_call_port_init:cell.call={}.{}\n".format(
            self.owner.get_name(), self.name))

        # 左辺は受け口か（受け口を初期化しようとしている）？
        if self.definition.get_port_type() == "ENTRY":
            self.cdl_error("S1101 \'$1\' cannot initialize entry port", self.name)
            return

#      # 配列添数の整合性チェック
#      # 呼び口の定義で、非配列なら添数なし、添数なし配列なら添数なし、添数あり配列なら添数あり
        as_ = self.definition.get_array_size()
        if (self.subscript is None and as_ is not None):
            self.cdl_error("S1102 $1: must specify array subscript here", self.name)
        elif (self.subscript is not None and as_ is None):
            self.cdl_error("S1103 $1: cannot specify array subscript here", self.name)
#    if @subscript == nil then
#      if as != nil then
#        cdl_error( "S1103 $1: need array subscript" , @name )
#      end
#    elsif @subscript == -1 then
#      if as != "[]" then
#        cdl_error( "S1104 $1: need array subscript number. ex. \'[0]\'" , @name )
#      end
#    else # @subscript >0
#      if as == nil then
#        cdl_error( "S1105 $1: cannot specify array subscript here" , @name )
#      elsif as == "[]" then
#        cdl_error( "S1106 $1: cannot specify array subscript number. use \'[]\'" , @name )
#      end
#    end

        # mikan Expression の get_type で型導出させる方がスマート
        #(1) '=' の右辺は "Cell.ePort" の形式か？
        #     演算子は "."  かつ "." の左辺が :IDENTIFIER
        #     "." の右辺はチェック不要 (synatax 的に :IDENTIFIER)
        #(2) "Cell" は存在するか？（名前が一致するものはあるか）
        #(3) "Cell" は cell か？
        #(4) "Cell" の celltype は有効か？ (無効なら既にエラー）
        #(5) "ePort" は "Cell" の celltype 内に存在するか？
        #(6) "ePort" は entry port か？
        #(7) signature は一致するか
        #(8) 右辺の配列(受け口配列)

        # 右辺がない（以前の段階でエラー）
        if not self.rhs:
            return

        # cCall = composite.cCall; のチェック．この形式は属性用
        # 呼び口を export するには cCall => composite.cCall; の形式を用いる
        if type(self.rhs) is list and self.rhs[0] == "COMPOSITE":
            self.cdl_error("S1107 to export port '$1', use \'cCall => composite.cCall\'", self.name)
            return
        elif type(self.rhs) is not Expression:
            raise Exception("Unknown bug. specify -t to find problem in source")

        # 右辺の Expression の要素を取り出す
        ret = self.rhs.analyze_cell_join_expression()
        if ret is None:   #1
            self.cdl_error("S1108 $1: rhs not \'Cell.ePort\' form", self.name)
            return

        nsp, self.rhs_subscript, self.port_name = ret[0], ret[1], ret[2]
        self.cell_name = nsp.get_name()     # mikan ns::cellname の形式の考慮

        # composite の定義の中なら object は結合先 cell か、見つからなければ nil が返る
        # composite の定義外なら false が返る
        object = CompositeCelltype.find_in_current(self.cell_name)
        if object is False:
            # p nsp.get_path_str, nsp.get_path
            object = Namespace.find(nsp)    #1
            in_composite = False
        else:
            if len(nsp.get_path()) != 1:
                self.cdl_error("$1 cannot have path", nsp.get_path_str())
            in_composite = True

        if object is None:                                             # (2)
            self.cdl_error("S1109 \'$1\' not found", str(nsp))
        elif type(object) is not Cell:                          # (3)
            self.cdl_error("S1110 \'$1\' not cell", str(nsp))
        else:
            dbgPrint("set_definition: set_f_ref {}.{} => {}\n".format(
                self.owner.get_name(), self.name, object.get_name()))
            object.set_f_ref()

            # 右辺のセルのセルタイプ
            celltype = object.get_celltype()

            if celltype:                                                # (4)
                object2 = celltype.find(self.port_name)
                if object2 is None:                                        # (5)
                    self.cdl_error("S1111 \'$1\' not found", self.port_name)
                elif (type(object2) is not Port
                        or object2.get_port_type() != "ENTRY"):                  # (6)
                    self.cdl_error("S1112 \'$1\' not entry port", self.port_name)
                elif self.definition.get_signature() != object2.get_signature(): # (7)
                    self.cdl_error("S1113 \'$1\' signature mismatch", self.port_name)
                elif object2.get_array_size():                             # (8)
                    # 受け口配列

                    # Ruby: unless @rhs_subscript — 0 は真。Python では is None で判定する
                    if self.rhs_subscript is None:
                        # 右辺に添数指定がなかった
                        self.cdl_error("S1114 \'$1\' should be array", self.port_name)
                    else:

                        as_ = object2.get_array_size()
                        if (isinstance(as_, int) and as_ <= self.rhs_subscript):
                            # 受け口配列の大きさに対し、右辺の添数が同じか大きい
                            self.cdl_error("S1115 $1[$2]: subscript out of range (< $3)",
                                           self.port_name, self.rhs_subscript, as_)
                        else:
                            dbgPrint("Join OK {}.{}[{}] = {}.{} {}\n".format(
                                self.owner.get_name(), self.name, self.rhs_subscript,
                                object.get_name(), self.port_name, self))
                            self.cell = object
                            self.celltype = celltype
                            self.port = object2
                            # 右辺のセルの受け口 object2 を参照済みにする
                            # object2: Port, @definition: Port
                            self.cell.set_entry_port_max_subscript(self.port, self.rhs_subscript)

                        # debug
                        dbgPrint("Join set_definition: rhs: {}  {}\n".format(
                            self.cell, self.cell.get_name() if self.cell else None))

                elif self.rhs_subscript is not None:
                    # 受け口配列でないのに右辺で添数指定されている
                    self.cdl_error("S1116 \'$1\' entry port is not array", self.port_name)
                else:
                    dbgPrint("Join OK {}.{} = {}.{} {}\n".format(
                        self.owner.get_name(), self.name, object.get_name(), self.port_name, self))
                    self.cell = object
                    self.port = object2
                    self.celltype = celltype

                    # 右辺のセル object の受け口 object2 を参照済みにする
                    # object2: Port, @definition: Port

                    # debug
                    # p "rhs:  #{@cell}  #{@cell.get_name}"
                # end of port (object2) チェック

                #else
                #  celltype == nil (すでにエラー)
            # end of celltyep チェック

            if (ThroughPlugin is None
                    or not isinstance(self.owner.get_plugin(), ThroughPlugin)):
                # 受け口の through を設定
                dbgPrint("ep_through_list: cell={} len={}\n".format(
                    object.get_name(), len(object.get_ep_through_list())))
                for ent in object.get_ep_through_list():
                    dbgPrint("Join name={} port_name={} ep_through={}\n".format(
                        self.name, self.port.get_name(), ent[0]))
                    if ent[0] == self.port.get_name():
                        plugin_name = str(ent[1])
                        cell_name = Sym(str(ent[1]) + "_")
                        plugin_arg = ent[2]
                        print("ep_through: plugin_name={}\n".format(plugin_name))
                        self.ep_through_list.append([plugin_name, cell_name, plugin_arg])
            self.check_region(object)

        # end of cell (object) チェック

    #=== Join# アロケータの結合を生成
    # STAGE: S
    #cell::  呼び口の結合先のセル
    #
    # ここでは呼び口側に生成されるアロケータ呼び口の結合を生成
    # 受け口側は Cell の set_specifier_list で生成
    #  a[*] の内容は Cell の set_specifier_list を参照
    def create_allocator_join(self):

        cell = self.get_rhs_cell2()   # 右辺のセルを得る
        port = self.get_rhs_port2()

        if (cell and cell.get_allocator_list()):      # cell == nil なら既にエラー

            dbgPrint("create_allocator_join: {}.{}=>{}\n".format(
                self.owner.get_name(), self.name,
                cell.get_name() if cell else "nil"))

            for a in cell.get_allocator_list():

                if (a[0 + 1] == port and a[1 + 1] == self.rhs_subscript):
                    # 名前の一致するものの結合を生成する
                    # 過不足は、別途チェックされる
                    cp_name = Sym("{}_{}_{}".format(self.name, a[2 + 1], a[3 + 1]))
                    # p "creating allocator join #{cp_name} #{@subscript} #{a[1+1]}"
                    join = Join(cp_name, self.subscript, a[4 + 1], self.locale)

                    #debug
                    dbgPrint("create_allocator_join: {}.{} [{}] {}\n".format(
                        self.owner.get_name(), cp_name, self.subscript, self.name))
                    self.owner.new_join_inst(join)
                else:
                    dbgPrint("create_allocator_join:3 not {}.{} {}\n".format(
                        self.owner.get_name(), a[0 + 1], self.name))

    #=== Join# リージョン間の結合をチェック
    # リージョン間の through による @region_through_list の作成
    # 実際の生成は check_and_gen_through で行う
    # mikan Cell#distance とRegion へたどり着くまでための処理に共通部分が多い
    def check_region(self, object):

        from tecslib.core.plugin_module import _import_plugin_class
        from tecslib.core.syntaxobj.cdlstring import CDLString

        ThroughPlugin = _import_plugin_class("ThroughPlugin")

        #debug
        dbgPrint("check_region {}.{} => {}\n".format(
            self.owner.get_name(), self.name, object.get_name()))
        # print "DOMAIN: check_region #{@owner.get_name}.#{@name} => #{object.get_name}\n"

        # プラグインで生成されたなかでは生成しない
        # さもないとプラグイン生成されたものとの間で、無限に生成される
##    if Generator.get_nest >= 1 then
##    if Generator.get_plugin then     # mikan これは必要？ (意味解析段階での実行になるので不適切)
        if ThroughPlugin is not None and isinstance(self.owner.get_plugin(), ThroughPlugin):
            # プラグイン生成されたセルの場合、結合チェックのみ
            return

        # region のチェック
        r1 = self.owner.get_region()      # 呼び口セルの region
        r2 = object.get_region()      # 受け口セルの region

        if r1 is not r2:      # 同一 region なら呼出し可能

            f1 = r1.get_family_line()
            len1 = len(f1)
            f2 = r2.get_family_line()
            len2 = len(f2)

            # 不一致になるところ（兄弟）を探す
            i = 1  # i = 0 は :RootRegion なので必ず一致
            while (i < len1 and i < len2):
                if (f1[i] != f2[i]):
                    break
                i += 1

            sibling_level = i     # 兄弟となるレベル、もしくはどちらか一方が終わったレベル

            # Ruby の Array#[] は範囲外で nil。Python は IndexError になるため安全に取る。
            def _ruby_at(lst, idx):
                return lst[idx] if 0 <= idx < len(lst) else None

            dbgPrint("sibling_level: {}\n".format(i))
            if _ruby_at(f1, i):
                dbgPrint("from: {}\n".format(f1[i].get_name()))
            if _ruby_at(f2, i):
                dbgPrint("to: {}\n".format(f2[i].get_name()))

            if _ruby_at(f1, sibling_level) and _ruby_at(f2, sibling_level):
                b_to_through = True
            else:
                b_to_through = False

            # 呼び側について呼び元のレベルから兄弟レベルまで（out_through をチェックおよび挿入）
            i = len1 - 1
            if b_to_through:
                end_level = sibling_level
            else:
                end_level = sibling_level - 1
            while i > end_level:
            # while i > sibling_level
            # while i >= sibling_level
                dbgPrint("going out from {} level={}\n".format(f1[i].get_name(), i))
                region_count = f1[i].next_out_through_count()
                out_through_list = f1[i].get_out_through_list()   # [ plugin_name, plugin_arg ]
                domain_type = f1[i].get_domain_type()
                class_type = f1[i].get_class_type()
                domain_through = None
                class_through = None
                if domain_type:
                    domain_through = domain_type.add_through_plugin(self, f1[i], f1[i - 1], Sym("OUT_THROUGH"))
                    if domain_through is None:
                        self.cdl_error("S9999 $1: going out from regin '$2' not permitted by domain '$3'",
                                       self.name, f1[i].get_name(), domain_type.get_name())
                elif class_type:
                    class_through = class_type.add_through_plugin(self, f1[i], f1[i - 1], Sym("OUT_THROUGH"))
                    if class_through is None:
                        self.cdl_error("S9999 $1: going out from regin '$2' not permitted by class '$3'",
                                       self.name, f1[i].get_name(), class_type.get_name())
                elif len(out_through_list) == 0:
                    self.cdl_error("S1118 $1: going out from region \'$2\' not permitted", self.name, f1[i].get_name())

                for ol in out_through_list:
                    if ol[0]:    # plugin_name が指定されていなければ登録しない
                        plugin_arg = CDLString.remove_dquote(ol[1])
                        through = [ol[0], Sym("Join_out_through_"), plugin_arg, f1[i], f1[i - 1], Sym("OUT_THROUGH"), region_count]
                        self.region_through_list.append(through)
                if domain_through and len(domain_through) > 0:
                    through = [domain_through[0], Sym("Join_domain_out_through_"), domain_through[1], f1[i], f1[i - 1], Sym("OUT_THROUGH"), region_count]
                    self.region_through_list.append(through)
                if class_through and len(class_through) > 0:
                    through = [class_through[0], Sym("Join_class_out_through_"), class_through[1], f1[i], f1[i - 1], Sym("OUT_THROUGH"), region_count]
                    self.region_through_list.append(through)
                i -= 1

            # 兄弟レベルにおいて（to_through をチェックおよび挿入）
            if _ruby_at(f1, sibling_level) and _ruby_at(f2, sibling_level):
                dbgPrint("going from {} to {}\n".format(
                    f1[sibling_level].get_name(), f2[sibling_level].get_name()))
                found = 0
                region_count = f1[i].next_to_through_count(f2[sibling_level].get_name())   # to_through の region カウント
                for t in f1[sibling_level].get_to_through_list():
                    if t[0][0] == f2[sibling_level].get_name():   # region 名が一致するか ?
                        if t[1]:    # plugin_name が指定されていなければ登録しない
                            plugin_arg = CDLString.remove_dquote(t[2])
                            through = [t[1], Sym("Join_to_through__"), plugin_arg, f1[sibling_level], f2[sibling_level], Sym("TO_THROUGH"), region_count]
                            self.region_through_list.append(through)
                        found = 1
                domain_type = f1[sibling_level].get_domain_type()
                class_type = f1[sibling_level].get_class_type()
                domain_through = None
                class_through = None
                if domain_type:
                    domain_through = domain_type.add_through_plugin(
                        self, f1[sibling_level], f2[sibling_level], Sym("TO_THROUGH"))
                    if domain_through is None:
                        self.cdl_error("S9999 $1: going from regin '$2' not permitted by domain'$3'",
                                       self.name, f1[sibling_level].get_name(),
                                       f2[sibling_level].get_domain_type().get_name())
                    if domain_through and len(domain_through) > 0:
                        through = [domain_through[0], Sym("Join_domain_to_through_"), domain_through[1],
                                   f1[sibling_level], f2[sibling_level], Sym("TO_THROUGH"), region_count]
                        self.region_through_list.append(through)
                    found = 1     # ２重エラー抑制のため、いずれにせよ found とする
                elif class_type:
                    class_through = class_type.add_through_plugin(
                        self, f1[sibling_level], f2[sibling_level], Sym("TO_THROUGH"))
                    if class_through is None:
                        self.cdl_error("S9999 $1: going from regin '$2' not permitted by class'$3'",
                                       self.name, f1[sibling_level].get_name(),
                                       f2[sibling_level].get_class_type().get_name())
                    if class_through and len(class_through) > 0:
                        through = [class_through[0], Sym("Join_class_to_through_"), class_through[1],
                                   f1[sibling_level], f2[sibling_level], Sym("TO_THROUGH"), region_count]
                        self.region_through_list.append(through)
                    found = 1     # ２重エラー抑制のため、いずれにせよ found とする
                region_count = f2[i].next_from_through_count(f1[sibling_level].get_name())   # form_through の region カウント
                for t in f2[sibling_level].get_from_through_list():
                    if t[0][0] == f1[sibling_level].get_name():   # region 名が一致するか ?
                        if t[1]:    # plugin_name が指定されていなければ登録しない
                            plugin_arg = CDLString.remove_dquote(t[2])
                            through = [t[1], Sym("Join_from_through__"), plugin_arg,
                                       f1[sibling_level], f2[sibling_level], Sym("FROM_THROUGH"), region_count]
                            self.region_through_list.append(through)
                        found = 1

                if found == 0:
                    self.cdl_error("S1119 $1: going from region \'$2\' to \'$3\' not permitted",
                                   self.name, f1[sibling_level].get_name(), f2[sibling_level].get_name())

            # 受け側について兄弟レベルから受け側のレベルまで（in_through をチェックおよび挿入）
            if b_to_through:
                i = sibling_level + 1      # to_through を経た場合、最初の in_through は適用しない
            else:
                i = sibling_level
            while i < len2:
                dbgPrint("going in to {} level={}\n".format(f2[i].get_name(), i))
                region_count = f2[i].next_in_through_count()
                in_through_list = f2[i].get_in_through_list()   # [ plugin_name, plugin_arg ]
                domain_type = f2[i].get_domain_type()
                class_type = f2[i].get_class_type()
                if domain_type:
                    domain_through = domain_type.add_through_plugin(self, f2[i - 1], f2[i], Sym("IN_THROUGH"))
                    if domain_through is None:
                        self.cdl_error("S9999 $1: going in from regin '$2' to '$3' not permitted by domain '$4'",
                                       self.name, f2[i - 1].get_name(), f2[i].get_name(), domain_type.get_name())
                    if domain_through and len(domain_through) > 0:
                        through = [domain_through[0], Sym("Join_domain_in_through_"), domain_through[1],
                                   f2[i - 1], f2[i], Sym("IN_THROUGH"), region_count]
                        self.region_through_list.append(through)
                elif class_type:
                    class_through = class_type.add_through_plugin(self, f2[i - 1], f2[i], Sym("IN_THROUGH"))
                    if class_through is None:
                        self.cdl_error("S9999 $1: going in from regin '$2' to '$3' not permitted by class '$4'",
                                       self.name, f2[i - 1].get_name(), f2[i].get_name(), class_type.get_name())
                    if class_through and len(class_through) > 0:
                        through = [class_through[0], Sym("Join_class_in_through_"), class_through[1],
                                   f2[i - 1], f2[i], Sym("IN_THROUGH"), region_count]
                        self.region_through_list.append(through)
                elif len(in_through_list) == 0:
                    self.cdl_error("S1120 $1: going in to region \'$2\' not permitted", self.name, f2[i].get_name())
                for il in in_through_list:
                    if il[0]:    # plugin_name が指定されていなければ登録しない
                        plugin_arg = CDLString.remove_dquote(il[1])
                        through = [il[0], Sym("Join_in_through_"), plugin_arg, f2[i - 1], f2[i], Sym("IN_THROUGH"), region_count]
                        self.region_through_list.append(through)
                i += 1

    #=== Join# 生成しないリージョンへの結合かチェック
    # 右辺のセルが、生成されないリージョンにあればエラー
    # 右辺は、プラグイン生成されたセルがあれば、それを対象とする
    def check_region2(self):
        lhs_cell = self.owner

        # 生成しないリージョンのセルへの結合か？
        # if join.get_cell && ! join.get_cell.is_generate? then
        # if get_rhs_cell && ! get_rhs_cell.is_generate? then # composite セルがプロタイプ宣言の場合例外
        # print "Link root: (caller #{@owner.get_name}) '#{@owner.get_region.get_link_root.get_name}'"
        # print " #{@owner.get_region.get_link_root == get_rhs_region.get_link_root ? "==" : "!="} "
        # print "'#{get_rhs_region.get_link_root.get_name}'  (callee #{@cell_name})\n"

        rhs_region = self.get_rhs_region()
        if rhs_region:
            dbgPrint("check_region2 {} => {}{}\n".format(
                lhs_cell.get_name(), rhs_region.get_path_string(), self.rhs.to_s()))

            # if get_rhs_region.is_generate? != true then  #3
            if self.owner.get_region().get_link_root() != rhs_region.get_link_root():
                self.cdl_error("S1121 \'$1\' in region \'$2\' cannot be directly joined $3 in  $4",
                               lhs_cell.get_name(),
                               lhs_cell.get_region().get_namespace_path().get_path_str(),
                               self.rhs.to_s(),
                               rhs_region.get_namespace_path().get_path_str())
        else:
            # rhs のセルが存在しなかった (既にエラー)
            pass

    def get_definition(self):
        return self.definition

    #=== Join# specifier を設定
    # STAGE: B
    # set_specifier_list は、join の解析の最後で呼び出される
    # through 指定子を設定
    #  check_and_gen_through を呼出して、through 生成
    def set_specifier_list(self, specifier_list):

        from tecslib.core.syntaxobj.cdlstring import CDLString

        for s in specifier_list:
            if s[0] == "THROUGH":
                # set plugin_name
                plugin_name = str(s[1])
                plugin_name = plugin_name[0].upper() + plugin_name[1:]     # 先頭文字を大文字に : ruby のクラス名の制約

                # set cell_name
                cell_name = Sym(str(s[1]) + "_")

                # set plugin_arg
                plugin_arg = CDLString.remove_dquote(str(s[2]))
                # plugin_arg = s[2].to_s.gsub( /\A"(.*)/, '\1' )   # 前後の "" を取り除く
                # plugin_arg.sub!( /(.*)"\z/, '\1' )

                self.cp_through_list.append([plugin_name, cell_name, plugin_arg])

    #=== Join# through のチェックと生成
    # new_join の中の check_region で region 間の through が @region_through に設定される
    # set_specifier で呼び口の結合で指定された through が @cp_through 設定される
    # その後、このメソッドが呼ばれる
    def check_and_gen_through(self):

        from tecslib.core.componentobj.cell import Cell
        from tecslib.core.componentobj.namespace import Namespace
        from tecslib.core.componentobj.port import Port
        from tecslib.core.plugin_module import _import_plugin_class

        ThroughPlugin = _import_plugin_class("ThroughPlugin")

        dbgPrint("check_and_gen_through {}.{}\n".format(self.owner.get_name(), self.name))

        if type(self.definition) is not Port:
            self.cdl_error("S1123 $1 : not port: \'through\' can be specified only for port", self.name)
            return
        if len(self.cp_through_list) > 0:
            # is_empty? must check before is_omit?
            if self.definition.get_signature() and self.definition.get_signature().is_empty():
                self.cdl_warning("W9999 'through' is specified for empty signature, ignored")
                return
            elif self.definition.is_omit():
                self.cdl_warning("W9999 'through' is specified for omitted port, ignored")
                return

        self.through_list = self.cp_through_list + self.region_through_list + self.ep_through_list
        # 後から @cp_through_list と @region_through_list に分けたため、このような実装になった

        if self.through_list:           # nil when the join is not Port
            len_ = len(self.through_list)    # through が連接している数
        else:
            len_ = 0
        cp_len = len(self.cp_through_list)
        rgn_len = len(self.region_through_list)
        # ep_len = @ep_through_list.length       # 使わない

        if self.owner.is_in_composite() and len_ > 0:
            self.cdl_error("S1177 cannot specify 'through' in composite in current version")
            return

        if ThroughPlugin is None and len_ > 0:
            self.cdl_error("P2001 $1.rb : fail to load plugin", "ThroughPlugin")
            return

        # 連続した through について、受け口側から順にセルを生成し解釈する
        i = len_ - 1
        while i >= 0:

            through = self.through_list[i]
            plugin_name = through[0]
            generating_cell_name = through[1]
            plugin_arg = through[2]

            if i != len_ - 1:

                try:
                    next_plugin = _ruby_at(self.through_generated_list, i + 1)
                    next_cell_nsp = next_plugin.get_cell_namespace_path()
                    next_port_name = next_plugin.get_through_entry_port_name()
                    next_port_subscript = next_plugin.get_through_entry_port_subscript()
                except Exception as evar:
                    self.cdl_error("S1124 $1: plugin function failed: \'get_through_entry_port_name\'", plugin_name)
                    print_exception(evar)
                    i -= 1
                    continue

                next_cell = Namespace.find(next_cell_nsp)    #1
                if next_cell is None:
                    # p "next_cell_path: #{next_cell_nsp.get_path_str}"
                    self.cdl_error("S1125 $1: not generated cell \'$2\'",
                                   next_plugin.__class__.__name__,
                                   next_cell_nsp.get_path_str())
                    return

            else:
                # 最後のセルの場合、次のセルの名前、ポート名
                next_cell = self.cell
                next_port_name = self.port_name
                next_port_subscript = self.rhs_subscript

                if next_cell is None:
                    # 結合先がない
                    return

            if i < cp_len:
                prev_region = self.owner.get_region()     # 呼び元セルのリージョン
            elif i < (cp_len + rgn_len):
                prev_region = self.through_list[i][3]   # region 間プラグイン
            else:
                if rgn_len > 0:
                    prev_region = self.through_list[cp_len + rgn_len - 1][3]   # reion 間のプラグインの一番後ろ
                else:
                    prev_region = self.owner.get_region()

            if cp_len <= i and i < (cp_len + rgn_len):
                # region_through_list 部分
                # region から @cell_name.@port_name への through がないか探す
                # rp = @through_list[i][3].find_cell_port_through_plugin( @cell_name, @port_name ) #762
                rp = self.through_list[i][3].find_cell_port_through_plugin(
                    self.cell.get_global_name(), self.port_name, self.rhs_subscript)
                # @through_list[i] と @region_through_list[i-cp_len] は同じ
                # 共用しないようにするには、見つからなかったことにすればよい
                # rp = nil
            else:
                # region 以外のものは共有しない
                # 呼び口側に指定されているし、plugin_arg が異なるかもしれない
                rp = None

            if rp is None:
                plClass = self.load_plugin(plugin_name, ThroughPlugin)
                if plClass:
                    self.gen_through_cell_code_and_parse(
                        plugin_name, i, prev_region, next_cell, next_port_name, next_port_subscript, plClass)
            else:
                # 見つかったものを共用する
                _ruby_aset(self.through_generated_list, i, rp)

            if cp_len <= i and i < (cp_len + rgn_len):
                # @through_generated_list のうち @region_through_listに対応する部分
                _ruby_aset(self.region_through_generated_list, i - cp_len, _ruby_at(self.through_generated_list, i))
                if rp is None:
                    # 生成したものを region(@through_list[i][3]) のリストに追加
                    # @through_list[i][3].add_cell_port_through_plugin( @cell_name, @port_name, @through_generated_list[i] ) #762
                    self.through_list[i][3].add_cell_port_through_plugin(
                        self.cell.get_global_name(), self.port_name, self.rhs_subscript,
                        _ruby_at(self.through_generated_list, i))

            if i == 0:
                # 最も呼び口側のセルは、CDL 上の結合がないため、参照されたことにならない
                if _ruby_at(self.through_generated_list, 0) is None:
                    return  # plugin_object の生成に失敗している
                cell = Namespace.find(_ruby_at(self.through_generated_list, 0).get_cell_namespace_path())    #1
                if type(cell) is Cell:
                    cell.set_f_ref()

            i -= 1

    def get_through_count(self, name):
        sym = Sym(str(name)) if not isinstance(name, Sym) else name
        if sym in Join.through_count:
            Join.through_count[sym] += 1
        else:
            Join.through_count[sym] = 0
        return Join.through_count[sym]

    #=== Join# through プラグインを呼び出して CDL 生成させるとともに、import する
    def gen_through_cell_code_and_parse(self, plugin_name, i, prev_region, next_cell,
                                        next_port_name, next_port_subscript, plClass):

        through = self.through_list[i]
        plugin_name = through[0]
        generating_cell_name = Sym("{}_{}".format(through[1], self.get_through_count(through[1])))
        plugin_arg = through[2]
        Join.start_region = prev_region
        # Ruby: through[3] は cp_through では nil（配列長3）。範囲外は nil。
        if _ruby_at(through, 3):
            # region 間の through の場合
            # @@start_region      = through[ 3 ]
            if next_cell.get_region() is Join.start_region:
                Join.end_region = Join.start_region
            else:
                Join.end_region = _ruby_at(through, 4)
            Join.through_type = _ruby_at(through, 5)
            Join.region_count = _ruby_at(through, 6)
        else:
            # 呼び口の through の場合
            # @@start_region      = @owner.get_region    # 呼び口側セルの region
            Join.end_region = next_cell.get_region() # 次のセルの region
            Join.through_type = Sym("THROUGH")             # 呼び口の through 指定
            Join.region_count = 0
        Join.plugin_creating_join = self
        caller_cell = self.owner

        try:
            plugin_object = plClass(
                Sym(str(generating_cell_name)), str(plugin_arg),
                next_cell, Sym(str(next_port_name)), next_port_subscript,
                self.definition.get_signature(), self.celltype, caller_cell)
            plugin_object.set_locale(self.locale)
        except Exception as evar:
            self.cdl_error("S1126 $1: fail to new", plugin_name)
            if self.celltype and self.definition.get_signature() and caller_cell and next_cell:
                print("signature: {} from: {} to: {} of celltype: {}\n".format(
                    self.definition.get_signature().get_name(), caller_cell.get_name(),
                    next_cell.get_name(), self.celltype.get_name()))
            print_exception(evar)
            return

        # Ruby の Array#[]= は自動拡張する
        while len(self.through_generated_list) <= i:
            self.through_generated_list.append(None)
        self.through_generated_list[i] = plugin_object

        # Region に関する情報を設定
        # 後から追加したので、new の引数外で設定
        # plugin_object.set_through_info( start_region, end_region, through_type )

        self.generate_and_parse(plugin_object)

    #プラグインへの引数で渡さないものを、一時的に記憶しておく
    # プラグインの initialize の中でコールバックして設定する

    #=== Join# ThroughPlugin の追加情報を設定する
    # このメソッドは ThroughPlugin#initialize から呼び出される
    # plugin_object を生成する際の引数では不足する情報を追加する
    @classmethod
    def set_through_info(cls, plugin_object):
        plugin_object.set_through_info(
            Join.start_region, Join.end_region, Join.through_type,
            Join.plugin_creating_join,
            Join.plugin_creating_join.get_cell(),
            Join.region_count)

    def get_name(self):
        return self.name

    #=== Join#配列添数を得る
    # @subscript の説明を参照のこと
    def get_subscript(self):
        return self.subscript

    def get_cell_name(self):         # 受け口セル名
        return self.cell_name

    def get_celltype(self):
        return self.celltype

    def get_cell(self):
        return self.cell

    #=== Join# 右辺の実セルを得る
    #    実セルとは through で挿入されたもの、composite の内部など実際に結合される先
    #    このメソッドは　get_rhs_port と対になっている
    #    このメソッドは、意味解析段階では呼び出してはならない (対象セルの意味解析が済む前には正しい結果を返さない)
    def get_rhs_cell(self):
        from tecslib.core.componentobj.namespace import Namespace
        # through 指定あり？
        if len(self.through_list) > 0 and self.through_list[0]:
            if _ruby_at(self.through_generated_list, 0):
                cell = Namespace.find(_ruby_at(self.through_generated_list, 0).get_cell_namespace_path())    #1
                # cell が nil になるのはプラグインの get_cell_namespace_path が正しくないか、
                # プラグイン生成コードがエラーになっている。
                # できの悪いプラグインが多ければ、cell == nil をはじいた方がよい。
                return cell.get_real_cell(_ruby_at(self.through_generated_list, 0).get_through_entry_port_name())
            else:
                return None            # generate に失敗している
        elif self.cell:
            return self.cell.get_real_cell(self.port_name)
        else:
            # 右辺が未定義の場合 @cell は nil (既にエラー)
            return None

    #=== Join# 右辺のセルを得る
    # 右辺のセルを得る。ただし、composite 展開されていない
    # composite 展開されたものを得るには get_rhs_cell を使う
    # プロトタイプ宣言しかされていない場合には、こちらしか使えない
    # このメソッドは get_rhs_port2 と対になっている
    def get_rhs_cell2(self):
        from tecslib.core.componentobj.namespace import Namespace
        # through 指定あり？
        if len(self.through_list) > 0 and self.through_list[0]:
            if _ruby_at(self.through_generated_list, 0):
                cell = Namespace.find(_ruby_at(self.through_generated_list, 0).get_cell_namespace_path())    #1
            else:
                cell = self.cell            # generate に失敗している
        else:
            cell = self.cell

        return cell

    #=== Join# 右辺のセルを得る
    # through は適用しないが、composite は展開した後のセル
    # (意味解析が終わっていないと、composite 展開が終わっていない)
    # このメソッドは get_rhs_port3 と対になっている
    def get_rhs_cell3(self):
        if self.cell:
            return self.cell.get_real_cell(self.port_name)

    #=== Join# 右辺のセルのリージョンを得る
    # 右辺が未定義の場合、nil を返す
    # composite の場合、実セルではなく composite cell の region を返す(composite はすべて同じ region に属する)
    # composite の cell がプロトタイプ宣言されているとき get_rhs_cell/get_real_cell は ruby の例外となる
    def get_rhs_region(self):
        from tecslib.core.componentobj.namespace import Namespace
        # through 指定あり？
        if len(self.through_list) > 0 and self.through_list[0]:
            if _ruby_at(self.through_generated_list, 0):
                cell = Namespace.find(_ruby_at(self.through_generated_list, 0).get_cell_namespace_path())    #1
                if cell:
                    return cell.get_region()
            else:
                return None       # generate に失敗している
        elif self.cell:
            return self.cell.get_region()
        # 右辺が未定義の場合 @cell は nil (既にエラー)
        return None

    def get_cell_global_name(self):  # 受け口セル名（コンポジットなら展開した内側のセル）

        # debug
        dbgPrint("cell get_cell_global_name:  {}\n".format(self.cell_name))
        # @cell.show_tree( 1 )

        if self.cell:
            return self.cell.get_real_global_name(self.port_name)
        else:
            return "NonDefinedCell?"

    #===  Join# 結合の右辺の受け口の名前
    #     namespace 名 + '_' + セル名 + '_' + 受け口名   （このセルが composite ならば展開後のセル名、受け口名）
    #subscript:: Integer  呼び口配列の時添数 または nil 呼び口配列でない時
    def get_port_global_name(self, subscript=None):  # 受け口名（コンポジットなら展開した内側のセル）

        from tecslib.core.componentobj.namespace import Namespace

        # debug
        dbgPrint("Cell get_port_global_name:  {}\n".format(self.cell_name))

        # through 指定あり？
        if len(self.through_list) > 0 and self.through_list[0]:
            cell = Namespace.find(_ruby_at(self.through_generated_list, 0).get_cell_namespace_path())    #1

            # through で挿入されたセルで、実際に接続されるセル（compositeの場合内部の)の受け口の C 言語名前
            return cell.get_real_global_port_name(
                _ruby_at(self.through_generated_list, 0).get_through_entry_port_name())
        else:

            # 実際に接続されるセルの受け口の C 言語名前
            if self.cell:
                return self.cell.get_real_global_port_name(self.port_name)
            else:
                return "UndefinedCellsPort?"

    def get_port_name(self):
        return self.port_name

    def get_rhs(self):
        return self.rhs

    # 末尾数字1 : CDL で指定された、右辺のセルを返す
    def get_rhs_cell1(self):   # get_cell と同じ
        return self.cell

    def get_rhs_port1(self):   # get_port_name 同じ
        return self.port_name

    def get_rhs_subscript1(self):
        return self.rhs_subscript

    #=== Join# 右辺のポートを得る
    #    右辺が composite の場合は、内部の繋がるセルのポート, through の場合は挿入されたセルのポート
    #    このメソッドは get_rhs_cell と対になっている
    def get_rhs_port(self):
        from tecslib.core.componentobj.namespace import Namespace
        # through 指定あり？
        if len(self.through_list) > 0 and self.through_list[0]:
            # through で生成されたセルを探す
            cell = Namespace.find(_ruby_at(self.through_generated_list, 0).get_cell_namespace_path())    #1
            # cell のプラグインで生成されたポート名のポートを探す (composite なら内部の繋がるポート)
            return cell.get_real_port(_ruby_at(self.through_generated_list, 0).get_through_entry_port_name())
        else:
            # ポートを返す(composite なら内部の繋がるポートを返す)
            return self.cell.get_real_port(self.port_name)

    #=== Join# 右辺の配列添数を得る
    #    右辺が through の場合は挿入されたセルの添数
    #    右辺が composite の場合は、内部の繋がるセルのポートの添数 (composite では変わらない)
    #    このメソッドは get_rhs_cell,  と対になっている
    def get_rhs_subscript(self):
        if len(self.through_list) > 0 and self.through_list[0]:
            return _ruby_at(self.through_generated_list, 0).get_through_entry_port_subscript()
        else:
            return self.rhs_subscript

    #=== Join# 右辺のポートを得る
    # 右辺のポートを得る。
    # これはプロトタイプ宣言しかされていない場合には、こちらしか使えない
    def get_rhs_port2(self):
        # through 指定あり？
        if len(self.through_list) > 0 and self.through_list[0]:
            if _ruby_at(self.through_generated_list, 0):
                port = Sym(str(_ruby_at(self.through_generated_list, 0).get_through_entry_port_name()))
            else:
                port = self.port_name    # generate に失敗している
        else:
            port = self.port_name

        return port

    #=== Join# 右辺のポートを得る
    # through は適用しないが、composite は展開した後のセルの対応するポート
    def get_rhs_port3(self):
        if self.cell:
            return self.cell.get_real_port(self.port_name)

    #=== Join# 呼び口配列の2番目以降の要素を追加する
    #     一番最初に定義された配列要素が全要素の初期値の配列を持つ
    #     このメソッドは非配列の場合も呼出される（join 重複エラーの場合）
    #join2:: Join  呼び口配列要素の Join
    def add_array_member(self, join2):

        # subscript2: join2 の左辺添数
        subscript2 = join2.get_subscript()

        if self.subscript is None:		# not array : initialize duplicate
            # 非配列の場合、join が重複している
            self.cdl_error("S1127 \'$1\' duplicate", self.name)
            # print "add_array_member2: #{@owner.get_name}\n"

        elif self.subscript >= 0:
            # 添数指定ありの場合
            if (subscript2 is None or subscript2 < 0):
                # join2 左辺は非配列または添数なし
                # 配列が不一致
                self.cdl_error("S1128 \'$1\' inconsistent array definition", self.name)
            elif subscript2 < len(self.array_member) and self.array_member[subscript2] is not None:
                # 同じ添数が既に定義済み
                self.cdl_error("S1129 \'$1\' redefinition of subscript $2", self.name, subscript2)
            else:
                # 添数の位置に要素を追加（Ruby の Array#[]= は自動拡張する）
                while len(self.array_member) <= subscript2:
                    self.array_member.append(None)
                while len(self.array_member2) <= subscript2:
                    self.array_member2.append(None)
                self.array_member[subscript2] = join2.get_rhs()
                self.array_member2[subscript2] = join2
#        p "0:#{join2.get_rhs}"

        else:
            # 添数指定なしの場合
            if (subscript2 is None or subscript2 >= 0):
                # join2 左辺は非配列または添数有
                # 配列が不一致
                self.cdl_error("S1130 \'R1\' inconsistent array definition", self.name)

            # 添数なし配列の場合、配列要素を追加
            self.array_member.append(join2.get_rhs())
            self.array_member2.append(join2)

    def get_array_member(self):
        return self.array_member

    def get_array_member2(self):
        return self.array_member2

    def change_name(self, name):
        # debug
        dbgPrint("change_name: {} to {}\n".format(self.name, name))

        self.name = name

        if self.array_member2:
            i = 0
            while i < len(self.array_member2):
                if self.array_member2[i] != self and self.array_member[i] is not None:
                    # @array_member2[i] が nil になるのは optional の時と、
                    # Join の initialize で無駄に @array_member2 が設定されている場合
                    # 無駄に設定されているものについては、再帰的に呼び出す必要はない（clone_for_composite では対策している）
                    self.array_member2[i].change_name(name)
                i += 1

    # composite cell を展開したセルの結合を clone したセルの名前に変更
    def change_rhs_port(self, clone_cell_list, celltype):
        from tecslib.core.componentobj.namespacepath import NamespacePath

        dbgPrint("change_rhs_port: name={}\n".format(self.name))

        # debug
        if G.debug:
#    if @name == :cCallB then
            # dbgPrint "change_rhs name: #{@name}  cell_name: #{@cell_name} #{@cell} #{self}\n"
            print("============")
            print("CHANGE_RHS change_rhs name: {}.{}  rhs cell_name: {} {} {}".format(
                self.owner.get_name(), self.name, self.cell_name, self.cell, self))

            for cell, ce in clone_cell_list.items():
                # dbgPrint "=== change_rhs:  #{cell.get_name}=#{cell} : #{ce.get_name}\n"
                print("   CHANGE_RHS  change_rhs:  {}={} : {}".format(
                    cell.get_name(), cell, ce.get_name()))
            print("============")

        c = clone_cell_list.get(self.cell)
        if c is None:
            return

        # debug
        dbgPrint("  REWRITE cell_name:  {}   {} => {}, {}\n".format(
            self.owner.get_name(), self.cell_name, c.get_global_name(), c.get_name()))

        # @rhs の内容を調整しておく（この内容は、subscript を除いて、後から使われていない）
        elements = self.rhs.get_elements()
        if elements[0] == "OP_SUBSC":  # 右辺：受け口配列？
            elements = elements[1]

        # 右辺が　cell.ePort の形式でない
        if elements[0] != "OP_DOT" or elements[1][0] != "IDENTIFIER":   #1
            return
        else:
            # セル名を composite 内部の名前から、外部の名前に入れ替える
            # elements[1][1] = Token.new( c.get_name, nil, nil, nil )
            elements[1][1] = NamespacePath(c.get_name(), False, c.get_namespace())

        self.cell_name = c.get_name()
        self.cell = c
        # @definition = nil          # @definition が有効： チェック済み（とは、しない）

        if self.array_member2:

            # debug
            dbgPrint("array_member2.len : {}\n".format(len(self.array_member)))

            i = 0
            while i < len(self.array_member2):
                # @array_member2[i] が nil になるのは optional の時と、
                # Join の initialize で無駄に @array_member2 が設定されている場合
                # 無駄に設定されているものについては、再帰的に呼び出す必要はない（clone_for_composite では対策している）
                if self.array_member2[i] != self and self.array_member[i] is not None:
                    dbgPrint("change_rhs array_member {}: {}  {}\n".format(i, self.name, self.cell_name))
                    self.array_member2[i].change_rhs_port(clone_cell_list, celltype)
                i += 1

    #=== Join# composite セル用にクローン
    #cell_global_name:: string : 親セルのグローバル名
    # 右辺の C_EXP に含まれる $id$, $cell$, $ct$ を置換
    # ここで置換するのは composite の attribute の C_EXP を composite セルタイプおよびセル名に置換するため
    # （内部セルの C_EXP もここで置換される）
    # @through_list などもコピーされるので、これが呼び出される前に確定する必要がある
    def clone_for_composite(self, ct_name, cell_name, locale, b_need_recursive=True):
        from tecslib.core.syntaxobj.cdlinitializer import CDLInitializer
        # debug
        dbgPrint("=====  clone_for_composite: {} {} {}   =====\n".format(
            self.name, self.cell_name, self))
        cl = copy.copy(self)

        if self.array_member2 and b_need_recursive:
            cl.clone_array_member(ct_name, cell_name, self, locale)

        rhs = CDLInitializer.clone_for_composite(self.rhs, ct_name, cell_name, locale)
        cl.change_rhs(rhs)

        # debug
        dbgPrint("join cloned : {}\n".format(cl))
        return cl

    def clone_array_member(self, ct_name, cell_name, prev, locale):
        # 配列のコピーを作る
        am = copy.copy(self.array_member)
        am2 = copy.copy(self.array_member2)

        # 配列要素のコピーを作る
        i = 0
        while i < len(am2):
            if self.array_member2[i] == prev:
                # 自分自身である（ので、呼出すと無限再帰呼出しとなる）
                am2[i] = self
                am[i] = am2[i].get_rhs()
            elif self.array_member2[i]:
#        am2[i] = @array_member2[i].clone_for_composite( ct_name, cell_name, locale, false )
                am2[i] = self.array_member2[i].clone_for_composite(ct_name, cell_name, locale, True)
                am[i] = am2[i].get_rhs()
            else:
                # 以前のエラーで array_member2[i] は nil になっている
                pass

            # debug
            dbgPrint("clone_array_member: {} subsript={} {} {}\n".format(
                self.name, i, am2[i], self.array_member2[i]))

            i += 1

        # i = 0 は、ここで自分自身を設定
        # am2[0] = self

        self.array_member = am
        self.array_member2 = am2

    #=== Join# rhs を入れ換える
    #rhs:: Expression | initializer
    # 右辺を入れ換える．
    # このメソッドは、composite で cell の属性の初期値を attribute の値で置き換えるのに使われる
    # このメソッドは composite 内の cell の属性の初期値が定数ではなく式になった場合、不要になる
    def change_rhs(self, rhs):
        self.rhs = rhs

    #=== Join# clone された join の owner を変更
    def set_cloned(self, owner):
        dbgPrint("Join#set_cloned: {}  prev owner: {} new owner: {}\n".format(
            self.name, self.owner.get_name(), owner.get_name()))
        self.owner = owner
        if self.array_member2:
            for join in self.array_member2:
                dbgPrint("Joinarray#set_cloned: {}  prev owner: {} new owner: {}\n".format(
                    self.name, join.get_owner().get_name(), owner.get_name()))
                join.set_owner(owner)

    def show_tree(self, indent):
        from tecslib.core.componentobj.port import Port
        print("  " * indent, end="")
        print("Join: name: {} owner: {} id: {}".format(self.name, self.owner.get_name(), self))
        if self.subscript is None:
            pass
        elif self.subscript >= 0:
            print("  " * (indent + 1), end="")
            print("subscript: {}".format(self.subscript))
        else:
            print("  " * (indent + 1), end="")
            print("subscript: not specified")
        print("  " * (indent + 1), end="")
        print("rhs: ")
        if type(self.rhs) is list:
            for i in self.rhs:
                if type(i) is list:
                    for j in i:
                        j.show_tree(indent + 3)
                elif isinstance(i, Sym):
                    print("  " * (indent + 2), end="")
                    print(i, end="")
                    print("")
                else:
                    i.show_tree(indent + 2)
        else:
            self.rhs.show_tree(indent + 2)
            print("  " * (indent + 1), end="")
            if self.definition:
                print("definition:")
                self.definition.show_tree(indent + 2)
            else:
                print("definition: not found")
        if type(self.definition) is Port:
            print("  " * (indent + 2), end="")
            if self.cell:
                print("cell: {} {}  port: {}  cell_global_name: {}".format(
                    self.cell_name, self.cell, self.port_name, self.cell.get_global_name()))
            else:
                print("cell: {} port: {}  (cell not found)".format(self.cell_name, self.port_name))
        if self.through_list:
            i = 0
            for t in self.through_list:
                print("  " * (indent + 2), end="")
                print("through: plugin name :  '{}' arg : '{}'".format(t[0], t[2]))
                if _ruby_at(self.through_generated_list, i):
                    self.through_generated_list[i].show_tree(indent + 3)
                i += 1
        if self.array_member2:
            print("  " * (indent + 1), end="")
            print("array member:")
            i = 0
            for j in self.array_member2:
                if j:
                    print("  " * (indent + 2), end="")
                    print("[{}]: {}  id: {} owner={}".format(
                        i, j.get_name(), j, j.get_owner().get_name()))
                    j.get_rhs().show_tree(indent + 3)
#          (indent+3).times { print "  " }
#          puts "cell global name: #{j.get_cell_global_name}"
#          puts "cell global name: #{j.get_rhs_cell.get_global_name}"
#          (indent+3).times { print "  " }
#          puts "port global name: #{j.get_port_global_name}"
#          puts "port global name: #{j.get_rhs_port.get_name}"
                else:
                    print("  " * (indent + 2), end="")
                    print("[{}]: [optional]  id: {}".format(i, j))
                i += 1
