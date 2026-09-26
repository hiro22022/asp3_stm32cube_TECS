# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/syntaxobj/namedlist.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

import copy

from tecslib.core.toplevel import dbgPrint
from tecslib.rubylib.symbol import Sym, is_symbol


class NamedList:
    #  @names:: {} of items
    #  @items:: [] of items : item の CLASS は get_name メソッドを持つこと get_name の戻り値は Symbol でなくてはならない
    #                         NamedList を clone_for_composite する場合は、item にもメソッドが必要
    #  @type:: string	エラーメッセージ

    def __init__(self, item, type_):
        self.names = {}
        self.items = []
        self.type = type_
        self.add_item(item)

    #=== 要素を加える
    # parse した時点で加えること(場所を記憶する)
    def add_item(self, item):
        from tecslib.core.bnf import Generator

        if item:
            dbgPrint("add_item: name={}   {}\n".format(item.get_name(), item.locale_str()))
            self.assert_name(item)
            name = item.get_name()
            prev = self.names.get(name)
            if prev:
                Generator.error("S2001 \'$1\' duplicate $2", name, self.type)
                prev_locale = prev.get_locale()
                print("previous: {}: line {} \'{}\' defined here".format(
                    prev_locale[0], prev_locale[1], name))
                return self

            self.names[name] = item
            self.items.append(item)

        return self

    def change_item(self, item):
        self.assert_name(item)
        name = item.get_name()

        prev_one = self.names.get(name)
        self.names[name] = item

        self.items = [i for i in self.items if i is not prev_one]
        self.items.append(item)

    def del_item(self, item):
        self.assert_name(item)
        name = item.get_name()
        self.names.pop(name, None)

        self.items = [i for i in self.items if i is not item]

    def get_item(self, name):
        if not is_symbol(name):
            print("get_item: '{}', items are below".format(name))
            for nm in self.names:
                print(repr(nm))
            raise Exception("get_item: {}: not Symbol".format(name))
        if name:
            return self.names.get(Sym(name))
        return None

    def get_items(self):
        return self.items

    #=== composite cell を clone した時に要素(JOIN) の clone する
    #
    # mikan このメソッドは Join に特化されているので NamedList から分離すべき
    def clone_for_composite(self, ct_name, cell_name, locale):
        cl = copy.copy(self)
        cl.set_cloned(ct_name, cell_name, locale)
        return cl

    #=== clone された NamedList インスタンスの参照するもの(item)を clone
    #
    # mikan このメソッドは Join に特化されているので NamedList から分離すべき
    def set_cloned(self, ct_name, cell_name, locale):
        items = []
        names = {}
        for i in self.items:
            dbgPrint("NamedList clone {}, {}, {}\n".format(ct_name, cell_name, i.get_name()))

            cl = i.clone_for_composite(ct_name, cell_name, locale)
            names[cl.get_name()] = cl
            items.append(cl)
        self.items = items
        self.names = names

    def assert_name(self, item):
        if not is_symbol(item.get_name()):
            raise Exception("Not symbol for NamedList item")

    def show_tree(self, indent):
        for i in self.items:
            i.show_tree(indent)
