# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project
#--
#   上記著作権者は，以下の(1)〜(4)の条件を満たす場合に限り，本ソフトウェ
#   ア（本ソフトウェアを改変したものを含む．以下同じ）を使用・複製・改
#   変・再配布（以下，利用と呼ぶ）することを無償で許諾する．
#   (1) 本ソフトウェアをソースコードの形で利用する場合には，上記の著作
#       権表示，この利用条件および下記の無保証規定が，そのままの形でソー
#       スコード中に含まれていること．
#   (2) 本ソフトウェアを，ライブラリ形式など，他のソフトウェア開発に使
#       用できる形で再配布する場合には，再配布に伴うドキュメント（利用
#       者マニュアルなど）に，上記の著作権表示，この利用条件および下記
#       の無保証規定を掲載すること．
#   (3) 本ソフトウェアを，機器に組み込むなど，他のソフトウェア開発に使
#       用できない形で再配布する場合には，次のいずれかの条件を満たすこ
#       と．
#     (a) 再配布に伴うドキュメント（利用者マニュアルなど）に，上記の著
#         作権表示，この利用条件および下記の無保証規定を掲載すること．
#     (b) 再配布の形態を，別に定める方法によって，TOPPERSプロジェクトに
#         報告すること．
#   (4) 本ソフトウェアの利用により直接的または間接的に生じるいかなる損
#       害からも，上記著作権者およびTOPPERSプロジェクトを免責すること．
#       また，本ソフトウェアのユーザまたはエンドユーザからのいかなる理
#       由に基づく請求からも，上記著作権者およびTOPPERSプロジェクトを
#       免責すること．
#
#   本ソフトウェアは，無保証で提供されているものである．上記著作権者お
#   よびTOPPERSプロジェクトは，本ソフトウェアに関して，特定の使用目的
#   に対する適合性も含めて，いかなる保証も行わない．また，本ソフトウェ
#   アの利用により直接的または間接的に生じたいかなる損害に関しても，そ
#   の責任を負わない．
#
#   このファイルは tecsgen (Ruby 版) の tecslib/plugin/ThroughPlugin.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．
#
#   $Id: ThroughPlugin.rb 3225 2021-09-26 05:08:38Z okuma-top $
#++

# mikan through plugin: namespace が考慮されていない

import re

from tecslib.core.plugin import Plugin, CFile
from tecslib.rubylib.symbol import Sym


#==  スループラグインの共通の親クラス　かつ （何もせず）スルーするセルを挿入するスループラグイン
#    スループラグインは ThroughPlugin の子クラスとして定義する
class ThroughPlugin(Plugin):
#@cell_name::      Symbol             生成するセル名（複数セルを生成する場合、受け口側のセル）
#@plugin_arg_str:: string             through で指定された引数
#@next_cell:: Cell                    呼び口を結合するセル
#@next_cell_port_name:: Symbol       呼び口を結合する受口の名前
#@next_cell_port_subscript::Nil|Integer   呼び口を結合する受口の配列添数．受け口配列でない場合 nil
#@signature::      Signature          シグニチャ
#@celltype::       Celltype           呼び先のセルのセルタイプ. through が連接する場合、最終的な呼び先のセルのセルタイプ
#@entry_port_name::Symbol             生成するセルの受け口名  "eThroughEntry"
#@call_port_name:: Symbol             生成するセルの呼び口名  "cCall"
#@ct_name::        Symbol             生成するセルのセルタイプ名   "t#{self.class.name}_#{@signature.get_global_name}"
#@plugin_arg_list:: Hash              プラグイン引数をパースした結果のハッシュ変数
#@caller_cell::    Cell               呼び元のセル．through プラグインが連接する場合では、最も呼び元のセル．($source$)
#                                     through プラグインが合流するケースでは、1つ目の呼び元セルのみ引数として与えられる
#                                     従って TracePlugin の呼び元の判別に利用する場合は、異なる呼び元から呼ばれる可能性があることに注意しなくてはならない
#@callee_cell:: Cell                  呼び先のセル($destination$)
#@plugin_arg_check_proc_tab:: [string => Proc]  プラグイン引数名⇒チェック関数
# 以下の変数は、initialize ではなく、後から設定される
#@start_@region::  Region             始まりのリージョン： caller_cell のリージョンとは異なる可能性がある ($start_region$)
#@end_region::  Region                終わりのリージョン： next_cell のリージョンとは異なる可能性がある ($end_region$)
#@region:: Region                     @start_region と @end_region のいずれかで、cell を置くのが好ましいリージョン ($preferred_region$)
#@through_type:: Symbol              :THROUGH, :TO_THROUGH, :FROM_THROUGH, :IN_THROUGH, :OUT_THROUGH のいずれか

    # この Plugin が生成したセルタイプのリスト
    generated_celltype = {}

    #=== ThroughPlugin の初期化
    #     through が指定された時点で生成が行われる
    #         初期化では、指定された引数を記録するに留める
    #cell_name::      Symbol             生成すべきセル名（受口側）
    #plugin_arg::     string             through で指定された引数
    #next_cell::      Cell               呼び口を接続するセル
    #next_cell_port_name:: Symbol        呼び口を接続する受口の名前
    #next_cell_port_subscript:: Nil|Integer  呼び口を接続する受口配列添数
    #signature::      Signature          シグニチャ
    #celltype::       Celltype           セルタイプ (呼び先のセルのセルタイプ)
    #caller_cell::    Cell               呼び元のセル．@caller_cell の項を参照
    def __init__(self, cell_name, plugin_arg, next_cell, next_cell_port_name, next_cell_port_subscript, signature, celltype, caller_cell):
        super().__init__()
        self.cell_name = cell_name                      # 生成すべきセル名（受け口側のセル名）
                                                        # この呼び先に別セルを生成する場合、この名前を接頭辞とすべき
        self.next_cell = next_cell                      # 呼び先のセル
        self.next_cell_port_name = next_cell_port_name
        self.next_cell_port_subscript = next_cell_port_subscript
        self.signature = signature
        self.entry_port_name = Sym("eThroughEntry")
        self.entry_port_subscript = None  # Ruby では未設定インスタンス変数は nil
        self.call_port_name = Sym("cCall")
        self.ct_name = Sym("t{}_{}".format(self.__class__.__name__, self.signature.get_global_name()))
        self.celltype = celltype
        self.plugin_arg_str = plugin_arg
        self.plugin_arg_list = {}                       # プラグイン引数をパースした結果のハッシュ変数
        self.caller_cell     = caller_cell
        self.plugin_arg_check_proc_tab = {}             # 子クラスでオーバーライドする
        # 引数で渡らない(後から追加された)ものは set_through_info で設定される
        from tecslib.core.componentobj.join import Join
        Join.set_through_info(self)
        print("{}.new( '{}', '{}', '{}', '{}', {} )\n".format(
            self.__class__.__name__, cell_name, plugin_arg,
            next_cell.get_name(), next_cell_port_name, celltype.get_name()))

    #=== 情報を設定する
    # 共有チャンネルの場合 caller_cell, next_cell のいずれの region でもないケースがある
    # 後から追加したので initialize の引数ではなく、別メソッドで設定
    # このメソッドは、オーバーライドしないでください．
    # かわりに set_through_info_hook をオーバーライドしてください。
    # Join と ThrougPlugin の間の連絡用で、今後とも引数が追加される可能性があるため
    # このメソッドは V1.C.0.34 で位置が移動され、ThroughPlugin#initialize で呼び出される
    def set_through_info(self, start_region, end_region, through_type, join, callee_cell, count):
        self.start_region = start_region
        self.end_region = end_region
        self.through_type = through_type
        self.join = join
        self.callee_cell = callee_cell
        self.count = count

        # preferred_region の設定
        if through_type in (Sym("IN_THROUGH"), Sym("THROUGH"), Sym("FROM_THROUGH")):
            self.region = end_region
        elif through_type in (Sym("OUT_THROUGH"), Sym("TO_THROUGH")):
            self.region = start_region
        else:
            raise Exception("Unknown through_type {}".format(through_type))
        self.set_through_info_hook()

    #=== 情報が設定されたあと呼び出されるメソッド
    # set_through_info はオーバーライド禁止されている。
    # 代わりにこちらのメソッドをオーバーライドしてください。
    def set_through_info_hook(self):
        pass

    #===  セルの名前を得る
    def get_cell_name(self):
        return self.cell_name

    #=== NamespacePath を得る
    # 生成するセルの namespace path を生成する
    def get_cell_namespace_path(self):
#        nsp = @region.get_namespace.get_namespace_path
        nsp = self.region.get_namespace_path()
        return nsp.append(self.cell_name)

    #===  生成されたセルの受け口の名前を得る
    def get_through_entry_port_name(self):
        return self.entry_port_name

    #===  生成されたセルの受け口配列添数を得る
    def get_through_entry_port_subscript(self):
        return self.entry_port_subscript

    #===  宣言コードの生成
    #      typedef, signature, celltype など（cell 以外）のコードを生成
    #          重複して生成してはならない（すでに生成されている場合は出力しないこと）
    #file::        FILE       生成するファイル
    def gen_plugin_decl_code(self, file):

        # このセルタイプ（同じシグニチャ）は既に生成されているか？
        if ThroughPlugin.generated_celltype.get(self.ct_name) is None:
            ThroughPlugin.generated_celltype[self.ct_name] = [self]
        else:
            ThroughPlugin.generated_celltype[self.ct_name].append(self)
            return

        from tecslib.core import globals as G
        file2 = CFile.open("{}/{}.cdl".format(G.gen, self.ct_name), "w")

        send_receive = []
        if self.signature is not None:
            def _each_param(fd, param):
                dir_ = param.get_direction()
                if str(dir_) in ("SEND", "RECEIVE"):
                    send_receive.append([dir_, fd, param])
            self.signature.each_param(_each_param)

        file2.print("/* generated by ThroughPlugin */\n\ncelltype {} {{\n".format(self.ct_name))

        if len(send_receive) > 0:
            file2.print("  [allocator(\n")
            delim = ""
            for a in send_receive:
                file2.print("{}\t{}.{}<={}.{}.{}".format(
                    delim,
                    a[1].get_name(), a[2].get_name(),
                    self.call_port_name, a[1].get_name(), a[2].get_name()))
                delim = ",\n"
            file2.print("), inline]\n")
        else:
            file2.print("  [inline]\n")

        file2.print(
            "    entry {} {};\n"
            "  call  {} {};\n"
            "}};\n".format(
                self.signature.get_namespace_path(), self.entry_port_name,
                self.signature.get_namespace_path(), self.call_port_name))
        file2.close()

        file.print("import( \"{}/{}.cdl\" );\n".format(G.gen, self.ct_name))

    #=== CDL ファイルの生成
    #file::     FILE    生成するファイル
    def gen_cdl_file(self, file):
        self.gen_plugin_decl_code(file)
        self.gen_through_cell_code(file)

    #===  セルコードの生成
    #     through 指定により生じるセルコード(CDL)を生成する
    #file::        FILE       生成するファイル
    def gen_through_cell_code(self, file):

        nest = self.region.gen_region_str_pre(file)
        nest_str = "  " * nest

        file.print(
            "{nest}cell {ct_name} {cell_name} {{\n"
            "{nest}  {call_port_name} = {path}.{next_port_name};\n"
            "{nest}}};\n".format(
                nest=nest_str,
                ct_name=self.ct_name,
                cell_name=self.cell_name,
                call_port_name=self.call_port_name,
                path=self.next_cell.get_namespace_path().get_path_str(),
                next_port_name=self.next_cell_port_name,
            ))
        self.region.gen_region_str_post(file)

    #=== 後ろのコードを生成
    #プラグインの後ろのコード (CDL) を生成
    #file:: File:
    @classmethod
    def gen_post_code(cls, file):
        # 複数のプラグインの post_code が一つのファイルに含まれるため、以下のような見出しをつけること
        # file.print("/* '{}' post code */\n".format(cls.__name__))
        pass

    #===  受け口関数の本体(C言語)を生成する
    #     通常であれば、ジェネレータは受け口関数のテンプレートを生成する
    #     プラグインの場合、変更する必要のないセルタイプコードを生成する
    #file::           FILE        出力先ファイル
    #b_singleton::    bool        true if singleton
    #ct_name::        Symbol
    #global_ct_name:: string
    #sig_name::       string
    #ep_name::        string
    #func_name::      string
    #func_global_name:: string
    #func_type::      class derived from Type
    def gen_ep_func_body(self, file, b_singleton, ct_name, global_ct_name, sig_name, ep_name, func_name, func_global_name, func_type, params):

        ret_type = func_type.get_type()
        b_ret_void = ret_type.is_void()

        if not b_ret_void:
            file.print("  {}  retval;\n".format(ret_type.get_type_str()))

        if not b_singleton:

            file.print(
                "  {ct_name}_CB    *p_cellcb;\n"
                "  if( VALID_IDX( idx ) ){{\n"
                "    p_cellcb = {global_ct_name}_GET_CELLCB(idx);\n"
                "  }}else{{\n"
                "     /* エラー処理コードをここに記述 */\n"
                "  }}\n\n".format(
                    ct_name=ct_name,
                    global_ct_name=global_ct_name,
                ))

        # p "celltype_name, sig_name, func_name, func_global_name"
        # p "#{ct_name}, #{sig_name}, #{func_name}, #{func_global_name}"

        delim = ""
        if not b_ret_void:
            file.print("  retval = ")

        file.print("{}_{}(".format(self.call_port_name, func_name))

#        if not b_singleton:
#            file.print(" tecs_this")
#            delim = ","

        for param in params:
            file.print("{} {}".format(delim, param.get_name()))
            delim = ","

        file.print(" );\n")

        if not b_ret_void:
            file.print("  return retval;\n")

    #=== Through プラグインの引数の名前を置換する
    def check_plugin_arg(self, ident, rhs):
        rhs = self.subst_name(rhs)
        super().check_plugin_arg(ident, rhs)

    #=== ThroughPlugin#名前の置換
    # プラグインオプション引数内の文字列を置換する
    #   $source$       … 呼び元のセル名
    #   $destination$  … 呼び先のセル名
    #   $SOURCE$       … 呼び元のセル名 (リージョン名を '_' で連結した global_name)
    #   $DESTINATION$  … 呼び先のセル名 (リージョン名を '_' で連結した global_name)
    #   $next$         … 次のセル名
    #                     複数の through がつながっている場合、すぐ後ろに来るもの
    #   $NEXT$         … 次のセル名 (リージョン名を '_' で連結した global_name)
    #                     複数の through がつながっている場合、すぐ後ろに来るもの
    #   $start_region$ … $source$ のセルの存在する region (global_name)
    #   $end_region$   … $destination$ のセルの存在する region (global_name)
    #   $preferred_region$  … 適切な region (global_name), start_region または end_region
    #   $count$        … region 間の through の適用数
    #   $$             … $ に置換
    def subst_name(self, s):
        # セル名の置換
        _caller_name    = self.caller_cell.get_name()
        _callee_name    = self.callee_cell.get_name()
        _caller_global  = self.caller_cell.get_global_name()
        _callee_global  = self.callee_cell.get_global_name()
        _next_name      = self.next_cell.get_name()
        _next_global    = self.next_cell.get_global_name()
        _start_region   = self.start_region.get_global_name()
        _end_region     = self.end_region.get_global_name()
        _preferred      = self.region.get_global_name()
        # Ruby の nil.to_s は "" だが portNo=8931+$count$ では None のとき 0 相当にする
        if self.count is None:
            _count_s = "0"
        else:
            _count_s = str(self.count)

        s = re.sub(r'(^|[^\$])\$source\$',
                   lambda m: m.group(1) + _caller_name, s)
        s = re.sub(r'(^|[^\$])\$destination\$',
                   lambda m: m.group(1) + _callee_name, s)
        s = re.sub(r'(^|[^\$])\$SOURCE\$',
                   lambda m: m.group(1) + _caller_global, s)
        s = re.sub(r'(^|[^\$])\$DESTINATION\$',
                   lambda m: m.group(1) + _callee_global, s)
        s = re.sub(r'(^|[^\$])\$next\$',
                   lambda m: m.group(1) + _next_name, s)
        s = re.sub(r'(^|[^\$])\$NEXT\$',
                   lambda m: m.group(1) + _next_global, s)
        # region 名の置換
        s = re.sub(r'(^|[^\$])\$start_region\$',
                   lambda m: m.group(1) + _start_region, s)
        s = re.sub(r'(^|[^\$])\$end_region\$',
                   lambda m: m.group(1) + _end_region, s)
        s = re.sub(r'(^|[^\$])\$preferred_region\$',
                   lambda m: m.group(1) + _preferred, s)
        s = re.sub(r'(^|[^\$])\$count\$',
                   lambda m: m.group(1) + _count_s, s)

        s = re.sub(r'\$\$', '$', s)                       # $$ を $ に置換

        return s

    def show_tree(self, indent):
        print("  " * indent, end="")
        print("Plugin: celltype: {} cell: {}".format(self.ct_name, self.cell_name))
        print("  " * (indent + 1), end="")
        print("next: signature: {} call = {}.{}".format(
            self.signature.get_namespace_path(), self.next_cell.get_name(), self.next_cell_port_name))
