# -*- coding: utf-8 -*-
#
#  NotifierPlugin.rb の Python 移植

import re

from tecslib.core import globals as G
from tecslib.core.generate import AppFile
from tecslib.core.plugin_module import _const_defined, _const_get, _import_plugin_class
from tecslib.core.toplevel import dbgPrint
from tecslib.plugin.CelltypePlugin import CelltypePlugin
from tecslib.rubylib import rb
from tecslib.rubylib.symbol import Sym


def _expr_str(val):
    from tecslib.core.expression import Expression

    if isinstance(val, Expression):
        elems = val.elements
        if elems and len(elems) >= 2 and elems[0] == "BOOL_CONSTANT":
            return rb.to_s(elems[1])
        return val.to_s()
    return rb.to_s(val)


def _set_factory(obj, rhs):
    obj.set_factory(rhs)


def _set_factory_output_file(obj, rhs):
    obj.set_factory_output_file(rhs)


NotifierPluginArgProc = {
    "factory": _set_factory,
    "output_file": _set_factory_output_file,
}


class Handler(object):
    def __init__(self, call_port_name):
        self.call_port_name = call_port_name


EVENT_HANDLER = Handler("ciNotificationHandler")
ERROR_HANDLER = Handler("ciErrorNotificationHandler")

HANDLERS = [
    EVENT_HANDLER,
    ERROR_HANDLER,
]


class HandlerAttribute(object):
    def __init__(self, name, error_name=None):
        self.name = name
        self.error_name = error_name if error_name is not None else (name + "ForError")

    def name_for_handler(self, handler):
        if handler is EVENT_HANDLER:
            return self.name
        if handler is ERROR_HANDLER:
            return self.error_name
        raise RuntimeError("unknown handler {!r}".format(handler))


SETVAR_ADDR_ATTR = HandlerAttribute("setVariableAddress")
SETVAR_VALUE_ATTR = HandlerAttribute("setVariableValue")
INCVAR_ADDR_ATTR = HandlerAttribute("incrementedVariableAddress")
SNDDTQ_VALUE_ATTR = HandlerAttribute("dataqueueSentValue")
SETFLG_FLAG_ATTR = HandlerAttribute("flagPattern")

ATTRS = [
    SETVAR_ADDR_ATTR,
    SETVAR_VALUE_ATTR,
    INCVAR_ADDR_ATTR,
    SNDDTQ_VALUE_ATTR,
    SETFLG_FLAG_ATTR,
]


class BaseHandlerType(object):
    def __init__(self):
        self.required_attributes = []

    def validate_join(self, handler, cell, join=None, *args):
        return self.generate_attr_map(handler, cell) is not None

    def generate_attr_map(self, handler, cell):
        amap = {}
        join_list = cell.get_join_list()

        for known_attr in ATTRS:
            attr_name = known_attr.name_for_handler(handler)
            join = join_list.get_item(Sym(attr_name))
            is_required = known_attr in self.required_attributes

            if (join is None) != (not is_required):
                return None

            if join is None:
                continue

            amap[known_attr] = join

        return amap

    def gen_cfg_handler_type(self, handler):
        raise RuntimeError("called abstract method gen_cfg_handler_type")

    def gen_cfg_handler_parameters(self, handler, join, attr_map, cell, adpt_gen):
        return None

    def might_fail(self):
        return False


class BaseTaskHandlerType(BaseHandlerType):
    def validate_join(self, handler, cell, join=None, *args):
        return (
            super().validate_join(handler, cell, join, *args)
            and join is not None
            and join.get_rhs_cell().get_celltype().get_name() == Sym("tTask")
        )

    def gen_cfg_handler_parameters(self, handler, join, attr_map, cell, adpt_gen):
        task_cell = join.get_cell()
        id_attr_join = task_cell.get_join_list().get_item(Sym("id"))
        id_attr = join.get_rhs_cell().get_celltype().find(Sym("id"))
        if id_attr_join:
            id_ = _expr_str(id_attr_join.get_rhs())
        else:
            id_ = _expr_str(id_attr.get_initializer())

        name_array = task_cell.get_celltype().get_name_array(task_cell)
        id_ = task_cell.get_celltype().subst_name(id_, name_array)
        return [id_]

    def might_fail(self):
        return True


class ActivateTaskHandlerType(BaseTaskHandlerType):
    def validate_join(self, handler, cell, join=None, *args):
        return (
            super().validate_join(handler, cell, join, *args)
            and join.get_port_name() == Sym("eiActivateNotificationHandler")
        )

    def gen_cfg_handler_type(self, handler):
        if handler is EVENT_HANDLER:
            return "TNFY_ACTTSK"
        if handler is ERROR_HANDLER:
            return "TENFY_ACTTSK"
        raise RuntimeError("unknown handler {!r}".format(handler))


class WakeUpTaskHandlerType(BaseTaskHandlerType):
    def validate_join(self, handler, cell, join=None, *args):
        return (
            super().validate_join(handler, cell, join, *args)
            and join.get_port_name() == Sym("eiWakeUpNotificationHandler")
        )

    def gen_cfg_handler_type(self, handler):
        if handler is EVENT_HANDLER:
            return "TNFY_WUPTSK"
        if handler is ERROR_HANDLER:
            return "TENFY_WUPTSK"
        raise RuntimeError("unknown handler {!r}".format(handler))


class SetVariableHandlerType(BaseHandlerType):
    def __init__(self):
        super().__init__()
        self.required_attributes = [SETVAR_ADDR_ATTR, SETVAR_VALUE_ATTR]

    def validate_join(self, handler, cell, join=None, *args):
        return (
            super().validate_join(handler, cell, join, *args)
            and join is None
            and handler is EVENT_HANDLER
        )

    def gen_cfg_handler_parameters(self, handler, join, attr_map, cell, adpt_gen):
        var_addr = _expr_str(attr_map[SETVAR_ADDR_ATTR].get_rhs())
        var_value = _expr_str(attr_map[SETVAR_VALUE_ATTR].get_rhs())
        name_array = cell.get_celltype().get_name_array(cell)
        var_addr = cell.get_celltype().subst_name(var_addr, name_array)
        var_value = cell.get_celltype().subst_name(var_value, name_array)
        return [var_addr, var_value]

    def gen_cfg_handler_type(self, handler):
        if handler is EVENT_HANDLER:
            return "TNFY_SETVAR"
        raise RuntimeError("unknown handler {!r}".format(handler))


class SetVariableToErrorCodeHandlerType(BaseHandlerType):
    def __init__(self):
        super().__init__()
        self.required_attributes = [SETVAR_ADDR_ATTR]

    def validate_join(self, handler, cell, join=None, *args):
        return (
            super().validate_join(handler, cell, join, *args)
            and join is None
            and handler is ERROR_HANDLER
        )

    def gen_cfg_handler_parameters(self, handler, join, attr_map, cell, adpt_gen):
        var_addr = _expr_str(attr_map[SETVAR_ADDR_ATTR].get_rhs())
        name_array = cell.get_celltype().get_name_array(cell)
        var_addr = cell.get_celltype().subst_name(var_addr, name_array)
        return [var_addr]

    def gen_cfg_handler_type(self, handler):
        if handler is ERROR_HANDLER:
            return "TENFY_SETVAR"
        raise RuntimeError("unknown handler {!r}".format(handler))


class IncrementVariableHandlerType(BaseHandlerType):
    def __init__(self):
        super().__init__()
        self.required_attributes = [INCVAR_ADDR_ATTR]

    def validate_join(self, handler, cell, join=None, *args):
        return super().validate_join(handler, cell, join, *args) and join is None

    def gen_cfg_handler_parameters(self, handler, join, attr_map, cell, adpt_gen):
        var_addr = _expr_str(attr_map[INCVAR_ADDR_ATTR].get_rhs())
        name_array = cell.get_celltype().get_name_array(cell)
        var_addr = cell.get_celltype().subst_name(var_addr, name_array)
        return [var_addr]

    def gen_cfg_handler_type(self, handler):
        if handler is EVENT_HANDLER:
            return "TNFY_INCVAR"
        if handler is ERROR_HANDLER:
            return "TENFY_INCVAR"
        raise RuntimeError("unknown handler {!r}".format(handler))


class SignalSemaphoreHandlerType(BaseHandlerType):
    def validate_join(self, handler, cell, join=None, *args):
        return (
            super().validate_join(handler, cell, join, *args)
            and join is not None
            and join.get_rhs_cell().get_celltype().get_name() == Sym("tSemaphore")
        )

    def gen_cfg_handler_parameters(self, handler, join, attr_map, cell, adpt_gen):
        semaphore_cell = join.get_cell()
        id_attr_join = semaphore_cell.get_join_list().get_item(Sym("id"))
        id_attr = join.get_rhs_cell().get_celltype().find(Sym("id"))
        if id_attr_join:
            id_ = _expr_str(id_attr_join.get_rhs())
        else:
            id_ = _expr_str(id_attr.get_initializer())
        name_array = semaphore_cell.get_celltype().get_name_array(semaphore_cell)
        id_ = semaphore_cell.get_celltype().subst_name(id_, name_array)
        return [id_]

    def might_fail(self):
        return True

    def gen_cfg_handler_type(self, handler):
        if handler is EVENT_HANDLER:
            return "TNFY_SIGSEM"
        if handler is ERROR_HANDLER:
            return "TENFY_SIGSEM"
        raise RuntimeError("unknown handler {!r}".format(handler))


class SetEventflagHandlerType(BaseHandlerType):
    def __init__(self):
        super().__init__()
        self.required_attributes = [SETFLG_FLAG_ATTR]

    def validate_join(self, handler, cell, join=None, *args):
        return (
            super().validate_join(handler, cell, join, *args)
            and join is not None
            and join.get_rhs_cell().get_celltype().get_name() == Sym("tEventflag")
        )

    def gen_cfg_handler_parameters(self, handler, join, attr_map, cell, adpt_gen):
        eventflag_cell = join.get_cell()
        id_attr_join = eventflag_cell.get_join_list().get_item(Sym("id"))
        id_attr = join.get_rhs_cell().get_celltype().find(Sym("id"))
        if id_attr_join:
            id_ = _expr_str(id_attr_join.get_rhs())
        else:
            id_ = _expr_str(id_attr.get_initializer())
        flg_pattern = _expr_str(attr_map[SETFLG_FLAG_ATTR].get_rhs())

        name_array = eventflag_cell.get_celltype().get_name_array(eventflag_cell)
        id_ = eventflag_cell.get_celltype().subst_name(id_, name_array)

        name_array = cell.get_celltype().get_name_array(cell)
        flg_pattern = cell.get_celltype().subst_name(flg_pattern, name_array)
        return [id_, flg_pattern]

    def might_fail(self):
        return True

    def gen_cfg_handler_type(self, handler):
        if handler is EVENT_HANDLER:
            return "TNFY_SETFLG"
        if handler is ERROR_HANDLER:
            return "TENFY_SETFLG"
        raise RuntimeError("unknown handler {!r}".format(handler))


class DataqueueHandlerType(BaseHandlerType):
    def validate_join(self, handler, cell, join=None, *args):
        return (
            super().validate_join(handler, cell, join, *args)
            and join is not None
            and join.get_rhs_cell().get_celltype().get_name() == Sym("tDataqueue")
        )

    def gen_cfg_handler_parameters(self, handler, join, attr_map, cell, adpt_gen):
        dataqueue_cell = join.get_cell()
        id_attr_join = dataqueue_cell.get_join_list().get_item(Sym("id"))
        id_attr = join.get_rhs_cell().get_celltype().find(Sym("id"))
        if id_attr_join:
            id_ = _expr_str(id_attr_join.get_rhs())
        else:
            id_ = _expr_str(id_attr.get_initializer())

        name_array = dataqueue_cell.get_celltype().get_name_array(dataqueue_cell)
        id_ = dataqueue_cell.get_celltype().subst_name(id_, name_array)
        return [id_]

    def might_fail(self):
        return True


class SendToDataqueueHandlerType(DataqueueHandlerType):
    def __init__(self):
        super().__init__()
        self.required_attributes = [SNDDTQ_VALUE_ATTR]

    def validate_join(self, handler, cell, join=None, *args):
        return super().validate_join(handler, cell, join, *args) and handler is EVENT_HANDLER

    def gen_cfg_handler_parameters(self, handler, join, attr_map, cell, adpt_gen):
        params = super().gen_cfg_handler_parameters(handler, join, attr_map, cell, adpt_gen)
        sent_value = _expr_str(attr_map[SNDDTQ_VALUE_ATTR].get_rhs())
        name_array = cell.get_celltype().get_name_array(cell)
        sent_value = cell.get_celltype().subst_name(sent_value, name_array)
        params.append(sent_value)
        return params

    def gen_cfg_handler_type(self, handler):
        if handler is EVENT_HANDLER:
            return "TNFY_SNDDTQ"
        raise RuntimeError("unknown handler {!r}".format(handler))


class SendErrorCodeToDataqueueHandlerType(DataqueueHandlerType):
    def validate_join(self, handler, cell, join=None, *args):
        return super().validate_join(handler, cell, join, *args) and handler is ERROR_HANDLER

    def gen_cfg_handler_type(self, handler):
        if handler is ERROR_HANDLER:
            return "TENFY_SNDDTQ"
        raise RuntimeError("unknown handler {!r}".format(handler))


class UserHandlerType(BaseHandlerType):
    def validate_join(self, handler, cell, join=None, *args):
        return (
            super().validate_join(handler, cell, join, *args)
            and handler is not ERROR_HANDLER
            and join is not None
            and join.get_rhs_cell().get_celltype().get_name() == Sym("tTimeEventHandler")
        )

    def gen_cfg_handler_type(self, handler):
        if handler is EVENT_HANDLER:
            return "TNFY_HANDLER"
        raise RuntimeError("unknown handler {!r}".format(handler))

    def gen_cfg_handler_parameters(self, handler, join, attr_map, cell, adpt_gen):
        handler_cell = join.get_rhs_cell()
        call_join = handler_cell.get_join_list().get_item(Sym("ciHandlerBody"))
        if not call_join:
            return []
        adapter_handle = adpt_gen.make_adapter_handle(call_join)
        return [adapter_handle[1], adapter_handle[0]]


class NullHandlerType(BaseHandlerType):
    def validate_join(self, handler, cell, join=None, *args):
        return (
            super().validate_join(handler, cell, join, *args)
            and join is None
            and handler is not EVENT_HANDLER
        )

    def gen_cfg_handler_type(self, handler):
        if handler is ERROR_HANDLER:
            return None
        raise RuntimeError("unknown handler {!r}".format(handler))


HANDLER_TYPES = [
    ActivateTaskHandlerType(),
    WakeUpTaskHandlerType(),
    SetVariableHandlerType(),
    SetVariableToErrorCodeHandlerType(),
    IncrementVariableHandlerType(),
    SignalSemaphoreHandlerType(),
    SetEventflagHandlerType(),
    SendToDataqueueHandlerType(),
    SendErrorCodeToDataqueueHandlerType(),
    UserHandlerType(),
    NullHandlerType(),
]

_OUT_OF_DOMAIN_HANDLER_TYPES = (
    ActivateTaskHandlerType,
    WakeUpTaskHandlerType,
    SetVariableHandlerType,
    SetVariableToErrorCodeHandlerType,
    IncrementVariableHandlerType,
    SignalSemaphoreHandlerType,
    SetEventflagHandlerType,
    SendToDataqueueHandlerType,
    SendErrorCodeToDataqueueHandlerType,
)


class NotifierPlugin(CelltypePlugin):

    class AdapterGenerator(object):

        class EntryProperty(object):
            def __init__(self, cell, subscript):
                self.cell = cell
                self.subscript = subscript

            @classmethod
            def from_join(cls, join):
                return cls(join.get_rhs_cell(), join.get_rhs_subscript())

            def __eq__(self, other):
                if not isinstance(other, NotifierPlugin.AdapterGenerator.EntryProperty):
                    return False
                return self.cell == other.cell and self.subscript == other.subscript

            def __hash__(self):
                return hash(self.cell) ^ hash(self.subscript)

        class EntryPort(object):
            def __init__(self, port, prefix):
                self.port = port
                self.global_name = "{}_{}_{}".format(
                    prefix, port.get_celltype().get_global_name(), port.get_name()
                )
                self.entry_fn_name = "{}_{}_main".format(
                    port.get_celltype().get_global_name(), port.get_name()
                )
                self.props = []
                self.prop_map = {}

            def adapter_handle_for_entry_property(self, ep):
                index = self.prop_map[ep]
                return [
                    "{}_{}_fp".format(self.global_name, index),
                    "{}_{}_arg".format(self.global_name, index),
                ]

            def generate_inner(self, context, fn_name, cell, subscript, callee_ct=None):
                source_file = context.source_file
                header_file = context.header_file

                source_file.print("void {}(intptr_t extinf) {{\n".format(fn_name))

                params = []
                ct = self.port.get_celltype()

                if not ct.is_singleton():
                    if cell == Sym("generic"):
                        params.append("({}_IDX)extinf".format(callee_ct.get_global_name()))
                    else:
                        if ct.has_INIB() or ct.has_CB():
                            params.append(ct.get_name_array(cell)[7])
                        else:
                            params.append("0")

                if self.port.get_array_size():
                    if subscript == Sym("generic"):
                        params.append("(int_t)extinf")
                    else:
                        params.append(str(subscript))

                params_str = ", ".join(params)

                source_file.print("\t{}({});\n".format(self.entry_fn_name, params_str))
                source_file.print("}\n\n")

                header_file.print("extern void {}(intptr_t extinf);\n\n".format(fn_name))

            def make_adapter_handle(self, join):
                prop = NotifierPlugin.AdapterGenerator.EntryProperty.from_join(join)
                if prop not in self.prop_map:
                    self.prop_map[prop] = len(self.props)
                    self.props.append(prop)
                return self.adapter_handle_for_entry_property(prop)

            def generate(self, context):
                header_file = context.header_file
                if not self.props:
                    return

                ct = self.port.get_celltype()

                header_file.print("/*\n * {}\n".format(self.global_name))

                cells = {}
                subscripts = {}
                for prop in self.props:
                    cells.setdefault(prop.cell, []).append(prop)
                    subscripts.setdefault(prop.subscript, []).append(prop)

                no_cellidx = False
                if not (ct.has_INIB() or ct.has_CB()):
                    generalize_by_cell_idx = False
                    no_cellidx = True
                    cells = {self.props[0].cell: self.props}
                    header_file.print(" * No INIB & CB: generalized by subscript\n")
                elif self.port.get_array_size():
                    generalize_by_cell_idx = len(cells) >= len(subscripts)
                    if generalize_by_cell_idx:
                        header_file.print(" * more cells than subscripts: generalized by cell\n")
                    else:
                        header_file.print(" * more subscripts than cells: generalized by subscript\n")
                else:
                    generalize_by_cell_idx = True
                    header_file.print(" * non-array entry port: generalized by cell\n")

                header_file.print(" */\n\n")

                if generalize_by_cell_idx:
                    for subscript, props in subscripts.items():
                        if subscript is not None:
                            fn_name = "{}_adap_{}".format(self.global_name, subscript)
                        else:
                            fn_name = "{}_adap".format(self.global_name)

                        self.generate_inner(context, fn_name, Sym("generic"), subscript, ct)

                        for prop in props:
                            handle = self.adapter_handle_for_entry_property(prop)
                            if ct.has_INIB() or ct.has_CB():
                                idx = ct.get_name_array(prop.cell)[7]
                            else:
                                idx = "0"
                            header_file.print("#define {} &{}\n".format(handle[0], fn_name))
                            header_file.print("#define {} {}\n\n".format(handle[1], idx))
                else:
                    for cell, props in cells.items():
                        if no_cellidx:
                            fn_name = "{}_adap".format(self.global_name)
                        else:
                            fn_name = "{}_adap_{}".format(self.global_name, cell.get_global_name())

                        self.generate_inner(context, fn_name, cell, Sym("generic"))

                        for prop in props:
                            handle = self.adapter_handle_for_entry_property(prop)
                            header_file.print("#define {} &{}\n".format(handle[0], fn_name))
                            sub = prop.subscript if prop.subscript is not None else 0
                            header_file.print("#define {} {}\n\n".format(handle[1], sub))

        def __init__(self, celltype_name, prefix):
            self.celltype_name = celltype_name
            self.prefix = prefix
            self.entry_ports = {}
            self.source_file = None
            self.header_file = None

        def make_adapter_handle(self, join):
            entry_port = self.entry_ports.get(join.get_rhs_port())
            if not entry_port:
                entry_port = NotifierPlugin.AdapterGenerator.EntryPort(
                    join.get_rhs_port(),
                    "{}_{}".format(self.celltype_name, self.prefix),
                )
                self.entry_ports[join.get_rhs_port()] = entry_port
            return entry_port.make_adapter_handle(join)

        def finish(self):
            self.source_file = AppFile.open("{}/{}.c".format(G.gen, self.celltype_name))
            self.source_file.print("\n/* Generated by {} */\n\n".format(self.__class__.__name__))
            self.source_file.print('#include "{}_aux.h"\n\n'.format(self.celltype_name))
            self.source_file.print('#include "{}_tecsgen.h"\n\n'.format(self.celltype_name))

            self.header_file = AppFile.open("{}/{}.h".format(G.gen, self.celltype_name))
            self.header_file.print("\n/* Generated by {} */\n\n".format(self.__class__.__name__))

            header_guard = "{}_H_{}".format(self.celltype_name, self.prefix)

            self.header_file.print("#ifndef {}\n".format(header_guard))
            self.header_file.print("#define {}\n\n".format(header_guard))
            self.header_file.print('#include "{}_aux.h"\n\n'.format(self.celltype_name))

            aux_header_file = AppFile.open("{}/{}_aux.h".format(G.gen, self.celltype_name))
            aux_header_file.print("\n/* Generated by {} */\n\n".format(self.__class__.__name__))

            aux_header_guard = "{}_AUX_H_{}".format(self.celltype_name, self.prefix)
            cb_type_only_guard = "{}_AUX_H_{}_CB_TYPE_ONLY".format(self.celltype_name, self.prefix)

            aux_header_file.print("#ifndef {}\n".format(aux_header_guard))
            aux_header_file.print("#define {}\n\n".format(aux_header_guard))

            aux_header_file.print("#ifndef TOPPERS_CB_TYPE_ONLY\n")
            aux_header_file.print("#define TOPPERS_CB_TYPE_ONLY\n")
            aux_header_file.print("#define {}\n".format(cb_type_only_guard))
            aux_header_file.print("#endif\n")

            seen_ct = []
            for ep in self.entry_ports.values():
                ct = ep.port.get_celltype()
                if ct not in seen_ct:
                    seen_ct.append(ct)
                    hname = "{}_tecsgen.{}".format(ct.get_global_name(), G.h_suffix)
                    aux_header_file.print('#include "{}"\n'.format(hname))

            aux_header_file.print("#ifdef {}\n".format(cb_type_only_guard))
            aux_header_file.print("#undef {}\n".format(cb_type_only_guard))
            aux_header_file.print("#undef TOPPERS_CB_TYPE_ONLY\n")
            aux_header_file.print("#endif\n\n")

            aux_header_file.print("#endif\n")
            aux_header_file.close()

            for entry_port in self.entry_ports.values():
                entry_port.generate(self)

            self.header_file.print("#endif\n")

            self.source_file.close()
            self.header_file.close()

    def __init__(self, celltype, option):
        super().__init__(celltype, option)
        self.plugin_arg_check_proc_tab = NotifierPluginArgProc
        self.factory = None
        self.output_file = None
        self.parse_plugin_arg()
        if not self.factory:
            self.cdl_error(
                "NTF1003 celltype $1: option factory is not specified",
                celltype.get_name(),
            )
        if not self.output_file:
            self.cdl_error(
                "NTF1003 celltype $1: option output_file is not specified",
                celltype.get_name(),
            )

    def set_factory(self, template_string):
        if self.factory is not None:
            self.cdl_error(
                "NTF1003 celltype $1: option factory was specified more than once",
                self.celltype.get_name(),
            )
        self.factory = template_string

    def set_factory_output_file(self, output_file):
        if self.output_file is not None:
            self.cdl_error(
                "NTF1003 celltype $1: option output_file was specified more than once",
                self.celltype.get_name(),
            )
        self.output_file = output_file

    def gen_factory(self, file):
        kernel_cfg = AppFile.open("{}/{}".format(G.gen, self.output_file))
        kernel_cfg.print("\n/* Generated by {} */\n".format(self.__class__.__name__))
        kernel_cfg.print('#include "tTimeEventHandler.h"\n')

        self.adpt_gen = NotifierPlugin.AdapterGenerator(
            "tTimeEventHandler", self.celltype.get_global_name()
        )

        for match in re.finditer(r"\{\{([a-zA-Z0-9_]*?)\}\}", self.factory):
            name = Sym(match.group(1))
            if name == Sym("_handler_params_"):
                continue
            subst_attr = self.celltype.find(name)
            if not subst_attr:
                self.cdl_error(
                    "NTF1007 celltype $1: additional_param: attribute $2 does not exist.",
                    self.celltype.get_name(),
                    name,
                )

        for cell in self.celltype.get_cell_list():
            self.gen_factory_for_cell(kernel_cfg, cell)

        self.adpt_gen.finish()
        kernel_cfg.close()

    def gen_factory_for_cell(self, kernel_cfg, cell):
        handler_flags = []
        handler_args = []

        event_handler_might_fail = True
        handler_flag = None

        ignore_errors_attr_join = cell.get_join_list().get_item(Sym("ignoreErrors"))
        ignore_errors_attr = cell.get_celltype().find(Sym("ignoreErrors"))
        if ignore_errors_attr_join:
            ignore_errors = _expr_str(ignore_errors_attr_join.get_rhs())
        else:
            ignore_errors = _expr_str(ignore_errors_attr.get_initializer())

        if ignore_errors == "true":
            ignore_errors = True
        elif ignore_errors == "false":
            ignore_errors = False
        else:
            self.cdl_warning2(
                cell.get_locale(),
                "NTF1005 cell $1: unrecognized value '$2' specified for ignoreErrors",
                cell.get_name(),
                ignore_errors,
            )
            ignore_errors = False

        pre_text = ""
        post_text = "\n"
        indent = ""

        for handler in (EVENT_HANDLER, ERROR_HANDLER):
            pre_text = ""
            post_text = "\n"
            indent = ""

            call_join = cell.get_join_list().get_item(Sym(handler.call_port_name))

            matches = [
                ht for ht in HANDLER_TYPES if ht.validate_join(handler, cell, call_join)
            ]

            if len(matches) == 0:
                self.cdl_error2(
                    cell.get_locale(),
                    "NTF1001 cell $1: no matching handler type found for $2",
                    cell.get_name(),
                    handler.call_port_name,
                )
                continue

            ht = matches[0]

            domain_root = cell.get_region().get_domain_root()
            domain_type = domain_root.get_domain_type()
            if domain_type:
                if domain_type.get_name() in (Sym("HRP"), Sym("HRMP")):
                    option = domain_type.get_option()
                    for match in matches:
                        if isinstance(match, _OUT_OF_DOMAIN_HANDLER_TYPES):
                            if option == "OutOfDomain":
                                self.cdl_error2(
                                    cell.get_locale(),
                                    "NTF9999: NotifierPlugin: $1 cannot be placed out of domain",
                                    cell.get_name(),
                                )
                            elif (
                                call_join.get_cell().get_region().get_domain_root() is None
                                or call_join.get_cell().get_region().get_domain_root()
                                != domain_root
                            ):
                                self.cdl_error2(
                                    cell.get_locale(),
                                    "NTF9999: NotifierPlugin: $1 and $2 must be placed in same domain",
                                    cell.get_name(),
                                    call_join.get_cell().get_name(),
                                )
                            dbgPrint("{}: match pattern 1.\n".format(self.__class__.__name__))
                        elif isinstance(match, UserHandlerType):
                            if option != "kernel":
                                self.cdl_error2(
                                    cell.get_locale(),
                                    "NTF9999: NotifierPlugin: $1 can be placed in kernel domain only, because notify target is handler",
                                    cell.get_name(),
                                )
                            elif (
                                call_join.get_cell().get_region().get_domain_root() is None
                                or call_join.get_cell().get_region().get_domain_root()
                                != domain_root
                            ):
                                self.cdl_error2(
                                    cell.get_locale(),
                                    "NTF9999: NotifierPlugin: $1 and $2 must be placed in same domain",
                                    cell.get_name(),
                                    call_join.get_cell().get_name(),
                                )
                            dbgPrint("{}: match pattern 2.\n".format(self.__class__.__name__))
                        elif isinstance(match, NullHandlerType):
                            dbgPrint("{}: match pattern 3.\n".format(self.__class__.__name__))

                    if option == "kernel":
                        pre_text = "KERNEL_DOMAIN{\n"
                        post_text = "}\n"
                        indent = "  "
                    elif option != "OutOfDomain":
                        pre_text = "DOMAIN({}){{\n".format(domain_root.get_name())
                        post_text = "}\n"
                        indent = "  "
                else:
                    self.cdl_error(
                        "NTF9999: NotifierPlugin: unknown domain type $1",
                        domain_type.get_name(),
                    )

            class_root = cell.get_region().get_class_root()
            if class_root is None:
                raise RuntimeError("class root is nil")
            class_type = class_root.get_class_type()
            if class_type:
                if class_type.get_name() in (Sym("FMP"), Sym("HRMP")):
                    attr = class_type.get_plugin().get_PU_attr()
                    if attr[Sym("class_name")] == "global":
                        self.cdl_error2(
                            cell.get_locale(),
                            "FMP9999 $1: not be placed in class region",
                            cell.get_name(),
                        )
                    else:
                        pre_text += "{}CLASS({}){{\n".format(indent, attr[Sym("class_name")])
                        post_text = "{}}}\n".format(indent) + post_text
                        indent += "  "
                else:
                    self.cdl_error(
                        "NTF9999: NotifierPlugin: unknown class type $1",
                        class_type.get_name(),
                    )

            if (
                handler is ERROR_HANDLER
                and not isinstance(ht, NullHandlerType)
                and not event_handler_might_fail
            ):
                self.cdl_error2(
                    cell.get_locale(),
                    "NTF1004 cell $1: handler type $2 which never raises an error was inferred for the normal notification handler, but an error notification handler was specified.",
                    cell.get_name(),
                    handler_flag,
                )
            if (
                handler is ERROR_HANDLER
                and isinstance(ht, NullHandlerType)
                and event_handler_might_fail
                and not ignore_errors
            ):
                self.cdl_warning2(
                    cell.get_locale(),
                    "NTF1006 cell $1: handler type $2 which might raise an error was inferred for the normal notificaton handler, but an error notification handler was not specified.",
                    cell.get_name(),
                    handler_flag,
                )

            if not ht.validate_join(handler, cell, call_join):
                raise RuntimeError("!validate_join")

            handler_flag = ht.gen_cfg_handler_type(handler)
            if handler_flag:
                handler_flags.append(handler_flag)

            attr_map = ht.generate_attr_map(handler, cell)

            handler_arg = ht.gen_cfg_handler_parameters(
                handler, call_join, attr_map, cell, self.adpt_gen
            )
            if handler_arg:
                handler_args += handler_arg

            if handler is EVENT_HANDLER:
                event_handler_might_fail = ht.might_fail()

        name_array = cell.get_celltype().get_name_array(cell)
        new_handler_args = []
        for e in handler_args:
            if e == "$cbp$":
                new_handler_args.append(cell.get_celltype().subst_name(e, name_array))
            else:
                new_handler_args.append(e)
        handler_args = new_handler_args

        def replace_factory(m):
            name = Sym(m.group(1))
            if name == Sym("_handler_params_"):
                args_joined = " | ".join(handler_flags)
                if handler_args:
                    if args_joined:
                        args_joined += ", "
                    args_joined += ", ".join(handler_args)
                return args_joined

            subst_attr = cell.get_celltype().find(name)
            if not subst_attr:
                return ""

            subst_attr_join = cell.get_join_list().get_item(name)
            if subst_attr_join:
                subst = _expr_str(subst_attr_join.get_rhs())
            else:
                subst = _expr_str(subst_attr.get_initializer())

            return cell.get_celltype().subst_name(subst, name_array)

        text = re.sub(r"\{\{([a-zA-Z0-9_]*?)\}\}", replace_factory, self.factory)

        kernel_cfg.print(pre_text)
        kernel_cfg.print(indent + text + "\n")
        self.gen_sac(kernel_cfg, cell, indent)
        kernel_cfg.print(post_text)

    def gen_sac(self, file, cell, indent):
        domain_root = cell.get_region().get_domain_root()
        domain_type = domain_root.get_domain_type()
        if not domain_type:
            return

        id_ = _expr_str(cell.get_attr_initializer(Sym("id")))
        name_array = cell.get_celltype().get_name_array(cell)
        ct_name = cell.get_celltype().get_name()
        if ct_name == Sym("tCyclicNotifier"):
            obj_type = "CYC"
        elif ct_name == Sym("tAlarmNotifier"):
            obj_type = "ALM"
        else:
            raise RuntimeError(
                "NotifierPlugin: unknown celltype {}".format(ct_name)
            )

        id_ = cell.get_celltype().subst_name(id_, name_array)

        domain_type_name = str(domain_type.get_name())
        plugin_name = domain_type_name + "DomainPlugin"
        if not _const_defined(plugin_name):
            plugin_name = domain_type_name + "Plugin"
            if not _const_defined(plugin_name):
                raise RuntimeError(
                    "NotifierPlugin: Unkown Domain Plugin {}".format(domain_type_name)
                )

        pl_class = _import_plugin_class(plugin_name)
        if pl_class is None:
            pl_class = _const_get(plugin_name)

        file.print(
            "{}{}_SAC( {}, {} );\n".format(
                indent, obj_type, id_, pl_class.get_sac_str(cell)
            )
        )
