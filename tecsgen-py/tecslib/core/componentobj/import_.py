# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/componentobj/import.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

import os
import re

from tecslib.core import globals as G
from tecslib.core.componentobj.importable import Importable
from tecslib.core.syntaxobj.node import Node
from tecslib.rubylib.rb import to_s


class Import(Node, Importable):
    # @b_reuse::bool:       再利用．セルタイプの template 生成不要
    # @b_reuse_real::bool:  実際に再利用
    # @cdl::      string:   import する CDL
    # @cdl_path:: string:   CDL のパス
    # @b_imported:: bool:   import された(コマンドライン指定されていない)

    # ヘッダの名前文字列のリスト  添字：expand したパス、値：Import
    import_list = {}

    nest_stack_index = -1
    nest_stack = []
    current_object = None
    current_import = None

    @classmethod
    def push(cls, object):
        cls.nest_stack_index += 1
        if cls.nest_stack_index >= len(cls.nest_stack):
            cls.nest_stack.append(None)
        cls.nest_stack[cls.nest_stack_index] = cls.current_object
        cls.current_object = object

    @classmethod
    def pop(cls):
        cls.current_object = cls.nest_stack[cls.nest_stack_index]
        cls.nest_stack_index -= 1
        if cls.nest_stack_index < -1:
            raise Exception("TooManyRestore")

    #=== Import# import を行う
    #cdl::      string   cdl へのパス．"" で囲まれていることを仮定
    #b_reuse::  bool     true: template を生成しない
    def __init__(self, cdl, b_reuse=False, b_imported=True):
        Import.push(self)
        self.b_imported = b_imported
        super().__init__()
        Import.current_import = self
        # ヘッダファイル名文字列から前後の "", <> を取り除くn
        self.cdl = re.sub(r'\A["<](.*)[">]\Z', r'\1', to_s(cdl))

        # サーチパスから探す
        found = False
        self.cdl_path = ""

        self.b_reuse = b_reuse
        from tecslib.core.bnf import Generator
        self.b_reuse_real = self.b_reuse or Generator.is_reuse()

        if Generator.get_plugin() and os.path.exists("{}/{}".format(G.gen, self.cdl)):
            self.cdl_path = "{}/{}".format(G.gen, self.cdl)
            found = True
        else:
            path = self.find_file(self.cdl)
            if path:
                found = True
                self.cdl_path = path

        if found == False:
            self.cdl_error("S1148 $1 not found in search path", self.cdl)
            return

        # 読込み済みなら、読込まない
        prev = Import.import_list.get(os.path.abspath(self.cdl_path))
        if prev:
            if prev.is_reuse_real() != self.b_reuse_real:
                self.cdl_warning("W1008 $1: reuse designation mismatch with previous import", self.cdl)
            return

        # import リストを記録
        Import.import_list[os.path.abspath(self.cdl_path)] = self

        # plugin から import されている場合
        plugin = Generator.get_plugin()

        # パーサインスタンスを生成(別パーサで読み込む)
        parser = Generator()

        # plugin から import されている場合の plugin 設定
        parser.set_plugin(plugin)

        # reuse フラグを設定
        parser.set_reuse(self.b_reuse_real)

        # cdl をパース
        parser.parse([self.cdl_path])

        # 終期化　パーサスタックを戻す
        parser.finalize()
        Import.pop()

    @classmethod
    def get_list(cls):
        return cls.import_list

    def get_cdl_path(self):
        return self.cdl_path

    def is_reuse_real(self):
        return self.b_reuse_real

    @classmethod
    def get_current(cls):
        return cls.current_object

    def is_imported(self):
        return self.b_imported

    #=== cdl の名前を返す
    # 引数で指定されている cdl 名。一部パスを含む可能性がある
    def get_cdl_name(self):
        return self.cdl
