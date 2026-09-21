# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/componentobj/namespace.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

from tecslib.core import globals as G
from tecslib.core.syntaxobj.node import NSBDNode
from tecslib.core.toplevel import dbgPrint


class _NamespaceGetGlobalName:
    # Ruby の Namespace.get_global_name (クラス) と Namespace#get_global_name (インスタンス) の同名共存
    def __get__(self, obj, owner):
        if obj is None:
            def class_get():
                # Ruby の @@ と同様、サブクラス経由でも Namespace 本体のクラス変数を使う
                if Namespace.namespace_sp <= 0:
                    return ""
                path = str(Namespace.namespace_stack[1].get_name())
                i = 2
                while i <= Namespace.namespace_sp:
                    path = path + "_" + str(Namespace.namespace_stack[i].get_name())
                    i += 1
                return path
            return class_get
        return lambda: obj.global_name


#== Namespace
#
# root namespace だけ、Region クラスのインスタンスとして生成される
# root namespace は、root region を兼ねるため
#
# @cell_list は Region の場合にのみ持つ (mikan @cell_list 関連は Region に移すべき)
#
class Namespace(NSBDNode):
# @name::  Symbol     # root の場合 "::" (String)
# @global_name:: str
# @name_list:: NamedList   Signature,Celltype,CompositeCelltype,Cell,Typedef,Namespace
# @struct_tag_list:: NamedList : StructType
# @namespace_list:: Namespace[] : Region は Namespace の子クラスであり、含まれる
# @signature_list:: Sginature[]
# @celltype_list:: Celltype[]
# @compositecelltype_list:: CompositeCelltype[]
# @cell_list:: Cell[]
# @typedef_list:: Typedef[]
# @decl_list:: ( Typedef | StructType | EnumType )[]   依存関係がある場合に備えて、順番どおりに配列に格納 mikan enum
# @const_decl_list:: Decl[]
# @cache_n_cells:: Integer :  get_n_cells の結果をキャッシュする
# @cache_generating_region:: Region :  get_n_cells の結果をキャッシュするしているリージョン
# @NamespacePath:: NamespacePath: NamespacePath クラスのオブジェクト
    # mikan namespace の push, pop

    # namespace 階層用のスタック
    namespace_stack = []      # namespace_stack[0] = "::" (generator.rb)
    namespace_sp = -1

    # Generator ネスト用のスタック (namespace 階層用のスタックを対比する)
    nest_stack_index = -1
    nest_stack = []

    root_namespace = None

    get_global_name = _NamespaceGetGlobalName()

    # Generator ネスト用スタックの push, pop (クラスメソッド)
    # Ruby の @@ クラス変数は継承階層で共有される。Python では cls.x = すると
    # Region.push() 経由で Region にシャドウが作られるため、常に Namespace. を使う。
    @classmethod
    def push(cls):
        dbgPrint("push Namespace\n")
        Namespace.nest_stack_index += 1
        if Namespace.nest_stack_index >= len(Namespace.nest_stack):
            Namespace.nest_stack.append(None)
        Namespace.nest_stack[Namespace.nest_stack_index] = [
            Namespace.namespace_stack, Namespace.namespace_sp]
        if Namespace.root_namespace:
            Namespace.namespace_sp = 0
            if Namespace.namespace_sp >= len(Namespace.namespace_stack):
                Namespace.namespace_stack.append(None)
            Namespace.namespace_stack[Namespace.namespace_sp] = Namespace.root_namespace

    @classmethod
    def pop(cls):
        dbgPrint("pop Namespace\n")
        Namespace.namespace_stack, Namespace.namespace_sp = (
            Namespace.nest_stack[Namespace.nest_stack_index])
        Namespace.nest_stack_index -= 1
        if Namespace.nest_stack_index < -1:
            raise Exception("TooManyRestore")

    # namespace 階層用スタックの push, pop (インスタンスメソッド)
    def push_inst(self, ns=None):
        Namespace.namespace_sp += 1
        if Namespace.namespace_sp >= len(Namespace.namespace_stack):
            Namespace.namespace_stack.append(None)
        Namespace.namespace_stack[Namespace.namespace_sp] = self
        dbgPrint("Namespace.PUSH {} {}\n".format(Namespace.namespace_sp, self.name))

    def pop_inst(self):
        dbgPrint("Namespace.POP {} {}\n".format(Namespace.namespace_sp, self.name))
        Namespace.namespace_sp -= 1
        if Namespace.namespace_sp < 0:
            raise Exception("StackUnderflow")

    def __init__(self, name):

        dbgPrint("Namespace: initialize name={} sp={} **\n".format(name, Namespace.namespace_sp))
        super().__init__()
        self.name = name

        if name == "::":
            if Namespace.root_namespace is not None:
                # root は一回のみ生成できる
                raise Exception("try to re-create root namespace")
            Namespace.root_namespace = self
            from tecslib.core.componentobj.namespacepath import NamespacePath
            self.NamespacePath = NamespacePath(name, True)
        else:
            ns = Namespace.namespace_stack[Namespace.namespace_sp].find_inst(name)
            if isinstance(ns, Namespace):
                dbgPrint("namespace: re-appear {}\n".format(self.name))
                # 登録済み namespace の再登録
                self.set_owner(Namespace.namespace_stack[Namespace.namespace_sp])
                ns.push_inst(ns)
                return
            elif ns:
                self.cdl_error("S1151 $1: not namespace", self.name)
                prev_locale = ns.get_locale()
                print("previous: {}: line {} '{}' defined here".format(
                    prev_locale[0], prev_locale[1], name))
            dbgPrint("namespace: 1st-appear {}\n".format(self.name))

        dbgPrint("Namespace: initialize name={} sp={}\n".format(name, Namespace.namespace_sp))
        if Namespace.namespace_sp >= 0:   # root は除外
            dbgPrint("Namespace: initialize2 name={} sp={}\n".format(name, Namespace.namespace_sp))
            # Ruby はインスタンスメソッド new_namespace を呼ぶ。classmethod 経由だと
            # Region インスタンスから呼ばれたとき cls=Region になり得るため直接呼ぶ。
            Namespace.namespace_stack[Namespace.namespace_sp].new_namespace_inst(self)
        self.push_inst()

        self.global_name = Namespace.get_global_name()    # stack 登録後取る
        from tecslib.core.syntaxobj.namedlist import NamedList
        self.name_list = NamedList(None, "symbol in namespace '{}'".format(self.name))
        self.struct_tag_list = NamedList(None, "struct tag")

        self.namespace_list = []
        self.signature_list = []
        self.celltype_list = []
        self.compositecelltype_list = []
        self.cell_list = []
        self.typedef_list = []
        self.decl_list = []
        self.const_decl_list = []
        self.cache_n_cells = None
        self.cache_generating_region = None
        if self.NamespacePath is None:
            # root namespace の場合は設定済 (親 namespace が見つからず例外になる)
            self.set_namespace_path()  # @NamespacePath の設定

    def end_of_parse(self):
        self.pop_inst()

    def get_name(self):
        return self.name

    #=== Namespace:: global_name を得る
    # parse 中のみこのメソッドは使える
    # STAGE: P
    # (get_global_name は _NamespaceGetGlobalName ディスクリプタ)

    #=== Namespace#セルの個数を得る
    # 子 region が linkunit, node 指定されていれば、含めない（別のリンク単位）
    # プロトタイプ宣言のもののみの個数を含めない
    # mikan namespace 下に cell を置けない仕様になると、このメソッドは Region のものでよい
    # mikan 上記の場合 instance_of? Namespace の条件判定は不要となる
    def get_n_cells(self):
        if self.cache_generating_region == G.generating_region:
            # このメソッドは繰り返し呼び出されるため、結果をキャッシュする
            return self.cache_n_cells

        count = 0
        for c in self.cell_list:
            # 定義かプロトタイプ宣言だけかは、new_cell の段階で判断できないため、カウントしなおす
            if c.get_f_def() == True:
                # print "get_n_cells: cell: #{c.get_name}\n"
                count += 1

        from tecslib.rubylib.symbol import Sym
        for ns in self.namespace_list:
            if type(ns) is Namespace:
                count += ns.get_n_cells()
            else:
                # ns は Region である
                rt = ns.get_region_type()
                # print "get_n_cells: region: #{ns.get_name}: #{rt}\n"
                if rt == Sym("NODE") or rt == Sym("LINKUNIT"):
                    # 別の linkunit なので加算しない
                    pass
                else:
                    count += ns.get_n_cells()

        self.cache_generating_region = G.generating_region
        self.cache_n_cells = count
        return count

    #=== Namespace.find : in_path で示されるオブジェクトを探す
    #in_path:: NamespacePath
    #in_path:: Array : 古い形式
    #  path [ "::", "ns1", "ns2" ]   absolute
    #  path [ "ns1", "ns2" ]         relative
    @classmethod
    def find(cls, in_path):

        if type(in_path) is list:
            # raise "Namespace.find: old fashion"

            path = in_path
            length = len(path)
            if length == 1:
                return cls.find_one(path[0])

            name = path[0]
            if name == "::":
                i = 1
                name = path[i]   # 構文的に必ず存在
                object = Namespace.root_namespace.find_inst(name)  # root
            else:
                # 相対パス
                i = 0
                object = Namespace.namespace_stack[Namespace.namespace_sp].find_one_inst(name) # crrent

        else:
            from tecslib.core.componentobj.namespacepath import NamespacePath
            if not isinstance(in_path, NamespacePath):
                raise Exception("unexpected path")
            path = in_path.get_path()
            length = len(path)

            if length == 0:
                if in_path.is_absolute():
                    return Namespace.root_namespace
                else:
                    raise Exception("path length 0, not absolute")

            i = 0
            name = path[0]
            if in_path.is_absolute():
                object = Namespace.root_namespace.find_inst(name)  # root
            else:
                bns = in_path.get_base_namespace()
                object = bns.find_one_inst(name)           # crrent

        i += 1
        while i < length:

            if not isinstance(object, Namespace):
                # クラスメソッド内で cdl_error を呼び出すことはできない
                # また、前方参照対応後、正確な行番号が出ない問題も生じる
                # cdl_error( "S1092 \'$1\' not namespace" , name )
                # このメソッドから nil が帰った場合 "not found" が出るので、ここでは出さない
                return None

            object = object.find_inst(path[i])
            i += 1

        return object


    def find_inst(self, name):
        return self.name_list.get_item(name)

    #=== Namespace# namespace から探す。見つからなければ親 namespace から探す
    @classmethod
    def find_one(cls, name):
        return Namespace.namespace_stack[Namespace.namespace_sp].find_one_inst(name)

    def find_one_inst(self, name):

        object = self.find_inst(name)
        # これは出すぎ
        # dbgPrint "in '#{@name}' find '#{name}' object #{object ? object.class : "Not found"}\n"

        if object is not None:
            return object
        elif self.name != "::":
            return self.owner.find_one_inst(name)
        else:
            return None

    @classmethod
    def get_current(cls):
        return Namespace.namespace_stack[Namespace.namespace_sp]

    @classmethod
    def find_tag(cls, name):
        # mikan tag : namespace の path に対応しない
        # namespace の中にあっても、root namespace にあるものと見なされる
        # よって カレント namespace から根に向かって探す
        i = Namespace.namespace_sp
        while i >= 0:
            res = Namespace.namespace_stack[i].find_tag_inst(name)
            if res:
                return res
            i -= 1

    def find_tag_inst(self, name):
        return self.struct_tag_list.get_item(name)

 ### namespace
    @classmethod
    def new_namespace(cls, namespace):
        Namespace.namespace_stack[Namespace.namespace_sp].new_namespace_inst(namespace)

    def new_namespace_inst(self, namespace):
        dbgPrint("new_namespace: {}:{} {}:{} \n".format(
            self.name, self, namespace.get_name(), namespace))
        namespace.set_owner(self)   # Namespace (Namespace)

        self.name_list.add_item(namespace)
        self.namespace_list.append(namespace)

 ### signature
    @classmethod
    def new_signature(cls, signature):
        Namespace.namespace_stack[Namespace.namespace_sp].new_signature_inst(signature)

    def new_signature_inst(self, signature):
        signature.set_owner(self)   # Signature (Namespace)
        self.name_list.add_item(signature)
        self.signature_list.append(signature)

 ### celltype
    @classmethod
    def new_celltype(cls, celltype):
        Namespace.namespace_stack[Namespace.namespace_sp].new_celltype_inst(celltype)

    def new_celltype_inst(self, celltype):
        celltype.set_owner(self)   # Celltype (Namespace)
        self.name_list.add_item(celltype)
        self.celltype_list.append(celltype)

 ### compositecelltype
    @classmethod
    def new_compositecelltype(cls, compositecelltype):
        Namespace.namespace_stack[Namespace.namespace_sp].new_compositecelltype_inst(compositecelltype)

    def new_compositecelltype_inst(self, compositecelltype):
        compositecelltype.set_owner(self)   # CompositeCelltype (Namespace)
        self.name_list.add_item(compositecelltype)
        self.compositecelltype_list.append(compositecelltype)

 ### cell (Namespace)
    @classmethod
    def new_cell(cls, cell):
        Namespace.namespace_stack[Namespace.namespace_sp].new_cell_inst(cell)

    def new_cell_inst(self, cell):
        dbgPrint("Namespace.new_cell: {}::{}\n".format(
            self.NamespacePath.get_path_str(), cell.get_name()))
        from tecslib.core.componentobj.region import Region
        if not self.is_root() and not isinstance(self, Region):
            self.cdl_error("S9999 '$1' cell cannot be placed under namespace", cell.get_name())
        cell.set_owner(self)   # Cell (Namespace)
        self.name_list.add_item(cell)
        self.cell_list.append(cell)

    #=== Namespace# 参照されているが、未定義のセルを探す
    # プロトタイプ宣言だけで定義されていないケースをエラーとする
    # 受動の未結合セルについて警告する
    def check_ref_but_undef(self):
        for c in self.cell_list:
            if not c.get_f_def():   # Namespace の @cell_list にはプロトタイプが含まれるケースあり
                if c.get_f_ref():
                    c.cdl_error("S1093 $1 : undefined cell", c.get_namespace_path().get_path_str())
                elif G.verbose:
                    c.cdl_warning("W1006 $1 : only prototype, unused and undefined cell",
                                  c.get_namespace_path().get_path_str())
            else:
                dbgPrint("check_ref_but_undef: {}\n".format(c.get_global_name()))
                ct = c.get_celltype()
                # if c.get_f_ref == false && c.is_generate? && ct && ct.is_inactive? then
                if c.get_f_ref() == False and ct and ct.is_inactive():
                    c.cdl_warning("W1007 $1 : non-active cell has no entry join and no factory",
                                  c.get_namespace_path().get_path_str())
                if c.has_ineffective_restrict_specifier():
                    c.cdl_warning("W9999: $1 has ineffective restrict specifier",
                                  c.get_namespace_path().get_path_str())
        for n in self.namespace_list:
            n.check_ref_but_undef()

    #=== Namespace# セルの受け口の参照カウントを設定する
    def set_port_reference_count(self):
        for c in self.cell_list:
            c.set_port_reference_count()
        for n in self.namespace_list:
            n.set_port_reference_count()

 ### struct
    @classmethod
    def new_structtype(cls, struct):
        Namespace.namespace_stack[Namespace.namespace_sp].new_structtype_inst(struct)

    def new_structtype_inst(self, struct):
        # struct.set_owner self   # StructType (Namespace) # StructType は BDNode ではない
        dup = self.struct_tag_list.get_item(struct.get_name())
        if dup is not None:
            if struct.same(dup):
                # 同じものが typedef された
                # p "#{struct.get_name}"
                return

        self.struct_tag_list.add_item(struct)
        self.decl_list.append(struct)

 ### typedef
    @classmethod
    def new_typedef(cls, typedef):
        Namespace.namespace_stack[Namespace.namespace_sp].new_typedef_inst(typedef)

    def new_typedef_inst(self, typedef):
        typedef.set_owner(self)   # TypeDef (Namespace)
        dup = self.name_list.get_item(typedef.get_name())
        if dup is not None:
            typedef_type = typedef.get_declarator().get_type().get_original_type()
            dup_type = dup.get_declarator().get_type().get_original_type()
            # print "typedef: #{typedef.get_name} = #{typedef_type.get_type_str} #{typedef_type.get_type_str_post}\n"
            if (typedef_type.get_type_str() == dup_type.get_type_str() and
                    typedef_type.get_type_str_post() == dup_type.get_type_str_post()):
                # 同じものが typedef された
                # ここへ来るのは C で関数ポインタを typedef しているケース
                # 以下のように二重に定義されている場合は type_specifier_qualifier_list として扱われる
                #    typedef long LONG;
                #    typedef long LONG;
                # bnf.y.rb では declarator に TYPE_NAME を許さないので、ここへ来ることはない
                # p "#{typedef.get_declarator.get_type.get_type_str} #{typedef.get_name} #{typedef.get_declarator.get_type.get_type_str_post}"
                return
            # p "prev: #{dup.get_declarator.get_type.get_type_str}#{dup.get_declarator.get_type.get_type_str_post} current:#{typedef.get_declarator.get_type.get_type_str} #{typedef.get_declarator.get_type.get_type_str_post}"

        # p "typedef: #{typedef.get_name}  #{typedef.get_declarator.get_type.get_original_type.get_type_str}#{typedef.get_declarator.get_type.get_original_type.get_type_str_post}"
        # typedef.show_tree 0

        self.name_list.add_item(typedef)
        self.typedef_list.append(typedef)
        self.decl_list.append(typedef)

    @classmethod
    def is_typename(cls, str_):
        i = Namespace.namespace_sp
        while i >= 0:
            if Namespace.namespace_stack[i].is_typename_inst(str_):
                return True
            i -= 1
        return False

    def is_typename_inst(self, str_):
        from tecslib.core.syntaxobj.typedef import Typedef
        if type(self.name_list.get_item(str_)) is Typedef:
            return True
        else:
            return False

 ### const_decl
    @classmethod
    def new_const_decl(cls, decl):
        Namespace.namespace_stack[Namespace.namespace_sp].new_const_decl_inst(decl)

    def new_const_decl_inst(self, decl):
        from tecslib.core.types import IntType, FloatType, BoolType, PtrType
        from tecslib.rubylib.symbol import Sym
        decl.set_owner(self)   # Decl (Namespace:const)
        if not decl.is_const():			# const 修飾さていること
            if decl.is_type(PtrType):
                self.cdl_error("S1094 $1: pointer is not constant. check 'const'", decl.get_name())
            else:
                self.cdl_error("S1095 $1: not constant", decl.get_name())
        elif (not decl.is_type(IntType) and not decl.is_type(FloatType) and
                not decl.is_type(BoolType) and not decl.is_type(PtrType)):
                                            # IntType, FloatType であること
            self.cdl_error("S1096 $1: should be int, float, bool or pointer type", decl.get_name())
        elif decl.get_initializer() is None:   # 初期値を持つこと
            self.cdl_error("S1097 $1: has no initializer", decl.get_name())
#        elif decl.get_initializer.eval_const(nil) == nil then  #eval_const は check_init で呼出されるので二重チェック
#                                            # mikan 初期値が型に対し適切であること
#            cdl_error( "S1098 $1: has unsuitable initializer" , decl.get_name )
        else:
            decl.get_type().check_init(self.locale, decl.get_name(), decl.get_initializer(), Sym("CONSTANT"))
            self.name_list.add_item(decl)
            self.const_decl_list.append(decl)

 ### region
    # def self.new_region( region )
    #   @@namespace_stack[ @@namespace_sp].new_region( region )
    # end
#
    # def new_region( region )
    #   region.set_owner self   # Rgion (Namespace)
    #   @name_list.add_item( region )
    # end

 ###

    #=== Namespace# すべてのセルの require ポートを設定
    # STAGE: S
    def set_require_join(self):
        for ct in self.celltype_list:
            ct.set_require_join()
        # すべての namespace について require ポートをセット
        for ns in self.namespace_list:
            ns.set_require_join()

    #=== Namespace# Join への definition の設定とチェック
    # セルタイプに属するすべてのセルに対して実施
    def set_definition_join(self):
        # celltype のコードを生成
        for c in self.cell_list:
            dbgPrint("set_definition_join {}\n".format(c.get_name()))
            c.set_definition_join()
        for ns in self.namespace_list:
            ns.set_definition_join()

    #=== Namespace# set_max_entry_port_inner_cell
    # セルタイプに属するすべてのセルに対して実施
    def set_max_entry_port_inner_cell(self):
        # celltype のコードを生成
        for c in self.cell_list:
            c.set_max_entry_port_inner_cell()
        for ns in self.namespace_list:
            ns.set_max_entry_port_inner_cell()

    #=== Namespace# セルの結合をチェックする
    def check_join(self):
        for c in self.cell_list:
            dbgPrint("check_join {}\n".format(c.get_name()))
            c.check_join()
            c.check_reverse_require()
        for ns in self.namespace_list:
            ns.check_join()

    #== Namespace# ルートか?
    # ルートネームスペース と ルートリージョンは同じ
    def is_root(self):
        return self.name == "::"

    #== Namespace# ルートを得る
    # ルートリージョンとルートネームスペースは同じオブジェクト
    @classmethod
    def get_root(cls):
        return Namespace.root_namespace

    #== Namespace に属するシグニチャのリスト
    def get_signature_list(self):
        return self.signature_list

    #== Namespace# 子ネームスペースのリスト
    #
    def get_namespace_list(self):
        return self.namespace_list

    #== Namespace (Region) に属するセルのリスト
    def get_cell_list(self):
        return self.cell_list

    #== Namespace (Region)# 子リージョンのリスト
    #
    # リージョンは Namespace クラスで namespace として記憶されている
    def get_region_list(self):
        return self.namespace_list

    #== Namespace # NamespacePath(クラスのインスタンス) を返す
    # NamespacePath クラスのインスタンスを返す (文字列などではなく)
    #
    def get_NamespacePath(self):
        return self.NamespacePath

    def show_tree(self, indent):
        print("  " * indent, end="")
        print("{}: name: {} path: {}".format(
            self.__class__.__name__, self.name, self.get_namespace_path().get_path_str()))
        self.struct_tag_list.show_tree(indent + 1)
        self.name_list.show_tree(indent + 1)
