# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/bnf.y.rb の inner / footer 部を
#   Python へ移植したものである．文法 rule 節は bnf.py 結合時に追加する．
#   ライセンスは tecsgen.py の冒頭を参照のこと．

import pprint
import re
import sys
from collections import defaultdict

from tecslib.core import globals as G
from tecslib.core.messages import TECSMsg
from tecslib.core.tecs_lang import Console
from tecslib.rubylib.symbol import Sym


# ファイル => INCLUDE("header")の配列
Include = defaultdict(list)


class Generator:
    # ---- inner (RESERVED / RESERVED2 および Generator 本体) ----

    RESERVED = {
        # keyword
        'namespace': "NAMESPACE",
        'signature': "SIGNATURE",
        'celltype': "CELLTYPE",
        'cell': "CELL",
        'attr': "ATTRIBUTE",
        'var': "VAR",
        'call': "CALL",
        'entry': "ENTRY",
        'composite': "COMPOSITE",
        'require': "REQUIRE",
        'factory': "FACTORY",
        'FACTORY': "CTFACTORY",
        'typedef': "TYPEDEF",
        'struct': "STRUCT",
        'region': "REGION",
        'import': "IMPORT",
        'import_C': "IMPORT_C",
        'generate': "GENERATE",
        '__tool_info__': "TOOL_INFO",

        # types
        'void': "VOID",

        'volatile': "VOLATILE",
        'const': "CONST",

        'signed': "SIGNED",
        'unsigned': "UNSIGNED",

        'int8_t': "INT8_T",
        'int16_t': "INT16_T",
        'int32_t': "INT32_T",
        'int64_t': "INT64_T",
        'int128_t': "INT128_T",
        'uint8_t': "UINT8_T",
        'uint16_t': "UINT16_T",
        'uint32_t': "UINT32_T",
        'uint64_t': "UINT64_T",
        'uint128_t': "UINT128_T",

        'float32_t': "FLOAT32_T",
        'double64_t': "DOUBLE64_T",
        'bool_t': "BOOL_T",
        'char_t': "CHAR_T",
        'schar_t': "SCHAR_T",
        'uchar_t': "UCHAR_T",

        # unrecommened types
        'int': "INT",
#   'intptr'  => :INTPTR,
        'short': "SHORT",
        'long': "LONG",

        # obsolete types
        'char': "CHAR",
#    'int8'    => :INT8,
#    'int16'   => :INT16,
#    'int32'   => :INT32,
#    'int64'   => :INT64,
#    'int128'  => :INT128,
#    'float'   => :FLOAT,
#    'double'  => :DOUBLE,
#    'bool'    => :BOOL,

        'enum': "ENUM",
        'enum8': "ENUM8",
        'enum16': "ENUM16",
        'enum32': "ENUM32",
        'enum64': "ENUM64",

        'true': "TRUE",
        'false': "FALSE",

        'C_EXP': "C_EXP",

        'Descriptor': "DESCRIPTOR",
    }

    # 指定子 '[]' 内でのみ使用できるキーワード
    RESERVED2 = {
        # specifier
        'id': "ID",

        # signature
        'callback': "CALLBACK",
        'context': "CONTEXT",
        'deviate': "DEVIATE",

        # celltype
        'singleton': "SINGLETON",
        'idx_is_id': "IDX_IS_ID",
        'active': "ACTIVE",
        'pseudo_active': "PSEUDO_ACTIVE",

        # port (entry)
        'inline': "INLINE",
        'ref_desc': "REF_DESC",   # call も可

        # port (call)
        'optional': "OPTIONAL",
        'dynamic': "DYNAMIC",

        # port (call), attribute
        'omit': "OMIT",

        # attribute
        'choice': "CHOICE",

        # cell
        'allocator': "ALLOCATOR",
        'prototype': "PROTOTYPE",
        'restrict': "RESTRICT",

        # FuncType
        'oneway': "ONEWAY",

        # parameter (basic)
        'in': "IN",
        'out': "OUT",
        'inout': "INOUT",
        'send': "SEND",
        'receive': "RECEIVE",

        # parameter
        'size_is': "SIZE_IS",
        'count_is': "COUNT_IS",
        'string': "STRING",
        'nullable': "NULLABLE",

        'through': "THROUGH",
        'in_through': "IN_THROUGH",
        'out_through': "OUT_THROUGH",
        'to_through': "TO_THROUGH",
        'from_through': "FROM_THROUGH",

        'node': "NODE",
        'linkunit': "LINKUNIT",
        'domain': "DOMAIN",
        'class': "CLASS",
    }

    # 再帰的なパーサのためのスタック
    generator_nest = -1
    generator_stack = []
    locale_stack = []

    # import_C 中である
    import_C = False

    # すべての構文解析が完了した
    b_end_all_parse = False

    # tag なし struct
    no_struct_tag_num = 0

    n_error = 0
    n_warning = 0
    n_info = 0

    statement_specifier_stack = []

    def __init__(self, plugin=None, b_reuse=False):
        self.plugin = plugin
        self.b_reuse = b_reuse
        self.q = []
        self.in_specifier = False
        # PLY は unit 規則 spec_L:'[' の還元前に lookahead を読む。
        # 直前トークンが '[' なら RESERVED2 を有効化する（racc との差の吸収）。
        self._prev_was_lbrack = False

    def finalize(self):
        from tecslib.core.componentobj.cell import Cell
        from tecslib.core.componentobj.celltype import Celltype
        from tecslib.core.componentobj.compositecelltype import CompositeCelltype
        from tecslib.core.componentobj.namespace import Namespace
        from tecslib.core.componentobj.signature import Signature

        # mikan Namespace.pop
        Namespace.pop()
        Signature.pop()
        Celltype.pop()
        Cell.pop()
        CompositeCelltype.pop()

    def set_plugin(self, plugin):
        self.plugin = plugin

    @classmethod
    def get_plugin(cls):
        if cls.generator_nest >= 0 and cls.generator_stack[cls.generator_nest]:
            # tecsgen 引数の cdl が import される場合は nil
            return cls.generator_stack[cls.generator_nest].get_plugin_inst()
        else:
            return None

    def get_plugin_inst(self):
        return self.plugin

    def set_reuse(self, b_reuse):
        self.b_reuse = b_reuse

    @classmethod
    def is_reuse(cls):
        if cls.generator_nest >= 0 and cls.generator_stack[cls.generator_nest]:
            # tecsgen 引数の cdl が import される場合は nil
            return cls.generator_stack[cls.generator_nest].is_reuse_inst()
        else:
            return False

    def is_reuse_inst(self):
        return self.b_reuse

    def parse(self, files):
        self._parse_inst(files)

    def _parse_inst(self, files):
        from tecslib.core.componentobj.cell import Cell
        from tecslib.core.componentobj.celltype import Celltype
        from tecslib.core.componentobj.compositecelltype import CompositeCelltype
        from tecslib.core.componentobj.namespace import Namespace
        from tecslib.core.componentobj.signature import Signature

        # mikan Namespace.push
        Namespace.push()
        Signature.push()
        Celltype.push()
        Cell.push()
        CompositeCelltype.push()

        Generator.generator_nest += 1
        Generator.generator_stack.append(None)
        Generator.generator_stack[Generator.generator_nest] = self
        self.in_specifier = False
        self._prev_was_lbrack = False
        # PLY 先読みで current_locale が 1 トークン先になる差を吸収（racc default reduce 相当）
        self._last_token_locale = None

        try:

            self.q = []
            b_in_comment = False
            b_in_comment2 = False
            b_in_string = False

            for file in files:
                lineno = 1
                try:
                    string = ""
#2.0      IO.foreach(file) {|line|
                    for line in TECSIO.foreach(file):
                        col = 1
#        line.rstrip!     改行含む文字列を扱うようになったので、ここで空白を取り除けなくなった

                        while line:

                            if b_in_comment or b_in_comment2:
                                if re.match(r'\A\*/', line):
                                    # コメント終了
                                    if b_in_comment:
                                        b_in_comment = False
                                    m = re.match(r'\A\*/', line)
                                    line = line[m.end():]
                                    col += len(m.group(0))
                                elif re.match(r'\A---\+', line):
                                    if b_in_comment2:
                                        b_in_comment2 = False
                                    m = re.match(r'\A---\+', line)
                                    line = line[m.end():]
                                    col += len(m.group(0))
                                elif re.match(r'\A.', line):
                                    m = re.match(r'\A.', line)
                                    line = line[m.end():]
                                    col += len(m.group(0))
                                elif re.match(r'\s+', line):
                                    # line.rstrip! を止めたため \n などの空白文字とまっちするルールが必要になった
                                    m = re.match(r'\s+', line)
                                    line = line[m.end():]
                                    col += len(m.group(0))
                                else:
                                    raise RuntimeError("lexer: unmatched in comment")
                            elif b_in_string:
                                m = re.match(r'\A(?:[^"\\]|\\.)*"', line)
                                if m:
                                    string = "{}{}".format(string, m.group(0))
                                    self.q.append(["STRING_LITERAL", Token(string, file, lineno, col)])
                                    b_in_string = False
                                    line = line[m.end():]
                                    col += len(m.group(0))
                                elif re.match(r'\A.*\\\n', line):
                                    m = re.match(r'\A.*\\\n', line)
                                    string += m.group(0)
                                    line = line[m.end():]
                                    col += len(m.group(0))
                                elif re.match(r'\A.*\n', line):
                                    m = re.match(r'\A.*\n', line)
                                    string += line
                                    # この位置では error メソッドは使えない (token 読出し前)
                                    print("{}:{}:{}: error: string literal has newline without escape".format(
                                        file, lineno, col))
                                    Generator.n_error += 1
                                    line = ""
                                else:
                                    raise RuntimeError("lexer: unmatched in string")
                            else:
                                matched = False
                                m = re.match(r'\A\s+', line)
                                if m:
                                    # 空白、プリプロセスディレクティブ
                                    matched = True
                                else:
                                    m = re.match(r'\A[a-zA-Z_]\w*', line)
                                    if m:
                                        # 識別子
                                        word = m.group(0)
                                        tok_type = Generator.RESERVED.get(word, "IDENTIFIER")
                                        self.q.append([tok_type, Token(Sym(word), file, lineno, col)])
                                        matched = True
                                    else:
                                        m = re.match(r'\A0x[0-9A-Fa-f]+', line)
                                        if m:
                                            # 16 進数定数
                                            self.q.append(["HEX_CONSTANT", Token(m.group(0), file, lineno, col)])
                                            matched = True
                                        else:
                                            m = re.match(r'\A0[0-7]+', line)
                                            if m:
                                                # 8 進数定数
                                                self.q.append(["OCTAL_CONSTANT", Token(m.group(0), file, lineno, col)])
                                                matched = True
                                            else:
                                                m = re.match(r'\A[0-9]+\.([0-9]*)?([Ee][+-]?[0-9]+)?', line)
                                                if m:
                                                    # 浮動小数定数
                                                    self.q.append(["FLOATING_CONSTANT", Token(m.group(0), file, lineno, col)])
                                                    matched = True
                                                else:
                                                    m = re.match(r'\A\d+', line)
                                                    if m:
                                                        # 整数定数
                                                        self.q.append(["INTEGER_CONSTANT", Token(int(m.group(0)), file, lineno, col)])
                                                        matched = True
                                                    else:
                                                        m = re.match(r"\A'(?:[^'\\]|\\.)'", line)
                                                        if m:
                                                            # 文字定数
                                                            self.q.append(["CHARACTER_LITERAL", Token(m.group(0), file, lineno, col)])
                                                            matched = True
                                                        else:
                                                            m = re.match(r'\A"(?:[^"\\]|\\.)*"', line)
                                                            if m:
                                                                # 文字列
#        "#include  #include #include \"../systask/logtask.cfg\"       最後の " 忘れ)で無限ループ
#        when /\A"(?:[^"\\]+|\\.)*"/
                                                                self.q.append(["STRING_LITERAL", Token(m.group(0), file, lineno, col)])
                                                                matched = True
                                                            else:
                                                                m = re.match(r'\A"(?:[^"\\]|\\.)*\\\n$', line)
                                                                if m:
                                                                    # 文字列 (改行あり)
                                                                    string = m.group(0)
                                                                    b_in_string = True
                                                                    matched = True
                                                                else:
                                                                    m = re.match(r'\A("(?:[^"\\]|\x1b.)*)\n$', line)
                                                                    if m:
                                                                        # 文字列 (改行あり, escape なし)
                                                                        string = m.group(1) + "\\\n"
                                                                        b_in_string = True
                                                                        # この位置では error メソッドは使えない (token 読出し前) # mikan cdl_error ではない
                                                                        print("{}:{}:{}: error: string literal has newline without escape".format(
                                                                            file, lineno, col))
                                                                        Generator.n_error += 1
                                                                        matched = True
                                                                    else:
                                                                        m = re.match(r'\A<(?:[^>\\]|\\.)*>', line)
                                                                        if m:
                                                                            # 山括弧で囲まれた文字列
                                                                            # when /\A<[0-9A-Za-z_\. \/]+>/   # AB: angle bracke
                                                                            self.q.append(["AB_STRING_LITERAL", Token(m.group(0), file, lineno, col)])
                                                                            matched = True
                                                                        else:
                                                                            m = re.match(r'\A//.*$', line)
                                                                            if m:
                                                                                # 行コメント
                                                                                # 読み飛ばすだけ
                                                                                matched = True
                                                                            else:
                                                                                m = re.match(r'\A/\*', line)
                                                                                if m:
                                                                                    # コメント開始
                                                                                    b_in_comment = True
                                                                                    matched = True
                                                                                else:
                                                                                    m = re.match(r'^\+\-\-\-', line)
                                                                                    if m:
                                                                                        b_in_comment2 = True
                                                                                        matched = True
                                                                                    else:
                                                                                        for pat in (r'\A>>', r'\A<<', r'\A==', r'\A!=', r'\A&&', r'\A\|\|'):
                                                                                            m = re.match(pat, line)
                                                                                            if m:
                                                                                                # '>>', '<<' など
                                                                                                lex = m.group(0)
                                                                                                self.q.append([lex, Token(lex, file, lineno, col)])
                                                                                                matched = True
                                                                                                break
                                                                                        if not matched:
                                                                                            for pat in (r'\A::', r'\A=>', r'\A<=', r'\A>='):
                                                                                                m = re.match(pat, line)
                                                                                                if m:
                                                                                                    lex = m.group(0)
                                                                                                    self.q.append([lex, Token(lex, file, lineno, col)])
                                                                                                    matched = True
                                                                                                    break
                                                                                        if not matched:
                                                                                            m = re.match(r'\A.', line)
                                                                                            if m:
                                                                                                # '(', ')' など一文字の記号、または未知の記号
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
                    Generator.error("G1014 while open or reading '$1'", file)
                    if G.debug:
                        pprint.pprint(evar)
                        pprint.pprint(sys.exc_info()[2])

            # 終了の印
            self.q.append(None)

            self.yydebug = True
            self.do_parse()

        finally:
            Generator.generator_nest -= 1
            if Generator.generator_stack:
                Generator.generator_stack.pop()

    def next_token(self):
        if not self.q:
            token = None
        else:
            token = self.q.pop(0)

        if token:
            while len(Generator.locale_stack) <= Generator.generator_nest:
                Generator.locale_stack.append(None)
            # 先読みトークンではなく、直前に返したトークンの位置を current_locale にする
            if self._last_token_locale is not None:
                Generator.locale_stack[Generator.generator_nest] = self._last_token_locale
            else:
                Generator.locale_stack[Generator.generator_nest] = token[1].locale()
            self._last_token_locale = token[1].locale()

            if token[0] == "IDENTIFIER":
                from tecslib.core.componentobj.namespace import Namespace
                # TYPE_NAME トークンへ置換え
                if Namespace.is_typename(token[1].val):
                    token[0] = "TYPE_NAME"
                else:
                    reserved2 = Generator.RESERVED2.get(str(token[1].val))
                    if reserved2 and (self.in_specifier or self._prev_was_lbrack):
                        # 指定子キーワード（ '[', ']' 内でのみ有効)
                        # _prev_was_lbrack: PLY が spec_L 還元前に lookahead する対策
                        token[0] = reserved2
                        self.in_specifier = True

            if token[0] == "]":
                self.in_specifier = False

            self._prev_was_lbrack = (token[0] == "[")

            if G.debug:     # 070107 token 無効時ここを通さないようした (through 対応 -d の時に例外発生)
                locale = Generator.locale_stack[Generator.generator_nest]
                if token:
                    print("{}: line {} : {} '{}'".format(
                        locale[0], locale[1], token[0], token[1].val))
                else:
                    print("{}: line {} : EOF".format(locale[0], locale[1]))
        else:
            token = (None, None)

        return token

    def on_error(self, t, v, vstack):
        # p t, token_to_str(t), vstack
        if self.token_to_str(t) == "$end":
            Generator.error("G1015 Unexpected EOF")
        else:
            Generator.error("G1016 syntax error near '$1'", v.val)

    @classmethod
    def set_locale_from_token(cls, tok):
        """PLY 先読みでずれた current_locale を、還元 RHS のトークン位置に戻す。"""
        if tok is None or not hasattr(tok, "locale"):
            return
        while len(cls.locale_stack) <= cls.generator_nest:
            cls.locale_stack.append(None)
        cls.locale_stack[cls.generator_nest] = tok.locale()

    def token_to_str(self, t):
        if t is None:
            return "$end"
        return str(t)

    def do_parse(self):
        # bnf.py 結合時に PLY/yacc パーサ実装で置き換える
        raise NotImplementedError("do_parse は bnf.py 結合時に定義される")

    @classmethod
    def current(cls):
        if cls.generator_nest >= 0:
            return cls.generator_stack[cls.generator_nest]
        return None

    @classmethod
    def current_locale(cls):
        if cls.generator_nest < 0 or cls.generator_nest >= len(cls.locale_stack):
            return None
        return cls.locale_stack[cls.generator_nest]

    # このメソッドは構文解析、意味解析からのみ呼出し可（コード生成でエラー発生は不適切）
    @classmethod
    def error(cls, msg, *arg):
        locale = None
        cls.error2(locale, msg, *arg)

    @classmethod
    def error2(cls, locale, msg, *arg):
        cls.n_error += 1

        msg = TECSMsg.get_error_message(msg)
        # $1, $2, ... を arg で置換
        count = 1
        for a in arg:
            str_a = TECSIO.str_code_convert(msg, str(a))
            msg = re.sub(r'\${}'.format(count), str_a, msg, count=1)
            count += 1

        # import_C の中でのエラー？
        if Generator.import_C:
            from tecslib.core.c_parser import C_parser
            # C_parser.error( msg )
            locale = C_parser.current_locale()
        else:

            # Node の記憶する 位置 (locale) を使用した場合、変更以前に比べ、
            # 問題発生箇所と異なる位置にエラーが出るため、構文解析中のエラー
            # は、解析中の位置を出力する．(new_XXX で owner が子要素のチェッ
            # クをすると owner の行番号が出てしまう点で、ずれが生じている)

            if Generator.b_end_all_parse == False or locale is None:
                locale = Generator.current_locale()
        if locale:
            Console.puts("{}:{}:{}: error: {}".format(locale[0], locale[1], locale[2], msg))
        else:
            Console.puts("error: {}".format(msg))

    # このメソッドは構文解析、意味解析からのみ呼出し可（コード生成でウォーニング発生は不適切）
    @classmethod
    def warning(cls, msg, *arg):
        locale = None
        cls.warning2(locale, msg, *arg)

    @classmethod
    def warning2(cls, locale, msg, *arg):
        cls.n_warning += 1

        msg = TECSMsg.get_warning_message(msg)
        # $1, $2, ... を arg で置換
        count = 1
        for a in arg:
            str_a = TECSIO.str_code_convert(msg, str(a))
            msg = re.sub(r'\${}'.format(count), str_a, msg, count=1)
            count += 1

        # import_C の中でのウォーニング？
        if Generator.import_C:
            from tecslib.core.c_parser import C_parser
            # C_parser.warning( msg )
            locale = C_parser.current_locale()
        else:
            if Generator.b_end_all_parse == False or locale is None:
                locale = Generator.current_locale()
        if locale:
            Console.puts("{}:{}:{}: warning: {}".format(locale[0], locale[1], locale[2], msg))
        else:
            Console.puts("warning: {}".format(msg))

    # このメソッドは構文解析、意味解析からのみ呼出し可
    @classmethod
    def info(cls, msg, *arg):
        locale = None
        cls.info2(locale, msg, *arg)

    @classmethod
    def info2(cls, locale, msg, *arg):
        cls.n_info += 1

        msg = TECSMsg.get_info_message(msg)
        # $1, $2, ... を arg で置換
        count = 1
        for a in arg:
            str_a = TECSIO.str_code_convert(msg, str(a))
            msg = re.sub(r'\${}'.format(count), str_a, msg, count=1)
            count += 1

        # import_C の中でのウォーニング？
        if Generator.import_C:
            from tecslib.core.c_parser import C_parser
            # C_parser.info( msg )
            locale = C_parser.current_locale()
        else:
            if Generator.b_end_all_parse == False or locale is None:
                locale = Generator.current_locale()
        if locale:
            Console.puts("{}:{}:{}: info: {}".format(locale[0], locale[1], locale[2], msg))
        else:
            Console.puts("info: {}".format(msg))

    @classmethod
    def get_n_error(cls):
        return cls.n_error

    @classmethod
    def get_n_warning(cls):
        return cls.n_warning

    @classmethod
    def get_n_info(cls):
        return cls.n_info

    @classmethod
    def get_nest(cls):
        return cls.generator_nest

    @classmethod
    def parsing_C(cls):
        return cls.import_C

    #===  '[' specifier 始め
    def set_in_specifier(self):
        # p "set_in_specifier"
        self.in_specifier = True

    #=== ']' specifier 終わり
    def unset_in_specifier(self):
        # p "unset_in_specifier"
        self.in_specifier = False

    # statement_specifier は構文解釈途中で参照したいため
    @classmethod
    def add_statement_specifier(cls, ss):
        while len(cls.statement_specifier_stack) <= cls.generator_nest:
            cls.statement_specifier_stack.append(None)
        if cls.statement_specifier_stack[cls.generator_nest] is None:
            cls.statement_specifier_stack[cls.generator_nest] = [ss]
        else:
            cls.statement_specifier_stack[cls.generator_nest].append(ss)

    @classmethod
    def get_statement_specifier(cls):
        while len(cls.statement_specifier_stack) <= cls.generator_nest:
            cls.statement_specifier_stack.append(None)
        spec_list = cls.statement_specifier_stack[cls.generator_nest]
        cls.statement_specifier_stack[cls.generator_nest] = None
        return spec_list

    #=== すべての構文解析が完了したことを報告
    @classmethod
    def end_all_parse(cls):
        cls.b_end_all_parse = True

    @classmethod
    def parse_class(cls, file_name, plugin=None, b_reuse=False):
        # Ruby: def self.parse  (Python ではインスタンス parse と同名衝突のため parse_class)
        # パーサインスタンスを生成(別パーサで読み込む)
        parser = Generator()

        # plugin から import されている場合の plugin 設定
        parser.set_plugin(plugin)

        # reuse フラグを設定
        parser.set_reuse(b_reuse)

        # cdl をパース
        parser._parse_inst([file_name])

        # 終期化　パーサスタックを戻す
        parser.finalize()


class Token:

    def __init__(self, val, file, lineno, col):
        self.val = val
        self.file = file
        self.lineno = lineno
        self.col = col

    def to_s(self):
        return str(self.val)

    def __str__(self):
        return self.to_s()

    def to_sym(self):
        if isinstance(self.val, Sym):
            return self.val
        return Sym(str(self.val))

    def get_name(self):
        return self.val

    def locale(self):
        return [self.file, self.lineno, self.col]

    def eql(self, other):
        if isinstance(other, Sym):
            return self.val == other
        elif type(other) is Token:
            return self.val == other.val
        elif isinstance(other, str):
            return str(self.val) == other
        else:
            raise TypeError

    __eq__ = eql

    def show_tree(self, indent):
        print("  " * indent, end="")
        print("{}".format(self.val))


#= TECSIO
#  Ruby2.0(1.9) 対応に伴い導入したクラス
#  SJIS 以外では、ASCII-8BIT として入力する
class TECSIO:

    @staticmethod
    def foreach(file):
        # obsolete Ruby 3.0 では使えなくなった
        # pr = Proc.new   # このメソッドのブロック引数を pr に代入

        msg = "E"
        enc = G.Ruby19_File_Encode
        if enc == "Shift_JIS":

            # Shift JIS は、いったん Windows-31J として読み込ませ、Shift_JIS に変換させる．
            # コメント等に含まれる SJIS に不適切な文字コードは '?' または REPLACEMENT CHARACTER に変換される．
            # EUC や UTF-8 で記述された CDL が混在していても、Ruby 例外が発生することなく処理を進めることができる．
            # 文字コード指定が SJIS であって、文字列リテラルの中に、文字コードがSJIS 以外の非 ASCII が含まれている場合、
            # Ruby 1.8 の tecsgen では文字コード指定に影響なく処理されたものが、Ruby 1.9 以降では '?' に置き換わる可能性がある．

            open_enc = "cp932"
        elif enc == "ASCII-8BIT":
            open_enc = "latin-1"
        else:
            open_enc = enc

        f = open(file, "r", encoding=open_enc, errors="replace")
        try:
            for line in f:
                # dbgPrint line
                line = TECSIO.str_code_convert(msg, line)
                yield line
        finally:
            f.close()

    #=== 文字コードが相違する場合一致させる
    # msg と str の文字コードが相違する場合、str を msg の文字コードに変換する
    # 変換不可の文字コードは '?' (utf-8 の場合 U+FFFD (REPLACEMENT CHARACTER )) に変換
    #
    # このメソッドは、エラーメッセージ出力でも使用されていることに注意．
    #
    #msg_enc::Encode | String
    @staticmethod
    def str_code_convert(msg, str_):
        s = str_ if isinstance(str_, str) else str(str_)
        enc = G.Ruby19_File_Encode
        if enc == "ASCII-8BIT" or enc == "UTF-8":
            return s
        try:
            return s.encode(enc, errors="replace").decode(enc)
        except (LookupError, UnicodeError):
            return s
