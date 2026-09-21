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
#= Ruby の Symbol 相当
#
# tecsgen は識別子を Symbol，文字列リテラルなどを String として扱い分けており，
# kind_of?( Symbol ) / instance_of?( String ) で判定している箇所がある．
# str のサブクラスとすることで，比較や辞書のキーとしては文字列と同じに働きつつ，
# isinstance で Symbol かどうかを判定できるようにする．


class Sym(str):
    __slots__ = ()

    def __repr__(self):
        return ":" + str.__str__(self)


#=== Ruby の instance_of?( String ) 相当 (Symbol は除く)
def is_string(obj):
    return isinstance(obj, str) and not isinstance(obj, Sym)


#=== Ruby の kind_of?( Symbol ) 相当
def is_symbol(obj):
    return isinstance(obj, Sym)
