# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/componentobj/compositecelltype.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

from tecslib.core.componentobj.celltype_module import CelltypePluginModule
from tecslib.core.plugin_module import PluginModule
from tecslib.core.syntaxobj.node import NSBDNode
from tecslib.core.toplevel import dbgPrint
from tecslib.rubylib.rb import to_s
from tecslib.rubylib.symbol import Sym


class CompositeCelltype(NSBDNode, CelltypePluginModule, PluginModule):  # < Nestable
# @name:: str
# @global_name:: str
# @cell_list_in_composite:: NamedList   Cell
# @cell_list::Array :: [ Cell ] : cell of CompositeCelltype's cell
# @export_name_list:: NamedList : CompositeCelltypeJoin
# @port_list:: CompositeCelltypeJoin[]
# @attr_list:: CompositeCelltypeJoin[]
# @b_singleton:: bool : 'singleton' specified
# @b_active:: bool : 'active' specified
# @real_singleton:: bool : has singleton cell in this composite celltype
# @real_active:: bool : has active cell in this composite celltype
# @name_list:: NamedList item: Decl (attribute), Port エクスポート定義
# @internal_allocator_list:: [ [cell, internal_cp_name, port_name, func_name, param_name, ext_alloc_ent], ... ]
# @generate:: [ Symbol, String, Plugin ]  = [ PluginName, option, Plugin ] Plugin は生成後に追加される
# @generate_list:: [ [ Symbol, String, Plugin ], ... ]   generate 文で追加された generate

    nest_stack_index = -1
    nest_stack = []
    current_object = None

    @classmethod
    def push(cls):
        cls.nest_stack_index += 1
        if cls.nest_stack_index >= len(cls.nest_stack):
            cls.nest_stack.append(None)
        cls.nest_stack[cls.nest_stack_index] = cls.current_object
        cls.current_object = None

    @classmethod
    def pop(cls):
        cls.current_object = cls.nest_stack[cls.nest_stack_index]
        cls.nest_stack_index -= 1
        if cls.nest_stack_index < -1:
            raise Exception("TooManyRestore")

    def __init__(self, name):
        from tecslib.core.bnf import Generator
        from tecslib.core.componentobj.namespace import Namespace
        from tecslib.core.syntaxobj.namedlist import NamedList

        super().__init__()
        self.name = name
        self.cell_list_in_composite = NamedList(None, "in composite celltype {}".format(name))
        self.cell_list = []
        self.export_name_list = NamedList(None, "export in composite celltype {}".format(name))
        self.name_list = NamedList(None, "in composite celltype {}".format(name))
        CompositeCelltype.current_object = self

        self.b_singleton = False
        self.real_singleton = None
        self.b_active = False
        self.real_active = None
        if to_s(Namespace.get_global_name()) == "":
            self.global_name = self.name
        else:
            self.global_name = Sym("{}_{}".format(Namespace.get_global_name(), self.name))

        Namespace.new_compositecelltype(self)
        self.set_namespace_path()  # @NamespacePath の設定

        self.port_list = []
        self.attr_list = []
        self.internal_allocator_list = []
        self._generate = None
        self.generate_list = []
        self.set_specifier_list(Generator.get_statement_specifier())

    @classmethod
    def end_of_parse(cls):
        cls.current_object.end_of_parse_inst()
        cls.current_object = None

    # CompositeCelltype#end_of_parse
    def end_of_parse_inst(self):
        from tecslib.core.componentobj.port import Port
        from tecslib.core.syntaxobj.decl import Decl

        # singleton に関するチェック
        if self.b_singleton and self.real_singleton is None:
            self.cdl_warning("W1004 $1 : specified singleton but has no singleton in this celltype", self.name)
        elif not self.b_singleton and self.real_singleton is not None:
            if not self.b_singleton:
                self.cdl_error("S1053 $1 must be singleton. inner cell '$2' is singleton",
                               self.name, self.real_singleton.get_name())

        # active に関するチェック
        if self.b_active and self.real_active is None:
            self.cdl_error("S1054 $1 : specified active but has no active in this celltype", self.name)
        elif not self.b_active and self.real_active is not None:
            self.cdl_error("S1055 $1 must be active. inner cell '$2' is active",
                           self.name, self.real_active.get_name())

        # @allocator_instance を設定する
        for n in self.name_list.get_items():
            if type(n) is Port:
                n.set_allocator_instance()

        # リレーアロケータの entry 側
        for p in self.port_list:
            if p.get_port_type() == "ENTRY":
                if p.get_allocator_instance() is None:
                    continue

                for name, ai in p.get_allocator_instance().items():
                    if ai[0] == "RELAY_ALLOC":
                        self.new_join_inst(
                            Sym("{}_{}_{}".format(p.get_name(), ai[4], ai[5])),
                            p.get_cell_name(),
                            Sym("{}_{}_{}".format(p.get_cell_elem_name(), ai[4], ai[5])),
                            "CALL")

        # mikan relay が正しく抜けているかチェックされていない

        # callback 結合
        for c in self.cell_list_in_composite.get_items():
            ct = c.get_celltype()
            if ct:
                c.create_reverse_join_inst()

        # 意味解析
        for c in self.cell_list_in_composite.get_items():
            c.set_definition_join()

        # cell の未結合の呼び口がないかチェック
        for c in self.cell_list_in_composite.get_items():
            c.check_join()
            c.check_reverse_require()

        # 呼び口の結合について、export と内部結合の両方がないかチェック
        # リレーアロケータ、内部アロケータの設定
        for p in self.port_list:
            p.check_dup_init()

        # すべてのエクスポート定義に対応した呼び口、受け口、属性が存在するかチェック
        for n in self.name_list.get_items():
            if self.export_name_list.get_item(n.get_name()) is None:
                self.cdl_error("S1056 $1 : cannot export, nothing designated", n.get_name())

        # 内部アロケータを設定する
        for cell, cp_internal_name, port_name, fd_name, par_name, ext_alloc_ent in self.internal_allocator_list:
            res = ext_alloc_ent.get_allocator_rhs_elements("INTERNAL_ALLOC")
            ep_name = res[0]
            cj = self.export_name_list.get_item(ep_name)
            internal_alloc_name_from_port_def = cj.get_cell_name()
            internal_alloc_ep_name_from_port_def = cj.get_cell_elem_name()

            # puts "internal_allocator #{cell.get_name} #{cp_internal_name} #{port_name}.#{fd_name}.#{par_name}"
            for a in cell.get_allocator_list():
                # puts "allocator_list of #{cell.get_name} #{a[0]} #{a[1]}.#{a[2]}.#{a[3]}.#{a[4]} #{a[5].to_s}"
                if cp_internal_name == Sym("{}_{}_{}".format(a[1], a[3], a[4])):
                    dbgPrint("internal_allocator {{cp_internal_name}} {}_{}_{}\n".format(a[1], a[3], a[4]))
                    dbgPrint("internal_allocator: {}, {}.{}\n".format(
                        a[5], internal_alloc_name_from_port_def, internal_alloc_ep_name_from_port_def))
                    if to_s(a[5]) != "{}.{}".format(internal_alloc_name_from_port_def, internal_alloc_ep_name_from_port_def):
                        self.cdl_error("S1173 $1: allocator mismatch from $2's allocator",
                                       "{}.{}.{}".format(port_name, fd_name, par_name), cell.get_name())

        # composite プラグイン
        if self._generate:
            self.celltype_plugin()

    ### CompositeCelltype#new_cell_in_composite
    @classmethod
    def new_cell_in_composite(cls, cell):
        cls.current_object.new_cell_in_composite_inst(cell)

    def new_cell_in_composite_inst(self, cell):
        cell.set_owner(self)  # Cell (in_omposite)
        self.cell_list_in_composite.add_item(cell)
        if cell.get_celltype():    # nil ならば、すでにセルタイプなしエラー
            if cell.get_celltype().is_singleton():
                self.real_singleton = cell
            if cell.get_celltype().is_active():
                self.real_active = cell

    ### join
    @classmethod
    def new_join(cls, export_name, internal_cell_name,
                 internal_cell_elem_name, type):
        # Ruby は最後の式が戻り値になるので return が必要
        return cls.current_object.new_join_inst(
            export_name, internal_cell_name, internal_cell_elem_name, type)

    ### CompositeCelltype#new_cell
    def new_cell(self, cell):
        self.cell_list.append(cell)

        # セルタイププラグインの適用
        self.celltype_plugin_new_cell(cell)

    #=== CompositeCelltype# CompositeCelltypeJoin を作成
    # STAGE: B
    #export_name:: Symbol : 外部に公開する名前
    #internal_cell_name:: Symbol : 内部セル名
    #internal_cell_elem_name:: Symbol : 内部セルの要素名（呼び口名、受け口名、属性名のいずれか）
    #type::  :CALL, :ENTRY, :ATTRIBUTE のいずれか（構文要素としてあるべきもの）
    #RETURN:: Decl | Port : エクスポート定義
    # new_join は
    #   cCall => composite.cCall;     (セル内)
    #   attr = composite.attr;        (セル内)
    #   composite.eEnt => cell2.eEnt; (セル外)
    # の構文要素の出現に対して呼び出される
    def new_join_inst(self, export_name, internal_cell_name,
                 internal_cell_elem_name, type_):

        from tecslib.core.componentobj.compositecelltypejoin import CompositeCelltypeJoin
        from tecslib.core.componentobj.port import Port
        from tecslib.core.syntaxobj.decl import Decl

        dbgPrint("new_join: {} {} {}\n".format(export_name, internal_cell_name, internal_cell_elem_name))

        cell = self.cell_list_in_composite.get_item(internal_cell_name)
        if cell is None:
            self.cdl_error("S1057 $1 not found in $2", internal_cell_name, self.name)
            return

        celltype = cell.get_celltype()
        if celltype is None:    # celltype == nil ならすでにエラー
            return

        # 内部セルのセルタイプから対応要素を探す
        # このメソッドは、構文上、呼び口、受け口、属性が記述できる箇所から呼出される
        # 構文上の呼出し位置（記述位置）と、要素が対応したものかチェック
        obj = celltype.find(internal_cell_elem_name)
        if type(obj) is Decl:
            if obj.get_kind() == "VAR":
                self.cdl_error("S1058 '$1' : cannot export var", internal_cell_elem_name)
                return
            elif type_ != "ATTRIBUTE":
                self.cdl_error("S1059 '$1' : exporting attribute. write in cell or use '=' to export attribute", export_name)
                # return 次のエラーを避けるために処理続行し、付け加えてみる
        elif type(obj) is Port:
            if obj.get_port_type() != type_:
                self.cdl_error("S1060 '$1' : port type mismatch. $2 type is allowed here.", export_name, type_)
                # return 次のエラーを避けるために処理続行し、付け加えてみる
        else:
            self.cdl_error("S1061 '$1' : not defined", internal_cell_elem_name)
            dbgPrint("S1061 CompositeCelltypeJoin#new_join: {} => {}.{} {}\n".format(
                export_name, internal_cell_name, internal_cell_elem_name, type_))
            return

        # エクスポート定義と一致するかどうかチェック
        obj2 = self.name_list.get_item(export_name)
        if obj2 is None:
            self.cdl_error("S1062 $1 has no export definition", export_name)
        elif type(obj2) is Decl:
            if type(obj) is not Decl:
                self.cdl_error("S1063 $1 is port but previously defined as an attribute", export_name)
            elif not obj.get_type().equal(obj2.get_type()):
                self.cdl_error("S1064 $1 : type '$2$3' mismatch with pprevious definition'$4$5'",
                               export_name,
                               obj.get_type().get_type_str(), obj.get_type().get_type_str_post(),
                               obj2.get_type().get_type_str(), obj2.get_type().get_type_str_post())
        elif type(obj2) is Port:
            if type(obj) is Port:
                if obj.get_port_type() != obj2.get_port_type():
                    self.cdl_error("S1065 $1 : port type $2 mismatch with previous definition $3",
                                   export_name, obj.get_port_type(), obj2.get_port_type())
                elif obj.get_signature() != obj2.get_signature():
                    if obj.get_signature() is not None and obj2.get_signature() is not None:
                        # nil ならば既にエラーなので報告しない
                        self.cdl_error("S1066 $1 : signature '$2' mismatch with previous definition '$3'",
                                       export_name, obj.get_signature().get_name(), obj2.get_signature().get_name())
                elif obj.get_array_size() != obj2.get_array_size():
                    self.cdl_error("S1067 $1 : array size mismatch with previous definition", export_name)
                elif obj.is_optional() != obj2.is_optional():
                    self.cdl_error("S1068 $1 : optional specifier mismatch with previous definition", export_name)
                elif obj.is_omit() != obj2.is_omit():
                    self.cdl_error("S9999 $1 : omit specifier mismatch with previous definition", export_name)
                elif obj.is_dynamic() != obj2.is_dynamic():
                    self.cdl_error("S9999 $1 : dynamic specifier mismatch with previous definition", export_name)
                elif obj.is_ref_desc() != obj2.is_ref_desc():
                    self.cdl_error("S9999 $1 : ref_desc specifier mismatch with previous definition", export_name)
            else:
                self.cdl_error("S1069 $1 is an attribute but previously defined as a port", export_name)

        join = CompositeCelltypeJoin(export_name, internal_cell_name,
                                     internal_cell_elem_name, cell, obj2)
        join.set_owner(self)   # CompositeCelltypeJoin
        cell.add_compositecelltypejoin(join)

        # debug
        dbgPrint("compositecelltype join: add {} {} = {}.{}\n".format(
            cell.get_name(), export_name, internal_cell_name, internal_cell_elem_name))

        if type(obj) is Decl:
            # attribute
#      # 内部から外部へ複数の結合がないかチェック
#      found = false
#      @attr_list.each{ |a|
#        if a.get_name == join.get_name then
#          found = true
#          break
#        end
#      }
#      if found == false then
            self.attr_list.append(join)
#      end
        else:
            # call/entry port
#      # 内部から外部へ複数の結合がないかチェック
#      found = false
#      @port_list.each{ |port|
#        if port.get_name == join.get_name then
#          found = true
#          break
#        end
#      }
#      if found == false then
            self.port_list.append(join)
#      end

        # join を @export_name_list に登録（重複チェックとともに，後で行われる CompositeCelltypeJoin の clone に備える）
        if type(obj) is Decl and self.export_name_list.get_item(export_name):
            # 既に存在する。追加しない。新仕様では、@export_name_list に同じ名前が含まれることがある。
            pass
        elif type(obj) is Port and obj.get_port_type() == "CALL" and self.export_name_list.get_item(export_name):
            # 既に存在する。追加しない。新仕様では、@export_name_list に同じ名前が含まれることがある。
            pass
        else:
            # print "Composite:new_join: #{join.get_name} len=#{@export_name_list.get_items.length}\n"
            self.export_name_list.add_item(join)

        # export するポートに含まれる send/receive パラメータのアロケータ(allocator)呼び口をセルと結合
        if type(obj2) is Port:
            def _each_param(port, fd, par):
                case = par.get_direction()                        # 引数の方向指定子 (in, out, inout, send, receive )
                if case in ("SEND", "RECEIVE"):
                    cp_name = Sym("{}_{}_{}".format(port.get_name(), fd.get_name(), par.get_name()))     # アロケータ呼び口の名前
                    #            ポート名         関数名         パラメータ名
                    cp_internal_name = Sym("{}_{}_{}".format(internal_cell_elem_name, fd.get_name(), par.get_name()))

                    # リレーアロケータ or 内部アロケータ指定がなされている場合、アロケータ呼び口を追加しない
                    # この時点では get_allocator_instance では得られないため tmp を得る
                    if port.get_allocator_instance_tmp():
                        found = False
                        for s in port.get_allocator_instance_tmp():
                            if s[1] == fd.get_name() and s[2] == par.get_name():
                                found = True

                                if s[0] == "INTERNAL_ALLOC":
                                    # 内部アロケータの場合    # mikan これは内部のセルに直結する。外部のポートに改めるべき
                                    self.internal_allocator_list.append(
                                        [cell, cp_internal_name, port.get_name(), fd.get_name(), par.get_name(), s[3]])
                        if found == True:
                            return

                    # 外部アロケータの場合
                    self.new_join_inst(cp_name, internal_cell_name, cp_internal_name, "CALL")

            obj2.each_param(_each_param)

        # エクスポート定義を返す
        return obj2

    @classmethod
    def has_attribute(cls, attr):
        return cls.current_object.has_attribute_inst(attr)

    def has_attribute_inst(self, attr):
        return self.name_list.get_item(attr) is not None

    @classmethod
    def new_port(cls, port):
        cls.current_object.new_port_inst(port)

    #=== CompositeCelltype# new_port
    def new_port_inst(self, port):
        from tecslib.core.componentobj.port import Port

        port.set_owner(self)   # Port (CompositeCelltype)
        dbgPrint("new_port: {}.{}\n".format(self.owner.get_name(), port.get_name()))
        self.name_list.add_item(port)

        # export するポートに含まれる send/receive パラメータのアロケータ呼び口の export を生成してポートに追加
        # この時点では内部アロケータかどうか判断できないので、とりあえず生成しておく
        def _each_param(port, fd, par):
            case = par.get_direction()                        # 引数の方向指定子 (in, out, inout, send, receive )
            if case in ("SEND", "RECEIVE"):
                #### リレーアロケータ or 内部アロケータ指定がなされている場合、アロケータ呼び口を追加しない
                # 内部アロケータ指定がなされている場合、アロケータ呼び口を追加しない
                # この時点では get_allocator_instance では得られないため tmp を得る
                if port.get_allocator_instance_tmp():
                    found = False
                    for s in port.get_allocator_instance_tmp():
                        if s[0] == "INTERNAL_ALLOC" and s[1] == fd.get_name() and s[2] == par.get_name():
                            found = True
                            break
                    if found == True:
                        return

                if par.get_allocator():
                    cp_name = Sym("{}_{}_{}".format(port.get_name(), fd.get_name(), par.get_name()))     # アロケータ呼び口の名前
                    #           ポート名          関数名         パラメータ名
                    alloc_sig_path = [par.get_allocator().get_name()]  # mikan Namespace アロケータ呼び口のシグニチャ
                    array_size = port.get_array_size()            # 呼び口または受け口配列のサイズ
                    created_port = Port(cp_name, alloc_sig_path, "CALL", array_size)  # 呼び口を生成
                    created_port.set_allocator_port(port, fd, par)
                    if port.is_omit():
                        created_port.set_omit()
                    self.new_port_inst(created_port)           # セルタイプに新しい呼び口を追加
                # else
                #   already error

        port.each_param(_each_param)

    @classmethod
    def new_attribute(cls, attr):
        cls.current_object.new_attribute_inst(attr)

    #=== CompositeCelltype# new_attribute for CompositeCelltype
    #attribute:: [Decl]
    def new_attribute_inst(self, attribute):
        for a in attribute:
            a.set_owner(self)   # Decl (CompositeCelltype)
            # V1.1.0.10 composite の attr の size_is は可となった
            # if a.get_size_is then
            #  cdl_error( "S1070 $1: size_is pointer cannot be exposed for composite attribute" , a.get_name )
            # end
            self.name_list.add_item(a)
            if a.get_initializer():
                a.get_type().check_init(self.locale, a.get_identifier(), a.get_initializer(), "ATTRIBUTE")

    #=== CompositeCelltype# 逆require の結合を生成する
    def create_reverse_require_join(self, cell):
        from tecslib.core.componentobj.port import Port

        for n in self.name_list.get_items():
            if type(n) is Port:
                n.create_reverse_require_join(cell)

    # false : if not in celltype definition, nil : if not found in celltype
    # Ruby: self.find (クラスメソッド) / find (インスタンスメソッド)
    # Python では同名だと instance.find が classmethod を呼んでしまうため別名にする
    @classmethod
    def find_in_current(cls, name):
        if cls.current_object is None:
            return False
        return cls.current_object.find(name)

    def find(self, name):
        dbgPrint("CompositeCelltype: find in composite: {}\n".format(name))
        cell = self.cell_list_in_composite.get_item(name)
        if cell:
            return cell

        dbgPrint("CompositeCelltype: {}, {}\n".format(name, self.name_list.get_item(name)))
        return self.name_list.get_item(name)

        # 従来仕様
#    cj = @export_name_list.get_item( name )
#p "#{name}, #{cj.get_port_decl}"
#    if cj then
#      return cj.get_port_decl
#    else
#      return nil
#    end

    #=== CompositeCelltype# export する CompositeCelltypeJoin を得る
    #name:: string:
    # attribute の場合、同じ名前に対し複数存在する可能性があるが、最初のものしか返さない
    def find_export(self, name):
        return self.export_name_list.get_item(name)

    #=== CompositeCelltype# composite celltype の cell を展開
    #name:: string: Composite cell の名前
    #global_name:: string: Composite cell の global name (C 言語名)
    #join_list:: NamedList : Composite cell に対する Join の NamedList
    #RETURN:
    # [ { name => cell }, [ cell, ... ] ]
    #  戻り値 前は 名前⇒cloneされた内部セル、後ろは composite の出現順のリスト
    def expand(self, name, global_name, namespacePath, join_list, region, plugin, locale):

        # debug
        dbgPrint("expand composite: {} name: {}  global_name: {}\njoin_list:\n".format(
            self.name, name, global_name))
        for j in join_list.get_items():
            dbgPrint("   {} {}\n".format(j.get_name(), j))

        # 展開で clone されたセルのリスト、右辺は Cell (composite の場合 composite な cell の clone)
        clone_cell_list = {}
        clone_cell_list2 = []
        clone_cell_list3 = {}

        #  composite 内部のすべての cell について
        for c in self.cell_list_in_composite.get_items():

            # debug
            dbgPrint("expand : cell {}\n".format(c.get_name()))

            # Join の配列
            ja = []

            # CompositeCelltype が export する呼び口、受け口、属性のリストについて
            # @export_name_list.get_items.each{ |cj|	# cj: CompositeCelltypeJoin
            # 新仕様では、@export_name_list に入っていない attr がありうる
            for cj in (self.port_list + self.attr_list):    # cj: CompositeCelltypeJoin

                # debug
                dbgPrint("        cj : {}\n".format(cj.get_name()))

                # CompositeCelltypeJoin (export) の対象セルか？
                if cj.match(c):

                    # 対象セル内の CompositeCelltype の export する Join (attribute または call port)
                    j = join_list.get_item(cj.get_name())

                    # debug
                    if j:
                        dbgPrint("  REWRITE_EX parent cell: {} child cell: {}:  parent's export port: {}  join: {}=>{}\n".format(
                            name, c.get_name(), cj.get_name(), j.get_name(), j.get_rhs()))
                    else:
                        dbgPrint("expand : parent cell: {} child cell: {}:  parent's export port: {}  join: nil\n".format(
                            name, c.get_name(), cj.get_name()))

                    if j:
                        # 呼び口、属性の場合
                        #  ComositeCell 用のもの(j) を対象セル用に clone (@through_list もコピーされる)
                        # p "expand: cloning Join #{j.get_name} #{@name} #{name}"
                        jc = j.clone_for_composite(self.name, name, locale)
                                        # celltype_name, cell_name

                        # debug
                        # p "cn #{jc.get_name} #{cj.get_cell_elem_name}"

                        # 対象セルの呼び口または属性の名前に変更
                        jc.change_name(cj.get_cell_elem_name())

                        # 対象セルに対する Join の配列
                        ja.append(jc)

                    # debug
                    dbgPrint("\n")

            # debug
            dbgPrint("expand : clone {}_{}\n".format(name, c.get_name()))

            # セルの clone を生成
#      clone_cell_list[ "#{name}_#{c.get_name}" ] =  c.clone_for_composite( name, global_name, ja )
            c2 = c.clone_for_composite(name, global_name, namespacePath, ja, self.name, region, plugin, locale)
            clone_cell_list["{}".format(c.get_local_name())] = c2
            clone_cell_list2.append(c2)
            clone_cell_list3[c] = c2

        for nm, c in clone_cell_list.items():
            dbgPrint("  cloned: {} = {}\n".format(nm, c.get_global_name()))
            # join の owner を clone されたセルに変更する V1.1.0.25
            for j in c.get_join_list().get_items():
                j.set_cloned(clone_cell_list["{}".format(c.get_local_name())])
            dbgPrint("change_rhs_port: inner cell {}\n".format(c.get_name()))
            c.change_rhs_port(clone_cell_list3)
        for c in clone_cell_list2:
            c.expand_inner()
        return [clone_cell_list, clone_cell_list2]

    #=== CompositeCelltype 指定子リストの設定
    def set_specifier_list(self, spec_list):
        if spec_list is None:
            return

        for s in spec_list:
            case = s[0]
            if case == "SINGLETON":
                self.b_singleton = True
            elif case == "IDX_IS_ID":
                self.cdl_warning("W1005 $1 : idx_is_id is ineffective for composite celltype", self.name)
            elif case == "ACTIVE":
                self.b_active = True
            elif case == "GENERATE":
                if self._generate:
                    self.cdl_error("S9999 generate specifier duplicate")
                self._generate = [s[1], s[2]]  # [ PluginName, "option" ]
            else:
                self.cdl_error("S1071 $1 cannot be specified for composite", s[0])

    def get_name(self):
        return self.name

    def get_global_name(self):
        return self.global_name

    def get_port_list(self):
        return self.port_list

    def get_attribute_list(self):
        return self.attr_list

    def get_var_list(self):
        return []   # 空の配列を返す

    def get_internal_allocator_list(self):
        return self.internal_allocator_list

    #== CompositeCelltype#get_real_celltype
    # port_name に接続されている内部のセルタイプを得る
    def get_real_celltype(self, port_name):
        cj = self.find_export(port_name)
        inner_celltype = cj.get_cell().get_celltype()
        if type(inner_celltype) is CompositeCelltype:
            return inner_celltype.get_real_celltype()
        else:
            return inner_celltype

    """
  @generate_list に @generate も入っているので、これは使わない方がよい
  #== CompositeCelltype# generate 指定子の情報
  # CompositeCelltype には generate が指定できないので nil を返す
  # Celltype::@generate を参照のこと
  def get_celltype_plugin
    nil
  end
    """

    def is_singleton(self):
        return self.b_singleton

    def is_active(self):
        return self.b_active

    #=== CompositeCelltype# アクティブではない
    # active ではないに加え、全ての内部セルのセルタイプが inactive の場合に inactive
    # （内部のセルが active または factory を持っている）
    def is_inactive(self):
        if self.b_active == False:
            for c in self.cell_list_in_composite.get_items():
                if c.get_celltype() and c.get_celltype().is_inactive() == False:
                    # c.get_celltype == nil の場合はセルタイプ未定義ですでにエラー
                    return False
            return True
        else:
            return False

    def get_id_base(self):
        raise Exception("get_id_base")

    def show_tree(self, indent):
        print("  " * indent, end="")
        print("CompositeCelltype: name: {}".format(self.name))
        print("  " * (indent + 1), end="")
        print("active: {}, singleton: {}".format(self.b_active, self.b_singleton))
        self.cell_list_in_composite.show_tree(indent + 1)
        print("  " * (indent + 1), end="")
        print("name_list")
        self.name_list.show_tree(indent + 2)
        print("  " * (indent + 1), end="")
        print("export_name_list")
        self.export_name_list.show_tree(indent + 2)
        if len(self.internal_allocator_list) > 0:
            print("  " * (indent + 1), end="")
            print("internal_allocator_list:")
            for a in self.internal_allocator_list:
                print("  " * (indent + 1), end="")
                print("  {} {} {} {} {}".format(a[0].get_name(), a[1], a[2], a[3], a[4]))
