# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2024-2026 by TOPPERS Project
#
#   このファイルは tecsgen (Ruby 版) の
#   tecslib/plugin/TransparentRPCSignaturePlugin.rb を Python へ移植したものである．
#   （tecsgen 配布ツリーに欠落しているため asp3 同梱版を参照）
#
#   $Id: TransparentRPCSignaturePlugin.rb 3300 2026-01-04 12:29:45Z okuma-top $
#++

# mikan through plugin: namespace が考慮されていない

from tecslib.core import globals as G
from tecslib.core.componentobj.celltype import Celltype
from tecslib.core.componentobj.compositecelltype import CompositeCelltype
from tecslib.core.componentobj.namespace import Namespace
from tecslib.core.componentobj.namespacepath import NamespacePath
from tecslib.core.plugin import CFile
from tecslib.plugin.SignaturePlugin import SignaturePlugin
from tecslib.plugin.lib.GenTransparentMarshaler import GenTransparentMarshaler, RPCPluginArgProc
from tecslib.plugin.lib.GenParamCopy import GenParamCopy
from tecslib.rubylib.symbol import Sym


def _set_noClientSemaphore(obj, rhs):
    obj.set_noClientSemaphore(rhs)


def _set_semaphoreCelltype(obj, rhs):
    obj.set_semaphoreCelltype(rhs)


def _set_datapumpholder(obj, rhs):
    obj.set_datapumpholder(rhs)


#==  Transparent RPC 用シグニチャプラグイン
#    RPC チャンネル複合セルタイプを生成する
class TransparentRPCSignaturePlugin(GenParamCopy, GenTransparentMarshaler, SignaturePlugin):

    generated_celltype = {}

    # RPCPlugin 専用のオプション
    TransparentRPCPluginArgProc = dict(RPCPluginArgProc)  # 複製を作って元を変更しないようにする
    TransparentRPCPluginArgProc["noClientSemaphore"] = _set_noClientSemaphore
    TransparentRPCPluginArgProc["semaphoreCelltype"] = _set_semaphoreCelltype
    TransparentRPCPluginArgProc["DataPumpHolder"] = _set_datapumpholder

    #=== RPCPlugin の initialize
    #  説明は ThroughPlugin (plugin.rb) を参照
    def __init__(self, signature, option):
        super().__init__(signature, option)
        self.b_noClientSemaphore = False
        self.semaphoreCelltype = "tSemaphore"
        self.b_datapumpholder = False
        self.call_port_name = Sym("cCall")

        # オプション：GenTransparentMarshaler 参照
        self.plugin_arg_check_proc_tab = TransparentRPCSignaturePlugin.TransparentRPCPluginArgProc
        self.parse_plugin_arg()

        # ThroughPlugin では、ｃCall (固定)
        # SignaturePlugin は、デフォルトではシグニチャ名由来の呼び口名が付く
        #    これを ThroughPlugin に合わせて cCall に変更する
        cell_name = "{}Cell".format(signature)          # dummy
        self.initialize_transparent_marshaler(cell_name)

        if self.b_datapumpholder is True:
            channel_head_append = "DPH"
        else:
            channel_head_append = ""

        self.rpc_channel_celltype_name = "tRPCPlugin{}_{}_{}".format(
            channel_head_append, self.TDRCelltype, self.signature.get_global_name())
        self.rpc_channel_celltype_name_full = "tRPCPlugin{}_{}_{}_{}".format(
            channel_head_append, self.TDRCelltype, self.channelCelltype, self.signature.get_global_name())
        self.rpc_channel_celltype_file_name = "{}/{}.cdl".format(G.gen, self.rpc_channel_celltype_name)
        # p "TransparentMarhslerPlugin: init: #{@rpc_channel_celltype_file_name}"

        if self.signature.need_PPAllocator():
            if self.PPAllocatorSize is None:
                self.cdl_error("RPC9999 PPAllocatorSize must be speicified for oneway [in] array")
                # @PPAllocatorSize = 0   # 仮に 0 としておく (cdl の構文エラーを避けるため)

    #=== CDL ファイルの生成
    # file::     FILE    生成するファイル
    def gen_cdl_file(self, file):
        # p "TransparentMarhslerPlugin: gen_cdl_file #{@rpc_channel_celltype_file_name}"
        self.gen_plugin_decl_code(file)

    #=== plugin の宣言コード (celltype の定義) 生成
    def gen_plugin_decl_code(self, file):
        file.print(
            "/*\n"
            " * genratedy by TransparentMarhsalerPlugin\n"
            "/ */\n"
            "import( \"{}\" );\n".format(self.rpc_channel_celltype_file_name)
        )

        ct_name = self.rpc_channel_celltype_file_name
        # このセルタイプ（同じシグニチャ）は既に生成されているか？
        if TransparentRPCSignaturePlugin.generated_celltype.get(ct_name) is None:
            TransparentRPCSignaturePlugin.generated_celltype[ct_name] = [self]
        else:
            TransparentRPCSignaturePlugin.generated_celltype[ct_name].append(self)
            return

        self.gen_marshaler_celltype()
        print(
            "[TransparentRPCSignaturePlugin]\n"
            "           create celltype {}\n"
            "                        in {}\n".format(
                self.rpc_channel_celltype_name,
                self.rpc_channel_celltype_file_name)
        )

        if self.PPAllocatorSize:
            alloc_cell = (
                "  cell tPPAllocator PPAllocator {{\n"
                "    heapSize = {};\n"
                "  }};\n".format(self.PPAllocatorSize)
            )
            alloc_call_port_join = "    cPPAllocator = PPAllocator.ePPAllocator;\n"
        else:
            alloc_cell = ""
            alloc_call_port_join = ""

        if self.b_noClientSemaphore is False:
            semaphore1 = (
                "  /* Semaphore for Multi-task use (\"specify noClientSemaphore\" option to delete this) / */\n"
                "  cell {} Semaphore {{\n"
                "    initialCount = 1;\n"
                "    attribute = C_EXP( \"TA_NULL\" );\n"
                "  }};\n".format(self.semaphoreCelltype)
            )
            semaphore2 = "    cLockChannel = Semaphore.eSemaphore;\n"
        else:
            semaphore1 = ""
            semaphore2 = ""

        # p "TransparentRPCSignaturePlugin: open #{@rpc_channel_celltype_file_name}"
        f = CFile.open(self.rpc_channel_celltype_file_name, "w")
        # 同じ内容を二度書く可能性あり (AppFile は不可)

        sig_nsp = self.signature.get_namespace_path()
        sig_gname = self.signature.get_global_name()
        ct = self.rpc_channel_celltype_name
        ct_full = self.rpc_channel_celltype_name_full
        call_port = self.call_port_name

        f.print(f"""\
/*
 * generated by TransparentRPCSignaturePlugin
 * for signature {sig_nsp}
/ */
import( "{self.marshaler_celltype_file_name}" );
import( <rpc/tDataqueueOWChannel.cdl> );

/****** Client Side Channel / ******/
composite {ct}_ClientSide {{
  /* Interface / */
  entry {sig_nsp} eThroughEntry;
  call sTDR       cTDR;
  call sEventflag cEventflag;

  /* Implementation / */
{semaphore1}  cell {self.marshaler_celltype_name} {sig_gname}_marshaler{{
    cTDR         => composite.cTDR;
    cEventflag   => composite.cEventflag;
{semaphore2}  }};
  composite.eThroughEntry => {sig_gname}_marshaler.eClientEntry;
}};

/****** Server Side Channel / ******/
composite {ct}_ServerSide {{
  /* Interface / */
  call {sig_nsp} cServerCall;
  call sTDR       cTDR;
  call sEventflag cEventflag;
  entry sTaskBody eMain;

  /* Implementation / */
{alloc_cell}  cell {self.unmarshaler_celltype_name} {sig_gname}_unmarshaler{{
    cTDR        => composite.cTDR;
    cEventflag  => composite.cEventflag;
    cServerCall => composite.cServerCall;
{alloc_call_port_join}  }};
  cell tRPCDedicatedTaskMain RPCTaskMain{{
    cMain = {sig_gname}_unmarshaler.eUnmarshalAndCallFunction;
  }};
  composite.eMain => RPCTaskMain.eMain;
}};

/****** Client & Server Combined Channel / ******/
[active]
composite {ct} {{
  /* Interface / */
  attr {{
    PRI taskPriority;
    size_t  stackSize = 4096;
    ATR     attribute = C_EXP( "TA_ACT" );  /* marshaler starts at the beginning / */
  }};
  entry {sig_nsp} eThroughEntry;
  call {sig_nsp} {call_port};
  call sTDR       cTDR;
  call sEventflag cEventflag;

  /* Implementation / */
  cell {ct}_ClientSide RPCChannel_ClientSide{{
    cTDR        => composite.cTDR;
    cEventflag  => composite.cEventflag;
  }};
  cell {ct}_ServerSide RPCChannel_ServerSide{{
    cTDR        => composite.cTDR;
    cEventflag  => composite.cEventflag;
    cServerCall => composite.{call_port};
  }};
  cell tTask Task {{
    cTaskBody = RPCChannel_ServerSide.eMain;
    priority  = composite.taskPriority;
    attribute = composite.attribute;
    stackSize = composite.stackSize;
  }};
  composite.eThroughEntry => RPCChannel_ClientSide.eThroughEntry;
}};

/****** Client & Server Combined Channel / ******/
[active]
composite {ct_full} {{
  /* Interface / */
  attr {{
    PRI taskPriority;
    size_t  stackSize = 4096;
    ATR     attribute = C_EXP( "TA_ACT" );  /* marshaler starts at the beginning / */
  }};
  entry {sig_nsp} eThroughEntry;
  call {sig_nsp} {call_port};

  /* Implementation / */
  cell {ct}_ClientSide RPCChannel_ClientSide{{
    cTDR         = Channel.eTDR;
    cEventflag   = Channel.eEventflag;
  }};
  cell {ct}_ServerSide RPCChannel_ServerSide{{
    cTDR         = Channel.eTDR;
    cEventflag   = Channel.eEventflag;
    cServerCall => composite.{call_port};
  }};
  cell tDataqueueOWChannel Channel {{
  }};
  cell tTask Task {{
    cTaskBody = RPCChannel_ServerSide.eMain;
    priority  = composite.taskPriority;
    attribute = composite.attribute;
    stackSize = composite.stackSize;
  }};
  composite.eThroughEntry => RPCChannel_ClientSide.eThroughEntry;
}};

""")
        # mikan stackSize option & 最新 tecs_package 対応

        f.close()

    #=== プラグイン引数 noClientSemaphore のチェック
    def set_noClientSemaphore(self, rhs):
        rhs = Sym(str(rhs))
        if rhs == Sym("true"):
            self.b_noClientSemaphore = True
        elif rhs == Sym("false"):
            self.b_noClientSemaphore = False
        else:
            self.cdl_error("RPC9999 specify true or false for noClientSemaphore")

    #=== プラグイン引数 semaphoreCelltype のチェック
    def set_semaphoreCelltype(self, rhs):
        self.semaphoreCelltype = Sym(str(rhs))
        nsp = NamespacePath.analyze(str(self.semaphoreCelltype))
        obj = Namespace.find(nsp)
        if not isinstance(obj, Celltype) and not isinstance(obj, CompositeCelltype):
            self.cdl_error("RPC9999 semaphoreCelltype '{}' not celltype or not defined".format(rhs))

    #=== プラグイン引数 datapumpholder のチェック
    def set_datapumpholder(self, rhs):
        rhs = Sym(str(rhs))
        if rhs == Sym("true"):
            self.b_datapumpholder = True
        elif rhs == Sym("false"):
            self.b_datapumpholder = False
        else:
            self.cdl_error("RPC9999 specify true or false for datapumpholder")
