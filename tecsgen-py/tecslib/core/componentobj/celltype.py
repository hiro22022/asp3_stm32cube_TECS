# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/componentobj/celltype.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

import re

from tecslib.core import globals as G
from tecslib.core.componentobj.celltype_module import CelltypePluginModule
from tecslib.core.plugin_module import PluginModule
from tecslib.core.syntaxobj.node import NSBDNode
from tecslib.core.toplevel import dbgPrint
from tecslib.rubylib.rb import to_s
from tecslib.rubylib.symbol import Sym


class Celltype(NSBDNode, PluginModule, CelltypePluginModule):  # < Nestable
# @name:: Symbol
# @global_name:: Symbol
# @name_list:: NamedList item: Decl (attribute, var), Port
# @port:: Port[]
# @attribute:: Decl[]
# @var:: Decl[]
# @require:: [[cp_name,Celltype|Cell,Port],...]
# @factory_list::   Factory[]
# @ct_factory_list::    Factory[] :    celltype factory
# @cell_list:: Cell[] : 定義のみ (V1.0.0.2 以降)
# @ordered_cell_list:: Cell[] : ID 順に順序付けされたセルリスト、最適化以降有効 (リンク単位ごとに生成されなおす)
# @b_reuse:: bool :  reuse 指定されて import された(template 不要)
# @singleton:: bool
# @idx_is_id:: bool
# @idx_is_id_act:: bool: actual value
# @b_need_ptab:: bool: true if having cells in multi-domain
# @active:: bool
# @pseudo_active:: bool  @pseudo_active が true の場合 @active も true
# @generate:: [ Symbol, String, Plugin ]  = [ PluginName, option, Plugin ] Plugin は生成後に追加される (generate指定子)
# @generate_list:: [ [ Symbol, String, Plugin ], ... ]   generate 指定と generate 文で追加された generate
#
# @n_attribute_ro:: int >= 0    none specified
# @n_attribute_rw:: int >= 0    # of [rw] specified attributes (obsolete)
# @n_attribute_omit : int >= 0  # of [omit] specified attributes
# @n_var:: int >= 0
# @n_var_size_is:: int >= 0     # of [size_is] specified vars # mikan count_is
# @n_var_omit:: int >= 0        # of [omit] specified vars # mikan var の omit は有？
# @n_var_init:: int >= 0        # of vars with initializer
# @n_call_port:: int >= 0       # dynamic ports are included
# @n_call_port_array:: int >= 0  # dynamic ports are included
# @n_call_port_omitted_in_CB:: int >= 0   最適化で省略される呼び口
# @n_call_port_dynamic:: int >= 0  #
# @n_call_port_array_dynamic:: int >= 0
# @n_call_port_ref_desc:: int >= 0  #
# @n_call_port_array_ref_desc:: int >= 0
# @n_entry_port:: int >= 0
# @n_entry_port_array:: int >= 0
# @n_entry_port_inline:: int >= 0
# @n_cell_gen:: int >= 0  生成するセルの数．コード生成の頭で算出する．意味解析段階では参照不可
# @id_base:: Integer : cell の ID の最小値(最大値は @id_base + @n_cell)
#
# @b_cp_optimized:: bool : 呼び口最適化実施
# @plugin:: PluginObject      このセルタイプがプラグインにより生成された CDL から生成された場合に有効。
#                              generate の指定は @generate にプラグインが保持される
#
# @included_header:: Hash :  include されたヘッダファイル
# @domain_roots::Hash { DomainTypeName(Symbol) => [ Region ] }  ドメインタイプ名と Region の配列 (optimize.rb で設定)
#                                               ルートリージョンはドメイン名が　nil
# @domain_class_roots::Hash { Region(domain_root) => { Region(class_root) => [ cell ] }
#                           @domain_class_roots[ domain_root ][ class_root ] = [ cell ]
# @domain_class_roots2::Hash { Region(sub_region:domain_or_class_root) => [ cell ] }
#                            @domain_class_roots2[ sub_region(domain_or_class_root) ] = [ cell ]
#                            sub_region: クラスルートまたはドメインルートの、いずれか末端側のリージョン
# @@domain_class_roots::Hash { sub_region => [ celltype ] }   # { region => celltype }

    nest_stack_index = -1
    nest_stack = []
    current_object = None
    celltype_list = []

    dynamic_join_checked_list = {}
    domain_class_roots = None

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
        Celltype.current_object = self
        self.name = name
        if to_s(Namespace.get_global_name()) != "":
            self.global_name = Sym("{}_{}".format(Namespace.get_global_name(), self.name))
        else:
            self.global_name = name

        self.name_list = NamedList(None, "symbol in celltype {}".format(name))
        self.port = []
        self.attribute = []
        self.var = []
        self.require = []
        self.factory_list = []
        self.ct_factory_list = []
        self.cell_list = []
        self.singleton = False
        self.active = False
        self.pseudo_active = False
        self._generate = None
        self.generate_list = []

        self.n_attribute_ro = 0
        self.n_attribute_rw = 0
        self.n_attribute_omit = 0
        self.n_var = 0
        self.n_var_omit = 0
        self.n_var_size_is = 0
        self.n_var_init = 0
        self.n_call_port = 0
        self.n_call_port_array = 0
        self.n_call_port_omitted_in_CB = 0
        self.n_call_port_dynamic = 0
        self.n_call_port_array_dynamic = 0
        self.n_call_port_ref_desc = 0
        self.n_call_port_array_ref_desc = 0
        self.n_entry_port = 0
        self.n_entry_port_array = 0
        self.n_entry_port_array_ns = 0
        self.n_entry_port_inline = 0
        self.n_cell_gen = 0

        self.b_cp_optimized = False

        self.plugin = Generator.get_plugin()
            # plugin の場合 PluginObject が返される
        # 元の Generator から呼出された Generator の中でパースおよび意味チェックされている

        # if @plugin then
        #  # plugin 生成されるセルタイプは再利用ではない   #833 不具合修正
        #  @b_reuse = false
        # else
        self.b_reuse = Generator.is_reuse()
        # end

        if G.idx_is_id:
            self.idx_is_id = True
            self.idx_is_id_act = True
            self.b_need_ptab = True
        else:
            self.idx_is_id = False
            self.idx_is_id_act = False
            self.b_need_ptab = False

        Namespace.new_celltype(self)
        self.set_namespace_path()  # @NamespacePath の設定
        self.set_specifier_list(Generator.get_statement_specifier())

        self.included_header = {}
        self.domain_roots = {}
        Celltype.celltype_list.append(self)

    def get_name(self):
        return self.name

    #== Celltype#ドメインルートを返す
    # @domain_roots はオプティマイズで設定される.
    # このためコード生成以降有効である.
    #
    # @domain_roots の説明を参照
    def get_domain_roots(self):
        return self.domain_roots
    # @domain_class_roots の説明を参照
    # @domain_class_roots はオプティマイズで設定される.
    # このためコード生成以降有効である.
    def get_domain_class_roots(self):
        return self.domain_class_roots
    # @domain_class_roots2 の説明を参照
    # @domain_class_roots2 はオプティマイズで設定される.
    # このためコード生成以降有効である.
    def get_domain_class_roots2(self):
        return self.domain_class_roots2
    # @domain_class_roots_total はオプティマイズで設定される.
    # このためコード生成以降有効である.
    @classmethod
    def get_domain_class_roots_total(cls):
        return cls.domain_class_roots

    # Celltype# end_of_parse
    def end_of_parse(self):
        # 属性・変数のチェック
        self.check_attribute()

        # アロケータ呼び口を内部生成
        self.generate_allocator_port()

        # リレーアロケータ、内部アロケータの設定
        for p in self.port:
            p.set_allocator_instance()

        if self.n_entry_port == 0 and self.active is False and len(self.factory_list) == 0 and \
                ((self.singleton and len(self.ct_factory_list) == 0) or not self.singleton):
            self.cdl_warning("W1002 $1: non-active celltype has no entry port & factory", self.name)

        if self._generate:
            self.celltype_plugin()

        # check_dynamic_join ##

        Celltype.current_object = None

    @classmethod
    def new_port(cls, port):
        cls.current_object.new_port_inst(port)

    def new_port_inst(self, port):
        port.set_owner(self)
        self.port.append(port)
        self.name_list.add_item(port)
        if port.get_port_type() == "CALL":
            self.n_call_port += 1
            if port.get_array_size() is not None:
                self.n_call_port_array += 1
            if port.is_dynamic():
                self.n_call_port_dynamic += 1
                if port.get_array_size() is not None:
                    self.n_call_port_array_dynamic += 1
            if port.is_ref_desc():
                self.n_call_port_ref_desc += 1
                if port.get_array_size() is not None:
                    self.n_call_port_array_ref_desc += 1
        else:
            self.n_entry_port += 1
            if port.get_array_size() is not None:
                self.n_entry_port_array += 1
            if port.get_array_size() == "[]":
                self.n_entry_port_array_ns += 1
            if port.is_inline():
                self.n_entry_port_inline += 1
        port.set_celltype(self)

    def get_port_list(self):
        return self.port

    @classmethod
    def new_attribute(cls, attribute):
        cls.current_object.new_attribute_inst(attribute)

    #=== Celltype# new_attribute for Celltype
    #attribute:: [Decl]
    def new_attribute_inst(self, attribute):
        self.attribute += attribute
        for a in attribute:
            a.set_owner(self)
            self.name_list.add_item(a)
            if a.is_omit():
                self.n_attribute_omit += 1
            elif a.is_rw():
                self.n_attribute_rw += 1
            else:
                self.n_attribute_ro += 1
            if a.get_initializer():
                # 登録後にチェックしても問題ない（attr を参照できないので、自己参照しない）
                a.get_type().check_init(self.locale, a.get_identifier(), a.get_initializer(), "ATTRIBUTE")

    #=== Celltype# celltype の attribute/var のチェック
    # STAGE:  S
    #
    # このメソッドは celltype のパースが完了した時点で呼出される．
    def check_attribute(self):
        from tecslib.core.expression import Expression
        from tecslib.core.types import PtrType

        # attribute の size_is 指定が妥当かチェック
        for a in self.attribute + self.var:
            if a.get_size_is():
                if not isinstance(a.get_type(), PtrType):
                    # size_is がポインタ型以外に指定された
                    self.cdl_error("S1011 $1: size_is specified for non-pointer type", a.get_identifier())
                else:

                    # 参照する変数が存在し、計算可能な型かチェックする
                    size = a.get_size_is().eval_const(self.name_list)  # C_EXP の可能性あり
                    init = a.get_initializer()
                    if init:
                        if type(init) is not list:
                            # 初期化子が配列ではない
                            self.cdl_error("S1012 $1: unsuitable initializer, need array initializer", a.get_identifier())
                        elif isinstance(size, int) and size < len(init):
                            # size_is 指定された個数よりも初期化子の配列要素が多い
                            self.cdl_error("S1013 $1: too many initializer, $2 for $3", a.get_identifier(), len(init), size)
                        # elsif a.get_size_is.eval_const( nil ) == nil  # C_EXP の可能性あり

            else:
                if isinstance(a.get_type(), PtrType):
                    init = a.get_initializer()
                    if type(init) is list or \
                            (isinstance(init, Expression) and
                             type(init.eval_const2(self.name_list)) is list):
                        # size_is 指定されていないポインタが Array で初期化されていたら、エラー
                        self.cdl_error("S1159 $1: non-size_is pointer cannot be initialized with array initializer", a.get_identifier())

    #=== Celltype# 属性 (attr) のリストを得る
    #  得られた attribute_list および、その中身は参照するだけで、書き換えないこと
    def get_attribute_list(self):
        return self.attribute

    #=== Celltype# アロケータ呼び口を生成
    #    send, receive 引数のアロケータを呼出すための呼び口を生成
    def generate_allocator_port(self):
        from tecslib.core.componentobj.port import Port

        for port in self.port:
            # ポートのすべてのパラメータを辿る
            def each_param_cb(port, fd, par):
                case = par.get_direction()                        # 引数の方向指定子 (in, out, inout, send, receive )
                if case == "SEND" or case == "RECEIVE":
                    if par.get_allocator():
                        cp_name = Sym("{}_{}_{}".format(port.get_name(), fd.get_name(), par.get_name()))     # アロケータ呼び口の名前
                        #           ポート名          関数名         パラメータ名
                        alloc_sig_path = par.get_allocator().get_namespace_path()
                        array_size = port.get_array_size()            # 呼び口または受け口配列のサイズ
                        created_port = Port(cp_name, alloc_sig_path, "CALL", array_size)  # 呼び口を生成
                        created_port.set_allocator_port(port, fd, par)
                        if port.is_optional():
                            created_port.set_optional()
                        if port.is_omit():
                            created_port.set_omit()
                        self.new_port_inst(created_port)                    # セルタイプに新しい呼び口を追加
                    # else
                    #  already error "not found or not signature" in class ParamDecl

            port.each_param(each_param_cb)

    def get_name_list(self):
        return self.name_list

    @classmethod
    def new_var(cls, var):
        cls.current_object.new_var_inst(var)

    #=== Celltype# 新しい内部変数
    #var:: [Decl]
    def new_var_inst(self, var):
        self.var += var
        for i in var:     # i: Decl
            i.set_owner(self)
            if i.is_omit():
                self.n_var_omit += 1
            else:
                self.n_var += 1
            self.name_list.add_item(i)

            # size_is 指定された配列? mikan  count_is
            if i.get_size_is():
                self.n_var_size_is += 1

            if i.get_initializer():
                i.get_type().check_init(self.locale, i.get_identifier(), i.get_initializer(), "VAR", self.name_list)
                self.n_var_init += 1

    #=== Celltype# 変数 (var) のリストを得る
    #  得られた var_list および、その中身は参照するだけで、書き換えないこと
    def get_var_list(self):
        return self.var

    #=== Celltype# celltype の指定子を設定
    def set_specifier_list(self, spec_list):
        if spec_list is None:
            return

        for s in spec_list:
            case = s[0]
            if case == "SINGLETON":
                self.singleton = True
            elif case == "IDX_IS_ID":
                self.idx_is_id = True
                self.idx_is_id_act = True
                self.b_need_ptab = True
            elif case == "ACTIVE":
                self.active = True
            elif case == "PSEUDO_ACTIVE":
                self.active = True
                self.pseudo_active = True
            elif case == "GENERATE":
                if self._generate:
                    self.cdl_error("S1014 generate specifier duplicate")
                self._generate = [s[1], s[2]]  # [ PluginName, "option" ]
            else:
                self.cdl_error("S1015 $1 cannot be specified for composite", case)
        if self.singleton:
            self.idx_is_id_act = False
            self.b_need_ptab = False

    #
    @classmethod
    def new_require(cls, ct_or_cell_nsp, ep_name, cp_name=None):
        from tecslib.rubylib.symbol import Sym as _Sym
        if not isinstance(ep_name, _Sym):
            ep_name = _Sym(str(ep_name))
        cls.current_object.new_require_inst(ct_or_cell_nsp, ep_name, cp_name)

    def new_require_inst(self, ct_or_cell_nsp, ep_name, cp_name):
        from tecslib.core.componentobj.cell import Cell
        from tecslib.core.componentobj.namespace import Namespace
        from tecslib.core.componentobj.port import Port

        # Require: set_owner するものがない
        obj = Namespace.find(ct_or_cell_nsp)    #1
        if type(obj) is Celltype:
            # Celltype 名で指定
            ct = obj
        elif type(obj) is Cell:
            # Cell 名で指定
            ct = obj.get_celltype()
        elif obj is None:
            self.cdl_error("S1016 $1 not found", ct_or_cell_nsp.get_path_str())
            return
        else:
            self.cdl_error("S1017 $1 : neither celltype nor cell", ct_or_cell_nsp.get_path_str())
            return

        if not ct.is_singleton():
            # シングルトンではない
            self.cdl_error("S1018 $1 : not singleton cell", obj.get_name())

        # 受け口を探す
        obj2 = ct.find(ep_name)
        if (type(obj2) is not Port) or obj2.get_port_type() != "ENTRY":
            self.cdl_error("S1019 \'$1\' : not entry port", ep_name)
            return
        elif obj2.get_array_size():
            self.cdl_error("S1020 \'$1\' : required port cannot be array", ep_name)
            return

        if obj2.get_signature() is None:
            # signature が未定義：既にエラー
            return

        require_call_port_prefix = Sym("_require_call_port")
        if cp_name is None:
            # 関数名重複チェック
            for req in self.require:
                if not re.match(r'^{}'.format(re.escape(str(require_call_port_prefix))), str(req[0])):
                    continue     # 名前ありの require は関数名重複チェックしない
                port = req[2]
                if port.get_signature() == obj2.get_signature():
                    # 同じ signature （すべて同じ関数名を持つ）個別に出すのではなく、まとめてエラーとする
                    self.cdl_error("S1021 $1 : require cannot have same signature with \'$2\'", obj2.get_name(), port.get_name())
                    continue
                fha = port.get_signature().get_function_head_array()
                fha2 = obj2.get_signature().get_function_head_array()
                if fha and fha2:
                    for f in fha:
                        # mikan ここは、namedList からの検索にならないの？（効率が悪い）
                        for f2 in fha2:
                            if f.get_name() == f2.get_name():
                                self.cdl_error("S1022 $1.$2 : \'$3\' conflict function name in $4.$5",
                                               obj.get_name(), obj2.get_name(), f.get_name(), req[1].get_name(), req[2].get_name())

        if cp_name is None:
            b_has_name = False
            cp_name = Sym("{}_{}_{}".format(require_call_port_prefix, ct.get_name(), obj2.get_name()))
        else:
            b_has_name = True
        # require を追加
        self.require.append([cp_name, obj, obj2])  # [ lhs:cp_name, rhs:Celltype, rhs:Port ]

        # require port を追加 (呼び口として追加する。ただし require をセットしておく)
        port = Port(cp_name, obj2.get_signature().get_namespace_path(), "CALL")
        port.set_require(b_has_name)
        self.new_port_inst(port)

    @classmethod
    def new_factory(cls, factory):
        cls.current_object.new_factory_inst(factory)

    def new_factory_inst(self, factory):
        factory.set_owner(self)
        if factory.get_f_celltype():
            self.ct_factory_list.append(factory)
        else:
            self.factory_list.append(factory)

        factory.check_arg(self)

    @classmethod
    def check_dynamic_join(cls):
        from tecslib.core.componentobj.namespace import Namespace

        def visit(ct):
            if cls.dynamic_join_checked_list.get(ct) is None:
                cls.dynamic_join_checked_list[ct] = True
                ct.check_dynamic_join_inst()

        Namespace.get_root().travers_all_celltype(visit)

    #=== Celltype#dynamic の適合性チェック
    def check_dynamic_join_inst(self):
        if not G.verbose:
            return
        for port in self.port:
            signature = port.get_signature()
            if signature is None:   # すでにエラー
                continue
            if port.is_dynamic():
                dbgPrint("[DYNAMIC] checking dynamic port: {}.{}\n".format(self.global_name, port.get_name()))
                # print( "[DYNAMIC] checking dynamic port: #{@global_name}.#{port.get_name}\n" )
                if self.find_ref_desc_port(signature):
                    continue
                if self.find_descriptor_param(signature, "DYNAMIC"):
                    continue
                self.cdl_warning('W9999 $1 cannot get information for dynamic port $2', self.name, port.get_name())
            elif port.is_ref_desc():
                dbgPrint("[DYNAMIC] checking ref_desc port: {}.{}\n".format(self.global_name, port.get_name()))
                # print( "[DYNAMIC] checking ref_desc port: #{@global_name}.#{port.get_name}\n" )
                if self.find_dynamic_port(signature):
                    continue
                if self.find_descriptor_param(signature, "REF_DESC"):
                    continue
                self.cdl_warning('W9999 $1 cannot put information from ref_desc port $2', self.name, port.get_name())
            elif port.get_signature():
                if port.get_signature().has_descriptor():
                    for signature, param in port.get_signature().get_descriptor_list().items():
                        dbgPrint("[DYNAMIC] checking Descriptor parameter: {}.{} ... {}\n".format(
                            self.global_name, port.get_name(), param.get_name()))
                        # print( "[DYNAMIC] checking Descriptor parameter: #{@global_name}.#{port.get_name} ... #{param.get_name}\n" )
                        if port.get_port_type() == "CALL":
                            if param.get_direction() == "IN":
                                if self.find_ref_desc_port(signature):
                                    continue
                                if self.find_descriptor_param(signature, "DYNAMIC"):
                                    continue
                            elif param.get_direction() == "OUT":
                                if self.find_dynamic_port(signature):
                                    continue
                                if self.find_descriptor_param(signature, "REF_DESC"):
                                    continue
                        else:  # :ENTRY
                            if param.get_direction() == "IN":
                                if self.find_dynamic_port(signature):
                                    continue
                                if self.find_descriptor_param(signature, "REF_DESC"):
                                    continue
                            elif param.get_direction() == "OUT":
                                if self.find_ref_desc_port(signature):
                                    continue
                                if self.find_descriptor_param(signature, "DYNAMIC"):
                                    continue
                        self.cdl_warning('W9999 "$1" cannot handle Descriptor "$2" information for port "$3"',
                                         self.name, param.get_name(), port.get_name())

    def find_dynamic_port(self, signature):
        dbgPrint("[DYNAMIC] find_dynamic_port signature={}\n".format(signature.get_name()))
        for port in self.port:
            dbgPrint("[DYNAMIC] port={} signature={} dynamic={}\n".format(
                port.get_name(), port.get_signature().get_name(), port.is_dynamic()))
            if port.is_dynamic() and port.get_signature() == signature:
                return port
        return None

    def find_ref_desc_port(self, signature):
        if signature is None:  # すでにエラー
            return None
        dbgPrint("[DYNAMIC] find_ref_desc_port signature={}\n".format(signature.get_name()))
        for port in self.port:
            dbgPrint("[DYNAMIC] port={} signature={} ref_desc={}\n".format(
                port.get_name(), port.get_signature().get_name(), port.is_ref_desc()))
            if port.is_ref_desc() and port.get_signature() == signature:
                return port
        return None

    #=== Celltype#ディスクリプタ型でシグニチャが一致し dyn_ref に対応づく引数を探す
    #dyn_ref::Symbol: :DYNAMIC=ディスクリプタを得る手段となる引数を探す．:REF_DESC=渡す手段となる引数を探す
    def find_descriptor_param(self, signature, dyn_ref):
        from tecslib.core.types import DescriptorType, PtrType

        param_list = []
        for port in self.port:
            fha = None
            if port.signature is None:
                continue
            fha = port.signature.get_function_head_array()
            if fha is None:
                continue
            for fh in fha:
                fd = fh.get_declarator()
                if not fd.is_function():
                    continue
                for param in fd.get_type().get_paramlist().get_items():
                    type_ = param.get_type()
                    while isinstance(type_, PtrType):
                        type_ = type_.get_type()
                    dbgPrint("[DYNAMIC] dyn_ref={} port_type={} dir={} paramName={} paramType={}\n".format(
                        dyn_ref, port.get_port_type(), param.get_direction(), param.get_name(), type_.__class__.__name__))
                    # print( "[DYNAMIC] dyn_ref=#{dyn_ref} port_type=#{port.get_port_type} dir=#{param.get_direction} paramName=#{param.get_name} paramType=#{type.class}\n" )
                    if isinstance(type_, DescriptorType):
                        if type_.get_signature() == signature:
                            dir = param.get_direction()
                            if dir == "INOUT":
                                dbgPrint("[DYNAMIC] found INOUT Descriptor parameter: {}.{} ... {}\n".format(
                                    self.global_name, port.get_name(), param.get_name()))
                                # print( "[DYNAMIC] found INOUT Descriptor parameter: #{@global_name}.#{port.get_name} ... #{param.get_name}\n" )
                                return param
                            elif dyn_ref == "DYNAMIC":
                                if (dir == "IN" and port.get_port_type() == "ENTRY") or \
                                   (dir == "OUT" and port.get_port_type() == "CALL"):
                                    dbgPrint("[DYNAMIC] found INBOUND Descriptor parameter: {}.{} ... {}\n".format(
                                        self.global_name, port.get_name(), param.get_name()))
                                    # print( "[DYNAMIC] found INBOUND Descriptor parameter: #{@global_name}.#{port.get_name} ... #{param.get_name}\n" )
                                    return param
                            elif dyn_ref == "REF_DESC":
                                if (dir == "IN" and port.get_port_type() == "CALL") or \
                                   (dir == "OUT" and port.get_port_type() == "ENTRY"):
                                    dbgPrint("[DYNAMIC] found OUTBOUND Descriptor parameter: {}.{} ... {}\n".format(
                                        self.global_name, port.get_name(), param.get_name()))
                                    # print( "[DYNAMIC] found OUTBOUND Descriptor parameter: #{@global_name}.#{port.get_name} ... #{param.get_name}\n" )
                                    return param
                            else:
                                raise Exception("unknown ref_desc")
        return None

    #=== Celltype# celltype に新しい cell を追加
    #cell:: Cell
    # 新しいセルをセルタイプに追加．
    # セルの構文解釈の最後でこのメソドを呼出される．
    # シングルトンセルが同じ linkunit に複数ないかチェック
    def new_cell(self, cell):
        dbgPrint("Celltype#new_cell( {} )\n".format(cell.get_name()))
        # Celltype では Cell の set_owner しない
        # シングルトンで、プロトタイプ宣言でない場合、コード生成対象リージョンの場合
        if self.singleton:
            for c in self.cell_list:
                if c.get_region().get_link_root() == cell.get_region().get_link_root():
                    self.cdl_error("S1024 $1: multiple cell for singleton celltype", self.name)
        self.cell_list.append(cell)

        # プラグインにより生成されたセルタイプか ?
        if self.plugin:
            self.plugin.new_cell(cell)

        # セルタイププラグインの適用
        self.celltype_plugin_new_cell(cell)

    #=== Celltype# セルタイプは INIB を持つか？
    # セルタイプが INIB を持つかどうかを判定する
    # $rom == false のとき:  INIB を持たない． （すべては CB に置かれる）
    # $rom == true のとき、INIB に置かれるものが一つでも存在すれば INIB を持つ
    #   INIB に置かれるものは
    #     attribute (omit のものは除く．現仕様では rw のものはない)
    #     size_is を伴う var
    #     呼び口（ただし、最適化で不要となるものは除く）
    def has_INIB(self):

        result = G.rom and \
                 (self.n_attribute_ro > 0 or
                  self.n_var_size_is > 0 or
                  (self.n_call_port - self.n_call_port_omitted_in_CB - (self.n_call_port_dynamic - self.n_call_port_array_dynamic)) > 0 or
                  G.ram_initializer and self.n_call_port_dynamic > 0 or
                  self.n_entry_port_array_ns > 0)
        # print "name=#{@name} n_attribute_ro=#{@n_attribute_ro}  n_var_size_is=#{@n_var_size_is} n_call_port=#{@n_call_port} n_call_port_omitted_in_CB=#{@n_call_port_omitted_in_CB} n_call_port_dynamic=#{@n_call_port_dynamic} n_call_port_array_dynamic=#{@n_call_port_array_dynamic} n_entry_port_array_ns=#{@n_entry_port_array_ns} has_INIB?=#{result}\n"

        return result

    #=== Celltype# セルタイプは CB を持つか？
    # $rom == true のとき、いかのものが置かれる．それらの一つでも存在すれば CB を持つ
    #   size_is が指定されていない var
    #   rw 指定された attribute (現仕様では存在しない)
    # $rom == false のとき、いかのものが置かれる．それらの一つでも存在すれば CB を持つ
    #   attribute
    #   var
    #   呼び口（ただし、最適化で不要となるものは除く）
    def has_CB(self):
        if G.rom:
            return self.n_attribute_rw > 0 or (self.n_var - self.n_var_size_is) > 0 or (self.n_call_port_dynamic - self.n_call_port_array_dynamic) > 0
            # return @n_attribute_rw > 0 || @n_var > 0
        else:
            return self.n_attribute_rw > 0 or self.n_attribute_ro > 0 or self.n_var > 0 or (self.n_call_port - self.n_call_port_omitted_in_CB) > 0 or self.n_entry_port_array_ns > 0

    #=== Celltype# SET_CB_INIB_POINTER, INITIALIZE_CB が必要か
    def need_CB_initializer(self):
        # Ruby: @n_var_init > 0 || has_CB? || ( @n_call_port_dynamic && $ram_initializer )
        # Ruby では整数 0 が truthy のため、(@n_call_port_dynamic && $ram_initializer) は
        # n_call_port_dynamic == 0 かつ $ram_initializer のときも真になる。
        # Python の 0 は falsy なので、同じ結果になるよう ram_initializer を直接見る。
        return self.n_var_init > 0 or self.has_CB() or bool(G.ram_initializer)

    #=== Celltype# 逆require の結合を生成する
    def create_reverse_require_join(self, cell):
        for p in self.port:
            p.create_reverse_require_join(cell)

    #=== Celltype# singleton セルを得る
    #region:: Region   : singleton を探す Region
    # 距離が最も近いものを返す
    # mikan 本当は region の範囲の singleton を探す必要がある
    def get_singleton_cell(self, region):
        cell = None
        dist = 999999999  # mikan 制限値（これは十分すぎるほどデカイが）
        # require: celltype で指定
        for c in self.cell_list:
            # 到達可能で最も近いセルを探す（複数の singleton があるかもしれない）
            d = region.distance(c.get_region())
            #debug
            dbgPrint("distance {} from {} to {} in {}\n".format(
                d, region.get_name(), c.get_name(), c.get_region().get_name()))
            if d is not None:
                if d < dist:
                    cell = c
                    dist = d
        if cell:
            dbgPrint("distance found:{} in {}\n".format(cell.get_name(), cell.get_region().get_name()))
        else:
            dbgPrint("distance not found\n")
        return cell

    def find(self, name):
        return self.name_list.get_item(name)

    #   @generate_list に @generate も入っているので、これは使わない方がよい
    #   #=== Celltype# セルタイププラグインを得る
    #   def get_celltype_plugin
    #     if @generate then
    #       return @generate[2]
    #     end
    #   end

    def get_global_name(self):
        return self.global_name

    def is_singleton(self):
        return self.singleton

    def is_active(self):
        return self.active

    def idx_is_id_act(self):
        return self.idx_is_id_act

    def multi_domain(self):
        return self.b_need_ptab

    #=== Celltype# アクティブではないか
    # このメソッドでは active の他に factory (singleton においては FACTORYを含む)がなければ inactive とする
    def is_inactive(self):
        if self.active is False and len(self.factory_list) == 0 and \
                ((self.singleton and len(self.ct_factory_list) == 0) or not self.singleton):
            return True
        return False

    def get_id_base(self):
        return self.id_base

    def get_plugin(self):
        return self.plugin

    def get_require(self):
        return self.require

    #=== Celltype# コード生成する必要があるか判定
    # セルの個数が 0 ならセルタイプコードは生成不要
    def need_generate(self):
        return self.n_cell_gen > 0

    #=== Celltype# require 呼び口の結合を行う
    # STAGE: S
    # セルタイプの require 呼び口について、結合を行う
    # セルが生成されないかチェックを行う
    def set_require_join(self):
        for req in self.require:
            cp_name = req[0]
            cell_or_ct = req[1]
            port = req[2]
            for c in self.cell_list:
                c.set_require_join(cp_name, cell_or_ct, port)

    def get_cell_list(self):
        return self.cell_list

    #=== Celltype# inline 受け口しかないか？
    # 受け口が無い場合、すべての受け口が inline とはしない
    def is_all_entry_inline(self):
        return self.n_entry_port == self.n_entry_port_inline and self.n_entry_port > 0

    #=== Celltype# セルタイプコード (celltype.c) を持つか
    #false の場合、celltype_inline.h しか持たない
    def has_celltype_code(self):
        return not (self.is_all_entry_inline() and not self.is_active())

    #=== Celltype.get_celltype_list
    @classmethod
    def get_celltype_list(cls):
        return cls.celltype_list

    def show_tree(self, indent):
        from tecslib.rubylib import rb
        print("  " * indent, end="")
        print("Celltype: name={} global_name={}".format(self.name, self.global_name))
        print("  " * (indent + 1), end="")
        plugin_class = rb.class_name(self.plugin)
        print("active={}, singleton={}, idx_is_id={} plugin={} reuse={}".format(
            rb.to_s(self.active), rb.to_s(self.singleton), rb.to_s(self.idx_is_id),
            plugin_class, rb.to_s(self.b_reuse)))
        print("  " * (indent + 1), end="")
        print("namespace_path: {}".format(self.NamespacePath))
        print("  " * (indent + 1), end="")
        print("port:")
        for i in self.port:
            i.show_tree(indent + 2)
        print("  " * (indent + 1), end="")
        print("attribute:")
        for i in self.attribute:
            i.show_tree(indent + 2)
        print("  " * (indent + 1), end="")
        print("var:")
        for i in self.var:
            i.show_tree(indent + 2)
#    (indent+1).times { print "  " }
#    puts "require:"   mikan
#    @require.each { |i| i.show_tree( indent + 2 ) }
        print("  " * (indent + 1), end="")
        print("factory:")
        for i in self.factory_list:
            i.show_tree(indent + 2)
        print("  " * (indent + 1), end="")
        print("@n_attribute_ro {}".format(self.n_attribute_ro))
        print("  " * (indent + 1), end="")
        print("@n_attribute_rw {}".format(self.n_attribute_rw))
# @n_attribute_omit : int >= 0  # of [omit] specified cells
# @n_var:: int >= 0
# @n_var_size_is:: int >= 0     # of [size_is] specified cells # mikan count_is
# @n_var_omit:: int >= 0        # of [omit] specified  cells # mikan var の omit は有？
# @n_call_port:: int >= 0
# @n_call_port_array:: int >= 0
# @n_call_port_omitted_in_CB:: int >= 0   最適化で省略される呼び口
# @n_entry_port:: int >= 0
# @n_entry_port_array:: int >= 0
        print("  " * (indent + 1), end="")
        print("@n_entry_port_inline {}".format(self.n_entry_port_inline))
# @n_cell:: int >= 0  コード生成の頭で算出する．意味解析段階では参照不可
# @id_base:: Integer : cell の ID の最小値(最大値は @id_base + @n_cell)
