# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#
#   このファイルは tecsgen (Ruby 版) の tecslib/plugin/lib/GenTransparentMarshaler.rb を
#   Python へ移植したものである．
#
#   $Id: GenTransparentMarshaler.rb 3302 2026-06-07 06:01:02Z okuma-top $
#

import re

from tecslib.rubylib.symbol import Sym
from tecslib.core import globals as G
from tecslib.core.plugin import CFile
from tecslib.core.types import (
    DefinedType, BoolType, IntType, FloatType, PtrType, StructType,
    VoidType, EnumType, FuncType, ArrayType,
)


def _rpc_set_taskPriority(obj, rhs):
    obj.set_taskPriority(rhs)


def _rpc_set_channelCelltype(obj, rhs):
    obj.set_channelCelltype(rhs)


def _rpc_set_TDRCelltype(obj, rhs):
    obj.set_TDRCelltype(rhs)


def _rpc_set_channelCellName(obj, rhs):
    obj.set_channelCellName(rhs)


def _rpc_set_PPAllocatorSize(obj, rhs):
    obj.set_PPAllocatorSize(rhs)


# プラグイン引数名と Proc
RPCPluginArgProc = {
    "taskPriority":    _rpc_set_taskPriority,
    "channelCelltype": _rpc_set_channelCelltype,
    "TDRCelltype":     _rpc_set_TDRCelltype,
    "channelCell":     _rpc_set_channelCellName,
    "PPAllocatorSize": _rpc_set_PPAllocatorSize,
}


#プラグインオプション用変数
#@task_priority:: Integer
#@channelCelltype:: String
#@channelCellName:: String
#@PPAllocatorSize:: Integer
class GenTransparentMarshaler:

    #=== プラグイン引数 taskPriority のチェック
    def set_taskPriority(self, rhs):
        self.task_priority = rhs

    #=== プラグイン引数 channelCelltype のチェック
    def set_channelCelltype(self, rhs):
        from tecslib.core.componentobj.namespacepath import NamespacePath
        from tecslib.core.componentobj.namespace import Namespace
        from tecslib.core.componentobj.celltype import Celltype
        from tecslib.core.componentobj.compositecelltype import CompositeCelltype
        self.channelCelltype = Sym(str(rhs))
        nsp = NamespacePath.analyze(str(self.channelCelltype))
        obj = Namespace.find(nsp)
        if not (type(obj) is Celltype) and not (type(obj) is CompositeCelltype):
            self.cdl_error("RPCPlugin: channeclCelltype '{}' not celltype or not found".format(rhs))

    #=== プラグイン引数 TDRCelltype のチェック
    def set_TDRCelltype(self, rhs):
        from tecslib.core.componentobj.namespacepath import NamespacePath
        from tecslib.core.componentobj.namespace import Namespace
        from tecslib.core.componentobj.celltype import Celltype
        from tecslib.core.componentobj.compositecelltype import CompositeCelltype
        self.TDRCelltype = Sym(str(rhs))
        nsp = NamespacePath.analyze(str(self.TDRCelltype))
        obj = Namespace.find(nsp)
        if not (type(obj) is Celltype) and not (type(obj) is CompositeCelltype):
            self.cdl_error("RPCPlugin: TDRCelltype '{}' not celltype or not found".format(rhs))

    #=== プラグイン引数 channelCellName のチェック
    def set_channelCellName(self, rhs):
        self.channelCellName = rhs
        if re.match(r'\A[a-zA-Z_]\w*', str(rhs)):
            pass
        else:
            self.cdl_error("RPCPlugin: channeclCellName '{}' unsuitable for identifier".format(rhs))

    #=== プラグイン引数 PPAllocatorSize のチェック
    def set_PPAllocatorSize(self, rhs):
        self.PPAllocatorSize = rhs

    #=== marshaler のセルタイプ名を設定する
    def initialize_transparent_marshaler(self, cell_name):
        # Ruby 未設定インスタンス変数は nil。getattr で同等にする。
        if getattr(self, "task_priority", None) is None:
            self.task_priority = 8
        if getattr(self, "channelCelltype", None) is None:
            self.channelCelltype = Sym("tDataqueueOWChannel")
        if getattr(self, "TDRCelltype", None) is None:
            self.TDRCelltype = Sym("tTDR")
        if getattr(self, "channelCellName", None) is None:
            self.channelCellName = "{}_Channel".format(cell_name)
        if getattr(self, "PPAllocatorSize", None) is None:
            self.PPAllocatorSize = None
        if getattr(self, "b_datapumpholder", None) is None:
            self.b_datapumpholder = False

        if self.b_datapumpholder is True:
            marshaler_head_append = "DPH"
        else:
            marshaler_head_append = ""
        self.marshaler_celltype_name = "tMarshaler{}_{}".format(
            marshaler_head_append, self.signature.get_global_name())
        self.unmarshaler_celltype_name = "tUnmarshaler{}_{}".format(
            marshaler_head_append, self.signature.get_global_name())
        self.marshaler_celltype_file_name = "{}/{}.cdl".format(
            G.gen, self.marshaler_celltype_name)

        if self.signature.get_context() != "task":
            self.cdl_error(
                "RPC9999 context of signature ($1) must be 'task'. $2 is not compatible with RPCPlugin",
                self.signature.get_name(), self.signature.get_context())

    def gen_marshaler_celltype(self):
        if self.PPAllocatorSize:
            alloc_call_port = "  call sPPAllocator cPPAllocator;\n"
        else:
            alloc_call_port = ""

        f = CFile.open(self.marshaler_celltype_file_name, "w")
        f.print("""\
/*
 * generated by GenTransparentMarshaler invoked by TransparentChannelPlugin
/ */
celltype {} {{
  entry {} eClientEntry;
  call sTDR        cTDR;
  call sEventflag  cEventflag;
  [optional]
    call sSemaphore cLockChannel;  // this port is eliminated by optimize
}};
celltype {} {{
  call {} cServerCall;
  call sTDR        cTDR;
  call sEventflag  cEventflag;
  entry sUnmarshalerMain  eUnmarshalAndCallFunction;
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

    def _fn_is(self, func_name, name):
        return str(func_name) == name

    #===  受け口関数の本体コードを生成（頭部と末尾は別途出力）
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

    #===  marshal コードの生成
    def gen_ep_func_body_marshal(self, file, b_singleton, ct_name, global_ct_name, sig_name,
                                 ep_name, func_name, func_global_name, func_type, params):
        b_void = False
        b_ret_er = False

        type_ = func_type.get_type().get_original_type()
        file.print("    /* (GenTransparentMarshler0101) */\n")
        if not type_.is_void():
            if (isinstance(func_type.get_type(), DefinedType)
                    and func_type.get_type().get_type_str() in ("ER", "ER_INT")):
                file.print("    {}  retval_ = E_OK;\n".format(func_type.get_type().get_type_str()))
                b_ret_er = True
            else:
                file.print("    {}  retval_;\n".format(func_type.get_type().get_type_str()))
        else:
            b_void = True

        file.print("    ER      ercd_;\n")
        file.print("    FLGPTN  flgptn;\n")

        signature = self.signature
        func_id = signature.get_id_from_func_name(func_name)
        file.print("    int16_t  func_id_ = {};    /* id of {}: {} */\n".format(
            func_id, func_name, func_id))

        if not b_singleton:
            file.print("""\
    {}_CB *p_cellcb;

    if( VALID_IDX( idx ) ){{
        p_cellcb = GET_CELLCB(idx);
""".format(ct_name))
            if b_ret_er:
                file.print("""\
    }else{
         return ERCD( E_RPC, E_ID );
    }
""")
            else:
                file.print("""\
    }else{
        /* エラー処理コードをここに記述 / */
    }
""")

        if self.b_datapumpholder is False or self._fn_is(func_name, "waitForReadDone"):
            file.print("""\
    /* Channel Lock / */
    if( is_cLockChannel_joined() )
      cLockChannel_wait();

""")

        if self.b_datapumpholder is False:
            file.print("    /* SOPの送出 (GenTransparentMarshler0102) */\n")
            file.print("    if( ( ercd_ = cTDR_sendSOP( true ) ) != E_OK )\n")
            file.print("      goto error_reset;\n")
        elif self._fn_is(func_name, "waitForReadDone"):
            file.print("   /* SOP の送出 (GenTransparentMarshler0102_2) */\n")
            file.print("   if( ( ercd_ = cTDR_putInt16(TDR_SOP_MAGIC1) ) != E_OK )\n")
            file.print("      goto error_reset;\n")

        file.print("    /* 関数 id の送出 (GenTransparentMarshler0103) */\n")
        file.print("    if( ( ercd_ = cTDR_putInt16( func_id_ ) ) != E_OK )\n")
        file.print("        goto error_reset;\n")

        b_get = False
        b_marshal = True

        file.print("    /* 入力引数送出 (GenTransparentMarshler0104) */\n")
        self.print_params(params, file, 1, b_marshal, b_get, True, func_type.is_oneway())
        self.print_params(params, file, 1, b_marshal, b_get, False, func_type.is_oneway())
        if not b_void and not func_type.is_oneway():
            ret_ptr_type = PtrType(func_type.get_type())
            self.print_param_nc("retval_", ret_ptr_type, file, 1, True, "&", None, b_get)

        file.print("    /* EOPの送出（パケットの掃きだし）(GenTransparentMarshler0105) */\n")
        b_continue = "true" if not func_type.is_oneway() else "false"
        if self.b_datapumpholder is False or self._fn_is(func_name, "newDataReady"):
            file.print("    if( (ercd_=cTDR_sendEOP({})) != E_OK )\n".format(b_continue))
            file.print("        goto error_reset;\n\n")

        if not func_type.is_oneway():
            file.print("""\
    if( (ercd_=cEventflag_wait( 0x01, TWF_ANDW, &flgptn )) != E_OK ){
      ercd_ = ERCD(E_RPC,ercd_);
      goto error_reset;
    }
    if( (ercd_=cEventflag_clear( 0x00 ) ) != E_OK ){
      ercd_ = ERCD(E_RPC,ercd_);
      goto error_reset;
    }
""")

        if self.b_datapumpholder is False or self._fn_is(func_name, "newDataReady"):
            file.print("""\
    /* Channel Lock / */
    if( is_cLockChannel_joined() )
      cLockChannel_signal();
""")

        if not b_void:
            file.print("    return retval_;\n")
        else:
            file.print("    return;\n")

        file.print("""\

error_reset:
    if( ercd_ != ERCD( E_RPC, E_RESET ) )
        (void)cTDR_reset();
""")

        if self.b_datapumpholder is False or self._fn_is(func_name, "newDataReady"):
            file.print("""\
    /* Channel Lock / */
    if( is_cLockChannel_joined() )
      cLockChannel_signal();

""")

        if b_ret_er:
            file.print("    return ercd_;\n")
        else:
            file.print("    return;\n")

    #===  unmarshal コードの生成
    def gen_ep_func_body_unmarshal(self, file, b_singleton, ct_name, global_ct_name, sig_name,
                                   ep_name, func_name, func_global_name, func_type, params):
        b_ret_er = False

        file.print("""\
    /* (GenTransparentMarshler0201) / */
    int16_t   func_id_;
    ER        ercd_;

    {}_CB *p_cellcb;

    if( VALID_IDX( idx ) ){{
        p_cellcb = GET_CELLCB(idx);
""".format(ct_name))

        if b_ret_er:
            file.print("""\
    }else{
        return ERCD( E_RPC, E_ID );
    }
""")
        else:
            file.print("""\
    }else{
        /* エラー処理コードをここに記述 / */
    }
""")

        if self.b_datapumpholder is False:
            file.print("""\

    /* SOPのチェック (GenTransparentMarshler0202) / */
    if( (ercd_=cTDR_receiveSOP( false )) != E_OK )
        goto error_reset;

    /* func_id の取得 / */
    if( (ercd_=cTDR_getInt16( &func_id_ )) != E_OK )
        goto error_reset;
""")
        else:
            file.print("""\

    /* func_id 取得 or SOPの受信 (GenTransparentMarshler0203) / */
    if( (ercd_=cTDR_getInt16( &func_id_ )) != E_OK )
        goto error_reset;
    if( func_id_ == TDR_SOP_MAGIC1 ){
      /* SOP の後の func_id の取得 / */
      if( (ercd_=cTDR_getInt16( &func_id_ )) != E_OK )
          goto error_reset;
    }
""")

        file.print("""\
#ifdef RPC_DEBUG
    syslog(LOG_INFO, "unmarshaler task: func_id: %d", func_id_ );
#endif
    switch( func_id_ ){
""")

        signature = self.signature
        for f in signature.get_function_head_array():
            f_name = f.get_name()
            f_type = f.get_declarator().get_type()
            id_ = signature.get_id_from_func_name(f_name)
            file.print("    case {}:       /*** {} ***/ \n".format(id_, f_name))
            file.print("        if( tTransparentUnmarshaler_{}_{}(p_cellcb) != E_OK )\n".format(
                self.signature.get_global_name(), f_name))
            file.print("            goto error_reset;\n")
            file.print("        break;\n")

        if self.PPAllocatorSize:
            ppallocator_dealloc_str = "    /* PPAllocator のすべてを解放 */\n    cPPAllocator_dealloc_all();"
        else:
            ppallocator_dealloc_str = ""

        file.print("""\
    default:
        syslog(LOG_INFO, "unmarshaler task: ERROR: unknown func_id: %d", func_id_ );
    }};
{}
    return E_OK;

error_reset:
    if( ercd_ != ERCD( E_RPC, E_RESET ) )
        (void)cTDR_reset();
{}
    return E_OK;
""".format(ppallocator_dealloc_str, ppallocator_dealloc_str))

    def print_params(self, params, file, nest, b_marshal, b_get, b_referenced, b_oneway=False):
        for param in params:
            if b_referenced != param.is_referenced():
                continue
            dir_ = param.get_direction()
            type_ = param.get_type()
            orig = type_.get_original_type()
            if (b_oneway and dir_ == "IN" and isinstance(orig, PtrType)
                    or isinstance(orig, ArrayType)):
                alloc_cp = "cPPAllocator_alloc"
                alloc_cp_extra = None
                self.print_param(param.get_name(), type_, file, nest, dir_, None, None,
                                 b_marshal, b_get, alloc_cp, alloc_cp_extra)
            else:
                if (b_get is False and b_marshal is True) or (b_get is True and b_marshal is False):
                    if dir_ in ("IN", "INOUT", "OUT", "SEND", "RECEIVE"):
                        self.print_param_nc(param.get_name(), type_, file, nest, b_marshal,
                                            None, None, b_get)

    def print_param_nc(self, name, type_, file, nest, b_marshal, outer, outer2, b_get):
        indent = "    " * (nest + 1)

        if isinstance(type_, DefinedType):
            self.print_param_nc(name, type_.get_type(), file, nest, b_marshal, outer, outer2, b_get)
        elif isinstance(type_, (BoolType, IntType, FloatType, PtrType, ArrayType)):
            if isinstance(type_, BoolType):
                type_str = "Int8"
                cast_str = "int8_t"
            elif isinstance(type_, IntType):
                bit_size = type_.get_bit_size()
                sign = type_.get_sign()
                if sign == "UNSIGNED":
                    signC = "U"
                    sign = "u"
                elif sign == "SIGNED":
                    if bit_size == -1 or bit_size == -11:
                        signC = "S"
                        sign = "s"
                    else:
                        signC = ""
                        sign = ""
                else:
                    signC = ""
                    sign = ""

                if bit_size in (-1, -11):
                    type_str = "{}Char".format(signC)
                    cast_str = "{}char_t".format(sign)
                elif bit_size == -2:
                    type_str = "{}Short".format(signC)
                    cast_str = "{}short_t".format(sign)
                elif bit_size == -3:
                    type_str = "{}Int".format(signC)
                    cast_str = "{}int_t".format(sign)
                elif bit_size == -4:
                    type_str = "{}Long".format(signC)
                    cast_str = "{}long_t".format(sign)
                elif bit_size == -5:
                    type_str = "Intptr"
                    cast_str = "intptr_t"
                elif bit_size in (8, 16, 32, 64, 128):
                    type_str = "{}Int{}".format(signC, bit_size)
                    cast_str = "{}int{}_t".format(sign, bit_size)
                else:
                    raise Exception("unknown bit_size '{}' for int type ".format(bit_size))

            elif isinstance(type_, FloatType):
                bit_size = type_.get_bit_size()
                if bit_size == 32:
                    type_str = "Float32"
                    cast_str = "float32_t"
                else:
                    type_str = "Double64"
                    cast_str = "double64_t"

            elif isinstance(type_, (PtrType, ArrayType)):
                type_str = "Intptr"
                cast_str = "intptr_t"

            if type_.get_type_str() == cast_str:
                cast_str = ""
            else:
                cast_str = "(" + cast_str + ")"

            o = outer or ""
            o2 = outer2 or ""
            nest_indent = "    " * nest
            if b_get:
                cast_str = cast_str.replace(")", "*)") if cast_str else cast_str
                file.print(nest_indent)
                file.print("if( ( ercd_ = cTDR_get{}( {}&({}{}{}) ) ) != E_OK )\n".format(
                    type_str, cast_str, o, name, o2))
                file.print(nest_indent)
                file.print("    goto error_reset;\n")
            else:
                file.print(nest_indent)
                file.print("if( ( ercd_ = cTDR_put{}( {}{}{}{} ) ) != E_OK )\n".format(
                    type_str, cast_str, o, name, o2))
                file.print(nest_indent)
                file.print("    goto error_reset;\n")

        elif isinstance(type_, StructType):
            members_decl = type_.get_members_decl()
            o = outer or ""
            o2 = outer2 or ""
            for m in members_decl.get_items():
                if m.is_referenced():
                    self.print_param_nc(m.get_name(), m.get_type(), file, nest, b_marshal,
                                        "{}{}{}.".format(o, name, o2), None, b_get)
            for m in members_decl.get_items():
                if not m.is_referenced():
                    self.print_param_nc(m.get_name(), m.get_type(), file, nest, b_marshal,
                                        "{}{}{}.".format(o, name, o2), None, b_get)
        elif isinstance(type_, VoidType):
            pass
        elif isinstance(type_, EnumType):
            pass
        elif isinstance(type_, FuncType):
            pass

    def gen_preamble(self, file, b_singleton, ct_name, global_name):
        if not self._unmarshaler_ct(ct_name):
            return

        file.print("/* アンマーシャラ関数のプロトタイプ宣言 (GenTransparentMarshler0301) */\n")
        for f in self.signature.get_function_head_array():
            f_name = f.get_name()
            id_ = self.signature.get_id_from_func_name(f_name)
            file.print("static ER  tTransparentUnmarshaler_{}_{}(CELLCB *p_cellcb);\t/* func_id: {} */\n".format(
                self.signature.get_global_name(), f_name, id_))
        file.print("\n")

    def gen_postamble(self, file, b_singleton, ct_name, global_name):
        if not self._unmarshaler_ct(ct_name):
            return

        file.print("\n/*** アンマーシャラ関数 (GenTransparentMarshler0401) ***/\n\n")
        for f in self.signature.get_function_head_array():
            f_name = f.get_name()
            f_type = f.get_declarator().get_type()
            id_ = self.signature.get_id_from_func_name(f_name)

            b_void = f_type.get_type().is_void()

            file.print("""\
/*
 * name:    {}
 * func_id: {} 
/ */
""".format(f_name, id_))
            file.print("static ER\n")
            file.print("tTransparentUnmarshaler_{}_{}( CELLCB  *p_cellcb )\n".format(
                self.signature.get_global_name(), f_name))
            file.print("{\n")
            file.print("\tER  ercd_;\n")

            param_list = f.get_declarator().get_type().get_paramlist().get_items()
            for par in param_list:
                name = par.get_name()
                ptype = par.get_type()
                if isinstance(ptype, ArrayType):
                    ptype = ptype.get_type()
                    aster = "(*"
                    aster2 = ")"
                else:
                    aster = ""
                    aster2 = ""
                type_str = re.sub(r'\bconst\b', '', ptype.get_type_str())
                file.print("    {:<12} {}{}{}{};\n".format(
                    type_str, aster, name, aster2, ptype.get_type_str_post()))

            if not b_void:
                if f.is_oneway():
                    retval_ptr = ""
                else:
                    retval_ptr = "*"
                file.print("    {:<12} {}retval_{};\n".format(
                    f_type.get_type().get_type_str(), retval_ptr, f_type.get_type().get_type_str_post()))

            file.print("\n        /* 入力引数受取 (GenTransparentMarshler0402) */\n")
            b_get = True
            b_marshal = False
            self.print_params(param_list, file, 1, b_marshal, b_get, True, f.is_oneway())
            self.print_params(param_list, file, 1, b_marshal, b_get, False, f.is_oneway())
            if not b_void and not f.is_oneway():
                ret_ptr_type = PtrType(f_type.get_type())
                self.print_param_nc("retval_", ret_ptr_type, file, 1, False, None, None, b_get)

            file.print("        /* パケット終わりをチェック (GenTransparentMarshler0403) */\n")
            b_continue = "true" if not f.is_oneway() else "false"
            if self.b_datapumpholder is False or str(f_name) == "newDataReady":
                file.print("    if( (ercd_=cTDR_receiveEOP({})) != E_OK )\n".format(b_continue))
                file.print("        goto error_reset;\n\n")

            file.print("    /* 対象関数の呼出し (GenTransparentMarshler0404) */\n")
            if b_void:
                file.print("    cServerCall_{}(".format(f_name))
            else:
                file.print("    {}retval_ = cServerCall_{}(".format(retval_ptr, f_name))

            delim = " "
            for par in param_list:
                file.print(delim)
                delim = ", "
                file.print(par.get_name())
            file.print(" );\n")

            if not f.is_oneway():
                file.print("""\
    /* 関数処理の終了を通知 (GenTransparentMarshler0405) / */
    if( ( ercd_ = cEventflag_set( 0x01 ) ) != E_OK ){
      goto error_reset;
    }
""")
            file.print("""\
    return E_OK;
error_reset:
    return ercd_;
}

""")
