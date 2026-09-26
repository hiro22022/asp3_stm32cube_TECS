#! /usr/bin/env python3
# -*- coding: utf-8 -*-

#
#  TECS merger
#      Merger for TECS generated templates
#
#   Copyright (C) 2008-2017 by TOPPERS Project
#
#   ライセンスは Ruby 版 tecsmerge.rb に準拠する．
#
#= tecsgen  : TECS のマージャ
#
#Authors::   大山 博司
#Version::
#Copyright:: Copyright (C) TOPPERS Project, 2008-2017. All rights reserved.
#License::   TOPPERS ライセンスに準拠

"""
tecsmerge はテンプレートファイルを元に作成されたセルタイプコード（含インライン関数を記述したセルタイプインラインヘッダ）を保守するものである。
セルタイプに以下の改変が加えられた場合に対応する。
・受け口関数が増えた
・受け口の名前が変更された
・受け口関数の名前が変更された

% tecsmerge source_dir   dest_dir
% tecsmerge source_files dest_dir

% tecsmerge -p port_name -f old_name:new_name source_file dest_dir
% tecsmerge -p old_name:new_name source_file dest_dir

source_file の名前は _teml.c, _templ.h で終わっていなくてはならない
dest_file は source_file の _templ を取り除いた名前でなくてはならない
dest_file が存在しない場合、_templ を取り除いた名前でコピーするだけである
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Dict, List, Optional

n_err = 0
b_show = False
b_exist = False  # コピー先にファイルがある場合のみマージ
old_mode = False  # old_mode (関数本体として /<ENTRY_FUNC> の代わりに '{' を使う


def write_array(file, array):
    for line in array:
        file.write(line)


class PortRenamer:
    port_renamer_list: Dict[str, "PortRenamer"] = {}
    port_renamer_current: Optional["PortRenamer"] = None

    def __init__(self, old_port_name, new_port_name):
        old_port_name = str(old_port_name)
        if new_port_name is not None:
            new_port_name = str(new_port_name)
        # p "port_renamer: #{old_port_name}"
        PortRenamer.port_renamer_list[old_port_name] = self
        PortRenamer.port_renamer_current = self
        self.old_port_name = old_port_name
        self.new_port_name = new_port_name
        self.func_renamer_list = {}

    @classmethod
    def add_func(cls, old_name, new_name):
        # p "add_func: #{old_name}"
        if PortRenamer.port_renamer_current is None:
            sys.stderr.write(f"error: {old_name}: specify -p before -f\n")
            global n_err
            n_err += 1
        else:
            PortRenamer.port_renamer_current.add_func_inst(old_name, new_name)

    def add_func_inst(self, old_name, new_name):
        global n_err
        old_name = str(old_name)
        new_name = str(new_name)
        if old_name in self.func_renamer_list:
            sys.stderr.write(f"error: {old_name}: duplicate in port {self.old_port_name}\n")
            n_err += 1
        elif old_name == new_name:
            sys.stderr.write(f"error: {old_name}: old and new are the same name\n")
            n_err += 1
        self.func_renamer_list[old_name] = new_name

    @classmethod
    def show(cls):
        if PortRenamer.port_renamer_list:
            for pr, pc in PortRenamer.port_renamer_list.items():
                pc.show_inst()

    @classmethod
    def get_list(cls):
        return PortRenamer.port_renamer_list

    def show_inst(self):
        sys.stdout.write(f"port: {self.old_port_name}")
        if self.new_port_name:
            sys.stdout.write(f" => {self.new_port_name}")
        sys.stdout.write("\n")

        for old, new in self.func_renamer_list.items():
            sys.stdout.write(f"  func: {old} => {new}\n")


class CDLEntryPort:
    # @entry_comment::      [string]
    # @entry_body::         [string]
    # @entry_func_comment:: {ep_func_name=>string}
    # @entry_func_body::    {ep_func_name=>string}
    # @entry_func_array::   [string]

    def __init__(self):
        self.entry_comment = []
        self.entry_body = []
        self.entry_func_comment = {}
        self.entry_func_body = {}
        self.entry_func_array = []

    def write(self, file):
        write_array(file, self.entry_comment)
        write_array(file, self.entry_body)
        for fnm in self.entry_func_array:
            # p @entry_func_comment[fnm][0]
            write_array(file, self.entry_func_comment[fnm])
            write_array(file, self.entry_func_body[fnm])


class CDLContents:
    # @head::             [string]
    # @preamble_comment:: [string]
    # @preamble_body::    [string]
    # @entry_port::       {ep_name=>CDLEntryPort}
    # @entry_port_array:: [CDLEntryPort]
    # @postamble_comment::[string]
    # @postamble_body::   [string]

    DELIMITERS = {
        # state             => [ regexp_original,                 [previous states]                   , Regexp ]
        "HEAD": ["#[<BeginingOfFile>]#", []],
        "PREAMBLE_COMMENT": ["/* #[<PREAMBLE>]#", ["HEAD"]],
        "PREAMBLE_BODY": [" * #[</PREAMBLE>]#", ["PREAMBLE_COMMENT"]],
        "ENTRY_COMMENT": ["/* #[<ENTRY_PORT>]# PORT_NAME", ["PREAMBLE_BODY", "ENTRY_FUNC_BODY", "ENTRY_FUNC_BODY2"]],
        "ENTRY_BODY": [" * #[</ENTRY_PORT>]#", ["ENTRY_COMMENT"]],
        "ENTRY_FUNC_COMMENT": ["/* #[<ENTRY_FUNC>]# FUNC_NAME", ["ENTRY_BODY", "ENTRY_FUNC_BODY", "ENTRY_FUNC_BODY2"]],
        "POSTAMBLE_COMMENT": ["/* #[<POSTAMBLE>]#", ["ENTRY_FUNC_BODY", "ENTRY_FUNC_BODY2", "PREAMBLE_BODY"]],
        "POSTAMBLE_BODY": [" * #[</POSTAMBLE>]#", ["POSTAMBLE_COMMENT"]],
        "EOF": ["#[</EndOfFile>]#", ["POSTAMBLE_BODY", "ENTRY_FUNC_BODY", "ENTRY_FUNC_BODY2", "PREAMBLE_BODY"]],
    }

    DELIMITERS_FUNC_BY_COMMENT = {
        "ENTRY_FUNC_BODY": [" * #[</ENTRY_FUNC>]#", ["ENTRY_FUNC_COMMENT"]],
        "ENTRY_FUNC_BODY2": [" * #[/ENTRY_FUNC>]#", ["ENTRY_FUNC_COMMENT"]],  # for Bug compatibility
    }

    DELIMITERS_FUNC_BY_BRACKET = {
        "ENTRY_FUNC_BODY": ["\\{", ["ENTRY_FUNC_COMMENT"]],
    }

    @classmethod
    def rewrite_DELIMITERS(cls, delimiters):
        for stat, stat_info in delimiters.items():
            s = re.sub(r"([*\[\]])", r"\\\1", stat_info[0])  # *, [, ] の前に \\ を挿入
            s = re.sub(r"\s*\w*_NAME", r"\\s*(\\w*)", s)  # ..._NAME を (w*) に変更
            s = "^" + s  # ^ を先頭に挿入
            while len(stat_info) < 3:
                stat_info.append(None)
            stat_info[2] = re.compile(s)
            # p stat_info[2]

    @classmethod
    def merge_DELIMITERS(cls, mode):
        # mode :OLD_FUNC_BODY, :NEW_FUNC_BODY
        if mode == "OLD_FUNC_BODY":
            cls.DELIMITERS.update(cls.DELIMITERS_FUNC_BY_COMMENT)
        elif mode == "NEW_FUNC_BODY":
            cls.DELIMITERS.update(cls.DELIMITERS_FUNC_BY_BRACKET)
        else:
            raise RuntimeError("unknown mode")

    # all_contents:: [string,...]
    def __init__(self, all_contents):
        global n_err, old_mode
        part = []
        line_no = 0
        stat = "HEAD"
        arg = None
        port_name = None
        func_name = None

        self.entry_port = {}
        self.entry_port_array = []

        self.head = []
        self.preamble_comment = []
        self.preamble_body = []
        self.postamble_comment = []
        self.postamble_body = []

        for line in list(all_contents) + [None]:  # None: EOF
            line_no += 1
            # p "L: #{line}"
            b_delim = False  # デリミタキーワードの行
            for next_stat, stat_info in list(CDLContents.DELIMITERS.items()):
                if next_stat == "HEAD" or (next_stat == "EOF" and line is not None):
                    continue
                # #1002 tecsmerge の非受け口関数 (POSTAMBLE部) の行頭に '{' があるとエラーになる
                if (not old_mode) and line is not None and re.match(r"^\{", line) and (
                    stat == "PREAMBLE_BODY" or stat == "POSTAMBLE_BODY"
                ):
                    # p line + "  next_stat=" + next_stat.to_s + "stat=" + stat.to_s
                    continue

                # p "R: #{stat_info[0]}"
                m = None
                if line is not None:
                    m = stat_info[2].match(line)
                if m or (line is None and next_stat == "EOF"):
                    # p "D: #{line}: #{stat}"
                    b_delim = True

                    found = False
                    for prev_stat in stat_info[1]:
                        if stat == prev_stat:
                            found = True
                    if not found:
                        sys.stderr.write(f'error {line_no}: unsuitable previous keyword\n')
                        sys.stderr.write(f'error {line_no}:   previous:  "{CDLContents.DELIMITERS[stat][0]}"\n')
                        sys.stderr.write(f'error {line_no}:   current:   "{CDLContents.DELIMITERS[next_stat][0]}"\n')
                        expect = ""
                        delim = ""
                        for prev_stat in stat_info[1]:
                            expect = f'{expect}{delim}"{CDLContents.DELIMITERS[prev_stat][0]}"'
                            delim = ", "
                        sys.stderr.write(f"error {line_no}:   suitable previous: {expect}\n")
                        n_err += 1

                    if stat in ("PREAMBLE_COMMENT", "ENTRY_COMMENT", "ENTRY_FUNC_COMMENT", "POSTAMBLE_COMMENT"):
                        part.append(line)

                    # case stat   # 前の状態
                    if stat == "HEAD":
                        self.head = part
                    elif stat == "PREAMBLE_COMMENT":
                        self.preamble_comment = part
                    elif stat == "PREAMBLE_BODY":
                        self.preamble_body = part
                    elif stat == "ENTRY_COMMENT":
                        port_name = str(arg) if arg is not None else ""
                        self.entry_port[port_name] = CDLEntryPort()
                        self.entry_port_array.append(port_name)
                        self.entry_port[port_name].entry_comment = part
                    elif stat == "ENTRY_BODY":
                        self.entry_port[port_name].entry_body = part
                    elif stat == "ENTRY_FUNC_COMMENT":
                        func_name = str(arg) if arg is not None else ""
                        if self.entry_port.get(port_name) is not None:  # None なら既にエラー
                            self.entry_port[port_name].entry_func_comment[func_name] = part
                            self.entry_port[port_name].entry_func_array.append(func_name)
                    elif stat in ("ENTRY_FUNC_BODY", "ENTRY_FUNC_BODY2"):
                        if self.entry_port.get(port_name) is not None:  # None なら既にエラー
                            self.entry_port[port_name].entry_func_body[func_name] = part
                    elif stat == "POSTAMBLE_COMMENT":
                        self.postamble_comment = part
                    elif stat == "POSTAMBLE_BODY":
                        self.postamble_body = part
                    else:
                        raise RuntimeError(f"Unknown state {stat}")

                    if next_stat in ("PREAMBLE_COMMENT", "ENTRY_COMMENT", "ENTRY_FUNC_COMMENT", "POSTAMBLE_COMMENT"):
                        part = [line]
                    else:
                        part = []

                    stat = next_stat
                    arg = m.group(1) if m and m.lastindex else None  # arg に取っておく
                    # p stat, arg
                    break

            if not b_delim:
                part.append(line)

    def check(self, template):
        # template にないものをチェック
        for port_name, entry_port in self.entry_port.items():
            temp_entry_port = template.entry_port.get(port_name)
            if temp_entry_port is None:
                sys.stderr.write(f"info: {port_name} is deleted port\n")
                continue
            # temp_entry_port.entry_func_body.each{ |f,b|  p f }
            for func_name, func_body in entry_port.entry_func_body.items():
                if temp_entry_port.entry_func_body.get(func_name) is None:
                    sys.stderr.write(f"info: {func_name} is deleted function\n")

    def rename(self):
        renamed_entry_port = {}
        for pon, pr in PortRenamer.get_list().items():
            # 対象受け口を捜す
            ep = self.entry_port.get(pon)
            if ep is None:
                sys.stderr.write(f"warning: {pon}: renaming port not found\n")
                continue

            # ポートの rename
            pnn = pr.new_port_name  # 置換後の名前
            if pnn:
                # 置換する名前があれば、登録しなおす
                renamed_entry_port[pnn] = self.entry_port[pon]
                del self.entry_port[pon]

            # 指定された関数の置換
            renamed_func_comment = {}
            renamed_func_body = {}
            for old, new in pr.func_renamer_list.items():
                ofn = f"{pon}_{old}"
                nfn = f"{pon}_{new}"
                # p "fnn: #{ofn} #{nfn} #{pon}"
                if ep.entry_func_comment.get(ofn) is None:
                    sys.stderr.write(f"warning: {old}: renaming function not found\n")
                    continue
                ep.entry_func_array = [nfn if fn == ofn else fn for fn in ep.entry_func_array]
                renamed_func_comment[nfn] = ep.entry_func_comment[ofn]
                renamed_func_body[nfn] = ep.entry_func_body[ofn]
                del ep.entry_func_comment[ofn]
                del ep.entry_func_body[ofn]
            ep.entry_func_comment.update(renamed_func_comment)
            ep.entry_func_body.update(renamed_func_body)

            # ポート名の変更による関数名の置換
            renamed_func_comment = {}
            renamed_func_body = {}
            if pnn:
                new_array = []
                for ofn in ep.entry_func_array:
                    nfn = re.sub(re.escape(str(pon)), str(pnn), str(ofn), count=1)
                    # p "pnn: #{ofn} #{nfn} #{pon}  #{pnn}"
                    if nfn != ofn:
                        renamed_func_comment[nfn] = ep.entry_func_comment[ofn]
                        renamed_func_body[nfn] = ep.entry_func_body[ofn]
                        del ep.entry_func_comment[ofn]
                        del ep.entry_func_body[ofn]
                        new_array.append(nfn)
                    else:
                        new_array.append(ofn)
                ep.entry_func_array = new_array
                ep.entry_func_comment.update(renamed_func_comment)
                ep.entry_func_body.update(renamed_func_body)

                # ep.entry_func_comment.each { |f,e| p "FF: #{f}" }
                # ep.entry_func_array.each { |f,e| p "FA: #{f}" }
        # p renamed_entry_port
        self.entry_port.update(renamed_entry_port)

    def merge(self, src):
        self.head = src.head
        self.preamble_body = src.preamble_body
        self.postamble_body = src.postamble_body

        for port_name in self.entry_port_array:
            # p "merging #{port_name}"
            entry_port = self.entry_port[port_name]
            src_entry_port = src.entry_port.get(port_name)
            if src_entry_port is None:
                sys.stdout.write(f"port merged:   {port_name}\n")
                continue
            entry_port.entry_body = src_entry_port.entry_body
            for func_name in entry_port.entry_func_array:
                # p "merging #{func_name}"
                if src_entry_port.entry_func_body.get(func_name) is None:
                    sys.stdout.write(f"func merged:   {func_name}\n")
                    continue
                sys.stdout.write(f"func remained: {func_name}\n")
                # entry_port.entry_func_comment[func_name] = src_entry_port.entry_func_comment[func_name]
                entry_port.entry_func_body[func_name] = src_entry_port.entry_func_body[func_name]

    def write(self, file):
        write_array(file, self.head)
        write_array(file, self.preamble_comment)
        write_array(file, self.preamble_body)
        for port_name in self.entry_port_array:
            self.entry_port[port_name].write(file)
        write_array(file, self.postamble_comment)
        write_array(file, self.postamble_body)


CDLContents.rewrite_DELIMITERS(CDLContents.DELIMITERS)
CDLContents.rewrite_DELIMITERS(CDLContents.DELIMITERS_FUNC_BY_COMMENT)
CDLContents.rewrite_DELIMITERS(CDLContents.DELIMITERS_FUNC_BY_BRACKET)


def merge(src_file, dst_dir):
    global n_err, b_exist
    m = re.search(r"(.*)_templ(.[ch])$", src_file)
    if not m:
        sys.stderr.write(f"error: {src_file}: not end with _templ.c/h\n")
        sys.exit(1)

    fname = f"{m.group(1)}{m.group(2)}"
    dst_file = f"{dst_dir}/{os.path.basename(fname)}"
    if os.path.isfile(dst_file):
        sys.stdout.write(f"merging {src_file} to {dst_file}\n")
        # dst_file の読込み
        try:
            with open(dst_file, "r", encoding="latin-1", newline="") as dst:
                old_contents = dst.readlines()
        except OSError:
            sys.stderr.write(f"error: cannot open {dst_file}\n")
            n_err += 1
            sys.exit(1)
        old = CDLContents(old_contents)

        # template の読込み
        try:
            with open(src_file, "r", encoding="latin-1", newline="") as src:
                new_contents = src.readlines()
        except OSError:
            sys.stderr.write(f"error: cannot open {src_file}\n")
            n_err += 1
            sys.exit(1)
        templ = CDLContents(new_contents)

        old.rename()
        error_check(dst_file, 1)

        old.check(templ)
        error_check(dst_file, 2)

        templ.merge(old)
        error_check(dst_file, 3)

        rename_dst(dst_file)

        try:
            with open(dst_file, "w", encoding="latin-1", newline="") as dst:
                templ.write(dst)
        except OSError:
            pass

    elif b_exist is False:
        # src_file を dst_file へコピー
        try:
            with open(src_file, "r", encoding="latin-1", newline="") as src:
                contents = src.readlines()
        except OSError:
            sys.stdout.write(f"{src_file}: fail to read\n")
            contents = None

        if contents is not None:
            try:
                with open(dst_file, "w", encoding="latin-1", newline="") as dst:
                    for line in contents:
                        dst.write(line)
            except OSError:
                sys.stdout.write(f"{dst_file}: fail to write\n")
    else:
        sys.stdout.write(f"info: {dst_file} skipped\n")


def error_check(dst_file, level):
    global n_err
    if n_err > 0:
        sys.stderr.write(f"=== {dst_file} not generated because of error ===\n")
        sys.exit(level)


# === rename_dst
# dst_file のバックアップファイル名を決定し、リネームする
# 成功すれば、リネーム後のファイル名を返す
# dst_file が存在しなければ（リネームは行われず）None を返す。
def rename_dst(dst_file):
    if not os.path.exists(dst_file):
        sys.stderr.write(f"info: backup not generated for {dst_file}\n")
        # なければ終わり
        return None

    i = 0
    found = True
    bkup_file = None
    while found is True:
        i = i + 1
        bkup_file = f"{dst_file}_{i}"
        if not os.path.exists(bkup_file):
            found = False

    try:
        os.rename(dst_file, bkup_file)
        sys.stderr.write(f"info: backup generated for {dst_file} to {bkup_file}\n")
        return bkup_file
    except OSError:
        sys.stderr.write(f"error: fail to rename backup file: {bkup_file}\n")
        sys.exit(1)


def main(argv=None):
    global n_err, b_show, b_exist, old_mode

    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        usage="tecsmerge [options] files_templ.c   src_dir\n"
        "       tecsmerge [options] gen_dir         src_dir",
        add_help=True,
    )
    parser.add_argument(
        "-e",
        "--exist-only",
        action="store_true",
        help="merge if exist in destination directory",
    )
    parser.add_argument(
        "-p",
        "--port",
        action="append",
        default=[],
        metavar="old_name:new_name",
        help="specify entry port name change",
    )
    parser.add_argument(
        "-f",
        "--func",
        action="append",
        default=[],
        metavar="old_name:new_name",
        help="specify entry function name change",
    )
    parser.add_argument(
        "-s",
        "--show_change_set",
        action="store_true",
        help="show change set. all substitute",
    )
    parser.add_argument(
        "-o",
        "--old-mode",
        action="store_true",
        help="old mode (function head not substituted)",
    )
    parser.add_argument("args", nargs="*", help=argparse.SUPPRESS)

    ns = parser.parse_args(argv)

    b_exist = bool(ns.exist_only)
    b_show = bool(ns.show_change_set)
    old_mode = bool(ns.old_mode)

    for ps in ns.port:
        p = ps.split(":")
        PortRenamer(p[0], p[1] if len(p) > 1 else None)

    for fs in ns.func:
        f = fs.split(":")
        PortRenamer.add_func(f[0], f[1] if len(f) > 1 else None)

    if len(ns.args) < 2:
        parser.print_help()
        sys.exit(1)

    if b_show:
        PortRenamer.show()

    if old_mode:
        CDLContents.merge_DELIMITERS("OLD_FUNC_BODY")
    else:
        CDLContents.merge_DELIMITERS("NEW_FUNC_BODY")

    if n_err > 0:
        sys.stderr.write(f"{n_err} errors\n")
        sys.exit(1)

    src = ns.args[0:-1]
    dst = ns.args[-1]

    try:
        if not os.path.isdir(dst):
            if not os.path.exists(dst):
                sys.stderr.write(f"error: {dst}: not found\n")
                sys.exit(1)
            sys.stderr.write(f"error: {dst}: not directory\n")
            sys.exit(1)
    except OSError:
        sys.stderr.write(f"error: {dst}: not found\n")
        sys.exit(1)

    for s in src:
        try:
            if not os.path.exists(s):
                sys.stderr.write(f"error: {s}: not found or cannot access\n")
                sys.exit(1)
        except OSError:
            sys.stderr.write(f"error: {s}: not found or cannot access\n")
            sys.exit(1)

        if os.path.isdir(s):
            for file in os.listdir(s):
                if re.search(r"_templ.[ch]$", file):
                    merge(f"{s}/{file}", dst)
        elif os.path.isfile(s):
            merge(s, dst)


if __name__ == "__main__":
    main()
