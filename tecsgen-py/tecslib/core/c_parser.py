# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#  C_parser.y.rb の rule 節 (_c_parser_rules_gen) と inner/footer (_c_parser_runtime) の結合．
#  ライセンスは tecsgen.py の冒頭を参照のこと．

import os
import re
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_VENDOR = os.path.join(_REPO_ROOT, "vendor")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

from ply import yacc  # noqa: E402

from tecslib.core._bnf_runtime import Generator, Token  # noqa: E402
from tecslib.core._c_parser_runtime import C_parser  # noqa: E402
from tecslib.core.componentobj.namespacepath import NamespacePath  # noqa: E402
from tecslib.core.ctypes import (  # noqa: E402
    CArrayType,
    CBoolType,
    CDefinedType,
    CEnumType,
    CFloatType,
    CFuncType,
    CIntType,
    CPtrType,
    CStructType,
    CVoidType,
)
from tecslib.core.expression import C_EXP, Expression  # noqa: E402
from tecslib.core.syntaxobj.decl import Decl  # noqa: E402
from tecslib.core.syntaxobj.typedef import Typedef  # noqa: E402
from tecslib.core.types import StructType  # noqa: E402

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
    "+=": "T_PLUSEQ",
    "-=": "T_MINUSEQ",
    "*=": "T_STAREQ",
    "/=": "T_SLASHEQ",
    "%=": "T_MODEQ",
    "&=": "T_AMPEQ",
    "|=": "T_PIPEEQ",
    "^=": "T_CARETEQ",
    "<<=": "T_LSHIFTEQ",
    ">>=": "T_RSHIFTEQ",
    "::": "T_COLCOL",
    "++": "T_INC",
    "--": "T_DEC",
}


def _fix_ply_docstring(doc):
    if not doc or ":" not in doc:
        return doc
    lhs, rhs = doc.split(":", 1)
    rhs = rhs.strip()
    if "空行" in rhs:
        return f"{lhs.strip()} : empty"
    for lex, alias in _LEXER_MULTI_TO_PLY.items():
        rhs = rhs.replace(f'"{lex}"', alias)
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

import tecslib.core._c_parser_rules_gen as _c_parser_rules_gen  # noqa: E402

_RULES_GLOBALS = {
    "re": re,
    "Generator": Generator,
    "C_parser": C_parser,
    "Token": Token,
    "Expression": Expression,
    "C_EXP": C_EXP,
    "Decl": Decl,
    "Typedef": Typedef,
    "NamespacePath": NamespacePath,
    "StructType": StructType,
    "CIntType": CIntType,
    "CVoidType": CVoidType,
    "CFloatType": CFloatType,
    "CBoolType": CBoolType,
    "CDefinedType": CDefinedType,
    "CEnumType": CEnumType,
    "CStructType": CStructType,
    "CFuncType": CFuncType,
    "CArrayType": CArrayType,
    "CPtrType": CPtrType,
    "isinstance": isinstance,
}
_c_parser_rules_gen.__dict__.update(_RULES_GLOBALS)

_patch_rule_docstrings(_c_parser_rules_gen)

tokens = sorted(
    _collect_rule_terminals(_c_parser_rules_gen)
    | set(C_parser.RESERVED.values())
    | set(_LEXER_MULTI_TO_PLY.values())
    | {"TYPE_NAME", "C_EXP", "_ASM", "EXTENSION", "SWITCH"}
)

from tecslib.core._c_parser_rules_gen import *  # noqa: F403, E402


def p_error(p):
    """構文エラー。statement:error があるため、PLY ではトークンを捨てないと無限ループする。"""
    cp = C_parser.current()
    if cp is None:
        return
    if p is None:
        cp.on_error(None, "$", None)
        return

    cp.on_error(p.type, p.value, None)

    tok = p
    while tok is not None and getattr(tok, "type", None) != ";":
        tok = parser.token()
    parser.errok()



parser = yacc.yacc(write_tables=False, debug=False, errorlog=type("L", (), {
    "debug": staticmethod(lambda *a, **k: None),
    "info": staticmethod(lambda *a, **k: None),
    "warning": staticmethod(lambda *a, **k: None),
    "error": staticmethod(lambda *a, **k: None),
})())

# PLY の set_defaulted_states は「アクション表のエントリが1個」のときだけ
# default reduce にする。typeof_skip / asm_skip は全 lookahead が同じ reduce でも
# エントリが複数あるため先読みしてしまう。racc（Ruby）は先読みしないので、
# next_token で (...)/; まで捨てる空規則が壊れる。対象状態だけ defaulted にする。
_SKIP_EMPTY_RULES = frozenset({"typeof_skip", "asm_skip"})
for _state, _actions in parser.action.items():
    _vals = set(_actions.values())
    if len(_vals) != 1:
        continue
    _v = next(iter(_vals))
    if _v >= 0:
        continue
    _prod = parser.productions[-_v]
    # 空規則は len==0 で falsy になるので is not None で判定する
    if _prod is not None and _prod.name in _SKIP_EMPTY_RULES:
        parser.defaulted_states[_state] = _v


def _c_parser_do_parse(self):
    def tokenfunc():
        t = self.next_token()
        if t[0] is None:
            return None
        tok = type("LexToken", (), {})()
        lex_type = t[0]
        tok.type = _LEXER_MULTI_TO_PLY.get(lex_type, lex_type)
        tok.value = t[1]
        loc = t[1].locale() if hasattr(t[1], "locale") else (None, 0, 0)
        tok.lineno = loc[1] if loc else 0
        tok.lexpos = loc[2] if loc else 0
        return tok

    return parser.parse(lexer=self, tokenfunc=tokenfunc)


C_parser.do_parse = _c_parser_do_parse

__all__ = ["C_parser", "parser"]
