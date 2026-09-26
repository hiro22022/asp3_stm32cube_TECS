# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#
#   このファイルは tecsgen (Ruby 版) の tecslib/plugin/OpaqueRPCPlugin.rb を
#   Python へ移植したものである．
#
#   $Id: OpaqueRPCPlugin.rb 3155 2020-06-28 12:57:32Z okuma-top $
#++

from tecslib.core import globals as G
from tecslib.core.componentobj.namespace import Namespace
from tecslib.core.plugin import CFile
from tecslib.plugin.ThroughPlugin import ThroughPlugin
from tecslib.plugin.lib.GenOpaqueMarshaler import GenOpaqueMarshaler, RPCPluginArgProc
from tecslib.plugin.lib.GenParamCopy import GenParamCopy
from tecslib.rubylib.symbol import Sym


def _set_noClientSemaphore(obj, rhs):
    obj.set_noClientSemaphore(rhs)


class OpaqueRPCPlugin(GenParamCopy, GenOpaqueMarshaler, ThroughPlugin):

    OpaqueRPCPluginArgProc = dict(RPCPluginArgProc)
    OpaqueRPCPluginArgProc["noClientSemaphore"] = _set_noClientSemaphore

    def __init__(self, cell_name, plugin_arg, next_cell, next_cell_port_name,
                 next_cell_port_subscript, signature, celltype, caller_cell):
        super().__init__(cell_name, plugin_arg, next_cell, next_cell_port_name,
                         next_cell_port_subscript, signature, celltype, caller_cell)
        self.b_noClientSemaphore = False
        self.initialize_opaque_marshaler()

        self.plugin_arg_check_proc_tab = OpaqueRPCPlugin.OpaqueRPCPluginArgProc
        self.parse_plugin_arg()
        self.check_opener_code()
        self.check_PPAllocator()

        print("OpaqueRPCPlugin: {}\n".format(self.clientChannelCell))

        self.rpc_server_channel_celltype_name = "tOpaqueRPCPlugin_{}_{}_{}".format(
            self.TDRCelltype, self.serverChannelCelltype, self.signature.get_global_name())
        self.rpc_server_channel_celltype_file_name = "{}/{}.cdl".format(
            G.gen, self.rpc_server_channel_celltype_name)
        self.rpc_client_channel_celltype_name = "tOpaqueRPCPlugin_{}_{}_{}".format(
            self.TDRCelltype, self.clientChannelCelltype, self.signature.get_global_name())
        self.rpc_client_channel_celltype_file_name = "{}/{}.cdl".format(
            G.gen, self.rpc_client_channel_celltype_name)

    def gen_plugin_decl_code(self, file):

        self.gen_marshaler_celltype()

        f = CFile.open(self.rpc_client_channel_celltype_file_name, "w")

        f.print("""\
import( "{}" );

/* RPC Client side composite celltype */
composite {} {{
  /* marshaler entry port */
  entry {} eThroughEntry;
  call  sChannel cChannel;
  [optional]
    call sRPCErrorHandler cErrorHandler;
  [optional]
    call sSemaphore cLockChannel;

  cell {} TDR {{
    cChannel => composite.cChannel;
  }};
  cell {} Marshaler{{
    cTDR = TDR.eTDR;
    cErrorHandler => composite.cErrorHandler;
    cLockChannel  => composite.cLockChannel;
  }};

  composite.eThroughEntry => Marshaler.eClientEntry;
}};
""".format(
            self.marshaler_celltype_file_name,
            self.rpc_client_channel_celltype_name,
            self.signature.get_namespace_path(),
            self.TDRCelltype,
            self.marshaler_celltype_name))
        f.close()

        if self.PPAllocatorSize:
            alloc_cell = "  cell tPPAllocator PPAllocator {{\n    heapSize = {};\n  }};\n".format(
                self.PPAllocatorSize)
            alloc_call_port_join = "    cPPAllocator = PPAllocator.ePPAllocator;\n"
        else:
            alloc_cell = ""
            alloc_call_port_join = ""

        f = CFile.open(self.rpc_server_channel_celltype_file_name, "w")

        f.print("""\
import( "{}" );

/* RPC Server side composite celltype */
composite {} {{
  /* Interface */
  call  {} {};
  call  sChannel   cChannel;
  [optional]
    call sRPCErrorHandler cErrorHandler;
  entry sUnmarshalerMain  eService;

  /* Implementation */
  cell {} TDR {{
    cChannel => composite.cChannel;
  }};
{}  cell {} Unmarshaler{{
    cTDR        = TDR.eTDR;
    cErrorHandler => composite.cErrorHandler;
    cServerCall => composite.{};
{}}};
  composite.eService => Unmarshaler.eService;
}};
""".format(
            self.marshaler_celltype_file_name,
            self.rpc_server_channel_celltype_name,
            self.signature.get_namespace_path(), self.call_port_name,
            self.TDRCelltype,
            alloc_cell,
            self.unmarshaler_celltype_name,
            self.call_port_name,
            alloc_call_port_join))
        f.close()

    def gen_through_cell_code(self, file):

        self.gen_plugin_decl_code(file)

        cell = Namespace.find(self.next_cell.get_namespace_path())

        file.print("""\
import( "{}" );
import( "{}" );

""".format(
            self.rpc_client_channel_celltype_file_name,
            self.rpc_server_channel_celltype_file_name))

        nest = self.start_region.gen_region_str_pre(file)
        nest_str = "  " * nest

        if self.b_noClientSemaphore is False:
            file.print("""\

{}  //  Semaphore for Multi-task use ("specify noClientSemaphore" option to delete this)
{}  cell {} {}_Semaphore{{
{}    {}
{}  }};
""".format(
                nest_str, nest_str, self.semaphoreCelltype, self.serverChannelCell,
                nest_str, self.semaphoreInitializer, nest_str))

        file.print("""\
{}  //  Client Side Channel
{}  cell {} {} {{
{}    {}
{}  }};

{}  //  Marshaler
""".format(
            nest_str, nest_str, self.clientChannelCelltype, self.clientChannelCell,
            nest_str, self.clientChannelInitializer, nest_str,
            nest_str))

        if self.b_noClientSemaphore is False:
            semaphore = "{}    cLockChannel = {}_Semaphore.eSemaphore;\n".format(
                nest_str, self.serverChannelCell)
        else:
            semaphore = ""

        if cell is not None and len(cell.get_allocator_list()) > 0:

            file.print(nest_str)
            file.print("[allocator(")

            delim = ""
            for type_, eport, subsc, func, buf, alloc in cell.get_allocator_list():

                alloc_str = str(alloc)
                subst = self.substituteAllocator.get(Sym(alloc_str))
                if subst:
                    alloc_str = subst[2] + "." + subst[3]

                file.print(delim)
                delim = ",\n"

                if subsc:
                    subsc_str = "[{}]".format(subsc)
                else:
                    subsc_str = ""

                eport = "eThroughEntry"
                file.print(nest_str)
                file.print("{}{}.{}.{} = {}".format(eport, subsc_str, func, buf, alloc_str))

            file.print(")]\n")

        if self.clientErrorHandler:
            clientErrorHandler_str = "{}    cErrorHandler = {};\n".format(
                nest_str, self.clientErrorHandler)
        else:
            clientErrorHandler_str = ""

        file.print("""\
{}  cell {} {} {{
{}    cChannel = {}.eC0;
{}{}  }};

""".format(
            nest_str, self.rpc_client_channel_celltype_name, self.cell_name,
            nest_str, self.clientChannelCell,
            clientErrorHandler_str, semaphore))

        self.start_region.gen_region_str_post(file)
        file.print("\n\n")

        nest = self.end_region.gen_region_str_pre(file)
        nest_str = "  " * nest
        if self.next_cell_port_subscript:
            subscript = '[' + str(self.next_cell_port_subscript) + ']'
        else:
            subscript = ""

        if self.serverErrorHandler:
            serverErrorHandler_str = "{}    cErrorHandler = {};\n".format(
                nest_str, self.serverErrorHandler)
        else:
            serverErrorHandler_str = ""

        if self.b_genOpener:
            opener = "{}    cOpener       = {}.eOpener;\n".format(
                nest_str, self.serverChannelCell)
        else:
            opener = ""

        file.print("""\

{}  //  Server Side Channel
{}  cell {} {} {{
{}    {}
{}  }};
""".format(
            nest_str, nest_str, self.serverChannelCelltype, self.serverChannelCell,
            nest_str, self.serverChannelInitializer, nest_str))

        file.print("""\

{}  //  Unmarshaler
{}  cell {} {}_Unmarshaler {{
{}    cChannel = {}.eC1;
{}    {} = {}.{}{};
{}{}  }};
""".format(
            nest_str, nest_str, self.rpc_server_channel_celltype_name, self.serverChannelCell,
            nest_str, self.serverChannelCell,
            nest_str, self.call_port_name, self.next_cell.get_namespace_path().get_path_str(),
            self.next_cell_port_name, subscript,
            serverErrorHandler_str, nest_str))

        file.print("""\

{}  //  Unmarshaler Task Main
{}  cell {} {}_TaskMain {{
{}    cMain         = {}_Unmarshaler.eService;
{}{}  }};
""".format(
            nest_str, nest_str, self.taskMainCelltype, self.serverChannelCell,
            nest_str, self.serverChannelCell,
            opener, nest_str))

        file.print("""\

{}  //  Unmarshaler Task
{}  cell {} {}_Task {{
{}    cTaskBody         = {}_TaskMain.eMain;
{}    priority      = {};
{}    stackSize     = {};
{}    attribute     = C_EXP( "TA_ACT" );  /* mikan : marshaler task starts at beginning */
{}  }};
""".format(
            nest_str, nest_str, self.taskCelltype, self.serverChannelCell,
            nest_str, self.serverChannelCell,
            nest_str, self.taskPriority,
            nest_str, self.stackSize,
            nest_str, nest_str))

        self.end_region.gen_region_str_post(file)

    def set_noClientSemaphore(self, rhs):
        rhs = Sym(str(rhs))
        if rhs == Sym("true"):
            self.b_noClientSemaphore = True
        elif rhs == Sym("false"):
            self.b_noClientSemaphore = False
        else:
            self.cdl_error("RPC9999 specify true or false for noClientSemaphore")
