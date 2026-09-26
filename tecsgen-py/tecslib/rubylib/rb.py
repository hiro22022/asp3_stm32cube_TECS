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
#= Ruby の細かな組み込み挙動の互換関数
#
# 文字列埋め込み "#{obj}" は nil を空文字列にするなど，Python の str() と
# 挙動が異なるものがある．出力を一致させるためにここへまとめる．


#=== Ruby の to_s / "#{obj}" 相当
# nil は空文字列，true/false は "true"/"false" になる
# Token などインスタンスメソッド to_s() を持つオブジェクトはそれを使う
def to_s(obj):
    if obj is None:
        return ""
    if obj is True:
        return "true"
    if obj is False:
        return "false"
    meth = getattr(type(obj), "to_s", None)
    if callable(meth) and meth is not to_s:
        return meth(obj)
    return str(obj)


#=== Ruby の obj.class 相当の表示 (nil → NilClass)
def class_name(obj):
    if obj is None:
        return "NilClass"
    return obj.__class__.__name__


#=== Ruby の Object#inspect の簡易版 (#<Class:0x...>)
def inspect(obj):
    if obj is None:
        return "nil"
    if obj is True:
        return "true"
    if obj is False:
        return "false"
    return "#<{}:0x{:016x}>".format(obj.__class__.__name__, id(obj))


#=== Ruby の Array#uniq 相当 (出現順を保つ)
def uniq(array):
    return list(dict.fromkeys(array))
