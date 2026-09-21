# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#
#   このファイルは tecsgen (Ruby 版) の tecslib/plugin/lib/GenOpaqueMarshaler.rb を
#   Python へ移植したものである．
#
#   $Id: GenOpaqueMarshaler.rb 3176 2020-10-25 08:07:05Z okuma-top $
#

import re

from tecslib.rubylib.symbol import Sym
from tecslib.core import globals as G
from tecslib.core.expression import Expression
from tecslib.core.plugin import CFile
from tecslib.core.types import (
    DefinedType, BoolType, IntType, FloatType, PtrType, StructType,
    VoidType, EnumType, FuncType, ArrayType,
)
from tecslib.core.componentobj.namespacepath import NamespacePath
from tecslib.core.componentobj.namespace import Namespace
from tecslib.core.componentobj.celltype import Celltype
from tecslib.core.componentobj.compositecelltype import CompositeCelltype
from tecslib.core.componentobj.port import Port


def _opaque_set_taskPriority(obj, rhs):
    obj.set_taskPriority(rhs)


def _opaque_set_serverChannelCelltype(obj, rhs):
    obj.set_serverChannelCelltype(rhs)


def _opaque_set_clientChannelCelltype(obj, rhs):
    obj.set_clientChannelCelltype(rhs)


def _opaque_set_serverChannelCell(obj, rhs):
    obj.set_serverChannelCell(rhs)


def _opaque_set_clientChannelCell(obj, rhs):
    obj.set_clientChannelCell(rhs)


def _opaque_set_clientChannelInitializer(obj, rhs):
    obj.set_clientChannelInitializer(rhs)


def _opaque_set_serverChannelInitializer(obj, rhs):
    obj.set_serverChannelInitializer(rhs)


def _opaque_set_clientSemaphoreCelltype(obj, rhs):
    obj.set_clientSemaphoreCelltype(rhs)


def _opaque_set_clientSemaphoreInitializer(obj, rhs):
    obj.set_clientSemaphoreInitializer(rhs)


def _opaque_set_clientErrorHandler(obj, rhs):
    obj.set_clientErrorHandler(rhs)


def _opaque_set_serverErrorHandler(obj, rhs):
    obj.set_serverErrorHandler(rhs)


def _opaque_set_TDRCelltype(obj, rhs):
    obj.set_TDRCelltype(rhs)


def _opaque_set_PPAllocatorSize(obj, rhs):
    obj.set_PPAllocatorSize(rhs)


def _opaque_set_substituteAllocator(obj, rhs):
    obj.set_substituteAllocator(rhs)


def _opaque_set_noServerChannelOpenerCode(obj, rhs):
    obj.set_noServerChannelOpenerCode(rhs)


def _opaque_set_taskCelltype(obj, rhs):
    obj.set_taskCelltype(rhs)


def _opaque_set_stackSize(obj, rhs):
    obj.set_stackSize(rhs)


#== GenOpaqueMarshaler
# OpaqueRPCPlugin, sharedOpaqueRPCPlugin 共通の要素を集めたモジュール
RPCPluginArgProc = {
    "clientChannelCelltype": _opaque_set_clientChannelCelltype,
    "serverChannelCelltype": _opaque_set_serverChannelCelltype,
    "clientChannelCell": _opaque_set_clientChannelCell,
    "serverChannelCell": _opaque_set_serverChannelCell,
    "clientChannelInitializer": _opaque_set_clientChannelInitializer,
    "serverChannelInitializer": _opaque_set_serverChannelInitializer,
    "clientSemaphoreCelltype": _opaque_set_clientSemaphoreCelltype,
    "clientSemaphoreInitializer": _opaque_set_clientSemaphoreInitializer,
    "clientErrorHandler": _opaque_set_clientErrorHandler,
    "serverErrorHandler": _opaque_set_serverErrorHandler,
    "TDRCelltype": _opaque_set_TDRCelltype,
    "PPAllocatorSize": _opaque_set_PPAllocatorSize,
    "substituteAllocator": _opaque_set_substituteAllocator,
    "noServerChannelOpenerCode": _opaque_set_noServerChannelOpenerCode,
    "taskCelltype": _opaque_set_taskCelltype,
    "taskPriority": _opaque_set_taskPriority,
    "stackSize": _opaque_set_stackSize,
}


class GenOpaqueMarshaler:

    def set_taskPriority(self, rhs):
        self.taskPriority = rhs

    def set_serverChannelCelltype(self, rhs):
        self.serverChannelCelltype = Sym(str(rhs))
        nsp = NamespacePath.analyze(str(self.serverChannelCelltype))
        obj = Namespace.find(nsp)
        if not (type(obj) is Celltype) and not (type(obj) is CompositeCelltype):
            self.cdl_error("RPCPlugin: serverChannelCelltype '{}' not celltype or not defined".format(rhs))

    def set_clientChannelCelltype(self, rhs):
        self.clientChannelCelltype = Sym(str(rhs))
        nsp = NamespacePath.analyze(str(self.clientChannelCelltype))
        obj = Namespace.find(nsp)
        if not (type(obj) is Celltype) and not (type(obj) is CompositeCelltype):
            self.cdl_error("RPCPlugin: clientChanneclCelltype '{}' not celltype or not defined".format(rhs))

    def set_serverChannelCell(self, rhs):
        self.serverChannelCell = Sym(str(rhs))

    def set_clientChannelCell(self, rhs):
        self.clientChannelCell = Sym(str(rhs))

    def set_serverChannelInitializer(self, rhs):
        self.serverChannelInitializer = Sym(str(rhs))

    def set_clientChannelInitializer(self, rhs):
        self.clientChannelInitializer = Sym(str(rhs))

    def set_taskCelltype(self, rhs):
        self.taskCelltype = Sym(str(rhs))
        nsp = NamespacePath.analyze(str(self.taskCelltype))
        obj = Namespace.find(nsp)
        if not (type(obj) is Celltype) and not (type(obj) is CompositeCelltype):
            self.cdl_error("RPCPlugin: taskCelltype '{}' not celltype or not defined".format(rhs))

    def set_stackSize(self, rhs):
        self.stackSize = rhs

    def set_PPAllocatorSize(self, rhs):
        self.PPAllocatorSize = rhs

    def set_TDRCelltype(self, rhs):
        self.TDRCelltype = Sym(str(rhs))
        nsp = NamespacePath.analyze(str(self.TDRCelltype))
        obj = Namespace.find(nsp)
        if not (type(obj) is Celltype) and not (type(obj) is CompositeCelltype):
            self.cdl_error("RPCPlugin: TDRCelltype '{}' not celltype or not found".format(rhs))

    def set_substituteAllocator(self, rhs):
        def optparse(s, regexp, expected):
            s = s.lstrip()
            m = re.match(regexp, s)
            if not m:
                self.cdl_error(
                    "syntax error in substituteAllocator option near '{}', expected '{}'".format(s, expected))
            return m.group(0), s[m.end():]

        opt = str(rhs)
        ident_rexpr = r'(\w[\w\d]*)'

        while True:
            lhs_alloc_cell, opt = optparse(opt, r'\A' + ident_rexpr, "allocator cell name")
            if not lhs_alloc_cell:
                break

            token, opt = optparse(opt, r'\A\.', ".")
            if not token:
                break

            lhs_alloc_ent, opt = optparse(opt, r'\A' + ident_rexpr, "allocator cell entry name")
            if not lhs_alloc_ent:
                break

            token, opt = optparse(opt, r'\A\=\>', "=>")
            if not token:
                break

            rhs_alloc_cell, opt = optparse(opt, r'\A' + ident_rexpr, "allocator cell name")
            if not rhs_alloc_cell:
                break

            token, opt = optparse(opt, r'\A\.', ".")
            if not token:
                break

            rhs_alloc_ent, opt = optparse(opt, r'\A' + ident_rexpr, "allocator cell entry name")
            if not rhs_alloc_ent:
                break

            self.substituteAllocator[Sym("{}".format(lhs_alloc_cell + "." + lhs_alloc_ent))] = [
                lhs_alloc_cell, lhs_alloc_ent, rhs_alloc_cell, rhs_alloc_ent]

            if not opt:
                break

            token, opt = optparse(opt, r'\A\,', ",")
            if not token:
                break

    def set_noServerChannelOpenerCode(self, rhs):
        rhs = Sym(str(rhs))
        if rhs == Sym("true"):
            self.noServerChannelOpenerCode = True
        elif rhs == Sym("false"):
            self.noServerChannelOpenerCode = False
        else:
            self.cdl_error("RPCPlugin: specify true or false for noServerChannelOpenerCode")

    def set_clientSemaphoreCelltype(self, rhs):
        self.semaphoreCelltype = Sym(str(rhs))
        nsp = NamespacePath.analyze(str(self.semaphoreCelltype))
        obj = Namespace.find(nsp)
        if not (type(obj) is Celltype) and not (type(obj) is CompositeCelltype):
            self.cdl_error("RPCPlugin: clientSemaphoreCelltype '{}' not celltype or not defined".format(rhs))

    def set_clientSemaphoreInitializer(self, rhs):
        self.semaphoreInitializer = Sym(str(rhs))

    def set_clientErrorHandler(self, rhs):
        self.clientErrorHandler = Sym(str(rhs))

    def set_serverErrorHandler(self, rhs):
        self.serverErrorHandler = Sym(str(rhs))

    def get_cell_name(self):
        return self.cell_name

    def initialize_opaque_marshaler(self):
        self.taskPriority = 9
        self.stackSize = 4096
        self.serverChannelCelltype = Sym("tSocketServer")
        self.clientChannelCelltype = Sym("tSocketClient")
        cell_name = getattr(self, "cell_name", None)
        if cell_name is None:
            ch_prefix = ""
        else:
            ch_prefix = str(cell_name)
        self.serverChannelCell = Sym("{}Server".format(ch_prefix))
        self.clientChannelCell = Sym("{}Client".format(ch_prefix))
        self.serverChannelInitializer = Sym(self.subst_name("portNo=8931+$count$;"))
        self.clientChannelInitializer = Sym(
            self.subst_name('portNo=8931+$count$; serverAddr="127.0.0.1"; '))
        self.taskCelltype = Sym("tTask")
        self.PPAllocatorSize = None
        self.TDRCelltype = Sym("tNBOTDR")
        self.substituteAllocator = {}
        self.noServerChannelOpenerCode = False
        self.semaphoreCelltype = Sym("tSemaphore")
        self.semaphoreInitializer = Sym('initialCount = 1; attribute = C_EXP( "TA_NULL" ); ')
        self.clientErrorHandler = None
        self.serverErrorHandler = None
        self.b_genOpener = False
        self.taskMainCelltype = Sym("tRPCDedicatedTaskMain")

        self.marshaler_celltype_name = "tOpaqueMarshaler_{}".format(self.signature.get_global_name())
        self.unmarshaler_celltype_name = "tOpaqueUnmarshaler_{}".format(self.signature.get_global_name())
        self.marshaler_celltype_file_name = "{}/{}.cdl".format(G.gen, self.marshaler_celltype_name)

        if self.signature.get_context() != "task":
            self.cdl_error(
                "OPQ9999 context of signature ($1) must be 'task'. $2 is not compatible with RPCPlugin",
                self.signature.get_name(), self.signature.get_context())

        def check_out_param(func_decl, param_decl):
            if param_decl.get_direction() == "OUT":
                if param_decl.get_count() and not param_decl.get_size():
                    self.cdl_error(
                        "{}.{}.{}: size_is must be specified for out parameter of Opaque RPC".format(
                            self.signature.get_namespace_path(), func_decl.get_name(), param_decl.get_name()))
                if param_decl.get_string() == -1:
                    self.cdl_error(
                        "{}.{}.{}: string length must be specified for out parameter of Opaque RPC".format(
                            self.signature.get_namespace_path(), func_decl.get_name(), param_decl.get_name()))

        self.signature.each_param(check_out_param)

    def check_opener_code(self):
        nsp = NamespacePath.analyze(str(self.serverChannelCelltype))
        scct = Namespace.find(nsp)
        if scct:
            obj = scct.find(Sym("eOpener"))
            if type(obj) is Port:
                if Sym(str(obj.get_signature().get_name())) == Sym("sServerChannelOpener"):
                    if self.noServerChannelOpenerCode is False:
                        self.b_genOpener = True
                        self.taskMainCelltype = Sym("tRPCDedicatedTaskMainWithOpener")
        if (self.noServerChannelOpenerCode is False
                and self.taskMainCelltype != Sym("tRPCDedicatedTaskMainWithOpener")):
            self.cdl_warning(
                "O9999 ServerChannelOpener code not generated, not found 'entry sServerChannelOpener eOpener'")

    def check_PPAllocator(self):
        if self.signature.need_PPAllocator(True):
            if self.PPAllocatorSize is None:
                self.cdl_error("PPAllocatorSize must be speicified for size_is array")

    def gen_marshaler_celltype(self):
        f = CFile.open(self.marshaler_celltype_file_name, "w")

        if self.PPAllocatorSize:
            alloc_call_port = "  call sPPAllocator cPPAllocator;\n"
        else:
            alloc_call_port = ""

        f.print("""\
// GenOpaqueMarshler0001
celltype {} {{
  entry {} eClientEntry;
  call sTDR       cTDR;
  [optional]
    call sSemaphore cLockChannel;
  [optional]
    call sRPCErrorHandler cErrorHandler;
}};
celltype {} {{
  call {} cServerCall;
  call  sTDR       cTDR;
  [optional]
    call sRPCErrorHandler cErrorHandler;
  entry sUnmarshalerMain  eService;
{}}};
""".format(
            self.marshaler_celltype_name,
            self.signature.get_namespace_path(),
            self.unmarshaler_celltype_name,
            self.signature.get_namespace_path(),
            alloc_call_port))
        f.close()

    def _unmarshaler_ct(self, ct_name):
        return str(ct_name) == str(self.unmarshaler_celltype_name)

    def gen_ep_func_body(self, file, b_singleton, ct_name, global_ct_name, sig_name, ep_name,
                         func_name, func_global_name, func_type, params):
        if self._unmarshaler_ct(ct_name):
            self.gen_ep_func_body_unmarshal(
                file, b_singleton, ct_name, global_ct_name, sig_name, ep_name,
                func_name, func_global_name, func_type, params)
        else:
            self.gen_ep_func_body_marshal(
                file, b_singleton, ct_name, global_ct_name, sig_name, ep_name,
                func_name, func_global_name, func_type, params)


    def gen_ep_func_body_marshal(self, file, b_singleton, ct_name, global_ct_name, sig_name,
                                 ep_name, func_name, func_global_name, func_type, params):
        b_void = False
        b_ret_er = False

        type_ = func_type.get_type().get_original_type()

        file.print("\t// GenOpaqueMarshler0010\n")
        if not type_.is_void():
            file.print("\t{}\t\tretval_;\n".format(func_type.get_type().get_type_str()))
            if (isinstance(func_type.get_type(), DefinedType)
                    and func_type.get_type().get_type_str() in ("ER", "ER_INT")):
                b_ret_er = True
        else:
            b_void = True

        file.print("\tER\t\tercd_;\n")
        file.print("\tint16_t\tstate_;\n")

        func_id = "FUNCID_{}_{}".format(self.signature.get_global_name(), func_name).upper()
        fid = self.signature.get_id_from_func_name(func_name)
        file.print("\tint16_t\tfunc_id_ = {};\t/* (id of '{}') = {}*/\n".format(func_id, func_name, fid))

        if not b_singleton:
            file.print("""\
\t{}_CB *p_cellcb;

\tif( VALID_IDX( idx ) ){{
\t\tp_cellcb = GET_CELLCB(idx);
""".format(ct_name))
            if b_ret_er:
                file.print("""\
\t}else{
\t\treturn ERCD( E_RPC, E_ID );
\t}
""")
            else:
                file.print("""\
\t}else{
\t\t/* エラー処理コードをここに記述 */
\t}

""")

        if func_type.has_receive():
            file.print("\t/* initialize receive parameters */\n")
            for param in params:
                if param.get_direction() == "RECEIVE":
                    file.print("\t*{} = 0;\n".format(param.get_name()))

        file.print("""\
\t/* Channel Lock (GenOpaqueMarshler0012) */
\tSET_RPC_STATE( state_, RPCSTATE_CLIENT_GET_SEM );
\tif( is_cLockChannel_joined() ){
\t\tif( (ercd_=cLockChannel_wait()) != E_OK )
\t\t\tgoto error_reset;
\t}
""")

        file.print("\t/* SOPの送出 (GenOpaqueMarshler0013) */\n")
        file.print("\tSET_RPC_STATE( state_, RPCSTATE_CLIENT_SEND_SOP );\n")
        file.print("\tif( ( ercd_ = cTDR_sendSOP( true ) ) != E_OK )\n")
        file.print("\t\tgoto error_reset;\n")

        file.print("\t/* 関数 id の送出 (GenOpaqueMarshler0014) */\n")
        file.print("\tif( ( ercd_ = cTDR_putInt16( func_id_ ) ) != E_OK )\n")
        file.print("\t\tgoto error_reset;\n")

        b_get = False
        b_marshal = True

        if func_type.has_inward():
            file.print("\t/* 入力引数送出 (GenOpaqueMarshler0015) */\n")
            file.print("\tSET_RPC_STATE( state_, RPCSTATE_CLIENT_SEND_BODY );\n")
            self.print_params(params, file, 1, b_marshal, b_get, True, "eClientEntry", func_name)
            self.print_params(params, file, 1, b_marshal, b_get, False, "eClientEntry", func_name)
        self.print_out_nullable(params, file, 1, b_marshal)

        b_continue = "true" if not func_type.is_oneway() else "false"
        file.print("\t/* EOPの送出（パケットの掃きだし）(GenOpaqueMarshler0016) */\n")
        file.print("\tSET_RPC_STATE( state_, RPCSTATE_CLIENT_SEND_EOP );\n")
        file.print("\tif( (ercd_=cTDR_sendEOP({})) != E_OK )\n".format(b_continue))
        file.print("\t\tgoto error_reset;\n\n")

        if func_type.has_send():
            file.print("\t/* dealloc send parameter while executing (GenOpaqueMarshler0017) */\n")
            file.print("\tSET_RPC_STATE( state_, RPCSTATE_CLIENT_EXEC );\n")
            self.dealloc_for_params(params, file, 1, "SEND", "eClientEntry_{}".format(func_name))

        if not func_type.is_oneway():
            file.print("\t/* パケットの始まりをチェック (GenOpaqueMarshler0018) */\n")
            file.print("\tSET_RPC_STATE( state_, RPCSTATE_CLIENT_RECV_SOP );\n")
            file.print("\tif( (ercd_=cTDR_receiveSOP( true )) != E_OK )\n")
            file.print("\t\tgoto error_reset;\n")

            b_get = True
            file.print("\t/* 戻り値の受け取り (GenOpaqueMarshler0019) */\n")
            self.print_param("retval_", func_type.get_type(), file, 1, "RETURN", None, None,
                             b_marshal, b_get)

            if func_type.has_outward():
                if b_ret_er:
                    indent_level = 2
                    file.print("\tif( MERCD( retval_ ) != E_RPC ){\n")
                else:
                    indent_level = 1

                indent = "\t" * indent_level
                file.print("{}/* 出力値の受け取り (GenOpaqueMarshler0020) */\n".format(indent))
                file.print("{}SET_RPC_STATE( state_, RPCSTATE_CLIENT_RECV_BODY );\n".format(indent))
                self.print_params(params, file, indent_level, b_marshal, b_get, True,
                                  "eClientEntry", func_name)
                self.print_params(params, file, indent_level, b_marshal, b_get, False,
                                  "eClientEntry", func_name)
                if b_ret_er:
                    file.print("\t}\n")

            file.print("\n\t/* パケットの終わりをチェック (GenOpaqueMarshler0021) */\n")
            file.print("\tSET_RPC_STATE( state_, RPCSTATE_CLIENT_RECV_EOP );\n")
            file.print("\tif( (ercd_=cTDR_receiveEOP(false)) != E_OK )\n")
            file.print("\t\tgoto error_reset;\n")

        file.print("""\
\t/* Channel Unlock (GenOpaqueMarshler0022) */
\tSET_RPC_STATE( state_, RPCSTATE_CLIENT_RELEASE_SEM );
\tif( is_cLockChannel_joined() ){
\t\tif( (ercd_=cLockChannel_signal()) != E_OK )
\t\t\tgoto error_reset;
\t}
""")

        file.print("""\
\t/* state_ is not used in normal case (GenOpaqueMarshler0023) */
  /* below is to avoid 'set but not used' warnning */
\t(void)state_;
""")

        if not b_void:
            file.print("\treturn retval_;\n")
        else:
            file.print("\treturn;\n")

        file.print("""\

error_reset:
""")

        if func_type.has_send():
            file.print("\t/* dealloc send parameter (GenOpaqueMarshler0024) */\n")
            file.print("\tif( state_ < RPCSTATE_CLIENT_EXEC ){\n")
            self.dealloc_for_params(params, file, 2, "SEND", "eClientEntry_{}".format(func_name))
            file.print("\t}\n")

        if func_type.has_receive():
            file.print("\t/* receive parameter (GenOpaqueMarshler0025) */\n")
            self.dealloc_for_params(params, file, 1, "RECEIVE", "eClientEntry_{}".format(func_name), True)

        file.print("""\
\tif( MERCD( ercd_ ) != E_RESET )
\t\t(void)cTDR_reset();
""")

        file.print("""\
\t/* Channel Unlock (GenOpaqueMarshler0026) */
\tif( is_cLockChannel_joined() )
\t\tcLockChannel_signal();

\tif( ercd_ != E_OK && is_cErrorHandler_joined() )
\t\tcErrorHandler_errorOccured( func_id_, ercd_, state_ );
""")

        if b_ret_er:
            file.print("\treturn ERCD( E_RPC, MERCD( ercd_ ) ); /* (GenOpaqueMarshler0027) */\n")
        else:
            file.print("\treturn;/* (GenOpaqueMarshler0028) */\n")

    def gen_ep_func_body_unmarshal(self, file, b_singleton, ct_name, global_ct_name, sig_name,
                                   ep_name, func_name, func_global_name, func_type, params):
        b_ret_er = True

        file.print("""\
  /* (GenOpaqueMarshler0101) */
\tint16_t\tfunc_id_;
\tER\t\tercd_ = E_OK;
\tint16_t\tstate_;

\t{}_CB *p_cellcb;

\tif( VALID_IDX( idx ) ){{
\t\tp_cellcb = GET_CELLCB(idx);
""".format(ct_name))

        if b_ret_er:
            file.print("""\
\t}else{
\t\treturn E_ID;
\t}
""")
        else:
            file.print("""\
\t}else{
\t\t/* エラー処理コードをここに記述 */
\t}
""")

        file.print("""\

  /* (GenOpaqueMarshler0102) */
#ifdef RPC_DEBUG
\tsyslog(LOG_INFO, "Entering RPC service loop" );
#endif

\t/* SOPのチェック */
\tSET_RPC_STATE( state_, RPCSTATE_SERVER_RECV_SOP );
\tif( (ercd_=cTDR_receiveSOP( false )) != E_OK )
\t\tgoto error_reset;
\t/* func_id の取得 */
\tif( (ercd_=cTDR_getInt16( &func_id_ )) != E_OK )
\t\tgoto error_reset;

#ifdef RPC_DEBUG
\tsyslog(LOG_INFO, "unmarshaler task: func_id: %d", func_id_ );
#endif
  /* (GenOpaqueMarshler0103) */
\tswitch( func_id_ ){
""")

        for f in self.signature.get_function_head_array():
            f_name = f.get_name()
            func_id = "FUNCID_{}_{}".format(self.signature.get_global_name(), f_name).upper()
            fid = self.signature.get_id_from_func_name(f_name)
            file.print("\tcase {}:\t\t/* (id of '{}') = {} */ \n".format(func_id, f_name, fid))
            file.print("\t\tercd_ = tOpaqueUnmarshaler_{}_{}( p_cellcb, &state_ );\n".format(
                self.signature.get_global_name(), f_name))
            file.print("\t\tbreak;\n")

        if self.PPAllocatorSize:
            ppallocator_dealloc_str = "\t/* PPAllocator のすべてを解放 */\n\tcPPAllocator_dealloc_all();"
        else:
            ppallocator_dealloc_str = ""

        file.print("""\
  /* (GenOpaqueMarshler0104) */
\tdefault:
\t\tsyslog(LOG_INFO, "unmarshaler task: ERROR: unknown func_id: %d", func_id_ );
\t\tercd_ = E_ID;
\t}};
error_reset:  /* OK cases also come here */
{}
\tif( ercd_ == E_OK )
\t\treturn ercd_;
\tif( is_cErrorHandler_joined() )
\t\tercd_ = cErrorHandler_errorOccured( func_id_, ercd_, state_ );
\tif( MERCD( ercd_ ) != E_RESET )
\t\t(void)cTDR_reset();
\treturn ercd_;
""".format(ppallocator_dealloc_str))

    def gen_preamble(self, file, b_singleton, ct_name, global_name):
        if not self._unmarshaler_ct(ct_name):
            return

        file.print("/* header file (strlen, memset) (GenOpaqueMarshler0201) */\n")
        file.print("#include\t<string.h>\n\n")
        file.print("/* アンマーシャラ関数のプロトタイプ宣言 */\n")
        for f in self.signature.get_function_head_array():
            f_name = f.get_name()
            id_ = self.signature.get_id_from_func_name(f_name)
            file.print("static ER  tOpaqueUnmarshaler_{}_{}(CELLCB *p_cellcb, int16_t *state);\t/* func_id: {} */\n".format(
                self.signature.get_global_name(), f_name, id_))
        file.print("\n")

    def gen_postamble(self, file, b_singleton, ct_name, global_name):
        if not self._unmarshaler_ct(ct_name):
            return

        file.print("\n/*** アンマーシャラ関数 (GenOpaqueMarshler0301) ***/\n\n")
        for f in self.signature.get_function_head_array():
            f_name = f.get_name()
            f_type = f.get_declarator().get_type()
            id_ = self.signature.get_id_from_func_name(f_name)

            b_ret_er = False
            init_retval = ""
            if f_type.get_type().is_void():
                b_void = True
            else:
                b_void = False
                if f_type.get_type().get_type_str() in ("ER", "ER_INT"):
                    b_ret_er = True
                    init_retval = " = E_OK"

            file.print("""\
/* (GenOpaqueMarshler0302)  */
/*
 * name:    {}
 * func_id: {} 
 */
""".format(f_name, id_))
            file.print("static ER\n")
            file.print("tOpaqueUnmarshaler_{}_{}(CELLCB *p_cellcb, int16_t *state_)\t\t\n".format(
                self.signature.get_global_name(), f_name))
            file.print("{\n")
            file.print("\tER      ercd_;\n")

            params = f.get_declarator().get_type().get_paramlist().get_items()
            for par in params:
                name = par.get_name()
                type_ = par.get_type().get_original_type()
                dir_ = par.get_direction()
                if dir_ == "RECEIVE":
                    type_ = type_.get_type()
                if dir_ in ("SEND", "RECEIVE"):
                    init = " = 0"
                else:
                    init = ""

                if isinstance(type_, ArrayType):
                    type_ = type_.get_type()
                    aster = "(*"
                    aster2 = ")"
                else:
                    aster = ""
                    aster2 = ""

                type_str = re.sub(r'\bconst\b', '', type_.get_type_str())
                file.print("\t{:<12} {}{}{}{}{};\n".format(
                    type_str, aster, name, aster2, type_.get_type_str_post(), init))

                if dir_ == "OUT" and type_.is_nullable():
                    file.print("\tint8_t\tb_{}_null_;\n".format(name))

            if not b_void:
                file.print("\t{:<12} retval_{}{};\n".format(
                    f_type.get_type().get_type_str(), f_type.get_type().get_type_str_post(), init_retval))

            file.print("\n\t/* 入力引数受取 (GenOpaqueMarshler0303) */\n")
            file.print("\tSET_RPC_STATE( *state_, RPCSTATE_SERVER_RECV_BODY );\n")
            b_get = True
            b_marshal = False
            self.print_params(params, file, 1, b_marshal, b_get, True, "cServerCall", f_name)
            self.print_params(params, file, 1, b_marshal, b_get, False, "cServerCall", f_name)
            self.print_out_nullable(params, file, 1, b_marshal)

            file.print("\t/* パケット終わりをチェック (GenOpaqueMarshler0304) */\n")
            file.print("\tSET_RPC_STATE( *state_, RPCSTATE_SERVER_RECV_EOP );\n")
            b_continue = "true" if not f_type.is_oneway() else "false"
            file.print("\tif( (ercd_=cTDR_receiveEOP({})) != E_OK )\n".format(b_continue))
            file.print("\t\tgoto error_reset;\n\n")

            self.alloc_for_out_params(params, file, 1, "OUT", "cPPAllocator_alloc", None)

            file.print("\t/* 対象関数の呼出し (GenOpaqueMarshler0305) */\n")
            file.print("\tSET_RPC_STATE( *state_, RPCSTATE_SERVER_EXEC );\n")
            if b_void:
                file.print("\tcServerCall_{}(".format(f_name))
            else:
                file.print("\tretval_ = cServerCall_{}(".format(f_name))

            delim = " "
            for par in params:
                file.print(delim)
                delim = ", "
                if par.get_direction() == "RECEIVE":
                    file.print("&")
                file.print(par.get_name())
            file.print(" );\n")

            if not f.is_oneway():
                file.print("\n\t/* SOPの送出 (GenOpaqueMarshler0306) */\n")
                file.print("\tSET_RPC_STATE( *state_, RPCSTATE_SERVER_SEND_SOP );\n")
                file.print("\tif( ( ercd_ = cTDR_sendSOP( false ) ) != E_OK )\n")
                file.print("\t\tgoto error_reset;\n")

                b_get = False
                if not b_void:
                    file.print("\t/* 戻り値の送出 */\n")
                    self.print_param("retval_", f_type.get_type(), file, 1, "RETURN", None, None,
                                     b_marshal, b_get)

                if f_type.has_outward():
                    if b_ret_er:
                        indent_level = 2
                        file.print("\tif( MERCD( retval_ ) != E_RPC ){\n")
                    else:
                        indent_level = 1
                    indent = "\t" * indent_level

                    file.print("{}/* 出力値の送出 (GenOpaqueMarshler0307) */\n".format(indent))
                    file.print("{}SET_RPC_STATE( *state_, RPCSTATE_SERVER_SEND_BODY );\n".format(indent))
                    self.print_params(params, file, indent_level, b_marshal, b_get, True,
                                      "cServerCall", f_name)
                    self.print_params(params, file, indent_level, b_marshal, b_get, False,
                                      "cServerCall", f_name)

                    if f_type.has_receive():
                        file.print("{}/* dealloc receive parameter */\n".format(indent))
                        self.dealloc_for_params(params, file, indent_level, "RECEIVE",
                                               "cServerCall_{}".format(f_name))

                    if b_ret_er:
                        file.print("\t}\n")

                file.print("\t/* パケットの終わり（掃きだし） (GenOpaqueMarshler0308) */\n")
                file.print("\tSET_RPC_STATE( *state_, RPCSTATE_SERVER_SEND_EOP );\n")
                file.print("\tif( (ercd_=cTDR_sendEOP(false)) != E_OK )\n")
                file.print("\t\tgoto error_reset;\n")

            file.print("\treturn E_OK;\n")
            file.print("""\

error_reset:
""")

            if f_type.has_send():
                file.print("\t/* dealloc send parameter (GenOpaqueMarshler0309) */\n")
                file.print("\tif( *state_ < RPCSTATE_SERVER_EXEC ){\n")
                self.dealloc_for_params(params, file, 2, "SEND", "cServerCall_{}".format(f_name), True)
                file.print("\t}\n")

            if f_type.has_receive() and b_ret_er:
                file.print("\t/* dealloc receive parameter (GenOpaqueMarshler0310) */\n")
                file.print("\tif( MERCD( retval_ ) != E_RPC ){\n")
                self.dealloc_for_params(params, file, 2, "RECEIVE", "cServerCall_{}".format(f_name))
                file.print("\t}\n")

            file.print("\treturn ERCD( E_RPC, MERCD( ercd_ ) );\n")
            file.print("}\n\n")

    def print_params(self, params, file, nest, b_marshal, b_get, b_referenced, port_name, func_name):
        for param in params:
            if b_referenced != param.is_referenced():
                continue

            dir_ = param.get_direction()
            if (b_get is False and b_marshal is True) or (b_get is True and b_marshal is False):
                if dir_ in ("IN", "INOUT"):
                    alloc_cp = "cPPAllocator_alloc"
                    self.print_param(param.get_name(), param.get_type(), file, nest, dir_, None, None,
                                     b_marshal, b_get, alloc_cp, None)
                elif dir_ == "SEND":
                    alloc_cp = "{}_{}_{}_alloc".format(port_name, func_name, param.get_name())
                    self.print_param(param.get_name(), param.get_type(), file, nest, dir_, None, None,
                                     b_marshal, b_get, alloc_cp, None)
            else:
                if dir_ in ("OUT", "INOUT"):
                    self.print_param(param.get_name(), param.get_type(), file, nest, dir_, None, None,
                                     b_marshal, b_get, None, None)
                elif dir_ == "RECEIVE":
                    alloc_cp = "{}_{}_{}_alloc".format(port_name, func_name, param.get_name())
                    if b_get:
                        outer = "(*"
                        outer2 = ")"
                    else:
                        outer = None
                        outer2 = None
                    type_ = param.get_type().get_referto()
                    self.print_param(param.get_name(), type_, file, nest, dir_, outer, outer2,
                                     b_marshal, b_get, alloc_cp, None)

    def alloc_for_out_params(self, params, file, nest, dir_, alloc_cp, alloc_cp_extra):
        for param in params:
            if param.get_direction() == "OUT":
                self.alloc_for_out_param(param.get_name(), param.get_type(), file, nest,
                                         None, None, alloc_cp, alloc_cp_extra)

    def alloc_for_out_param(self, name, type_, file, nest, outer, outer2, alloc_cp, alloc_cp_extra):
        org_type = type_.get_original_type()
        if org_type.is_nullable():
            indent = "\t" * nest
            file.print("{}if( ! b_{}_null_  ){{\n".format(indent, name))
            nest += 1

        if isinstance(org_type, PtrType):
            indent = "\t" * nest
            count = type_.get_count()
            size = type_.get_size()
            string = type_.get_string()
            o = outer or ""
            o2 = outer2 or ""
            extra = alloc_cp_extra or ""
            if count or size or string:
                loop_counter_type = IntType(16)
                if count:
                    len_ = count.to_s()
                elif size:
                    len_ = size.to_s()
                elif string:
                    if isinstance(string, Expression):
                        len_ = string.to_s()
                    else:
                        raise Exception("unsuscripted string used for out parameter {}".format(name))

                if org_type.get_max() is not None and string is None:
                    file.print("{}/* (GenOpaqueMarshler0401) */\n".format(indent))
                    file.print("{}if( {} > {} ){{\t/* GenOpaqueMarshaler max check 2 */\n".format(
                        indent, len_, type_.get_max()))
                    file.print("{}\tercd_ = E_PAR;\n".format(indent))
                    file.print("{}\tgoto error_reset;\n".format(indent))
                    file.print("{}}}\n".format(indent))

                file.print("""\
{indent}/* (GenOpaqueMarshler0402) */
{indent}if((ercd_={alloc_cp}(sizeof({tstr}{tpost})*{len_},(void **)&{o}{name}{o2}{extra}))!=E_OK)\t/* GenOpaqueMarshaler 1 */
{indent}\tgoto error_reset;
""".format(
                    indent=indent, alloc_cp=alloc_cp,
                    tstr=type_.get_type().get_type_str(), tpost=type_.get_type().get_type_str_post(),
                    len_=len_, o=o, name=name, o2=o2, extra=extra))

                if isinstance(type_.get_type(), PtrType):
                    file.print("{}{{\t/* (GenOpaqueMarshler0403) */\n".format(indent))
                    file.print("{}\t{}  i__{}, length__{} = {};\n".format(
                        indent, loop_counter_type.get_type_str(), nest, nest, len_))
                    file.print("{}\tfor( i__{} = 0; i__{} < length__{}; i__{}++ ){{\n".format(
                        indent, nest, nest, nest, nest))
                    self.alloc_for_out_param(name, type_.get_type(), file, nest + 2, outer,
                                             "{}[i__{}]".format(o2, nest), alloc_cp, alloc_cp_extra)
                    file.print("{}\t}}\n".format(indent))
                    file.print("{}}}\n".format(indent))

            else:
                file.print("""\
{indent}/* (GenOpaqueMarshler0404) */
{indent}if((ercd_={alloc_cp}(sizeof({tstr}{tpost}),(void **)&{o}{name}{o2}{extra}))!=E_OK)\t/* GenOpaqueMarshaler 2 */
{indent}\tgoto error_reset;
""".format(
                    indent=indent, alloc_cp=alloc_cp,
                    tstr=type_.get_type().get_type_str(), tpost=type_.get_type().get_type_str_post(),
                    o=o, name=name, o2=o2, extra=extra))

        if org_type.is_nullable():
            nest -= 1
            indent = "\t" * nest
            file.print("{}}} else {{\n".format(indent))
            file.print("{}\t{} = NULL;\n".format(indent, name))
            file.print("{}}}\n".format(indent))

    def dealloc_for_params(self, params, file, nest, dir_, dealloc_cp, b_reset=False):
        reset_str = "_reset" if b_reset else ""
        for param in params:
            if dir_ == param.get_direction():
                indent = "\t" * nest
                type_ = param.get_type().get_original_type()
                aster = ""
                if dir_ == "RECEIVE":
                    type_ = type_.get_type().get_original_type()
                    if b_reset:
                        aster = "*"
                count = type_.get_count()
                size = type_.get_size()
                if (size or count) and type_.get_type().has_pointer():
                    if count:
                        len_ = ", {}".format(count.to_s())
                    elif size:
                        len_ = ", {}".format(size.to_s())
                else:
                    len_ = ""
                cp = "{}_{}_dealloc{}".format(dealloc_cp, param.get_name(), reset_str).upper()
                file.print("{}{}({}{}{});\n".format(indent, cp, aster, param.get_name(), len_))

    def print_out_nullable(self, params, file, nest, b_marshal):
        indent = "\t" * nest
        for param in params:
            if param.get_direction() != "OUT":
                continue
            if not param.is_nullable():
                continue
            if b_marshal:
                file.print("{}if( (ercd_=cTDR_putInt8( (int8_t)({} == NULL) )) != E_OK )\n".format(
                    indent, param.get_name()))
                file.print("{}\tgoto error_reset;\n".format(indent))
            else:
                file.print("{}if( (ercd_=cTDR_getInt8( &b_{}_null_)) != E_OK )\n".format(
                    indent, param.get_name()))
                file.print("{}\tgoto error_reset;\n".format(indent))
