# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/pluginModule.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

import importlib.util
import os
import sys

from tecslib.core import globals as G
from tecslib.core.toplevel import dbgPrint, print_exception
from tecslib.rubylib.symbol import Sym


def _to_sym(name):
    if isinstance(name, Sym):
        return name
    return Sym(str(name))


def _require_tecsgen_lib(fname, b_fatal=True):
    """Ruby 版 tecsgen.rb の require_tecsgen_lib 相当（plugin ロード用）"""
    dbgPrint("require_lib: {}\n".format(fname))
    b_require = False
    b_exception = False

    rb_base = fname
    if rb_base.endswith(".rb"):
        py_base = rb_base[:-3] + ".py"
        plugin_class_name = rb_base[:-3]
    else:
        py_base = rb_base + ".py"
        plugin_class_name = rb_base

    # lib/Foo.rb → モジュール名はスラッシュ不可
    plugin_mod_suffix = plugin_class_name.replace("/", ".").replace("\\", ".")
    plugin_attr_name = plugin_class_name.split("/")[-1].split("\\")[-1]

    # パッケージ同梱プラグインは通常 import する（_dyn_ 再ロードだと
    # issubclass 判定が別クラス扱いになり P2002 になる）
    for cand in (
        "tecslib.plugin." + plugin_mod_suffix,
        "tecslib.plugin." + plugin_attr_name,
    ):
        try:
            mod = importlib.import_module(cand)
            if hasattr(mod, plugin_attr_name):
                return True
        except ImportError:
            pass

    load_paths = list(G.library_path) + list(sys.path)

    for path in load_paths:
        for lp in ("", "tecslib/plugin/"):
            lib = os.path.normpath(os.path.join(os.path.expanduser(path), lp, py_base))
            if os.path.isfile(lib):
                try:
                    pkg_mod_name = "tecslib.plugin.{}".format(plugin_mod_suffix)
                    if pkg_mod_name in sys.modules:
                        b_require = True
                        break
                    mod_name = "tecslib.plugin._dyn_{}".format(plugin_attr_name)
                    if mod_name in sys.modules and hasattr(sys.modules[mod_name], plugin_attr_name):
                        b_require = True
                        break
                    spec = importlib.util.spec_from_file_location(mod_name, lib)
                    if spec is None or spec.loader is None:
                        b_exception = True
                        break
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[mod_name] = module
                    spec.loader.exec_module(module)
                    b_require = True
                except Exception as evar:
                    b_exception = True
                    print_exception(evar)
                break
        if b_require:
            break

    if b_require is False and b_exception is False:
        for lp in ("", "tecslib/plugin/"):
            rel = (lp + py_base).replace("/", ".").replace(".py", "")
            try:
                importlib.import_module(rel)
                b_require = True
                break
            except ImportError:
                pass
            except Exception as evar:
                b_exception = True
                print_exception(evar)
                break

    if b_require is False:
        if b_exception is False:
            sys.stderr.write(
                "tecsgen: Fail to load {}. plugin は未対応 "
                "(Check library path or -L option)\n".format(fname)
            )
        if b_fatal:
            sys.stderr.write("tecsgen: Exit because of unrecoverble error\n")
            sys.exit(1)
        return False
    return True


def _const_get(plugin_name):
    name = str(plugin_name)
    attr = name.split("/")[-1]
    # 同梱プラグインを優先（_dyn_ と二重定義を避ける）
    for cand in (
        "tecslib.plugin." + name.replace("/", "."),
        "tecslib.plugin." + attr,
    ):
        try:
            mod = importlib.import_module(cand)
            return getattr(mod, attr)
        except (ImportError, AttributeError):
            pass
    mod_name = "tecslib.plugin._dyn_{}".format(attr)
    if mod_name in sys.modules:
        return getattr(sys.modules[mod_name], attr)
    raise ImportError("plugin は未対応: {} をロードできません".format(name))


def _const_defined(plugin_name):
    try:
        _const_get(plugin_name)
        return True
    except (ImportError, AttributeError):
        return False


def _import_plugin_class(class_name):
    for mod_path in (
        "tecslib.plugin.{}".format(class_name),
        "tecslib.plugin.{}".format(_camel_to_snake(class_name)),
    ):
        try:
            mod = importlib.import_module(mod_path)
            return getattr(mod, class_name)
        except ImportError:
            continue
    return None


def _camel_to_snake(name):
    out = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0:
            out.append("_")
        out.append(ch.lower())
    return "".join(out)


#== プラグインをロードする側のモジュール
# @@loaded_plugin_list:: {Symbol=>Integer}
class PluginModule:

    loaded_plugin_list = {}

    # 後ろのコードの出力順の指定 (数字が少ないほどプライオリティは高い)
    MULTI_PLUGIN_POST_CODE_PRIORITY = 0
    DOMAIN_PLUGIN_POST_CODE_PRIORITY = 10000
    CLASS_PLUGIN_POST_CODE_PRIORITY = 10000
    THROUGH_PLUGIN_POST_CODE_PRIORITY = 20000
    CELLTYPE_PLUGIN_POST_CODE_PRIORITY = 30000
    COMPOSITE_PLUGIN_POST_CODE_PRIORITY = 40000
    CELL_PLUGIN_POST_CODE_PRIORITY = 50000
    SIGNATURE_PLUGIN_POST_CODE_PRIORITY = 60000

    _MULTI_PLUGIN_MARKER = Sym("MultiPlugin")

    #=== プラグインをロードする
    # return:: PluginClass
    # V1.4.1 まで return:: true : 成功、 false : 失敗
    #
    # #{plugin_name}.rb をロードし、plugin_name クラスのオブジェクトを生成する．
    # plugin_name が MultiPlugin の場合、get_plugin により、superClass のプラグインオブジェクトをロードする．
    #
    # すでにロードされているものは、重複してロードしない
    # load 時の例外はこのメソッドの中でキャッチされて false が返される
    def load_plugin(self, plugin_name, superClass):
        dbgPrint("PluginModule: load_plugin: {}\n".format(plugin_name))
        try:
            sym = _to_sym(plugin_name)
            if sym not in PluginModule.loaded_plugin_list:
                PluginModule.loaded_plugin_list[sym] = 0
                if G.verbose:
                    print("load '{}.rb'".format(plugin_name))
                # "#{plugin_name}.rb" をロード（システム用ではないので、fatal エラーにしない）
                if _require_tecsgen_lib("{}.rb".format(plugin_name), False) is False:
                    self.cdl_error("P2001 $1.rb : fail to load plugin", plugin_name)
                    return None

            plClass = _const_get(plugin_name)
            if not isinstance(plClass, type):
                self.cdl_error("P2003 $1: load failed", plugin_name)
                return None
            if superClass is None or not isinstance(superClass, type):
                self.cdl_error("P2003 $1: load failed", plugin_name)
                return None
            if issubclass(plClass, superClass):       # plClass inherits superClass
                return plClass
            else:
                MultiPlugin = _import_plugin_class("MultiPlugin")
                if MultiPlugin is not None and issubclass(plClass, MultiPlugin):     # plClass inherits MultiPlugin
                    dbgPrint("pluginClass={}\n".format(plClass))
                    plugin_object = plClass.get_plugin(superClass)
                    dbgPrint("pluginClass={}\n".format(plugin_object))
                    if plugin_object is None:
                        self.cdl_error("P9999 '$1': MultiPlugin not support '$2'", plugin_name, superClass.__name__)
                        return None
                    if not isinstance(plugin_object, type):
                        self.cdl_error("P2003 $1: load failed", plugin_name)
                        return None
                    PluginModule.loaded_plugin_list[sym] = PluginModule._MULTI_PLUGIN_MARKER
                    return plugin_object
                else:
                    self.cdl_error("P2002 $1: not kind of $2", plugin_name, superClass.__name__)
                    return None
        except Exception as evar:
            if G.debug:
                print(type(evar))
                import traceback
                traceback.print_exc()
            self.cdl_error("P2003 $1: load failed", plugin_name)
            return None
        # ここへは来ない
        return None

    #=== プラグインの gen_cdl_file を呼びして cdl ファイルを生成させ、解釈を行う
    def generate_and_parse(self, plugin_object):
        if plugin_object is None:     # プラグインのロードに失敗している（既にエラー）
            return
        plugin_name = _to_sym(plugin_object.__class__.__name__)
        if PluginModule.loaded_plugin_list.get(plugin_name) == PluginModule._MULTI_PLUGIN_MARKER:
            print("{}: MultiPlugin".format(plugin_name))
            return
        elif plugin_name not in PluginModule.loaded_plugin_list:
            #raise "#{plugin_name} might have different name "
            ## プラグインのファイル名と、プラグインのクラス名が相違する場合
            #MultiPlugin の get_plugin で返されたケースでは nil になっている
            PluginModule.loaded_plugin_list[plugin_name] = 0
        count = PluginModule.loaded_plugin_list[plugin_name]
        PluginModule.loaded_plugin_list[plugin_name] = count + 1
        tmp_file_name = "{}/tmp_{}_{}.cdl".format(G.gen, plugin_name, count)

        tmp_file = None
        try:
            from tecslib.core.plugin import CFile
            tmp_file = CFile.open(tmp_file_name, "w")
        except Exception as evar:
            self.cdl_error("P2004 $1: open error \'$2\'", plugin_name, tmp_file_name)
            print_exception(evar)
        dbgPrint("generate_and_parse: {}: gen_cdl_file\n".format(plugin_object.__class__))
        try:
            plugin_object.gen_cdl_file(tmp_file)
        except Exception as evar:
            self.cdl_error("P2005 $1: plugin error in gen_through_cell_code ", plugin_name)
            print_exception(evar)
        try:
            if tmp_file is not None:
                tmp_file.close()
        except Exception as evar:
            self.cdl_error("P2006 $1: close error \'$2\'", plugin_name, tmp_file_name)
            print_exception(evar)

        from tecslib.core.bnf import Generator
        generator = Generator()
        generator.set_plugin(plugin_object)
        generator.parse([tmp_file_name])
        generator.finalize()

    #=== プラグインが CDL の POST コードを生成
    # tmp_plugin_post_code.cdl への出力
    @classmethod
    def gen_plugin_post_code(cls):
        dbgPrint("------------  gen_plugin_post_code  -------------\n")
        dbgPrint("PluginModule {}\n".format(PluginModule.loaded_plugin_list))
        sorted_plugin_list = cls.sort_and_load(list(PluginModule.loaded_plugin_list.keys()))
        new_plugin_list = []
        for plugin_name, count in PluginModule.loaded_plugin_list.items():
            b_found = False
            for plugin in sorted_plugin_list:
                if _to_sym(plugin.__name__) == _to_sym(plugin_name):
                    b_found = True
                    break
            if not b_found:
                new_plugin_list.append(plugin_name)
        cls.sort_and_load(new_plugin_list)

    @classmethod
    def sort_and_load(cls, plugin_list):
        from tecslib.core.bnf import Generator
        from tecslib.core.plugin import CFile
        #------ post_code priority 順のリストを作成  ------#
        plugin_priority_list = {}
        for plugin_name in plugin_list:
            if not _const_defined(plugin_name):    # undefined PluginModule
                continue
            plClass = _const_get(plugin_name)
            # Ruby: plClass.respond_to?(:get_post_code_priority) — クラス固有の無引数版
            # （例: TECSInfoPlugin）。無い場合は PluginModule.get_post_code_priority(plClass)。
            if "get_post_code_priority" in plClass.__dict__:
                prio = plClass.get_post_code_priority()
            else:
                prio = cls.get_post_code_priority(plClass)
            if plugin_priority_list.get(prio) is None:
                plugin_priority_list[prio] = [plClass]
            else:
                plugin_priority_list[prio].append(plClass)
            dbgPrint("pluginModule: prio={} plugin={}\n".format(prio, plClass.__name__))
        sorted_plugin_list = []
        for prio in sorted(plugin_priority_list.keys()):
            if prio != 0:   # exclude MultiPlugin
                plClassList = plugin_priority_list[prio]
                sorted_plugin_list += plClassList
        #----- post code priority 順に post code を生成  -------#
        for plClass in sorted_plugin_list:
            tmp_file_name = "{}/tmp_{}_post_code.cdl".format(G.gen, plClass.__name__)
            file = None
            try:
                file = CFile.open(tmp_file_name, "w")
            except Exception:
                Generator.error("G9999 fail to create {}".format(tmp_file_name))

            if file:
                dbgPrint("PluginModule: {}\n".format(plClass.__name__))
                eval_str = "{}.gen_post_code( file )".format(plClass.__name__)
                if G.verbose:
                    print("gen_plugin_post_code: {}".format(eval_str))
                try:
                    plClass.gen_post_code(file)
                except Exception as evar:
                    Generator.error("P2007 $1: fail to generate post code", plClass.__name__)
                    print_exception(evar)
                try:
                    file.close()
                except Exception:
                    Generator.error("G9999 fail to close {}".format(tmp_file_name))
                dbgPrint("## Import Post Code\n")
                from tecslib.core.componentobj.import_ import Import
                Import(tmp_file_name)
        return sorted_plugin_list

    #=== プラグインの後ろの CDL コードの生成順を指定
    @classmethod
    def get_post_code_priority(cls, plClass):
        MultiPlugin = _import_plugin_class("MultiPlugin")
        DomainPlugin = _import_plugin_class("DomainPlugin")
        ClassPlugin = _import_plugin_class("ClassPlugin")
        ThroughPlugin = _import_plugin_class("ThroughPlugin")
        CompositePlugin = _import_plugin_class("CompositePlugin")
        CelltypePlugin = _import_plugin_class("CelltypePlugin")
        CellPlugin = _import_plugin_class("CellPlugin")
        SignaturePlugin = _import_plugin_class("SignaturePlugin")
        if MultiPlugin is not None and issubclass(plClass, MultiPlugin):
            return cls.MULTI_PLUGIN_POST_CODE_PRIORITY
        elif DomainPlugin is not None and issubclass(plClass, DomainPlugin):
            return cls.DOMAIN_PLUGIN_POST_CODE_PRIORITY
        elif ClassPlugin is not None and issubclass(plClass, ClassPlugin):
            return cls.CLASS_PLUGIN_POST_CODE_PRIORITY
        elif ThroughPlugin is not None and issubclass(plClass, ThroughPlugin):
            return cls.THROUGH_PLUGIN_POST_CODE_PRIORITY
        elif CompositePlugin is not None and issubclass(plClass, CompositePlugin):
            return cls.COMPOSITE_PLUGIN_POST_CODE_PRIORITY
        elif CelltypePlugin is not None and issubclass(plClass, CelltypePlugin):
            return cls.CELLTYPE_PLUGIN_POST_CODE_PRIORITY
        elif CellPlugin is not None and issubclass(plClass, CellPlugin):
            return cls.CELL_PLUGIN_POST_CODE_PRIORITY
        elif SignaturePlugin is not None and issubclass(plClass, SignaturePlugin):
            return cls.SIGNATURE_PLUGIN_POST_CODE_PRIORITY
        else:
            raise Exception("Unknown Plugin type '{}'".format(plClass.__name__))
