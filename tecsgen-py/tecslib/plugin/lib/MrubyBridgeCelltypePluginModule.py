# -*- coding: utf-8 -*-
#
#  MrubyBridgeCelltypePluginModule.rb の Python 移植

import tecsgen
from tecslib.core import globals as G
from tecslib.core.componentobj.import_ import Import
from tecslib.core.componentobj.port import Port
from tecslib.core.syntaxobj.cdlstring import CDLString
from tecslib.core.toplevel import dbgPrint
from tecslib.rubylib.symbol import Sym

TECSGEN = tecsgen.TECSGEN


def _set_ignoreUnsigned(obj, rhs):
    obj.set_ignoreUnsigned(rhs)


def _set_include_inner_cell(obj, rhs):
    obj.set_include_inner_cell(rhs)


def _set_exclude_cell(obj, rhs):
    obj.set_exclude_cell(rhs)


def _set_exclude_port(obj, rhs):
    obj.set_exclude_port(rhs)


def _set_exclude_port_func(obj, rhs):
    obj.set_exclude_port_func(rhs)


def _set_auto_exclude(obj, rhs):
    obj.set_auto_exclude(rhs)


class MrubyBridgeCelltypePluginModule(object):

    MrubyBridgePluginArgProc = {
        "ignoreUnsigned": _set_ignoreUnsigned,
        "include_inner_cell": _set_include_inner_cell,
        "exclude_cell": _set_exclude_cell,
        "exclude_port": _set_exclude_port,
        "exclude_port_func": _set_exclude_port_func,
        "auto_exclude": _set_auto_exclude,
    }

    plugin_list = []
    count = 1
    b_gen_post_code_called = False

    def __init__(self, celltype, option):
        dbgPrint("{}: initialzie: {}\n".format(self.__class__.__name__, celltype.get_name()))
        super().__init__(celltype, option)
        self.celltype = celltype
        self.cell_list = []
        self.include_inner_cell = False
        self.exclude_cells = []
        self.exclude_port = []
        self.exclude_port_func = {}
        self.b_ignoreUnsigned = False
        self.b_auto_exclude = True
        MrubyBridgeCelltypePluginModule.plugin_list.append(self)

        self.plugin_arg_check_proc_tab = MrubyBridgeCelltypePluginModule.MrubyBridgePluginArgProc
        self.plugin_arg_str = CDLString.remove_dquote(option)
        self.parse_plugin_arg()

    def new_cell(self, cell):
        dbgPrint("MrubyBridgeCelltypePluginModule: new_cell: {}\n".format(cell.get_name()))

        if cell in self.cell_list:
            return
        if TECSGEN.post_coded():
            self.cdl_info(
                "I9999 MrubyBridgeCelltypePlugin: $1 is excluded because cell generated after post_coded",
                cell.get_name())
            return

        if cell.is_cloned() and self.include_inner_cell is False:
            self.cdl_info("I9999 MrubyBridgeCelltypePlugin: inner cell $1 is excluded", cell.get_name())
            return

        if cell.get_name() in self.exclude_cells:
            return

        opt_str = "ignoreUnsigned={}, auto_exclude={}".format(self.b_ignoreUnsigned, self.b_auto_exclude)
        for port in self.exclude_port:
            opt_str += ",exclude_port={}".format(port)
        for port, funcs in self.exclude_port_func.items():
            for func in funcs:
                opt_str += ",exclude_port_func={}.{}".format(port, func)

        fn2 = "{}/tmp_MrubyBridgeCelltypePluginModule_{}_{}.cdl".format(
            G.gen, self.celltype.get_name(), MrubyBridgeCelltypePluginModule.count)
        with open(fn2, "w") as f2:
            f2.write("""/* MrubyBridgeCelltypePluginModule: celltype={} */
generate( MrubyBridgeCellPlugin, {}, "{}" );
""".format(self.celltype.get_name(), cell.get_namespace_path(), opt_str))
        dbgPrint("MrubyBridgeCelltypePluginModule new_cell: Import {}\n".format(fn2))
        Import(fn2)
        MrubyBridgeCelltypePluginModule.count += 1

    def gen_cdl_file(self, file):
        pass

    def gen_factory(self, file):
        pass

    def get_celltype(self):
        return self.celltype

    @classmethod
    def gen_post_code(cls, file):
        dbgPrint("{}: gen_post_code_body\n".format(cls.__name__))
        if cls.b_gen_post_code_called is False:
            cls.b_gen_post_code_called = True

    def set_ignoreUnsigned(self, rhs):
        if rhs == "true" or rhs is None:
            self.b_ignoreUnsigned = True

    def set_include_inner_cell(self, rhs):
        if rhs == "true" or rhs is None:
            self.include_inner_cell = True

    def set_exclude_cell(self, rhs):
        cells = rhs.split(',')
        for rhs_cell in cells:
            rhs_cell = rhs_cell.replace(' ', '')
            self.exclude_cells.append(Sym(rhs_cell))

    def set_exclude_port(self, rhs):
        ports = rhs.split(',')
        ct = self.celltype
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
        ct = self.celltype
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
                    rhs_port_func, ct.get_name())
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
                        "MRB9999 include_port_func: func '$1' not found in port '$2' celltype $3",
                        port_func[1], port_func[0], ct.get_name())

    def set_auto_exclude(self, rhs):
        if rhs == "false":
            self.b_auto_exclude = False
        elif rhs == "true":
            self.b_auto_exclude = True
        else:
            self.cdl_warning("MRB9999 auto_exclude: unknown rhs value ignored. specify true or false")
