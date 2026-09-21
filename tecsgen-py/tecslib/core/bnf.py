# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#  bnf.y.rb の rule 節 (_bnf_rules_gen) と inner/footer (_bnf_runtime) の結合．
#  ライセンスは tecsgen.py の冒頭を参照のこと．

import os
import re
import sys

# vendor/ply を import 可能にする
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_VENDOR = os.path.join(_REPO_ROOT, "vendor")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

from ply import yacc  # noqa: E402

from tecslib.core._bnf_runtime import Generator, Include, TECSIO, Token  # noqa: E402
from tecslib.core.componentobj.cell import Cell  # noqa: E402
from tecslib.core.componentobj.celltype import Celltype  # noqa: E402
from tecslib.core.componentobj.compositecelltype import CompositeCelltype  # noqa: E402
from tecslib.core.componentobj.factory import Factory  # noqa: E402
from tecslib.core.componentobj.generate import Generate  # noqa: E402
from tecslib.core.componentobj.import_ import Import  # noqa: E402
from tecslib.core.componentobj.import_c import Import_C  # noqa: E402
from tecslib.core.componentobj.join import Join  # noqa: E402
from tecslib.core.componentobj.namespace import Namespace  # noqa: E402
from tecslib.core.componentobj.namespacepath import NamespacePath  # noqa: E402
from tecslib.core.componentobj.port import Port  # noqa: E402
from tecslib.core.componentobj.region import Region  # noqa: E402
from tecslib.core.componentobj.reversejoin import ReverseJoin  # noqa: E402
from tecslib.core.componentobj.signature import Signature  # noqa: E402
from tecslib.core.expression import C_EXP, Expression  # noqa: E402
from tecslib.core.syntaxobj.decl import Decl  # noqa: E402
from tecslib.core.syntaxobj.funchead import FuncHead  # noqa: E402
from tecslib.core.syntaxobj.namedlist import NamedList  # noqa: E402
from tecslib.core.syntaxobj.paramdecl import ParamDecl  # noqa: E402
from tecslib.core.syntaxobj.paramlist import ParamList  # noqa: E402
from tecslib.core.syntaxobj.typedef import Typedef  # noqa: E402
from tecslib.core.types import (  # noqa: E402
    ArrayType,
    BoolType,
    DefinedType,
    DescriptorType,
    EnumType,
    FloatType,
    FuncType,
    IntType,
    PtrType,
    StructType,
    VoidType,
)

from tecslib.core.tool_info import TOOL_INFO  # noqa: E402

# 字句解析器が返す複数文字トークン → PLY 用終端名（引用リテラルは 1 文字のみ可のため）
_LEXER_MULTI_TO_PLY = {
    "->": "T_ARROW",
    "<<": "T_LSHIFT",
    ">>": "T_RSHIFT",
    "<=": "T_LE",
    ">=": "T_GE",
    "==": "T_EQ",
    "!=": "T_NE",
    "&&": "T_AND",
    "||": "T_OR",
    "...": "T_ELLIPSIS",
    "::": "T_COLCOL",
    "=>": "T_DARROW",
}
_JSON_NONTERMS = (
    "JSON_object",
    "JSON_property_list",
    "JSON_value",
    "JSON_array",
    "JSON_array_list",
    "JSON_string",
    "JSON_number",
)


def _fix_ply_docstring(doc):
    """racc_to_ply 生成物を PLY の制約に合わせて docstring を調整する."""
    if not doc or ":" not in doc:
        return doc
    lhs, rhs = doc.split(":", 1)
    rhs = rhs.strip()
    if "空行" in rhs:
        return f"{lhs.strip()} : empty"
    for lex, alias in _LEXER_MULTI_TO_PLY.items():
        rhs = rhs.replace(f'"{lex}"', alias)
    for nt in _JSON_NONTERMS:
        rhs = rhs.replace(f'"{nt}"', nt)
    return f"{lhs.strip()} : {rhs}"


def _patch_rule_docstrings(mod):
    for _name, obj in vars(mod).items():
        if not _name.startswith("p_") or not callable(obj):
            continue
        doc = obj.__doc__
        if not doc:
            continue
        fixed = _fix_ply_docstring(doc.strip())
        if fixed != doc.strip():
            obj.__doc__ = fixed


def _collect_rule_terminals(mod):
    terms = set()
    for _name, obj in vars(mod).items():
        if not _name.startswith("p_") or not callable(obj) or not obj.__doc__:
            continue
        _lhs, rhs = obj.__doc__.split(":", 1)
        for tok in rhs.split():
            if re.match(r"^[A-Z][A-Z0-9_]*$", tok):
                terms.add(tok)
    return terms


start = "all"

# 生成 rule 節の action が参照する名前（関数の __globals__ は _bnf_rules_gen）
import tecslib.core._bnf_rules_gen as _bnf_rules_gen  # noqa: E402

_RULES_GLOBALS = {
    "re": re,
    "Generator": Generator,
    "Token": Token,
    "Cell": Cell,
    "Celltype": Celltype,
    "CompositeCelltype": CompositeCelltype,
    "Signature": Signature,
    "Namespace": Namespace,
    "NamespacePath": NamespacePath,
    "Region": Region,
    "StructType": StructType,
    "VoidType": VoidType,
    "BoolType": BoolType,
    "IntType": IntType,
    "FloatType": FloatType,
    "EnumType": EnumType,
    "DefinedType": DefinedType,
    "DescriptorType": DescriptorType,
    "ArrayType": ArrayType,
    "FuncType": FuncType,
    "PtrType": PtrType,
    "Expression": Expression,
    "C_EXP": C_EXP,
    "Decl": Decl,
    "ParamDecl": ParamDecl,
    "ParamList": ParamList,
    "FuncHead": FuncHead,
    "NamedList": NamedList,
    "Typedef": Typedef,
    "Port": Port,
    "Factory": Factory,
    "Import": Import,
    "Import_C": Import_C,
    "Generate": Generate,
    "Join": Join,
    "ReverseJoin": ReverseJoin,
    "TOOL_INFO": TOOL_INFO,
    "isinstance": isinstance,
}
_bnf_rules_gen.__dict__.update(_RULES_GLOBALS)

_patch_rule_docstrings(_bnf_rules_gen)

tokens = sorted(
    _collect_rule_terminals(_bnf_rules_gen)
    | set(Generator.RESERVED.values())
    | set(Generator.RESERVED2.values())
    | set(_LEXER_MULTI_TO_PLY.values())
    | {"TYPE_NAME"}
)

from tecslib.core._bnf_rules_gen import *  # noqa: F403, E402


def p_error(p):
    """構文エラー。statement:error があるため、PLY ではトークンを捨てないと無限ループする。

    racc はエラー回復時に入力を読み進めるが、PLY は error 記号のシフト／還元だけだと
    先読みが変わらず statement→specified_statement→component_description が回り続ける。
    """
    gen = Generator.current()
    if gen is None:
        return
    if p is None:
        gen.on_error(None, None, None)
        return

    gen.on_error(p.type, p.value, None)

    # Panic-mode: ';' まで破棄して同期（次の statement 境界）
    tok = p
    while tok is not None and getattr(tok, "type", None) != ";":
        tok = parser.token()
    parser.errok()



# PLY の未使用トークン警告は Ruby 版に無いため抑止する
class _NullLogger(object):
    def debug(self, *args, **kwargs):
        pass

    info = debug
    warning = debug
    error = debug


parser = yacc.yacc(write_tables=False, debug=False, errorlog=_NullLogger())



def _generator_do_parse(self):
    self._ply_lookahead_tok = None

    def tokenfunc():
        t = self.next_token()
        if t[0] is None:
            self._ply_lookahead_tok = None
            return None
        tok = type("LexToken", (), {})()
        lex_type = t[0]
        tok.type = _LEXER_MULTI_TO_PLY.get(lex_type, lex_type)
        tok.value = t[1]
        loc = t[1].locale() if hasattr(t[1], "locale") else (None, 0, 0)
        tok.lineno = loc[1] if loc else 0
        tok.lexpos = loc[2] if loc else 0
        # PLY が typedef 還元前に先読みした IDENTIFIER を、後から TYPE_NAME へ昇格できるよう保持
        self._ply_lookahead_tok = tok
        return tok

    return parser.parse(lexer=self, tokenfunc=tokenfunc)


Generator.do_parse = _generator_do_parse


def upgrade_lookahead_typename(name):
    """typedef 登録直後、PLY lookahead が同名 IDENTIFIER なら TYPE_NAME に直す。"""
    gen = Generator.current()
    if gen is None:
        return
    tok = getattr(gen, "_ply_lookahead_tok", None)
    if tok is None or tok.type != "IDENTIFIER":
        return
    val = tok.value.val if hasattr(tok.value, "val") else tok.value
    if str(val) == str(name):
        tok.type = "TYPE_NAME"


__all__ = [
    "Generator",
    "Token",
    "TECSIO",
    "Include",
    "parser",
    "upgrade_lookahead_typename",
]
