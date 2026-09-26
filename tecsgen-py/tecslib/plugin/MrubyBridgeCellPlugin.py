# -*- coding: utf-8 -*-
#
#  MrubyBridgeCellPlugin.rb の Python 移植

from tecslib.core.componentobj.port import Port
from tecslib.core.syntaxobj.cdlstring import CDLString
from tecslib.core.toplevel import dbgPrint
from tecslib.plugin.CellPlugin import CellPlugin
from tecslib.rubylib.symbol import Sym


def _set_ignoreUnsigned(obj, rhs):
    obj.set_ignoreUnsigned(rhs)


def _set_exclude_port(obj, rhs):
    obj.set_exclude_port(rhs)


def _set_exclude_port_func(obj, rhs):
    obj.set_exclude_port_func(rhs)


def _set_auto_exclude(obj, rhs):
    obj.set_auto_exclude(rhs)


class MrubyBridgeCellPlugin(CellPlugin):

    MrubyBridgePluginArgProc = {
        "ignoreUnsigned": _set_ignoreUnsigned,
        "exclude_port": _set_exclude_port,
        "exclude_port_func": _set_exclude_port_func,
        "auto_exclude": _set_auto_exclude,
    }

    cell_list = {}
    signature_list = {}

    def __init__(self, cell, option):
        dbgPrint("  {}: initialzie={} option={}\n".format(
            self.__class__.__name__, cell.get_name(), option))
        super().__init__(cell, option)
        self.cell = cell

        self.b_ignoreUnsigned = False
        self.exclude_port = []
        self.exclude_port_func = {}
        self.b_auto_exclude = True

        self.plugin_arg_str = CDLString.remove_dquote(option)
        self.plugin_arg_list = {}
        dbgPrint("{}: initialzie: {}\n".format(self.__class__.__name__, cell.get_name()))
        self.plugin_arg_check_proc_tab = MrubyBridgeCellPlugin.MrubyBridgePluginArgProc
        self.parse_plugin_arg()

        self.port_list = {}
        ct = self.cell.get_celltype()
        if ct is None:
            return

        port_list = ct.get_port_list()
        if len(self.exclude_port) > 0:
            for port in port_list:
                if port.get_name() not in self.exclude_port:
                    self.port_list[port] = ""
        else:
            for port in port_list:
                self.port_list[port] = ""

        if len(self.exclude_port_func) > 0:
            for port, opt_str in list(self.port_list.items()):
                delim = ""
                if str(port.get_name()) in self.exclude_port_func:
                    for func_name in self.exclude_port_func[str(port.get_name())]:
                        opt_str += delim + "exclude=" + func_name
                        delim = ","
                self.port_list[port] = opt_str

    def gen_cdl_file(self, file):
        dbgPrint("{}: gen_cdl_file: {}\n".format(self.__class__.__name__, self.cell.get_name()))

        file.print("/* MrubyBridgeCellPlugin: generate for cell={} */\n".format(self.cell.get_name()))

        if MrubyBridgeCellPlugin.cell_list.get(self.cell):
            file.print("""
/*
 * generate for {} duplicate and ignored.
 * This might comes from generate for celltype.
 */
""".format(self.cell.get_name()))
            self.cdl_info("MrubyBridgeCellPlugin: generate duplicate for cell '$1'", self.cell.get_name())
            return
        MrubyBridgeCellPlugin.cell_list[self.cell] = self.cell

        for port, opt_str in self.port_list.items():
            if port.get_signature() is None:
                continue
            ctx = port.get_signature().get_context()
            if ctx not in ("task", "any"):
                continue
            if port.get_port_type() == Sym("ENTRY"):
                print("  MrubyBridgeCellPlugin: [cell.port] {}.{} => [mruby instance] TECS::T{}.new( '{}{}Bridge' ) \n".format(
                    self.cell.get_name(), port.get_name(), port.get_signature().get_global_name(),
                    self.cell.get_name(), port.get_name()))
                if MrubyBridgeCellPlugin.signature_list.get(port.get_signature()) is None:
                    opt_str = "ignoreUnsigned={}, auto_exclude={}, ".format(
                        self.b_ignoreUnsigned, self.b_auto_exclude) + opt_str
                    file.print("""
/* cell.port={}.{} */
generate( MrubyBridgePlugin, {}, "{}" );
""".format(self.cell.get_name(), port.get_name(),
           port.get_signature().get_namespace_path(), opt_str))
                    MrubyBridgeCellPlugin.signature_list[port.get_signature()] = True

                nest = self.cell.get_region().gen_region_str_pre(file)
                nest_str = "  " * nest
                file.print("""{0}/* BridgeCell */
{0}cell nMruby::t{1} {2}{3}Bridge {{
{0}    cTECS = {4}.{5};
{0}}};
""".format(nest_str, port.get_signature().get_global_name(), self.cell.get_name(), port.get_name(),
           self.cell.get_namespace_path(), port.get_name()))
                self.cell.get_region().gen_region_str_post(file)

    @classmethod
    def gen_post_code(cls, file):
        dbgPrint("{}: gen_post_code\n".format(cls.__name__))
        cls.gen_post_code_body(file)

    @classmethod
    def gen_post_code_body(cls, file):
        dbgPrint("{}: gen_post_code_body\n".format(cls.__name__))

    def set_ignoreUnsigned(self, rhs):
        if rhs == "true" or rhs is None:
            self.b_ignoreUnsigned = True

    def set_exclude_port(self, rhs):
        ports = rhs.split(',')
        ct = self.cell.get_celltype()
        if ct is None:
            return
        for rhs_port in ports:
            obj = ct.find(Sym(rhs_port))
            if (type(obj) is not Port) or obj.get_port_type() != Sym("ENTRY"):
                self.cdl_error(
                    "MRB9999 exclude_port '$1' not found or not entry in celltype '$2'",
                    rhs_port, ct.get_name())
            else:
                self.exclude_port.append(rhs_port)

    def set_exclude_port_func(self, rhs):
        port_funcs = rhs.split(',')
        ct = self.cell.get_celltype()
        if ct is None:
            return
        for rhs_port_func in port_funcs:
            port_func = rhs_port_func.split('.')
            if len(port_func) != 2:
                self.cdl_error("MRB9999 exclude_port_func: '$1' not in 'port.func' form", rhs_port_func)
            obj = ct.find(Sym(port_func[0]))
            if (type(obj) is not Port) or obj.get_port_type() != Sym("ENTRY"):
                self.cdl_error(
                    "MRB9999 exclude_port_func: port '$1' not found in celltype '$2'",
                    port_func[0], ct.get_name())
            else:
                signature = obj.get_signature()
                if signature is None:
                    continue
                if signature.get_function_head(Sym(port_func[1])):
                    if port_func[0] in self.exclude_port_func:
                        self.exclude_port_func[port_func[0]].append(port_func[1])
                    else:
                        self.exclude_port_func[port_func[0]] = [port_func[1]]
                else:
                    self.cdl_error(
                        "MRB9999 exclude_port_func: func '$1' not found in port '$2' celltype $3",
                        port_func[1], port_func[0], ct.get_name())

    def set_auto_exclude(self, rhs):
        if rhs == "false":
            self.b_auto_exclude = False
        elif rhs == "true":
            self.b_auto_exclude = True
        else:
            self.cdl_warning("MRB9999 auto_exclude: unknown rhs value ignored. specify true or false")
