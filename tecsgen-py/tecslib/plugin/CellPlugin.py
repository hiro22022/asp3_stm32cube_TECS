# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2011 by TOPPERS Project
#
#   このファイルは tecsgen (Ruby 版) の tecslib/plugin/CellPlugin.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．
#
#   $Id: CellPlugin.rb 2952 2018-05-07 10:19:07Z okuma-top $
#++

#== celltype プラグインの共通の親クラス
from tecslib.core.plugin import Plugin
from tecslib.core.syntaxobj.cdlstring import CDLString


class CellPlugin(Plugin):

    #=== CellPlugin# initialize
    # cell::     Cell        セル（インスタンス）
    # このメソッドは、セルの構文解析が終わったところで呼び出される
    # この段階では意味解析が終わっていない
    def __init__(self, cell, option):
        super().__init__()
        self.cell = cell
        self.plugin_arg_str = CDLString.remove_dquote(option)
        # @plugin_arg_str = option.gsub( /\A"(.*)/, '\1' )    # 前後の "" を取り除く
        # @plugin_arg_str.sub!( /(.*)"\z/, '\1' )
        self.plugin_arg_list = {}

    #=== 後ろの CDL コードを生成
    # プラグインの後ろの CDL コードを生成
    # file:: File:
    @classmethod
    def gen_post_code(cls, file):
        # 複数のプラグインの post_code が一つのファイルに含まれるため、以下のような見出しをつけること
        # file.print "/* '#{self.class.name}' post code */\n"
        pass
