# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/syntaxobj/cdlinitializer.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

from tecslib.rubylib.symbol import Sym


#== CDL の初期化子を扱うためのクラス
# CDL の初期化子そのものではない
class CDLInitializer:
    #=== 初期化子のクローン
    # 初期化子は Expression, C_EXP, Array のいずれか
    @classmethod
    def clone_for_composite(cls, rhs, ct_name, cell_name, locale):
        from tecslib.core.expression import Expression, C_EXP

        if type(rhs) is C_EXP:
            # C_EXP の clone を作るとともに置換
            rhs = rhs.clone_for_composite(ct_name, cell_name, locale)
        elif type(rhs) is Expression:
            rhs = rhs.clone_for_composite()
        elif type(rhs) is list:
            rhs = cls.clone_for_compoiste_array(rhs, ct_name, cell_name, locale)
        else:
            raise Exception("unknown rhs for join")
        return rhs

    #=== 初期化子（配列）のクローン
    # 要素は clone_for_composite を持つものだけ
    @classmethod
    def clone_for_compoiste_array(cls, array, ct_name, cell_name, locale):
        # "compoiste.identifier" の場合 (CDL としては誤り)
        if array[0] == Sym("COMPOSITE"):
            return list(array)

        return [cls.clone_for_composite(m, ct_name, cell_name, locale) for m in array]
