# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/componentobj/signature.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

from tecslib.core import globals as G
from tecslib.core.plugin_module import PluginModule
from tecslib.core.syntaxobj.node import NSBDNode
from tecslib.rubylib.rb import to_s
from tecslib.rubylib.symbol import Sym


class Signature(NSBDNode, PluginModule):  # < Nestable
#  @name:: Symbol
#  @global_name:: Symbol
#  @function_head_list:: NamedList : FuncHead のインスタンスが要素
#  @func_name_to_id::  {String}  :  関数名を添字とする配列で id を記憶する．id は signature の出現順番 (1から始まる)
#  @context:: string : コンテキスト名
#  @b_callback:: bool: callback : コールバック用のシグニチャ
#  @b_deviate:: bool: deviate : 逸脱（pointer level mismatch を出さない）
#  @b_checked_as_allocator_signature:: bool:  アロケータシグニチャとしてチェック済み
#  @b_empty:: Bool: 空(関数が一つもない状態)
#  @descriptor_list:: nil | { Signature => ParamDecl }  最後の ParamDecl しか記憶しないことに注意
#  @generate:: [ Symbol, String, Plugin ]  = [ PluginName, option, Plugin ] Plugin は生成後に追加される

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

    # STAGE: P
    # このメソッドは parse 中のみ呼び出される
    @classmethod
    def get_current(cls):
        return cls.current_object

    #
    # STAGE: B
    def __init__(self, name):
        from tecslib.core.bnf import Generator
        from tecslib.core.componentobj.namespace import Namespace

        super().__init__()
        self.name = name
        Namespace.new_signature(self)
        self.set_namespace_path()  # @NamespacePath の設定
        if to_s(Namespace.get_global_name()) == "":
            self.global_name = self.name
        else:
            self.global_name = Sym("{}_{}".format(Namespace.get_global_name(), self.name))

        self.func_name_to_id = {}
        self.function_head_list = None
        self.context = None
        self.b_callback = False
        self.b_deviate = False
        self.b_empty = False
        self.b_checked_as_allocator_signature = False
        self.descriptor_list = None
        self._generate = None
        Signature.current_object = self
        self.set_specifier_list(Generator.get_statement_specifier())

    #
    # STAGE: B
    def end_of_parse(self, function_head_list):
        self.function_head_list = function_head_list

        # id を割付ける
        id = 1
        for f in function_head_list.get_items():
            self.func_name_to_id[f.get_name()] = id
            f.set_owner(self)
            id += 1
        if id == 1:
            self.b_empty = True

        # set_descriptor_list ##

        if self._generate:
            self.signature_plugin()

        Signature.current_object = None

        return self

    #=== Signature# signature の指定子を設定
    # STAGE: B
    #spec_list::      [ [ :CONTEXT,  String ], ... ]
    #                     s[0]        s[1]
    def set_specifier_list(self, spec_list):
        from tecslib.core.syntaxobj.cdlstring import CDLString

        if spec_list is None:  # 空ならば何もしない
            return

        for s in spec_list:
            case = s[0]     # statement_specifier
            if case == "CALLBACK":
                self.b_callback = True
            elif case == "CONTEXT":         # [context("non-task")] etc
                if self.context:
                    self.cdl_error("S1001 context specifier duplicate")
                # @context = s[1].gsub( /\A\"(.*)\"$/, "\\1" )
                self.context = CDLString.remove_dquote(s[1])
                if self.context == "non-task" or self.context == "task" or self.context == "any":
                    pass
                else:
                    self.cdl_warning("W1001 \'$1\': unknown context type. usually specifiy task, non-task or any", self.context)
            elif case == "DEVIATE":
                self.b_deviate = True
            elif case == "GENERATE":
                if self._generate:
                    self.cdl_error("S9999 generate specifier duplicate")
                self._generate = [s[1], s[2]]  # [ PluginName, "option" ]
            else:
                self.cdl_error("S1002 \'$1\': unknown specifier for signature", s[0])

    def get_name(self):
        return self.name

    def get_global_name(self):
        return self.global_name

    def get_function_head_array(self):
        if self.function_head_list:
            return self.function_head_list.get_items()
        else:
            return None

    def get_function_head(self, func_name):
        from tecslib.rubylib.symbol import is_symbol

        if not is_symbol(func_name):
            func_name = Sym(func_name)
        return self.function_head_list.get_item(func_name)

    #=== Signature# 関数名から signature 内の id を得る
    def get_id_from_func_name(self, func_name):
        return self.func_name_to_id[func_name]

    #=== Signature# context を得る
    # context 文字列を返す "task", "non-task", "any"
    # 未指定時のデフォルトとして task を返す
    def get_context(self):
        if self.context:
            return self.context
        else:
            return "task"

    #=== Signature# signaure のすべての関数のすべてのパラメータをたどる
    #block:: ブロックを引数に取る
    # ブロックは2つの引数を受け取る  Decl, ParamDecl     ( Decl: 関数ヘッダ )
    # Port クラスにも each_param がある（同じ働き）
    def each_param(self, pr):  # ブロック引数 { |func_decl, param_decl| }
        fha = self.get_function_head_array()                       # 呼び口または受け口のシグニチャの関数配列
        if fha is None:                                # nil なら文法エラーで有効値が設定されなかった
            return

        # obsolete Ruby 3.0 では使えなくなった
        # pr = Proc.new   # このメソッドのブロック引数を pr に代入
        for fh in fha:  # fh: FuncHead                      # 関数配列中の各関数頭部
            fd = fh.get_declarator()                            # fd: Decl  (関数頭部からDeclarotorを得る)
            if fd.is_function():                           # fd が関数でなければ、すでにエラー
                for par in fd.get_type().get_paramlist().get_items():  # すべてのパラメータについて
                    pr(fd, par)

    #=== Signature# 正当なアロケータ シグニチャかテストする
    # alloc, dealloc 関数を持つかどうか、第一引き数がそれぞれ、整数、ポインタ、第二引き数が、ポインタへのポインタ、なし
    def is_allocator(self):

        # 一回だけチェックする
        if self.b_checked_as_allocator_signature is True:
            return True
        self.b_checked_as_allocator_signature = True

        from tecslib.core.syntaxobj.paramdecl import ParamDecl
        from tecslib.core.types import IntType, PtrType

        fha = self.get_function_head_array()                       # 呼び口または受け口のシグニチャの関数配列
        if fha is None:                                  # nil なら文法エラーで有効値が設定されなかった
            return False

        found_alloc = False
        found_dealloc = False
        for fh in fha:  # fh: FuncHead                      # 関数配列中の各関数頭部
            fd = fh.get_declarator()                            # fd: Decl  (関数頭部からDeclarotorを得る)
            if fd.is_function():                           # fd が関数でなければ、すでにエラー
                func_name = fd.get_name()
                if func_name == Sym("alloc"):
                    found_alloc = True
                    params = fd.get_type().get_paramlist().get_items()
                    if params:
                        if (not isinstance(params[0], ParamDecl)
                                or not isinstance(params[0].get_type().get_original_type(), IntType)
                                or params[0].get_direction() != "IN"):
                            # 第一引数が int 型でない
                            if (not isinstance(params[0], ParamDecl)
                                    or not isinstance(params[0].get_type(), PtrType)
                                    or not isinstance(params[0].get_type().get_type(), PtrType)
                                    or isinstance(params[0].get_type().get_type().get_type(), PtrType)
                                    or params[0].get_direction() != "OUT"):
                                # 第一引数がポインタ型でもない
                                self.cdl_error3(self.locale, "S1003 $1: \'alloc\' 1st parameter neither [in] integer type nor [out] double pointer type", self.name)
                        elif (not isinstance(params[1], ParamDecl)
                                or not isinstance(params[1].get_type(), PtrType)
                                or not isinstance(params[1].get_type().get_type(), PtrType)
                                or isinstance(params[1].get_type().get_type().get_type(), PtrType)
                                or params[0].get_direction() != "IN"):
                            # (第一引数が整数で) 第二引数がポインタでない
                            self.cdl_error3(self.locale, "S1004 $1: \'alloc\' 2nd parameter not [in] double pointer", self.name)
                    else:
                        self.cdl_error3(self.locale, "S1005 $1: \'alloc\' has no parameter, unsuitable for allocator signature", self.name)
                elif func_name == Sym("dealloc"):
                    found_dealloc = True
                    params = fd.get_type().get_paramlist().get_items()
                    if params:
                        if (not isinstance(params[0], ParamDecl)
                                or not isinstance(params[0].get_type(), PtrType)
                                or isinstance(params[0].get_type().get_type(), PtrType)
                                or params[0].get_direction() != "IN"):
                            self.cdl_error3(self.locale, "S1006 $1: \'dealloc\' 1st parameter not [in] pointer type", self.name)
#            elif params[1] != nil then    # 第二引き数はチェックしない
#              cdl_error3( @locale, "S1007 Error message is changed to empty" )
#                 cdl_error3( @locale, "S1007 $1: \'dealloc\' cannot has 2nd parameter" , @name )
                    else:
                        self.cdl_error3(self.locale, "S1008 $1: \'dealloc\' has no parameter, unsuitable for allocator signature", self.name)
                if found_alloc and found_dealloc:
                    return True
        if not found_alloc:
            self.cdl_error3(self.locale, "S1009 $1: \'alloc\' function not found, unsuitable for allocator signature", self.name)
        if not found_dealloc:
            self.cdl_error3(self.locale, "S1010 $1: \'dealloc\' function not found, unsuitable for allocator signature", self.name)
        return False

    #=== Signature# シグニチャプラグイン (generate 指定子)
    def signature_plugin(self):
        plugin_name = self._generate[0]
        option = self._generate[1]
        self.apply_plugin(plugin_name, option)

    #== Signature#apply_plugin
    def apply_plugin(self, plugin_name, option):
        from tecslib.core.plugin_module import _import_plugin_class
        from tecslib.core.toplevel import print_exception

        if self.is_empty():
            self.cdl_warning("S9999 $1 is empty. cannot apply signature plugin. ignored", self.name)
            return

        SignaturePlugin = _import_plugin_class("SignaturePlugin")
        plClass = self.load_plugin(plugin_name, SignaturePlugin)
        if plClass is None:
            return
        if G.verbose:
            print("new through: plugin_object = {}.new( {}, {} )\n".format(plClass.__name__, self.name, option))

        plugin_object = None
        try:
            plugin_object = plClass(self, option)
            plugin_object.set_locale(self.locale)
        except Exception as evar:
            self.cdl_error("S1150 $1: fail to new", plugin_name)
            print_exception(evar)
        self.generate_and_parse(plugin_object)

    #== Signature# 引数で参照されている Descriptor 型のリストを
    #RETURN:: Hash { Signature => ParamDecl }:  複数の ParamDecl から参照されている場合、最後のものしか返さない
    def get_descriptor_list(self):
        # print "Signature#get_descriptor_list #{@name}\n"
        # 本来 Signature.set_descriptor_list の呼出しで @descriptor_list が設定されるのだが、
        # post_code.cdl (ジェネレータ生成) で生成、または import されたシグニチャには設定されない。
        # 読み出し時に、オンデマンドで設定する。
        if self.descriptor_list is None:
            self.set_descriptor_list_inst()
        return self.descriptor_list

    _set_descriptor_list = {}

    @classmethod
    def set_descriptor_list(cls):
        from tecslib.core.componentobj.namespace import Namespace

        def visit(sig):
            if cls._set_descriptor_list.get(sig) is None:
                cls._set_descriptor_list[sig] = True
                sig.set_descriptor_list_inst()

        Namespace.get_root().travers_all_signature(visit)

    #== Signature# 引数で参照されている Descriptor 型のリストを作成する
    def set_descriptor_list_inst(self):
        from tecslib.core.types import DescriptorType, PtrType

        desc_list = {}
        # p "has_desc #{@name}"
        fha = self.get_function_head_array()                       # 呼び口または受け口のシグニチャの関数配列
        if fha is None:                                  # nil の場合、自己参照によるケースと仮定
            self.descriptor_list = desc_list
            return desc_list
        for fh in fha:
            fd = fh.get_declarator()                            # fd: Decl  (関数頭部からDeclarotorを得る)
            if fd.is_function():                           # fd が関数でなければ、すでにエラー
                params = fd.get_type().get_paramlist().get_items()
                if params:
                    for param in params:
                        t = param.get_type().get_original_type()
                        while isinstance(t, PtrType):
                            t = t.get_referto()
                        # p "has_desc #{param.get_name} #{t}"
                        if isinstance(t, DescriptorType):
                            desc_list[t.get_signature()] = param
                            # p self.get_name, t.get_signature.get_name
                            if t.get_signature() == self:
                                pass
                               # cdl_error( "S9999 Descriptor argument '$1' is the same signature as this parameter '$2' included", @name, param.get_name )
                            dir = param.get_direction()
                            if dir != "IN" and dir != "OUT" and dir != "INOUT":
                                self.cdl_error("S9999 Descriptor argument '$1' cannot be specified for $2 parameter", param.get_name(), dir.lower())
        self.descriptor_list = desc_list

    #=== Signature# 引数に Descriptor があるか？
    def has_descriptor(self):
        if self.get_descriptor_list() is None:
            # end_of_parse が呼び出される前に has_descriptor? が呼び出された
            # 呼び出し元は DescriptorType#initialize
            # この場合、同じシグニチャ内の引数が Descriptor 型である
            return True
        elif len(self.get_descriptor_list()) > 0:
            return True
        else:
            return False

    #=== Signature# コールバックか？
    # 指定子 callback が指定されていれば true
    def is_callback(self):
        return self.b_callback

    #=== Signature# 逸脱か？
    # 指定子 deviate が指定されていれば true
    def is_deviate(self):
        return self.b_deviate

    #=== Signature# 空か？
    def is_empty(self):
        return self.b_empty

    #=== Signature# Push Pop Allocator が必要か？
    # Transparent RPC の場合 oneway かつ in の配列(size_is, count_is, string のいずれかで修飾）がある
    def need_PPAllocator(self, b_opaque=False):
        fha = self.get_function_head_array()                       # 呼び口または受け口のシグニチャの関数配列
        for fh in fha:
            fd = fh.get_declarator()
            if fd.get_type().need_PPAllocator(b_opaque):
                # p "#{fd.get_name} need_PPAllocator: true"
                self.b_need_PPAllocator = True
                return True
            # p "#{fd.get_name} need_PPAllocator: false"
        return False

    def show_tree(self, indent):
        from tecslib.rubylib import rb
        print("  " * indent, end="")
        print("Signature: name: {} context: {} deviate : {} PPAllocator: {} {}".format(
            self.name, rb.to_s(self.context), rb.to_s(self.b_deviate),
            rb.to_s(getattr(self, "b_PPAllocator", None)), rb.inspect(self)))
        print("  " * (indent + 1), end="")
        print("namespace_path: {}".format(self.NamespacePath))
        print("  " * (indent + 1), end="")
        print("function head list:")
        self.function_head_list.show_tree(indent + 2)
