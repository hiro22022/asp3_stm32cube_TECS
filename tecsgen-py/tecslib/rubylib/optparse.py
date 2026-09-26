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
#= Ruby の optparse (OptionParser) 互換シム
#
# tecsgen.rb は ARGV.options{|parser| ... } でオプションを解析しており，
# ヘルプの書式や短縮形の解決規則が Ruby 版と一致している必要がある．
# ここでは tecsgen が使用する範囲だけを Ruby と同じ挙動で実装する．
#
# Ruby 版と一致させている点
#   ・ヘルプの桁揃え (summary_indent = 4 文字, summary_width = 32 文字)
#   ・長いオプションの前方一致による短縮 (--def は --define に解決される)
#   ・未定義の短いオプションを長いオプション名で補完する
#     (-h は --h-suffix に解決され "missing argument: -h" となる)
#   ・エラー時は "#{$0}: #{message}" を stderr へ出力して解析を打ち切る

import sys

# OptionParser の既定値
SUMMARY_WIDTH = 32
SUMMARY_INDENT = "    "


class ParseError(Exception):
    """OptionParser::ParseError 相当"""

    REASON = "parse error"

    def __init__(self, arg):
        self.arg = arg
        super().__init__("{}: {}".format(self.REASON, arg))


class InvalidOption(ParseError):
    REASON = "invalid option"


class MissingArgument(ParseError):
    REASON = "missing argument"


class NeedlessArgument(ParseError):
    REASON = "needless argument"


class AmbiguousOption(ParseError):
    REASON = "ambiguous option"


class Switch:
    """オプション一つ分の定義"""

    def __init__(self, short, long_spec, desc, block):
        self.short = short          # "-D" | None
        self.long_spec = long_spec  # "--define=def" | "--dryrun" | None
        self.desc = desc
        self.block = block

        if long_spec and "=" in long_spec:
            long_name, self.arg_name = long_spec.split("=", 1)
            self.long = long_name[2:]
        else:
            self.arg_name = None
            self.long = long_spec[2:] if long_spec else None

    #=== ヘルプの左側 ("-D, --define=def" または "    --dryrun")
    def summary_left(self):
        if self.short:
            return "{}, {}".format(self.short, self.long_spec)
        # 短いオプションがない場合，その桁分 ("-X, ") を空白で埋める
        return "{}{}".format(" " * 4, self.long_spec)

    def call(self, val):
        if self.block is None:
            return
        if self.arg_name:
            self.block(val)
        else:
            self.block()


class OptionParser:
    def __init__(self, argv, program_name):
        self.argv = argv
        self.program_name = program_name
        self.banner = "Usage: {} [options]".format(program_name)
        self.version = None
        self.release = None
        self._switches = []
        self._short = {}
        self._long = {}
        self._pos = 0   # parse_bang が argv のどこまで消費したか

    #=== オプションを定義する
    # 引数は Ruby と同じく順不同の文字列で与える
    #   on('-D', '--define=def', 'desc'){|v| ... }
    #   on('--dryrun', 'desc'){ ... }
    def on(self, *args, block=None):
        short = None
        long_spec = None
        desc = ""
        for a in args:
            if a.startswith("--"):
                long_spec = a
            elif a.startswith("-") and len(a) == 2:
                short = a
            else:
                desc = a

        sw = Switch(short, long_spec, desc, block)
        self._switches.append(sw)
        if sw.short:
            self._short[sw.short] = sw
        if sw.long:
            self._long[sw.long] = sw
        return sw

    #=== ヘルプ文字列 (OptionParser#help 相当)
    def help(self):
        lines = [self.banner + "\n"]
        for sw in self._switches:
            left = sw.summary_left()
            if len(left) <= SUMMARY_WIDTH:
                lines.append(SUMMARY_INDENT + left.ljust(SUMMARY_WIDTH) + " " + sw.desc + "\n")
            else:
                lines.append(SUMMARY_INDENT + left + "\n")
                lines.append(SUMMARY_INDENT + " " * SUMMARY_WIDTH + " " + sw.desc + "\n")
        return "".join(lines)

    #=== 長いオプション名を前方一致で解決する
    #name:: str     : "--" を除いた名前
    #disp:: str     : エラーメッセージに出す表記
    def _complete_long(self, name, disp):
        sw = self._long.get(name)
        if sw:
            return sw
        cands = [k for k in self._long if k.startswith(name)]
        if len(cands) == 1:
            return self._long[cands[0]]
        if len(cands) == 0:
            raise InvalidOption(disp)
        raise AmbiguousOption(disp)

    #=== ARGV を破壊的に解析する (OptionParser#parse! 相当)
    # オプションを取り除き，残りの引数を argv に書き戻す
    # Ruby は argv を先頭から取り出しながら解析するため，途中でエラーになった場合は
    # そこまでの引数が argv から失われる．その挙動も合わせる．
    def parse_bang(self):
        argv = self.argv
        rest = []
        self._pos = 0
        try:
            self._parse_in_order(argv, rest)
        finally:
            argv[:] = rest + argv[self._pos:]
        return argv

    def _parse_in_order(self, argv, rest):
        while self._pos < len(argv):
            a = argv[self._pos]
            self._pos += 1

            if a == "--":
                rest.extend(argv[self._pos:])
                self._pos = len(argv)
                break

            if a.startswith("--") and len(a) > 2:
                body = a[2:]
                if "=" in body:
                    name, val = body.split("=", 1)
                else:
                    name, val = body, None

                # officious option: --help は定義されていなくても使える
                if name == "help" and "help" not in self._long:
                    sys.stdout.write(self.help())
                    sys.exit(0)

                sw = self._complete_long(name, "--" + name)
                if sw.arg_name:
                    if val is None:
                        if self._pos >= len(argv):
                            raise MissingArgument(a)
                        val = argv[self._pos]
                        self._pos += 1
                    sw.call(val)
                else:
                    if val is not None:
                        raise NeedlessArgument(a)
                    sw.call(None)

            elif a.startswith("-") and len(a) > 1:
                # "-vd" のようにまとめて書けるので一文字ずつ処理する
                j = 1
                while j < len(a):
                    c = a[j]
                    j += 1
                    sw = self._short.get("-" + c)
                    if sw is None:
                        # 未定義の短いオプションは長いオプション名で補完される
                        sw = self._complete_long(c, "-" + c)
                    if sw.arg_name:
                        val = a[j:]
                        j = len(a)
                        if val == "":
                            if self._pos >= len(argv):
                                raise MissingArgument("-" + c)
                            val = argv[self._pos]
                            self._pos += 1
                        sw.call(val)
                    else:
                        sw.call(None)

            else:
                rest.append(a)


#=== Ruby の ARGV.options{|parser| ... } 相当
# ParseError は捕捉して "#{$0}: #{message}" を stderr に出し，解析を打ち切る
def options(argv, program_name, body):
    parser = OptionParser(argv, program_name)
    try:
        body(parser)
    except ParseError as evar:
        sys.stderr.write("{}: {}\n".format(program_name, evar))
    return parser
