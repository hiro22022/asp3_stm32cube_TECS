# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2014 by TOPPERS Project
#
#   このファイルは tecsgen (Ruby 版) の tecslib/plugin/CelltypePlugin.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．
#
#   $Id: CelltypePlugin.rb 3302 2026-06-07 06:01:02Z okuma-top $
#++

#== celltype プラグインの共通の親クラス
# セルタイププラグインを実装する場合の親クラス
# このクラスの親クラスで定義されている各メソッドも呼び出される、または呼び出せる
from tecslib.core.plugin import Plugin
from tecslib.core.syntaxobj.cdlstring import CDLString


class CelltypePlugin(Plugin):

    # celltype::     Celltype        セルタイプ（インスタンス）
    def __init__(self, celltype, option):
        super().__init__()
        self.celltype = celltype
        # @plugin_arg_str = option.gsub( /\A"(.*)/, '\1' )    # 前後の "" を取り除く
        # @plugin_arg_str.sub!( /(.*)"\z/, '\1' )
        self.plugin_arg_str = CDLString.remove_dquote(option)
        self.plugin_arg_list = {}

    #=== 新しいセル
    # cell::        Cell            セル
    #
    # celltype プラグインを指定されたセルタイプのセルが生成された
    # セルタイププラグインに対する新しいセルの報告
    def new_cell(self, cell):
        pass

    #=== 後ろの CDL コードを生成
    # プラグインの後ろの CDL コードを生成
    # file:: File:
    @classmethod
    def gen_post_code(cls, file):
        # 複数のプラグインの post_code が一つのファイルに含まれるため、以下のような見出しをつけること
        # file.print "/* '#{self.class.name}' post code */\n"
        pass

    #------ コード生成段階で呼び出されるメソッド --------#

    #=== tCelltype_factory.h に挿入するコードを生成する
    # file 以外の他のファイルにファクトリコードを生成してもよい
    # セルタイププラグインが指定されたセルタイプのみ呼び出される
    def gen_factory(self, file):
        pass
