# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/syntaxobj/node.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

from tecslib.core.toplevel import dbgPrint


#== Node
#
# Node の直接の子クラス： C_EXP, Type, BaseVal, BDNode(ほとんどのものは BDNode の子クラス)
# Node に (BDNodeにも) 入らないもの: Token, Import, Import_C, Generate
#
# owner を持たないものが Node となる
# エラーは、cdl_error を通じて報告する (意味解析が構文解析後に行われる場合には、行番号が正しく出力できる
#
class Node:
    #@locale::    [file, lineno, col]

    def __init__(self):
        from tecslib.core.bnf import Generator
        self.locale = Generator.current_locale()

    #=== エラーを出力する
    def cdl_error(self, message, *arg):
        from tecslib.core.bnf import Generator
        Generator.error2(self.locale, message, *arg)

    #=== エラーを出力する
    #locale:: Array(locale info) : 構文解析中は無視される
    def cdl_error2(self, locale, message, *arg):
        from tecslib.core.bnf import Generator
        Generator.error2(locale, message, *arg)

    #=== エラーを出力する
    #locale:: Array(locale info)
    # 構文解析中 cdl_error2 では locale が無視されるため、別に locale を出力する
    def cdl_error3(self, locale, message, *arg):
        from tecslib.core.bnf import Generator
        from tecslib.core.tecs_lang import Console
        Generator.error(message, *arg)
        Console.puts("check: {}: line {} for above error".format(locale[0], locale[1]))

    #=== ウォーニング出力する
    def cdl_warning(self, message, *arg):
        from tecslib.core.bnf import Generator
        Generator.warning2(self.locale, message, *arg)

    #=== ウォーニング出力する
    def cdl_warning2(self, locale, message, *arg):
        from tecslib.core.bnf import Generator
        Generator.warning2(locale, message, *arg)

    #=== 情報を表示する
    def cdl_info(self, message, *arg):
        from tecslib.core.bnf import Generator
        Generator.info2(self.locale, message, *arg)

    #=== 情報を表示する
    def cdl_info2(self, locale, message, *arg):
        from tecslib.core.bnf import Generator
        Generator.info2(locale, message, *arg)

    def get_locale(self):
        return self.locale

    def set_locale(self, locale):
        self.locale = locale

    def locale_str(self):
        if self.locale:
            return "locale=({}, {})".format(self.locale[0], self.locale[1])
        return "locale=(?)"


#== 双方向 Node (Bi Direction Node)
#
#  Node の子クラス
#  owner Node から参照されているもの (owner へのリンクも取り出せる)
#
#  get_owner で得られるもの
#    FuncHead => Signature
#    Decl => Namespace(const), Typedef(typedef),
#            Celltype, CompositeCelltype(attr,var)
#            Struct(member), ParamDecl(parameter), FuncHead(funchead)
#    Signature, Celltype, CompositeCelltype, Typedef => Namespace
#,   Namespace => Namespace, Generator.class (root Namespace の場合)
#    Cell => Region, CompositeCelltype(in_composite)
#    Port => Celltype, Composite
#    Factory => Celltype
#    Join => Cell
#    CompositeCelltypeJoin => CompositeCelltype
#    Region => Region,
#    ParamDecl => ParamList
#    ParamList => FuncHead
#    Expression => Namespace
#    大半のものは new_* メソッドで owner Node に伝達される
#    そのメソッドが呼び出されたときに owner Node が記録される
#    new_* がないもの：
#            Decl(parameter), ParamDecl, ParamList, FuncHead, Expression
#
#    Expression は、owner Node となるものが多くあるが、改造が困難であるため
#    Expression が定義されたときの Namespace を owner Node とする
#    StructType は Type の一種なので owner を持たない
#
class BDNode(Node):
    #@owner::Node
    #@NamespacePath:: NamespacePath
    #@import::Import

    def __init__(self):
        from tecslib.core.componentobj.import_ import Import
        super().__init__()
        self.owner = None
        self.NamespacePath = None
        self.import_ = Import.get_current()

    #=== owner を設定する
    def set_owner(self, owner):
        dbgPrint("set_owner: {}\n".format(owner.__class__.__name__))
        self.owner = owner

    #=== owner を得る
    # class の説明を参照
    def get_owner(self):
        if self.owner is None:
            raise Exception("Node have no owner {} {}".format(
                self.__class__.__name__, self.get_name()))
        return self.owner


#== Namespace 名を持つ BDNode
# Namespace(Region), Signature, Celltype, CompositeCelltype, Cell
class NSBDNode(BDNode):

    def __init__(self):
        super().__init__()

    #=== 属する namespace を得る
    # owner を namespace にたどり着くまで上にたどる
    def get_namespace(self):
        from tecslib.core.componentobj.namespace import Namespace
        if isinstance(self.owner, Namespace):
            return self.owner
        elif self.owner is not None:
            return self.owner.get_namespace()
        else:
            # owner が None なら "::"
            if self.name != "::":
                raise Exception("non-root namespace has no owner {}#{} {}".format(
                    self.__class__.__name__, self.name, self))
            return None

    def set_namespace_path(self):
        ns = self.get_namespace()
        if ns:
            self.NamespacePath = ns.get_namespace_path().append(self.get_name())
        else:
            raise Exception("get_namespace_path: no namespace found")

    #=== NamespacePath を得る
    def get_namespace_path(self):
        return self.NamespacePath

    def is_imported(self):
        if self.import_:
            return self.import_.is_imported()
        return False    # mikan: 仮 import_ が None になるケースが追求できていない
