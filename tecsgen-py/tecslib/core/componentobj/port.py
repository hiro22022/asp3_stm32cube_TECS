# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/componentobj/port.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

from tecslib.core import globals as G
from tecslib.core.syntaxobj.node import BDNode


#== 構文要素：口を表すクラス（セルタイプの呼び口、受け口）
class Port(BDNode):
# @name::  str
# @signature:: Signature
# @port_type::  :CALL, :ENTRY
# @array_size:: nil: not array, "[]": sizeless, Integer: sized array
# @reverse_require_cell_path:: NamespacePath :     逆require呼び元セル  mikan namespace (呼び口のみ指定可能)
# @reverse_require_callport_name:: Symbol:  逆require呼び元セルの呼び口名
#
# set_allocator_port によって設定される．設定された場合、このポートはアロケータポートである。
# @allocator_port:: Port : この呼び口ができる元となった呼び口または受け口
# @allocator_func_decl:: Decl : この呼び口ができる元となった呼び口または受け口の関数
# @allocator_param_decl:: ParamDecl : この呼び口ができる元となった呼び口または受け口のパラメータ
#
# set_specifier によって設定される(
# @allocator_instance:: Hash : {"func_param" => [ :RELAY_ALLOC, func_name, param_name, rhs_cp_name, rhs_func_name, rhs_param_name ]}
#                                               [:INTERNAL_ALLOC, func_name, param_name, rhs_ep_name ]
# @allocator_instance_tmp:: Hash : {"func_param" => [:INTERNAL_ALLOC|:RELAY_ALLOC,  IDENTIFIER, IDENTIFIER, expression ],..}
#                                                                                    function    parameter   rhs
#
# @b_require:: bool : require により生成された call port の場合 true
# @b_has_name:: bool : require : 名前ありのリクワイア呼び口
# @b_inline:: bool : entry port のみ
# @b_omit:: bool : omit 指定子が指定された (call port のみ)
# @b_optional:: bool : call port のみ
# @b_ref_desc:: bool :  ref_desc キーワードが指定された
# @b_dynamic:: bool :  dynamic キーワードが指定された (呼び口のみ)
#
# optimize::
# @celltype:: 属するセルタイプ
#
# :CALL の場合の最適化
# @b_VMT_useless:: bool                     # VMT 関数テーブルを使用しない
# @b_skelton_useless:: bool                 # スケルトン関数不要   (true の時、受け口関数を呼出す)
# @b_cell_unique:: bool                     # 呼び先は唯一のセル
# @only_callee_port:: Port                  # 唯一の呼び先ポート
# @only_callee_cell:: Cell                  # 唯一の呼び先セル (@b_PEPDES_in_CB_useless = true の時有効)
#
# :ENTRY の場合の最適化（呼び口最適化と同じ変数名を使用）
# @b_VMT_useless:: bool                     # VMT 関数テーブルが不要
# @b_skelton_useless:: bool                 # スケルトン関数不要

    def __init__(self, name, sig_path, port_type, array_size=None,
                 reverse_require_cell_path=None, reverse_require_entry_port_name=None):
        from tecslib.core.componentobj.namespace import Namespace
        from tecslib.core.componentobj.signature import Signature
        from tecslib.core.expression import Expression

        super().__init__()
        self.name = name
        self.port_type = port_type

        if array_size == "[]":
#      if port_type == :ENTRY then
#        cdl_error( "S1072 $1: entry port: sizeless array not supported in current version" , name )
#      end
            self.array_size = array_size
        elif array_size is not None:
            if isinstance(array_size, Expression):
                array_size = array_size.eval_const(None)
            else:
                array_size = array_size   # これはアロケータ呼び口の場合（元の呼び口で既に評価済み）
            self.array_size = array_size
            if self.array_size is None:
                self.cdl_error("S1073 Not constant expression $1", str(array_size))

            #if Integer( @array_size ) != @array_size || @array_size <= 0 then
            if not isinstance(self.array_size, int):
                self.cdl_error("S1074 Not Integer $1", str(array_size))
        else:
            self.array_size = None

        self.signature = None
        self.allocator_instance = None
        self.allocator_instance_tmp = None
        self.allocator_port = None
        self.allocator_func_decl = None
        self.allocator_param_decl = None

        object = Namespace.find(sig_path)    #1
        if object is None:
            # mikan signature の名前が不完全
            self.cdl_error("S1075 \'$1\' signature not found", sig_path)
        elif type(object) is not Signature:
            # mikan signature の名前が不完全
            self.cdl_error("S1076 \'$1\' not signature", sig_path)
        else:
            self.signature = object

        # 逆require
        self.reverse_require_cell_path = None
        self.reverse_require_entry_port_name = None
        if reverse_require_cell_path:
            if port_type == "CALL":
                self.cdl_error("S1152 $1 call port cannot have fixed join", self.name)
            else:
                self.reverse_require_cell_path = reverse_require_cell_path
                self.reverse_require_entry_port_name = reverse_require_entry_port_name

                # 受け口配列か？
                if array_size:
                    self.cdl_error("S1153 $1: cannot be entry port array for fixed join port", self.name)

                # 呼び口のセルタイプを探す
                ct_or_cell = Namespace.find(self.reverse_require_cell_path)  #1
                from tecslib.core.componentobj.cell import Cell
                from tecslib.core.componentobj.celltype import Celltype

                if type(ct_or_cell) is Cell:
                    ct = ct_or_cell.get_celltype()
                elif type(ct_or_cell) is Celltype:
                    ct = ct_or_cell
                    if not ct.is_singleton():
                        self.cdl_error("S1154 $1: must be singleton celltype for fixed join", str(reverse_require_cell_path))
                else:
                    ct = None
                    self.cdl_error("S1155 $1: not celltype or not found", reverse_require_cell_path.get_path_str())

                if ct is None:
                    return    # 既にエラー

                # 添え字なしの呼び口配列か？
                port = ct.find(self.reverse_require_entry_port_name)
                if port is None or port.get_port_type() != "CALL":
                    self.cdl_error("S1156 $1: not call port or not found", reverse_require_entry_port_name)
                else:
                    if port.get_array_size() != "[]":
                        self.cdl_error("S1157 $1: sized array or not array", reverse_require_entry_port_name)

        self.b_require = False
        self.b_has_name = False
        self.b_inline = False
        self.b_optional = False
        self.b_omit = False
        self.b_ref_desc = False
        self.b_dynamic = False
        self.reset_optimize()

    #=== Port#最適化に関する変数をリセットする
    # Region ごとに最適化のやりなおしをするため、リセットする
    def reset_optimize(self):
        if self.port_type == "CALL":
            # call port optimize
            self.b_VMT_useless = False                     # VMT 不要 (true の時 VMT を介することなく呼出す)
            self.b_skelton_useless = False                 # スケルトン関数不要   (true の時、受け口関数を呼出す)
            self.b_cell_unique = False                     # 唯一の呼び先セル
            self.only_callee_port = None                    # 唯一の呼び先ポート
            self.only_callee_cell = None                    # 唯一の呼び先セル
        else:
            # entry port optimize
            if G.unopt or G.unopt_entry:
                # 最適化なし
                self.b_VMT_useless = False                     # VMT 不要 (true の時 VMT を介することなく呼出す)
                self.b_skelton_useless = False                 # スケルトン関数不要   (true の時、受け口関数を呼出す)
            else:
                # 最適化あり
                self.b_VMT_useless = True                      # VMT 不要 (true の時 VMT を介することなく呼出す)
                self.b_skelton_useless = True                  # スケルトン関数不要   (true の時、受け口関数を呼出す)

    def set_celltype(self, celltype):
        self.celltype = celltype

    def get_name(self):
        return self.name

    def get_port_type(self):
        return self.port_type

    def get_signature(self):
        return self.signature

    def get_array_size(self):
        return self.array_size

    def get_celltype(self):
        return self.celltype

    #=== Port# アロケータポートの設定
    #port:: Port : send/receive のあった呼び口または受け口
    #fd:: Decl : 関数の declarator
    #par:: ParamDecl : send/receive のあった引数
    # この呼び口が生成されるもとになった呼び口または受け口の情報を設定
    def set_allocator_port(self, port, fd, par):
        self.allocator_port = port
        self.allocator_func_decl = fd
        self.allocator_param_decl = par

    def is_allocator_port(self):
        return self.allocator_port is not None

    def get_allocator_port(self):
        return self.allocator_port

    def get_allocator_func_decl(self):
        return self.allocator_func_decl

    def get_allocator_param_decl(self):
        return self.allocator_param_decl

    def set_require(self, b_has_name):
        self.b_require = True
        self.b_has_name = b_has_name

    def is_require(self):
        return self.b_require

    #=== Port# require 呼び口が名前を持つ？
    # require 限定
    def has_name(self):
        return self.b_has_name

    def is_optional(self):
        return self.b_optional

    def set_optional(self):
        self.b_optional = True

    #=== Port# omit 指定されている?
    def is_omit(self):
        return self.b_omit or (self.signature and self.signature.is_empty())

    def set_omit(self):
        self.b_omit = True

    def set_VMT_useless(self):                     # VMT 関数テーブルを使用しない
        self.b_VMT_useless = True

    def set_skelton_useless(self):                 # スケルトン関数不要   (true の時、受け口関数を呼出す)
        self.b_skelton_useless = True

    def set_cell_unique(self):                     # 呼び先セルは一つだけ
        self.b_cell_unique = True

    #=== Port# 呼び口/受け口の指定子の設定
    # inline, allocator の指定
    def set_specifier(self, spec_list):
        for s in spec_list:
            case = s[0]
            if case == "INLINE":
                if self.port_type == "CALL":
                    self.cdl_error("S1077 inline: cannot be specified for call port")
                    continue
                self.b_inline = True
            elif case == "OMIT":
                if self.port_type == "ENTRY":
                    self.cdl_error("S9999 omit: cannot be specified for entry port")
                    continue
                self.b_omit = True
            elif case == "OPTIONAL":
                if self.port_type == "ENTRY":
                    self.cdl_error("S1078 optional: cannot be specified for entry port")
                    continue
                self.b_optional = True
            elif case == "REF_DESC":
                if self.port_type == "ENTRY":
                    self.cdl_error("S9999 ref_desc: cannnot be specified for entry port")
                    continue
                self.b_ref_desc = True
            elif case == "DYNAMIC":
                if self.port_type == "ENTRY":
                    self.cdl_error("S9999 dynamic: cannnot be specified for entry port")
                    continue
                self.b_dynamic = True
            elif case == "ALLOCATOR":
                if self.port_type == "CALL":
                    self.cdl_error("S1079 allocator: cannot be specified for call port")
                if self.allocator_instance_tmp:
                    self.cdl_error("S1080 duplicate allocator specifier")
                    continue
                self.allocator_instance_tmp = s[1]
            else:
                raise Exception("unknown specifier {}".format(s[0]))
        if self.b_dynamic or self.b_ref_desc:
            if self.b_dynamic:
                dyn_ref = "dynamic"
            else:
                dyn_ref = "ref_desc"
            if self.b_omit:     # is_omit? は is_empty? も含んでいるので使えない
                self.cdl_error("S9999 omit cannot be specified with $1", dyn_ref)
            elif self.signature and self.signature.is_empty():
                self.cdl_error("S9999 $1 cannot be specified for empty signature", dyn_ref)
            elif self.signature and self.signature.has_descriptor():
                pass
                # cdl_error( "S9999 $1 port '$2' cannot have Descriptor in its signature", dyn_ref, @name )

        elif self.b_dynamic and self.b_ref_desc:
            self.cdl_error("S9999 both dynamic & ref_desc cannot be specified simultaneously")

    #=== Port# リレーアロケータ、内部アロケータのインスタンスを設定
    # 呼び口の前方参照可能なように、セルタイプの解釈の最後で行う
    def set_allocator_instance(self):
        if self.allocator_instance_tmp is None:
            return

        from tecslib.core.bnf import Token
        from tecslib.core.componentobj.compositecelltype import CompositeCelltype

        self.allocator_instance = {}
        for ai in self.allocator_instance_tmp:
            direction = None
            alloc_type = ai[0]
            # ai = [ :INTERNAL_ALLOC|:RELAY_ALLOC, func_name, param_name, rhs ]
            if alloc_type == "INTERNAL_ALLOC":
                if type(self.owner) is not CompositeCelltype:  # ミスを防ぐために composite でなければとした
                    self.cdl_error("S1081 self allocator not supported yet")   # mikan これはサポートされているはず。要調査 12/1/15
                    continue
                # OK
            elif alloc_type == "RELAY_ALLOC":
                # OK
                pass
            elif alloc_type == "NORMAL_ALLOC":
                # ここへ来るのは composite の受け口で右辺が "eEnt.func.param" 形式で指定されていた場合
                self.cdl_error("S1174 $1 not suitable for lhs, suitable lhs: 'func.param'", "{}.{}.{}".format(ai[1], ai[3], ai[4]))
                continue
            else:
                raise Exception("Unknown allocator type {}".format(ai[1]))

            # '=' 左辺(func_name,param_name)は実在するか?
            if self.signature:       # signature = nil なら既にエラー
                fh = self.signature.get_function_head(ai[1])
                if fh is None:
                    self.cdl_error("S1082 function \'$1\' not found in signature", ai[1])
                    continue
                decl = fh.get_declarator()
                if not decl.is_function():
                    continue   # 既にエラー
                paramdecl = decl.get_type().get_paramlist().find(ai[2])
                if paramdecl is None:
                    self.cdl_error("S1083 \'$1\' not found in function \'$2\'", ai[2], ai[1])
                    continue
                case_dir = paramdecl.get_direction()
                if case_dir == "SEND" or case_dir == "RECEIVE":
                    # OK
                    direction = paramdecl.get_direction()
                else:
                    self.cdl_error("S1084 \'$1\' in function \'$2\' is not send or receive", ai[2], ai[1])
                    continue

            # 重複指定がないか?
            if self.allocator_instance.get("{}_{}_{}".format(self.name, ai[1], ai[2])):
                self.cdl_error("S1085 duplicate allocator specifier for \'$1_$2\'", ai[1], ai[2])

            # 右辺のチェック
            if alloc_type == "INTERNAL_ALLOC":

                ele = ai[3].get_elements()
                if ele[0] != "IDENTIFIER":
                    self.cdl_error("S1086 $1: rhs not in 'allocator_entry_port' form", str(ai[3]))
                    continue

                ep_name = ele[1]   # アロケータ受け口名
                ep = self.owner.find(ep_name.get_path()[0])  # mikan "a::b"
                if ep is None or type(ep) is not Port or ep.get_port_type() != "ENTRY" or not ep.get_signature().is_allocator():
                    self.cdl_error("S1175 $1 not found or not allocator entry port for $2", ep_name, ai[1])
                # 右辺チェック終わり
                # ai2 = [ :INTERNAL_ALLOC, func_name, param_name, rhs_ep_name ]
                ai2 = [ai[0], ai[1], ai[2], ep_name]

            elif alloc_type == "RELAY_ALLOC":
                ele = ai[3].get_elements()
                if (ele[0] != "OP_DOT"
                        or ele[1][0] != "OP_DOT" or ele[1][1][0] != "IDENTIFIER" or not ele[1][1][1].is_name_only()
                        or type(ele[1][2]) is not Token or type(ele[2]) is not Token):   #1
                    # [ :OP_DOT, [ :OP_DOT, [ :IDENTIFIER,  name_space_path ],  Token(1) ],  Token(2) ]
                    #    ele[0]    ele[1][0]  ele[1][1][0]  ele[1][1][1]        ele[1][2]    ele[2]
                    #      name_space_path.Token(1).Token(2) === call_port.func.param
                    #  mikan Expression#analyze_cell_join_expression の変種を作成して置き換えるべき

                    self.cdl_error("S1176 rhs not in 'call_port.func.param' form for for $1_$2", ai[1], ai[2])   # S1086
                    continue
                func_name = ele[1][2]
                cp_name = ele[1][1][1].get_name()
                param_name = ele[2].to_sym()
                cp = self.owner.find(cp_name)    # リレーする先の呼び口
                if cp:
# mikan cp が呼び口であることのチェック（属性の場合もある）
# mikan 受け口から受け口へのリレーへの対応 (呼び口から呼び口へのリレーはありえない)  <=== 文法にかかわる事項（呼び口側でアロケータが決定される）
                    sig = cp.get_signature()
                    if sig and self.signature:
                        fh = self.signature.get_function_head(func_name)
                        if fh is None:
                            self.cdl_error("S1087 function \'$1\' not found in signature \'$2\'", func_name, sig.get_name())
                            continue
                        decl = fh.get_declarator()
                        if not decl.is_function():
                            continue   # 既にエラー
                        paramdecl = decl.get_type().get_paramlist().find(param_name)
                        if paramdecl is None:
                            self.cdl_error("S1088 \'$1\' not found in function \'$2\'", param_name, func_name)
                            continue
                        case_dir = paramdecl.get_direction()
                        if case_dir == "SEND" or case_dir == "RECEIVE":
                            # OK
                            if alloc_type == "RELAY_ALLOC" and direction != paramdecl.get_direction():
                                self.cdl_error("S1089 relay allocator send/receive mismatch between $1.$2 and $3_$4.$5", ai[1], ai[2], cp_name, func_name, param_name)
                        else:
                            self.cdl_error("S1090 \'$1\' in function \'$2\' is not send or receive", param_name, func_name)
                            continue

                        # else
                        # sig == nil ならば既にエラー
                else:
                    if self.celltype:
                        ct_name = self.celltype.get_name()
                    else:
                        ct_name = "(None)"
                    self.cdl_error("S1091 call port \'$1\' not found in celltype $2", cp_name, ct_name)
                    continue
                # 右辺チェック終わり
                # ai2 = [ :RELAY_ALLOC, func_name, param_name, rhs_cp_name, rhs_func_name, rhs_param_name ]
                ai2 = [ai[0], ai[1], ai[2], cp_name, func_name, param_name]

            self.allocator_instance["{}_{}_{}".format(self.name, ai[1], ai[2])] = ai2

    def is_inline(self):
        return self.b_inline

    def is_VMT_useless(self):                     # VMT 関数テーブルを使用しない
        if self.port_type == "ENTRY" and G.unopt_entry is True:
            # プラグインから $unopt_entry を設定するケースのため
            # ここで読み出すときに、false を返す (reset_optimize での設定変更は速すぎる)
            return False
        else:
            return self.b_VMT_useless

    def is_skelton_useless(self):                 # スケルトン関数不要   (true の時、受け口関数を呼出す)
        if self.port_type == "ENTRY" and G.unopt_entry is True:
            # プラグインから $unopt_entry を設定するケースのため
            # ここで読み出すときに、false を返す (reset_optimize での設定変更は速すぎる)
            return False
        else:
            return self.b_skelton_useless

    def is_cell_unique(self):                     # 呼び先のセルは一つ？
        return self.b_cell_unique

    #=== Port# 受け口最適化の設定
    # この受け口を参照する呼び口が VMT, skelton を必要としているかどうかを設定
    # 一つでも呼び口が必要としている（すなわち b_*_useless が false）場合は、
    # この受け口の最適化を false とする
    def set_entry_VMT_skelton_useless(self, b_VMT_useless, b_skelton_useless):
        if not b_VMT_useless:
            self.b_VMT_useless = False
        if not b_skelton_useless:
            self.b_skelton_useless = False

    #=== Port# 唯一の結合先を設定
    # 最適化で使用
    #  b_VMT_useless == true || b_skelton_useless == true の時に設定される
    #  optional の場合 callee_cell, callee_port が nil となる
    def set_only_callee(self, callee_port, callee_cell):
        self.only_callee_port = callee_port
        self.only_callee_cell = callee_cell

    #=== Port# 唯一の結合先ポートを返す(compositeの場合実セル)
    # optional 呼び口で未結合の場合 nil を返す
    def get_real_callee_port(self):
        if self.only_callee_cell:
            return self.only_callee_cell.get_real_port(self.only_callee_port.get_name())

    #=== Port# 唯一の結合先セルを返す(compositeの場合実セル)
    # optional 呼び口で未結合の場合 nil を返す
    def get_real_callee_cell(self):
        if self.only_callee_cell:
            return self.only_callee_cell.get_real_cell(self.only_callee_port.get_name())

    def get_allocator_instance(self):
        return self.allocator_instance

    def get_allocator_instance_tmp(self):
        return self.allocator_instance_tmp

    #=== Port# 逆require の結合を生成する
    # STAGE: S
    def create_reverse_require_join(self, cell):
        if self.reverse_require_cell_path is None:
            return

        from tecslib.core.bnf import Token
        from tecslib.core.componentobj.cell import Cell
        from tecslib.core.componentobj.celltype import Celltype
        from tecslib.core.componentobj.join import Join
        from tecslib.core.componentobj.namespace import Namespace
        from tecslib.core.componentobj.namespacepath import NamespacePath
        from tecslib.core.expression import Expression
        from tecslib.core.toplevel import dbgPrint

        # 呼び元セルを探す
        ct_or_cell = Namespace.find(self.reverse_require_cell_path)   # mikan namespace    #1
        if type(ct_or_cell) is Cell:
            cell2 = ct_or_cell
            ct = cell2.get_celltype()
            if ct is None:
                return    # 既にエラー
        elif type(ct_or_cell) is Celltype:
            cell2 = ct_or_cell.get_singleton_cell(cell.get_region())
            if cell2 is None:
                self.cdl_error("S1158 $1: singleton cell not found for fixed join", ct_or_cell.get_name())
                return
            ct = ct_or_cell
        else:
            # 既にエラー：無視
            return

        # 結合を生成する
        dbgPrint("create_reverse_require_join {}.{}[] = {}.{}\n".format(
            cell2.get_name(), self.reverse_require_entry_port_name, cell.get_name(), self.name))
        nsp = NamespacePath(cell.get_name(), False, cell.get_namespace())
#    rhs = Expression.new( [ :OP_DOT, [ :IDENTIFIER, Token.new( cell.get_name, nil, nil, nil ) ],
        rhs = Expression(["OP_DOT", ["IDENTIFIER", nsp],
                          Token(self.name, None, None, None)], cell.get_locale())   #1
        join = Join(self.reverse_require_entry_port_name, -1, rhs, cell.get_locale())
        cell2.new_join_inst(join)
        join.set_definition(ct.find(join.get_name()))

    #=== Port# signature のすべての関数のすべてのパラメータをたどる
    #block:: ブロックを引数として取る(ruby の文法で書かない)
    #  ブロックは3つの引数を受け取る(Port, Decl,      ParamDecl)    Decl: 関数ヘッダ
    # Signature クラスにも each_param がある（同じ働き）
    def each_param(self, pr):  # ブロック引数{  |port, func_decl, param_decl| }
        if self.signature is None:                         # signature 未定義（既にエラー）
            return
        fha = self.signature.get_function_head_array()            # 呼び口または受け口のシグニチャの関数配列
        if fha is None:                                # nil なら文法エラーで有効値が設定されなかった
            return

        # obsolete Ruby 3.0 では使用できない
        # pr = Proc.new   # このメソッドのブロック引数を pr に代入
        port = self
        for fh in fha:  # fh: FuncHead                      # 関数配列中の各関数頭部
            fd = fh.get_declarator()                            # fd: Decl  (関数頭部からDeclarotorを得る)
            if fd.is_function():                           # fd が関数でなければ、すでにエラー
                for par in fd.get_type().get_paramlist().get_items():  # すべてのパラメータについて
                    pr(port, fd, par)

    #=== Port# 逆require指定されている？
    def is_reverse_required(self):
        return self.reverse_require_cell_path is not None

    #=== Port# is_dynamic?
    def is_dynamic(self):
        return self.b_dynamic

    #=== Port# is_ref_desc?
    def is_ref_desc(self):
        return self.b_ref_desc

    def show_tree(self, indent):
        from tecslib.rubylib import rb
        print("  " * indent, end="")
        print("Port: name:{} port_type:{} require:{} inline:{} omit:{} optional:{} ref_desc:{} dynamic:{}".format(
            self.name, self.port_type,
            rb.to_s(self.b_require), rb.to_s(self.b_inline), rb.to_s(self.b_omit),
            rb.to_s(self.b_optional), rb.to_s(self.b_ref_desc), rb.to_s(self.b_dynamic)))
        print("  " * (indent + 1), end="")
        if self.signature:
            print("signature: {} {}".format(self.signature.get_name(), rb.inspect(self.signature)))
        else:
            print("signature: NOT defined")
        if self.array_size == "[]":
            print("  " * (indent + 1), end="")
            print("array_size: not specified")
        elif self.array_size is not None:
            print("  " * (indent + 1), end="")
            print("array_size: {}".format(self.array_size))
        if self.allocator_instance:
            print("  " * (indent + 1), end="")
            print("allocator instance:")
            for b, a in self.allocator_instance.items():
                print("  " * (indent + 2), end="")
                print("{} {} {} ".format(a[0], a[1], b))
                # a[3].show_tree( indent+3 )
        print("  " * (indent + 1), end="")
        if self.port_type == "CALL":
            print("VMT_useless : {}  skelton_useless : {}  cell_unique : {}".format(
                rb.to_s(self.b_VMT_useless), rb.to_s(self.b_skelton_useless),
                rb.to_s(self.b_cell_unique)))
        else:
            print("VMT_useless : {}  skelton_useless : {}".format(
                rb.to_s(self.b_VMT_useless), rb.to_s(self.b_skelton_useless)))
