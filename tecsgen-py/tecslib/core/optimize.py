# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/optimize.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

#
# This file includes the processes between semantics analysis and code generation.
# Optimize is one of them.
# Other processes are setting ID for each cell and setting domain information
#
# このファイルには、意味解析からコード生成の間で行うべき処理が含まれる．
# 最適化もその一つである．
# その他に、セル毎の ID 付け、ドメインわけを行う．
# コード生成対象となるセルを対象に処理を行うものが含まれる．
#

from tecslib.core import globals as G
from tecslib.core.componentobj.celltype import Celltype
from tecslib.core.componentobj.namespace import Namespace
from tecslib.core.toplevel import dbgPrint
from tecslib.rubylib.rb import uniq
from tecslib.rubylib.reopen import reopen
from tecslib.rubylib.symbol import Sym


def _sparse_list_get(lst, index):
    if index < len(lst):
        return lst[index]
    return None


def _sparse_list_set(lst, index, value):
    while len(lst) <= index:
        lst.append(None)
    lst[index] = value


Celltype.ID_BASE = 1
Celltype._ID_BASE = Celltype.ID_BASE
if Celltype.domain_class_roots is None:
    Celltype.domain_class_roots = {}


@reopen(Namespace)
class _NamespaceOptimize:

    #===  各セルに ID （整数値）を割付ける
    def set_cell_id_and_domain(self):
        # celltype の各セルに ID を割付ける
        for t in self.celltype_list:
            t.set_cell_id_and_domain()

        # サブネームスペースの各セルに ID を割付ける
        for n in self.namespace_list:
            n.set_cell_id_and_domain()

    def optimize(self):
        # celltype の最適化
        for t in self.celltype_list:
            t.optimize()

        # サブネームスペースの最適化
        for n in self.namespace_list:
            n.optimize()

    def reset_optimize(self):
        # celltype の最適化
        for t in self.celltype_list:
            t.reset_optimize()

        # サブネームスペースの最適化
        for n in self.namespace_list:
            n.reset_optimize()


@reopen(Celltype)
class _CelltypeOptimize:

    def set_cell_id_and_domain(self):
        self.set_cell_id()
        self.set_domain()
        self.set_domain_class()

    #=== 各セルに ID （整数値）を割付ける
    def set_cell_id(self):

        if G.verbose:
            print("=== id for the cells of celltype {} ===\n".format(
                self.get_namespace_path().get_path_str()))

        if G.unique_id:
            self.id_base = Celltype._ID_BASE   # id をシステム全体で連番にする
        else:
            self.id_base = 1           # base を常に 1 から始める

        id_specified_cells = []
        no_id_specified_cells = []

        # プロトタイプを除いた数を求める
        for c in self.cell_list:
            if c.is_generate():
                # c.set_id( @id_base + @n_cell_gen )
                id = c.get_specified_id()
                if id is not None:
                    id_specified_cells.append(c)
                else:
                    no_id_specified_cells.append(c)

                # p "#{c.get_name} #{@id_base+@n_cell_gen}"
                Celltype._ID_BASE += 1
                self.n_cell_gen += 1

        self.ordered_cell_list = []   # id = 1 が添数 0 に格納される
        # ID 指定されているセルに id 番号を与える
        for c in id_specified_cells:
            id = c.get_specified_id()
            dbgPrint("id_specified_cells celltype={} cell={} id={} n_cell={}\n".format(
                self.name, c.get_name(), id, self.n_cell_gen))
            if id > 0:
                if id >= self.n_cell_gen:
                    self.cdl_error("S3001 $1: id too large $2 (max=$3)",
                                   c.get_name(), id, self.n_cell_gen)
                    continue
            else:
                if - id >= self.n_cell_gen:
                    self.cdl_error("S3002 $1: id too large $2 (max=$3)",
                                   c.get_name(), id, self.n_cell_gen)
                    continue
                id = self.n_cell_gen + id + 1

            if _sparse_list_get(self.ordered_cell_list, id - 1):
                self.cdl_error("S3003 $1: id number '$2' conflict with $3",
                               c.get_name(), id,
                               self.ordered_cell_list[id - 1].get_name())
            _sparse_list_set(self.ordered_cell_list, id - 1, c)
            # 通し番号とする場合のため @id_base を加える
            c.set_id(self.id_base - 1 + id)
            if G.verbose:
                print("{}: id={}  specified id={}\n".format(
                    c.get_name(), c.get_id(), c.get_specified_id()))

        # ID 指定されていないセルに id 番号を与える
        i = 0
        for c in no_id_specified_cells:
            while _sparse_list_get(self.ordered_cell_list, i) is not None:
                i += 1
            _sparse_list_set(self.ordered_cell_list, i, c)
            c.set_id(self.id_base + i)
            if G.verbose:
                print("{}: id={}\n".format(c.get_name(), c.get_id()))
        if self.n_cell_gen > 0 and i >= self.n_cell_gen:
            raise Exception("id over id={} N={}".format(i, self.n_cell_gen))

    def set_domain(self):
        domain_cells = {}
        for c in self.cell_list:
            if c.is_generate():
                dr = c.get_region().get_domain_root()
                if dr.get_domain_type():
                    dn = dr.get_domain_type().get_name()
                else:
                    dn = None
                if self.domain_roots.get(dn):
                    self.domain_roots[dn].append(dr)
                else:
                    self.domain_roots[dn] = [dr]
                if domain_cells.get(dr):
                    domain_cells[dr].append(c)
                else:
                    domain_cells[dr] = [c]

        for dn, drs in self.domain_roots.items():
            drs[:] = uniq(drs)
            if G.verbose and dn:
                # print "[domain] celltype=#{@name} domainType=#{dn} domainRootRegions={"
                delim = ""
                for r in drs:
                    print(delim, r.get_name(), end="")
                    delim = ", "
                print("}\n")
                for r in drs:
                    # unjoin_plugin 後に get_kind すると Ruby 例外が発生するため、get_kind を外してある
                    # print "[domain] celltype=#{@name} domainRootRegion=#{r.get_name} domainType=#{dn} domainKind=#{r.get_domain_root.get_domain_type.get_kind} domainCells={"
                    print("[domain] celltype={} domainRootRegion={} domainType={}(".format(
                        self.name, r.get_name(), dn), end="")
                    delim = ""
                    for c in domain_cells[r]:
                        print("{}{}".format(delim, c.get_name()), end="")
                        delim = ", "
                    print("}\n")

        if len(self.domain_roots) > 1:
            print(self.domain_roots)
            raise Exception("ambigous DomainType")

        for dn, regions in self.domain_roots.items():
            # domain_type は一つのノードに一つしかないので、一つの要素を無条件で取り出す
            if len(regions) > 1:
                if G.verbose:
                    self.cdl_info("I9999 celltype '$1' has cells in multi-domain.\n", self.name)
                # if @idx_is_id == false then
                #   cdl_info( "I9999 celltype '$1' forcely set idx_is_id\n", @name )
                # end
                self.b_need_ptab = True
                # @idx_is_id_act = true

    #Celltype# @domain_class_roots を設定
    def set_domain_class(self):
        self.domain_class_roots = {}
        for c in self.cell_list:
            if c.is_generate():
                dr = c.get_region().get_domain_root()
                cr = c.get_region().get_class_root()

                # set @domain_class_roots
                if self.domain_class_roots.get(dr) is None:
                    self.domain_class_roots[dr] = {}
                if self.domain_class_roots[dr].get(cr):
                    self.domain_class_roots[dr][cr].append(c)
                else:
                    self.domain_class_roots[dr][cr] = [c]

                # set @domain_class_roots2
                if dr.is_sub_region_of(cr):
                    sub_region = dr
                else:
                    sub_region = cr
                if self.domain_class_roots2.get(sub_region):
                    self.domain_class_roots2[sub_region].append(c)
                else:
                    self.domain_class_roots2[sub_region] = [c]

                # set @@domain_class_roots
                if Celltype.domain_class_roots.get(sub_region):
                    Celltype.domain_class_roots[sub_region].append(self)
                else:
                    Celltype.domain_class_roots[sub_region] = [self]

        # domain_type は一つのノードに一つしかないので、一つの要素を無条件で取り出す
        if len(self.domain_class_roots2) > 1:
            self.b_need_ptab = True
            nr = list(self.domain_class_roots2.keys())[0].get_link_root()
            if nr.get_domain_type():
                if nr.get_domain_type().get_kind() != Sym("OutOfDomain"):
                    # link root が OutOfDomain でない場合エラーとする
                    # ptab を 置く場所に使われるため（mikan 本来なら OutOfDoamin のファイルに置けばよい)
                    self.cdl_error(
                        "S9999 region '$1' is node/link root and not out of domain ($2). "
                        "This is limitation in current version",
                        nr.get_name(), nr.get_domain_type().get_kind())

            # node root
            if Celltype.domain_class_roots.get(nr) is None:
                Celltype.domain_class_roots[nr] = []

        if G.verbose:
            self.cdl_info("I9999 celltype '$1' has cells in multi-domain.\n", self.name)
            for sub_region, cell_list in self.domain_class_roots2.items():
                delim = ""
                print("celltype={} subRegion={} cells={{".format(
                    self.name, sub_region.get_name()), end="")
                for c in cell_list:
                    print("{}{}".format(delim, c.get_name()), end="")
                    delim = ","
                print(" }\n")

    def optimize(self):

        # port の参照するセルタイプの数、セルの数を求める
        if G.verbose:
            print("=== optimizing celltype {} ===\n".format(
                self.get_namespace_path().get_path_str()))

        self.optimize_call()
        if G.unopt_entry is False:
            self.optimize_entry()

    #=== Celltype#呼び口最適化
    def optimize_call(self):
        for port in self.port:
            if port.get_port_type() != "CALL":
                continue
            if port.is_omit():
                # 呼び口最適化実施
                self.b_cp_optimized = True
                self.n_call_port_omitted_in_CB += 1               # CB で省略する呼び口
                port.set_skelton_useless()                      # スケルトン関数不要最適化
                port.set_VMT_useless()                          # VMT 不要最適化 (直接受け口関数を呼出す)
                if G.verbose:
                    print("optimized by omit: port: {} : o\n".format(port.get_name()))
                continue
            elif port.is_dynamic():
                if G.verbose:
                    print("unoptimized by dynamic: port: {}\n".format(port.get_name()))
                continue
            elif port.is_ref_desc():
                if G.verbose:
                    print("unoptimized by ref_desc: port: {}\n".format(port.get_name()))
                continue

            if G.verbose:
                print("optimizing port : {}\n".format(port.get_name()))

            port_cells = []    # 呼び先セル
            port_ports = []    # 呼び先のポート

            # セルの参照するセルを集める（ポートも一緒に集める）
            for cell in self.cell_list:

                if not cell.is_generate():
                    continue

                jl = cell.get_join_list()
                j = jl.get_item(port.get_name())

                if j:
                    if j.get_array_member2():
                        # 呼び口配列の場合、全部の結合先を集める
                        for j2 in j.get_array_member2():
                            if j2:
                                port_cells.append(j2.get_rhs_cell())
                                port_ports.append(j2.get_rhs_port())   # 右辺のポート
                            else:
                                # optional で、ある添数のみ初期化されていない（すべて初期化されない場合は、下）
                                port_cells.append(None)
                                port_ports.append(None)
                    else:
                        # 全ての結合先を集める
                        port_cells.append(j.get_rhs_cell())
                        port_ports.append(j.get_rhs_port())   # 右辺のポート
                else:
                    # optional で初期化されていない（nil を要素に加えておく）
                    port_cells.append(None)
                    port_ports.append(None)   # 右辺のポート

            # 重複要素を取り除く
            port_cells = uniq(port_cells)
            port_ports = uniq(port_ports)

            # 呼び口の呼び先が一つのポートだけか？
            if len(port_ports) == 1:

                # 呼び口配列が可変長の場合、最適化しない
                     # mikan 呼び口配列要素数マクロ不具合暫定対策
                     # より望ましい修正は、受け口へのポインタは省略するが、配列個数は出力する(#_CP_#, #_TCP_#)
                     # さらに配列個数が定数化できるのであれば、定数マクロを出力 (#_NCPA_#)
                if port.get_array_size() == "[]":
                    continue

                # 呼び口最適化実施
                self.b_cp_optimized = True

                # 呼び先が一つのセルだけか？
                if len(port_cells) == 1:

                    # 呼び口は optional で初期化されていない、または受け口は配列ではないか？
                    if port_ports[0] is None or port_ports[0].get_array_size() is None:

                        self.n_call_port_omitted_in_CB += 1               # CB で省略する呼び口
                        port.set_cell_unique()                          # セル一つだけ最適化
                        port.set_skelton_useless()                      # スケルトン関数不要最適化
                        port.set_VMT_useless()                          # VMT 不要最適化 (直接受け口関数を呼出す)

                        if G.verbose:
                            print("cell_unique, VMT_useless & skelton_useless optimize\n")
                    else:
                        port.set_VMT_useless()                          # VMT 不要最適化 (スケルトン関数を呼出す)

                        if G.verbose:
                            print("VMT_useless optimize\n")

                else:  # 呼び先が複数のセル（単一のポート）

                    # 呼び口は optional で初期化されていない、または受け口は配列ではないか？
                    if port_ports[0] is None or port_ports[0].get_array_size() is None:
                        if not self.singleton:
                            port.set_skelton_useless()                    # スケルトン関数不要最適化
                            port.set_VMT_useless()                        # VMT 不要最適化 (スケルトン関数 or 受け口関数を呼出す)

                            if G.verbose:
                                print("VMT_useless & skelton useless optimize\n")
                        else:
                            port.set_VMT_useless()                           # VMT 不要最適化 (スケルトン関数 or 受け口関数を呼出す)

                            if G.verbose:
                                print("VMT_useless optimize\n")

                port.set_only_callee(port_ports[0], port_cells[0])
                   # set_cell_unique でない場合 cell は意味がない

            # debug
            dbgPrint("{} : # of cells : {}  # of ports : {}\n".format(
                port.get_name(), len(port_cells), len(port_ports)))

    #=== Celltype#受け口最適化
    # optimize_entry は、呼び口最適化の結果を使用している
    def optimize_entry(self):
        # 受け口最適化の設定
        for port in self.port:
            if port.get_port_type() != "CALL":
                continue

            # 呼び口側の最適化状態
            b_VMT_useless = port.is_VMT_useless()
            b_skelton_useless = port.is_skelton_useless()

            # セルの参照するセルを集める（ポートも一緒に集める）
            for cell in self.cell_list:

                if not cell.is_generate():
                    continue

                jl = cell.get_join_list()
                j = jl.get_item(port.get_name())

                if j:    # optional で結合されていない場合 nil
                    if j.get_array_member2():
                        # 呼び口配列
                        for j2 in j.get_array_member2():
                            if j2:
                                port2 = j2.get_rhs_port()   # 右辺のポート
                                # 受け口側の最適化可能性を設定
                                port2.set_entry_VMT_skelton_useless(b_VMT_useless, b_skelton_useless)
                            #else
                            #  optional で呼び口配列要素が初期化されていない
                    else:
                        port2 = j.get_rhs_port()      # 右辺のポート
                        # 受け口側の最適化可能性を設定
                        port2.set_entry_VMT_skelton_useless(b_VMT_useless, b_skelton_useless)

    #Celltype# リセットする
    def reset_optimize(self):
        Celltype._ID_BASE = Celltype.ID_BASE      # 本当は一回だけでよい
        self.id_base = 1             # set_cell_id でリセットされるので不要

        self.b_cp_optimized = False  # 呼び口最適化
        self.n_call_port_omitted_in_CB = 0 # 呼び口最適化により不生成となったポートの数
        self.n_cell_gen = 0          # 生成セル個数
        for p in self.port:
            p.reset_optimize()
        self.included_header = {}
        self.domain_roots = {}
        self.domain_class_roots = {}
        self.domain_class_roots2 = {}

    #Celltype# ヘッダは include されているか
    #hname::Symbol : ヘッダ名
    #RETURN:: bool_t: false インクルードされていない、true インクルードされている
    # #_ISH_#, #_ICT_# でヘッダが取り込まれているかチェックする
    # false が返った場合、hname は登録されて、次回の呼び出しでは true が返る
    def header_included(self, hname):
        if self.included_header.get(hname) is None:
            self.included_header[hname] = True
            return False
        else:
            return True
