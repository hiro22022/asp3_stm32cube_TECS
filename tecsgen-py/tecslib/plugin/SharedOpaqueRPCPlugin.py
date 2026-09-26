# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#
#   このファイルは tecsgen (Ruby 版) の tecslib/plugin/SharedOpaqueRPCPlugin.rb を
#   Python へ移植したものである．
#
#   $Id: SharedOpaqueRPCPlugin.rb 3155 2020-06-28 12:57:32Z okuma-top $
#++

from tecslib.core import globals as G
from tecslib.core.componentobj.namespace import Namespace
from tecslib.core.plugin import CFile
from tecslib.plugin.ThroughPlugin import ThroughPlugin
from tecslib.plugin.lib.GenOpaqueMarshaler import GenOpaqueMarshaler, RPCPluginArgProc
from tecslib.plugin.lib.GenParamCopy import GenParamCopy
from tecslib.rubylib.symbol import Sym


def _set_sharedChannelName(obj, rhs):
    obj.set_sharedChannelName(rhs)


class SharedOpaqueRPCPlugin(GenParamCopy, GenOpaqueMarshaler, ThroughPlugin):

    shared_channel_list = {}

    SharedOpaqueRPCPluginArgProc = dict(RPCPluginArgProc)
    SharedOpaqueRPCPluginArgProc["sharedChannelName"] = _set_sharedChannelName

    def __init__(self, cell_name, plugin_arg, next_cell, next_cell_port_name,
                 next_cell_port_subscript, signature, celltype, caller_cell):
        super().__init__(cell_name, plugin_arg, next_cell, next_cell_port_name,
                         next_cell_port_subscript, signature, celltype, caller_cell)
        self.initialize_opaque_marshaler()
        self.entry_port_name = Sym("eClientEntry")

        self.plugin_arg_check_proc_tab = SharedOpaqueRPCPlugin.SharedOpaqueRPCPluginArgProc
        self.sharedChannelName = None
        self.parse_plugin_arg()
        self.check_opener_code()
        self.check_PPAllocator()

        self.shared_channel_ct_name = "tSharedOpaqueRPCPluginChannel_tTDR"
        self.shared_channel_server_ct_name = "{}_Server".format(self.shared_channel_ct_name)
        self.shared_channel_client_ct_name = "{}_Client".format(self.shared_channel_ct_name)
        self.shared_channel_ct_file_name = "{}/{}.cdl".format(G.gen, self.shared_channel_ct_name)
        if self.sharedChannelName is None:
            self.cdl_error("'sharedChannelName' option: mandatory")
        else:
            self.shared_channel_cell = self.sharedChannelName

        if SharedOpaqueRPCPlugin.shared_channel_list.get(self.shared_channel_cell) is None:
            SharedOpaqueRPCPlugin.shared_channel_list[self.shared_channel_cell] = [self]
        else:
            SharedOpaqueRPCPlugin.shared_channel_list[self.shared_channel_cell].append(self)
        self.sub_channel_no = len(SharedOpaqueRPCPlugin.shared_channel_list[self.shared_channel_cell]) - 1

        prev_start = SharedOpaqueRPCPlugin.shared_channel_list[self.shared_channel_cell][0].start_region
        if self.start_region != prev_start:
            self.cdl_error(
                "SharedRPCPlugin: start region mismatch current: {} previous: {}".format(
                    self.region.get_name(), prev_start.get_name()))

        prev_end = SharedOpaqueRPCPlugin.shared_channel_list[self.shared_channel_cell][0].end_region
        if self.end_region != prev_end:
            self.cdl_error(
                "SharedRPCPlugin: end region mismatch current: {} previous: {}".format(
                    self.region.get_name(), prev_end.get_name()))

    def set_sharedChannelName(self, rhs):
        self.sharedChannelName = rhs

    def gen_plugin_decl_code(self, file):

        if ThroughPlugin.generated_celltype.get(self.shared_channel_server_ct_name) is None:
            ThroughPlugin.generated_celltype[self.shared_channel_server_ct_name] = [self]
        else:
            ThroughPlugin.generated_celltype[self.shared_channel_server_ct_name].append(self)

        self.gen_marshaler_celltype()

        if self.PPAllocatorSize:
            alloc_call_port = "  call sPPAllocator cPPAllocator;\n"
            alloc_call_port_join = "  cPPAllocator => composite.cPPAllocator;\n"
        else:
            alloc_call_port = ""
            alloc_call_port_join = ""

        f = CFile.open(self.shared_channel_ct_file_name, "w")

        f.print("""\

/* Shared Channel Celltype for Client */
composite {} {{
  entry  sTDR       eTDR;
  entry  sSemaphore eSemaphore[];
  call   sChannel   cClientChannel;

  cell tTDR TDR {{
    cChannel => composite.cClientChannel;
  }};
  cell tSemaphore Semaphore {{
    initialCount = 1;
    attribute = C_EXP("TA_NULL");
  }};
  cell tRPCSharedChannelMan SharedChannelMan{{
    cSemaphore             = Semaphore.eSemaphore;
    cClientSideTDR         = TDR.eTDR;
  }};
  composite.eSemaphore     => SharedChannelMan.eSemaphore;
  composite.eTDR           => TDR.eTDR;
}};

/* Shared Channel Celltype for Server */
[active]
composite {} {{
  entry  sTDR       eTDR;
  call   sChannel   cServerChannel;
  call   sUnmarshalerMain  cUnmarshalAndCallFunction[];
  call   sServerChannelOpener cOpener;
  attr {{
    PRI    priority;
  }};

  cell tTDR TDR {{
    cChannel => composite.cServerChannel;
  }};
  cell tRPCSharedTaskMainWithOpener RPCSharedTaskMain {{
    cUnmarshalAndCallFunction => composite.cUnmarshalAndCallFunction;
    cServerSideTDR = TDR.eTDR;
    cOpener => composite.cOpener;
  }};
  cell tTask Task {{
    cTaskBody = RPCSharedTaskMain.eMain;
    attribute = C_EXP("TA_ACT");
    stackSize = 4096;
    priority = composite.priority;
  }};
  composite.eTDR           => TDR.eTDR;
}};

""".format(self.shared_channel_client_ct_name, self.shared_channel_server_ct_name))
        f.close()

    def gen_through_cell_code(self, file):

        self.gen_plugin_decl_code(file)

        file.print("""\

import( "{}" );
import( "{}" );
""".format(self.marshaler_celltype_file_name, self.shared_channel_ct_file_name))

        nest = self.start_region.gen_region_str_pre(file)
        indent_str = "  " * nest
        if self.next_cell_port_subscript:
            subscript = '[' + str(self.next_cell_port_subscript) + ']'
        else:
            subscript = ""

        cell = Namespace.find(self.next_cell.get_namespace_path())

        file.print("{}cell {} {};\n".format(
            indent_str, self.shared_channel_client_ct_name, self.shared_channel_cell))

        if cell is not None and len(cell.get_allocator_list()) > 0:

            file.print("{}[allocator(".format(indent_str))

            delim = ""
            for type_, eport, subsc, func, buf, alloc in cell.get_allocator_list():

                alloc_str = str(alloc)
                subst = self.substituteAllocator.get(Sym(alloc_str))
                if subst:
                    alloc_str = subst[2] + "." + subst[3]

                file.print(delim)
                delim = ",\n{}           ".format(indent_str)

                if subsc:
                    subsc_str = "[{}]".format(subsc)
                else:
                    subsc_str = ""

                eport = self.entry_port_name
                file.print("{}{}.{}.{} = {}".format(eport, subsc_str, func, buf, alloc_str))

            file.print(")]\n")

        file.print("""\
/* OpaqueRPC Marshaler Cell */
{}cell {} {} {{
{}  cTDR         = {}.eTDR;
{}  cLockChannel = {}.eSemaphore[{}];
{}}};
""".format(
            indent_str, self.marshaler_celltype_name, self.cell_name,
            indent_str, self.shared_channel_cell,
            indent_str, self.shared_channel_cell, self.sub_channel_no,
            indent_str))

        self.start_region.gen_region_str_post(file)

        nest = self.end_region.gen_region_str_pre(file)

        file.print("""\
/* Server Channel Cell prototype */
{}cell {} {}_Server;

""".format(indent_str, self.shared_channel_server_ct_name, self.sharedChannelName))

        if self.PPAllocatorSize:
            if self.sub_channel_no == 0:
                file.print("""\
{}cell tPPAllocator PPAllocator_{}{{
{}  heapSize = {};
{}}};
""".format(indent_str, self.shared_channel_cell, indent_str, self.PPAllocatorSize, indent_str))

            ppallocator_join = "{}  cPPAllocator = PPAllocator_{}.ePPAllocator;\n".format(
                indent_str, self.shared_channel_cell)
        else:
            ppallocator_join = ""

        file.print("""\
{}cell {} {}_Server {{
{}  cTDR         = {}_Server.eTDR;
{}  cServerCall  = {}.{}{};
{}{}}};
""".format(
            indent_str, self.unmarshaler_celltype_name, self.cell_name,
            indent_str, self.shared_channel_cell,
            indent_str, self.next_cell.get_namespace_path().get_path_str(),
            self.next_cell_port_name, subscript,
            ppallocator_join, indent_str))

        self.end_region.gen_region_str_post(file)

    @classmethod
    def gen_post_code(cls, file):

        file.print("/* '{}' post code */\n".format(cls.__name__))

        for chan_name, plugin_obj_array in SharedOpaqueRPCPlugin.shared_channel_list.items():
            file.print("/* '{}' shared channel */\n".format(chan_name))
            plugin_obj_array[0].gen_post_code_body(file, plugin_obj_array)

    def gen_post_code_body(self, file, plugin_obj_array):

        nest = self.start_region.gen_region_str_pre(file)
        indent_str = "  " * nest
        file.print("""\
{}cell {} {} {{
{}    cClientChannel = {}.eC0;
{}}};
""".format(
            indent_str, self.shared_channel_client_ct_name, self.sharedChannelName,
            indent_str, self.clientChannelCell,
            indent_str))
        self.start_region.gen_region_str_post(file)

        nest = self.end_region.gen_region_str_pre(file)
        indent_str = "  " * nest
        file.print("{}cell {} {}_Server {{\n".format(
            indent_str, self.shared_channel_server_ct_name, self.sharedChannelName))
        file.print("""\
{}    cServerChannel = {}.eC1;
{}    cOpener        = {}.eOpener;
""".format(indent_str, self.serverChannelCell, indent_str, self.serverChannelCell))
        for po in plugin_obj_array:
            file.print("""\
{}    cUnmarshalAndCallFunction[] = {}_Server.eService;
""".format(indent_str, po.cell_name))
        file.print("{}    priority = {};\n{}}};\n".format(
            indent_str, self.taskPriority, indent_str))
        self.end_region.gen_region_str_post(file)
