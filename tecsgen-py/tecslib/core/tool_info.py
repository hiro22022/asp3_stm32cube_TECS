# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/tool_info.rb を
#   Python へ移植したものである．

import sys

from tecslib.core import globals as G
from tecslib.core.toplevel import dbgPrint
from tecslib.rubylib.symbol import Sym


def _sym_key(k):
    if isinstance(k, Sym):
        return k
    return Sym(str(k))


def _schema_key(k):
    if isinstance(k, Sym):
        return k
    if isinstance(k, str):
        return Sym(k)
    return k


class TOOL_INFO:
    tool_info = {}

    TECSGEN_schema = {
        Sym("tecsgen"): {
            Sym("base_dir"): [Sym("string")],
            Sym("direct_import"): [Sym("string")],
            Sym("import_path"): [Sym("string")],
            Sym("define_macro"): [Sym("string")],
            Sym("tecscde_version"): Sym("string"),
            Sym("cde_format_version"): Sym("string"),
            Sym("save_date"): Sym("string"),
        },
        Sym("__tecsgen"): {
            Sym("cpp"): Sym("string"),
        },
    }

    def __init__(self, name, val):
        name = _sym_key(name)
        TOOL_INFO.tool_info[name] = val
        if name == Sym("tecsgen"):
            self.set_tecsgen_tool_info()

    @classmethod
    def get_tool_info(cls, name):
        return cls.tool_info.get(_sym_key(name))

    def set_tecsgen_tool_info(self):
        validator = TOOL_INFO.VALIDATOR(Sym("tecsgen"), TOOL_INFO.TECSGEN_schema)
        if validator.validate() or getattr(G, "b_force_apply_tool_info", False):
            info = TOOL_INFO.get_tool_info(Sym("tecsgen"))
            if info is None:
                return
            for bd in info.get(Sym("base_dir"), []):
                if bd not in G.base_dir:
                    G.base_dir[bd] = True
            for path in info.get(Sym("import_path"), []):
                if path not in G.import_path:
                    G.import_path.append(path)
            for define in info.get(Sym("define_macro"), []):
                if define not in G.define:
                    G.define.append(define)
            cpp = info.get(Sym("cpp"))
            if cpp and not G.b_cpp_specified:
                G.cpp = cpp
                G.b_cpp_specified = True
            direct = info.get(Sym("direct_import"))
            if direct:
                from tecslib.core.componentobj.import_ import Import
                for imp in direct:
                    Import(imp, False, False)

    class VALIDATOR:
        def __init__(self, name, schema):
            self.name = _sym_key(name)
            self.schema = schema
            self.b_ok = True

        def error(self, msg):
            sys.stderr.write("__tool_info__: " + msg)
            self.b_ok = False

        def validate(self):
            info = TOOL_INFO.get_tool_info(self.name)
            if info is None:
                self.error('"{}" not found\n'.format(self.name))
                return self.b_ok
            self.validate_object(info, self.name, self.name)
            return self.b_ok

        def validate_object(self, obj, require_type, path):
            obj_type = self.schema.get(_schema_key(require_type))
            if obj_type is None:
                return
            for name, val_type in obj_type.items():
                val = obj.get(name)
                if val is None:
                    val = obj.get(_sym_key(name))
                path2 = "{}.{}".format(path, name)
                if val is None:
                    self.error("{}: required property not found '{}'\n".format(path, name))
                    continue
                if isinstance(val_type, list):
                    self.validate_array_member(val, val_type, path2)
                else:
                    self.validate_types(val, val_type, path2)

            opt_key = Sym("__" + str(require_type))
            optional = self.schema.get(opt_key)
            if optional:
                for name, val_type in optional.items():
                    val = obj.get(name)
                    if val is None:
                        val = obj.get(_sym_key(name))
                    if val is None:
                        continue
                    path2 = "{}.{}".format(path, name)
                    if isinstance(val_type, list):
                        self.validate_array_member(val, val_type, path2)
                    else:
                        self.validate_types(val, val_type, path2)

        def validate_array_member(self, array, val_types, path):
            if not isinstance(array, list):
                self.error("{}: array required as value\n".format(path))
                return
            index = 0
            for member in array:
                typ = self.get_object_type(member)
                i = None
                for j, vt in enumerate(val_types):
                    if vt == typ or (isinstance(vt, Sym) and vt == typ):
                        i = j
                        break
                if i is None and typ == Sym("integer"):
                    for j, vt in enumerate(val_types):
                        if vt == Sym("number"):
                            i = j
                            break
                if i is None:
                    self.error("{}: array member type mismatch, {} for {}\n".format(path, typ, val_types))
                    index += 1
                    continue
                val_type = val_types[i]
                self.validate_types(member, val_type, "{}[{}].".format(path, index))
                index += 1

        def validate_types(self, obj, val_type, path):
            typ = self.get_object_type(obj)
            vt = _schema_key(val_type)
            if vt == Sym("integer"):
                if typ == Sym("integer"):
                    return
            elif vt == Sym("number"):
                if typ in (Sym("integer"), Sym("number")):
                    return
            elif vt == Sym("string"):
                if typ == Sym("string"):
                    return
            elif isinstance(val_type, str):
                if typ == Sym("string") and obj == val_type:
                    return
            else:
                if typ == vt:
                    self.validate_object(obj, val_type, path + str(val_type))
                    return
            self.error("{}: type mismatch, {} for {}\n".format(path, typ, val_type))

        def get_object_type(self, obj):
            if isinstance(obj, bool):
                return Sym("bool")
            if isinstance(obj, int):
                return Sym("integer")
            if isinstance(obj, float):
                return Sym("number")
            if isinstance(obj, str):
                return Sym("string")
            if isinstance(obj, dict):
                t = obj.get(Sym("type"))
                if t is None:
                    t = obj.get("type")
                if isinstance(t, Sym):
                    return t
                if t is not None:
                    return Sym(str(t))
            return None
