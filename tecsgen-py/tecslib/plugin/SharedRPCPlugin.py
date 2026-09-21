# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#
#   このファイルは tecsgen (Ruby 版) の tecslib/plugin/SharedRPCPlugin.rb を
#   Python へ移植したものである．
#
#   $Id: SharedRPCPlugin.rb 3155 2020-06-28 12:57:32Z okuma-top $
#++

from tecslib.core import globals as G
from tecslib.core.componentobj.namespace import Namespace
from tecslib.core.plugin import CFile
from tecslib.plugin.ThroughPlugin import ThroughPlugin
from tecslib.plugin.lib.GenTransparentMarshaler import GenTransparentMarshaler, RPCPluginArgProc
from tecslib.plugin.lib.GenParamCopy import GenParamCopy


class SharedRPCPlugin(GenParamCopy, GenTransparentMarshaler, ThroughPlugin):

    shared_channel_list = {}

    def __init__(self, cell_name, plugin_arg, next_cell, next_cell_port_name,
                 next_cell_port_subscript, signature, celltype, caller_cell):

        super().__init__(cell_name, plugin_arg, next_cell, next_cell_port_name,
                         next_cell_port_subscript, signature, celltype, caller_cell)
        self.initialize_transparent_marshaler(cell_name)

        self.plugin_arg_check_proc_tab = RPCPluginArgProc
        self.channelCellName = ""
        self.parse_plugin_arg()

        self.shared_channel_ct_name = "tSharedRPCPlugin_{}".format(self.channelCelltype)
        self.shared_channel_ct_file_name = "{}/{}.cdl".format(G.gen, self.shared_channel_ct_name)
        self.rpc_channel_celltype_name = "tSharedRPCPlugin_{}_{}_{}".format(
            self.TDRCelltype, self.channelCelltype, self.signature.get_global_name())
        self.rpc_channel_celltype_file_name = "{}/{}.cdl".format(
            G.gen, self.rpc_channel_celltype_name)

        self.shared_channel_cell = self.channelCellName
        if self.shared_channel_cell == "":
            self.cdl_error("SharedRPCPlugin: need channelCellName option")

        if SharedRPCPlugin.shared_channel_list.get(self.shared_channel_cell) is None:
            SharedRPCPlugin.shared_channel_list[self.shared_channel_cell] = [self]
        else:
            SharedRPCPlugin.shared_channel_list[self.shared_channel_cell].append(self)
        self.sub_channel_no = len(SharedRPCPlugin.shared_channel_list[self.shared_channel_cell]) - 1

        prev = SharedRPCPlugin.shared_channel_list[self.shared_channel_cell][0]
        if self.region != prev.region:
            self.cdl_error(
                "SharedRPCPlugin: preferred region mismatch current: {} previous: {}".format(
                    self.region.get_name(), prev.region.get_name()))

        if self.signature.need_PPAllocator():
            if self.PPAllocatorSize is None:
                self.cdl_error("PPAllocatorSize must be speicified for oneway [in] array")

    def gen_plugin_decl_code(self, file):

        if ThroughPlugin.generated_celltype.get(self.shared_channel_ct_name) is None:
            ThroughPlugin.generated_celltype[self.shared_channel_ct_name] = [self]
        else:
            ThroughPlugin.generated_celltype[self.shared_channel_ct_name].append(self)

        if ThroughPlugin.generated_celltype.get(self.ct_name) is None:
            ThroughPlugin.generated_celltype[self.ct_name] = [self]
        else:
            ThroughPlugin.generated_celltype[self.ct_name].append(self)

        self.gen_marshaler_celltype()

        if self.signature.need_PPAllocator():
            alloc_call_port = "  call sPPAllocator cPPAllocator;\n"
            alloc_call_port_join = "  cPPAllocator => composite.cPPAllocator;\n"
        else:
            alloc_call_port = ""
            alloc_call_port_join = ""

        f = CFile.open(self.rpc_channel_celltype_file_name, "w")

        f.print("""\
import( "{}" );

composite {} {{
  /* Interface */
  call  {} {};
  entry {} eThroughEntry;
  call  sTDR       cTDR;
  call  sEventflag cEventflag;
  entry sUnmarshalerMain  eUnmarshalAndCallFunction;
{}
  [optional]
    call sSemaphore cLockChannel;

  /* Implementation */
  cell {} {}_marshaler{{
    cTDR         => composite.cTDR;
    cEventflag   => composite.cEventflag;
    cLockChannel => composite.cLockChannel;
  }};
  cell {} {}_unmarshaler{{
    cTDR         => composite.cTDR;
    cEventflag   => composite.cEventflag;
    cServerCall  => composite.{};
{}  }};
  composite.eThroughEntry => {}_marshaler.eClientEntry;
  composite.eUnmarshalAndCallFunction => {}_unmarshaler.eUnmarshalAndCallFunction;
}};
""".format(
            self.marshaler_celltype_file_name,
            self.rpc_channel_celltype_name,
            self.signature.get_namespace_path(), self.call_port_name,
            self.signature.get_namespace_path(),
            alloc_call_port,
            self.marshaler_celltype_name, self.signature.get_global_name(),
            self.unmarshaler_celltype_name, self.signature.get_global_name(),
            self.call_port_name,
            alloc_call_port_join,
            self.signature.get_global_name(),
            self.signature.get_global_name()))
        f.close()

        f = CFile.open("{}/{}.cdl".format(G.gen, self.shared_channel_ct_name), "w")

        f.print("""\
[active]
composite {} {{
  /* Interface */
  entry  sSemaphore eSemaphore[];
  call   sUnmarshalerMain  cUnmarshalAndCallFunction[];

  entry  sDataqueue eDataqueue;
  entry  sTDR       eTDR;
  entry  sEventflag eEventflag;

  attr {{
    PRI    priority;
  }};

  /* Implementation */
  cell {} Channel{{
  }};
  cell tSemaphore Semaphore {{initialCount = 1; attribute = C_EXP("TA_NULL");}};
  cell tRPCSharedTaskMain RPCSharedTaskMain {{
    cUnmarshalAndCallFunction => composite.cUnmarshalAndCallFunction;
    cServerSideTDR            = Channel.eTDR;
  }};
  cell tRPCSharedChannelMan RPCChannelMan {{
    cSemaphore                = Semaphore.eSemaphore;
    cClientSideTDR            = Channel.eTDR;
  }};
  cell tTask RPCSharedTask {{
    cTaskBody = RPCSharedTaskMain.eMain;
    attribute = C_EXP("TA_ACT");
    stackSize = 4096;
    priority = composite.priority;
  }};
  composite.eTDR           => Channel.eTDR;
  composite.eEventflag     => Channel.eEventflag;
  composite.eSemaphore     => RPCChannelMan.eSemaphore;
  composite.eDataqueue     => Channel.eDataqueue;
}};
""".format(self.shared_channel_ct_name, self.channelCelltype))
        f.close()

    def gen_through_cell_code(self, file):

        self.gen_plugin_decl_code(file)

        file.print("""\
import( "{}" );
import( "{}/{}.cdl" );
""".format(
            self.rpc_channel_celltype_file_name,
            G.gen, self.shared_channel_ct_name))

        nest = self.region.gen_region_str_pre(file)
        indent_str = "  " * nest
        if self.next_cell_port_subscript:
            subscript = '[' + str(self.next_cell_port_subscript) + ']'
        else:
            subscript = ""

        cell = Namespace.find(self.next_cell.get_namespace_path())

        if self.signature.need_PPAllocator():
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

        file.print("{}cell {} {};\n".format(
            indent_str, self.shared_channel_ct_name, self.shared_channel_cell))

        if cell is not None and len(cell.get_allocator_list()) > 0:

            file.print("{}[allocator(".format(indent_str))

            delim = ""
            for type_, eport, subsc, func, buf, alloc in cell.get_allocator_list():

                file.print(delim)
                delim = ",\n{}           ".format(indent_str)

                if subsc:
                    subsc_str = "[{}]".format(subsc)
                else:
                    subsc_str = ""

                eport = "eThroughEntry"
                file.print("{}{}.{}.{} = {}".format(eport, subsc_str, func, buf, alloc))

            file.print(")]\n")

        file.print("""\
{}cell {} {} {{
{}  {} = {}.{}{};
{}  cTDR         = {}.eTDR;
{}  cEventflag   = {}.eEventflag;
{}  cLockChannel =  {}.eSemaphore[{}];
{}{}}};
""".format(
            indent_str, self.rpc_channel_celltype_name, self.cell_name,
            indent_str, self.call_port_name, self.next_cell.get_name(),
            self.next_cell_port_name, subscript,
            indent_str, self.shared_channel_cell,
            indent_str, self.shared_channel_cell,
            indent_str, self.shared_channel_cell, self.sub_channel_no,
            ppallocator_join, indent_str))

        self.region.gen_region_str_post(file)

    @classmethod
    def gen_post_code(cls, file):
        file.print("/* '{}' post code */\n".format(cls.__name__))
        for chan_name, plugin_obj in SharedRPCPlugin.shared_channel_list.items():
            plugin_obj[0].gen_post_code_body(file, plugin_obj)

    def gen_post_code_body(self, file, plugin_obj):

        chan_name = self.shared_channel_cell

        nest = self.region.gen_region_str_pre(file)
        indent_str = "  " * nest

        file.print("{}cell tSharedRPCPlugin_{} {} {{\n".format(
            indent_str, self.channelCelltype, chan_name))
        for po in plugin_obj:
            file.print("""\
{}    cUnmarshalAndCallFunction[] = {}.eUnmarshalAndCallFunction;
""".format(indent_str, po.cell_name))
        file.print("{}    priority = {};\n{}}};\n".format(
            indent_str, self.task_priority, indent_str))
        self.region.gen_region_str_post(file)
