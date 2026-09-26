# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) を Python へ移植したものの一部である．
#   ライセンスは tecsgen.py の冒頭を参照のこと．
#
#= Ruby のクラス再オープン相当
#
# tecsgen は generate.rb が Namespace, Celltype, Cell などにメソッドを追加する，
# いわゆるクラスの再オープンを多用している．Python には同じ構文がないため，
# 追加したいメソッドをまとめたクラスを書き，@reopen で対象クラスへ流し込む．
#
#   @reopen(Celltype)
#   class _:
#     def generate(self):
#       ...

_SKIP = ("__dict__", "__weakref__", "__module__", "__qualname__", "__doc__")


#=== donor に定義されたメソッドを target に追加する
#target:: type   : メソッドを追加される側のクラス
def reopen(target):
    def apply(donor):
        for name, value in vars(donor).items():
            if name in _SKIP:
                continue
            setattr(target, name, value)
        return target
    return apply
