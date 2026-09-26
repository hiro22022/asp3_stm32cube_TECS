# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#  C_parser.y.rb の inner / footer 部（字句解析・C_parser 本体）．
#  文法 rule 節は c_parser.py 結合時に追加する．
#  ライセンスは tecsgen.py の冒頭を参照のこと．

import re
import sys

from tecslib.core import globals as G
from tecslib.core._bnf_runtime import Generator, TECSIO, Token
from tecslib.core.toplevel import print_exception
from tecslib.rubylib.symbol import Sym


class C_parser:
    # ---- inner (RESERVED および C_parser 本体) ----

    RESERVED = {
        # keyword
        'typedef': "TYPEDEF",
        'struct': "STRUCT",
        'union': "UNION",
        'sizeof': "SIZEOF",
        '__typeof__': "TYPEOF",
        'typeof': "TYPEOF",
        'throw': "THROW",

        # specifier / types
        'void': "VOID",
        'char': "CHAR",
        'short': "SHORT",

        'volatile': "VOLATILE",
        'const': "CONST",
        'extern': "EXTERN",

        'long': "LONG",
        'float': "FLOAT",
        'double': "DOUBLE",
        'signed': "SIGNED",
        'unsigned': "UNSIGNED",

        'int': "INT",
        'enum': "ENUM",

        'if': "IF",
        'else': "ELSE",
        'while': "WHILE",
        'do': "DO",
        'for': "FOR",
        'case': "CASE",
        'default': "DEFAULT",
        'goto': "GOTO",
        'continue': "CONTINUE",
        'break': "BREAK",
        'return': "RETURN",
        '__inline__': "__INLINE__",
        'inline': "INLINE",
        '__inline': "__INLINE",
        'Inline': "CINLINE",
        'static': "STATIC",
        'register': "REGISTER",
        'auto': "AUTO",
        '__extension__': "EXTENSION",
        '__asm__': "_ASM",

        '__int64': "INT64",
        '_Bool': "BOOL",
    }

    generator_nest = -1
    generator_stack = []
    locale_stack = []

    def __init__(self, plugin=None):
        self.plugin = plugin
        self.q = []
        self.b_no_type_name = False
        self.in_typedef_struct = False
        self.count = 0
        self.prev_block_end = True
        self._prev_token_val = None
        self.yydebug = False

    def finalize(self):
        from tecslib.core.componentobj.cell import Cell
        from tecslib.core.componentobj.celltype import Celltype
        from tecslib.core.componentobj.compositecelltype import CompositeCelltype
        from tecslib.core.componentobj.region import Region

        Celltype.pop()
        Cell.pop()
        CompositeCelltype.pop()
        Region.pop()

    def set_plugin(self, plugin):
        self.plugin = plugin

    @classmethod
    def get_plugin(cls):
        if cls.generator_nest >= 0 and cls.generator_stack[cls.generator_nest]:
            return cls.generator_stack[cls.generator_nest].get_plugin_inst()
        return None

    def get_plugin_inst(self):
        return self.plugin

    def parse(self, files):
        from tecslib.core.componentobj.cell import Cell
        from tecslib.core.componentobj.celltype import Celltype
        from tecslib.core.componentobj.compositecelltype import CompositeCelltype
        from tecslib.core.componentobj.region import Region

        Celltype.push()
        Cell.push()
        CompositeCelltype.push()
        Region.push()

        C_parser.generator_nest += 1
        while len(C_parser.generator_stack) <= C_parser.generator_nest:
            C_parser.generator_stack.append(None)
        C_parser.generator_stack[C_parser.generator_nest] = self
        self.b_no_type_name = False

        try:
            self.q = []
            self.in_typedef_struct = False
            self.count = 0
            self.prev_block_end = True
            self._prev_token_val = None
            # PLY 先読みで current_locale が 1 トークン先になる差を吸収（racc default reduce 相当）
            self._last_token_locale = None

            integer_qualifier = r"([Uu][Ll][Ll]|[Uu][Ll]|[Uu]|[Ll][Ll]|[Ll])?"

            for file in files:
                lineno = 1
                in_comment = False
                try:
                    for line in TECSIO.foreach(file):
                        col = 1
                        line = line.rstrip("\n\r")

                        while line:
                            if in_comment:
                                m = re.match(r'\A\*/', line)
                                if m:
                                    in_comment = False
                                    line = line[m.end():]
                                    col += len(m.group(0))
                                    continue
                                m = re.match(r'\A.', line)
                                if m:
                                    line = line[m.end():]
                                    col += len(m.group(0))
                                    continue
                                break

                            matched = False
                            m = re.match(r'\A\s+', line)
                            if m:
                                matched = True
                            else:
                                m = re.match(r'\A[a-zA-Z_]\w*', line)
                                if m:
                                    word = m.group(0)
                                    tok_type = C_parser.RESERVED.get(word, "IDENTIFIER")
                                    self.q.append([tok_type, Token(Sym(word), file, lineno, col)])
                                    matched = True
                                else:
                                    m = re.match(r'\A0x[0-9A-Fa-f]+' + integer_qualifier, line)
                                    if m:
                                        self.q.append(["HEX_CONSTANT", Token(m.group(0), file, lineno, col)])
                                        matched = True
                                    else:
                                        m = re.match(r'\A0[0-7]+' + integer_qualifier, line)
                                        if m:
                                            self.q.append(["OCTAL_CONSTANT", Token(m.group(0), file, lineno, col)])
                                            matched = True
                                        else:
                                            m = re.match(r'\A[0-9]+\.([0-9]*)?([Ee][+-]?[0-9]+)?', line)
                                            if m:
                                                self.q.append(["FLOATING_CONSTANT", Token(m.group(0), file, lineno, col)])
                                                matched = True
                                            else:
                                                m = re.match(r'\A\d+' + integer_qualifier, line)
                                                if m:
                                                    val = m.group(0)
                                                    try:
                                                        ival = int(re.sub(integer_qualifier + r'\Z', '', val))
                                                    except ValueError:
                                                        ival = int(val)
                                                    self.q.append(["INTEGER_CONSTANT", Token(ival, file, lineno, col)])
                                                    matched = True
                                                else:
                                                    m = re.match(r"\A'(?:[^'\\]|\\.)'", line)
                                                    if m:
                                                        self.q.append(["CHARACTER_LITERAL", Token(m.group(0), file, lineno, col)])
                                                        matched = True
                                                    else:
                                                        m = re.match(r'\A"(?:[^"\\]|\\.)*"', line)
                                                        if m:
                                                            self.q.append(["STRING_LITERAL", Token(m.group(0), file, lineno, col)])
                                                            matched = True
                                                        else:
                                                            m = re.match(r'\A//.*$', line)
                                                            if m:
                                                                matched = True
                                                            else:
                                                                m = re.match(r'\A/\*', line)
                                                                if m:
                                                                    in_comment = True
                                                                    matched = True
                                                                else:
                                                                    for pat in (
                                                                        r'\A>>=', r'\A<<=', r'\A>>', r'\A<<',
                                                                        r'\A\+=', r'\A\-=', r'\A\*=', r'\A/=',
                                                                        r'\A%=', r'\A&=', r'\A\|=', r'\A\^=',
                                                                        r'\A::', r'\A==', r'\A!=', r'\A>=', r'\A<=',
                                                                        r'\A\->', r'\A\+\+', r'\A\-\-',
                                                                        r'\A\|\|', r'\A&&',
                                                                    ):
                                                                        m = re.match(pat, line)
                                                                        if m:
                                                                            lex = m.group(0)
                                                                            self.q.append([lex, Token(lex, file, lineno, col)])
                                                                            matched = True
                                                                            break
                                                                    if not matched:
                                                                        m = re.match(r'\A.', line)
                                                                        if m:
                                                                            lex = m.group(0)
                                                                            self.q.append([lex, Token(lex, file, lineno, col)])
                                                                            matched = True
                                                                        else:
                                                                            raise RuntimeError("lexer: no match")

                            if matched and m:
                                line = line[m.end():]
                                col += len(m.group(0))

                        lineno += 1

                except Exception as evar:
                    Generator.error("B1002 while open or reading '$1'", file)
                    print_exception(evar)

            self.q.append(None)
            self.yydebug = True
            self.do_parse()

        finally:
            C_parser.generator_nest -= 1
            if C_parser.generator_stack:
                C_parser.generator_stack.pop()

    def next_token(self):
        if not self.q:
            token = None
        else:
            token = self.q.pop(0)

        if self.in_typedef_struct:
            self.prev_block_end = False
            if token and token[0] == '{':
                self.count += 1
            elif token and token[0] == '}':
                self.count -= 1
            elif token and token[0] == ';' and self.count == 0:
                self.in_typedef_struct = False
                self.prev_block_end = True
        else:
            while token:
                if (token[0] == "TYPEDEF" or token[0] == "STRUCT") and self.prev_block_end:
                    self.in_typedef_struct = True
                    self.prev_block_end = False
                    break
                if token[0] == ';' or token[0] == '}':
                    self.prev_block_end = True
                else:
                    self.prev_block_end = False
                if not self.q:
                    token = None
                    break
                token = self.q.pop(0)

        if token:
            while len(C_parser.locale_stack) <= C_parser.generator_nest:
                C_parser.locale_stack.append(None)
            if self._last_token_locale is not None:
                C_parser.locale_stack[C_parser.generator_nest] = self._last_token_locale
            else:
                C_parser.locale_stack[C_parser.generator_nest] = token[1].locale()
            self._last_token_locale = token[1].locale()

            # struct/union 本体内でメンバ宣言が始まる位置（'{' または前メンバの ';' の直後）は
            # 型名を TYPE_NAME 化する。struct_tag 還元が PLY lookahead 後に no_tn=True を
            # 立て直すため、ここで打ち消す（racc との差の吸収）。
            if (self.in_typedef_struct and self.count > 0
                    and self._prev_token_val in ("{", ";")):
                self.set_no_type_name(False)

            if token[1].val in (";", ":", ",", "(", ")", "{", "}"):
                # '}' で最外の struct/union が閉じた直後は declarator 名が続く。
                # PLY は還元前に lookahead するため、ここで no_type_name を立てて TYPE_NAME 化を抑止する。
                if (token[1].val == "}" and self.in_typedef_struct and self.count == 0):
                    self.set_no_type_name(True)
                else:
                    self.set_no_type_name(False)
            elif token[1].val in (".", "->"):
                self.set_no_type_name(True)

            if not self.b_no_type_name:
                if token[0] == "IDENTIFIER":
                    from tecslib.core.componentobj.namespace import Namespace
                    if Namespace.is_typename(token[1].val):
                        token[0] = "TYPE_NAME"
                        # type_specifier 還元前に次トークンを読む PLY 向け:
                        # 型名の直後は declarator なので TYPE_NAME 化を抑止する
                        self.set_no_type_name(True)

            # 組み込み型トークンも type_specifier 還元時の set_no_type_name(true) 相当。
            # PLY は INT 等の還元前に declarator 名を lookahead するため、ここで立てないと
            # 既登録 typedef 名（例: __pid_t）が TYPE_NAME 化され再 typedef が壊れる。
            if token[0] in (
                "VOID", "CHAR", "SHORT", "INT", "INT64", "LONG",
                "SIGNED", "UNSIGNED", "FLOAT", "DOUBLE", "BOOL",
                "STRUCT", "UNION", "ENUM",
            ):
                self.set_no_type_name(True)

            self._prev_token_val = token[1].val if hasattr(token[1], "val") else token[0]

            if G.debug:
                locale = C_parser.locale_stack[C_parser.generator_nest]
                if token:
                    print("{}: line {} : {} '{}'".format(
                        locale[0], locale[1], token[0], token[1].val))
                else:
                    print("{}: line {} : EOF".format(locale[0], locale[1]))
        else:
            token = (None, None)

        return token

    def on_error(self, t, v, vstack):
        if v == "$":
            Generator.error("B1003 Unexpected EOF")
        else:
            Generator.error("B1004 syntax error near '$1'", v.val)

    def do_parse(self):
        raise NotImplementedError("do_parse は c_parser.py 結合時に定義される")

    @classmethod
    def current(cls):
        if cls.generator_nest >= 0 and cls.generator_nest < len(cls.generator_stack):
            return cls.generator_stack[cls.generator_nest]
        return None

    @classmethod
    def current_locale(cls):
        if cls.generator_nest < 0 or cls.generator_nest >= len(cls.locale_stack):
            return None
        return cls.locale_stack[cls.generator_nest]

    @classmethod
    def get_nest(cls):
        return cls.generator_nest

    def set_no_type_name(self, b_no_type_name):
        self.b_no_type_name = b_no_type_name
