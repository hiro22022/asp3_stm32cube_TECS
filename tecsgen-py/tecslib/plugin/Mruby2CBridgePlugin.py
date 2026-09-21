# -*- coding: utf-8 -*-
#
#  Mruby2CBridgePlugin.rb の Python 移植

from tecslib.core import globals as G
from tecslib.core.plugin import CFile
from tecslib.plugin.SignaturePlugin import SignaturePlugin
from tecslib.rubylib.symbol import Sym


class Mruby2CBridgePlugin(SignaturePlugin):

    signature_list = {}

    def __init__(self, signature, option):
        super().__init__(signature, option)
        self.celltype_name = Sym("t{}".format(self.signature.get_global_name()))
        self.class_name = Sym("T{}".format(self.signature.get_global_name()))
        self.parse_plugin_arg()

    def gen_cdl_file(self, file):
        c2tecs = ""
        if len(Mruby2CBridgePlugin.signature_list) == 0:
            self.print_msg(
                "  Mruby2CBridgePlugin: [initialize function] "
                "'void initializeBridge( mrb_state *mrb )' must be called from VM.\n")
            c2tecs = 'generate( C2TECSBridgePlugin, nMruby::sInitializeBridge, "silent=true" );\n'

        gname = self.signature.get_global_name()
        if Mruby2CBridgePlugin.signature_list.get(gname):
            Mruby2CBridgePlugin.signature_list[gname].append(self)
            self.cdl_warning(
                "MRCW001 signature '$1' duplicate. ignored current one",
                self.signature.get_namespace_path())
            return

        Mruby2CBridgePlugin.signature_list[gname] = [self]
        self.print_msg(
            "  Mruby2CBridgePlugin: [object creattion]    object = TECS::{}.new( 'C{}' )\n".format(
                self.class_name, self.signature.get_global_name()))
        self.print_msg(
            "  Mruby2CBridgePlugin: [function call]       result = object.function( params )  "
            "# substitute 'function' and params \n")

        cf = CFile.open("{}/Mruby2C_tsInitializerBridge.cdl".format(G.gen), "w")
        cf.print("""cell nC2TECS::tnMruby_sInitializeBridge C2TECS_tsInitializeBridge{
    cCall = VM_TECSInitializer.eInitialize;
};
""")
        cf.close()

        file.print("""generate( MrubyBridgePlugin, {}, "silent=true" );
generate( TECS2CBridgePlugin, {}, "silent=true" );
{}
cell nMruby::t{} C{} {{
    cTECS = TECS2C_{}.eEnt;
}};
cell nTECS2C::t{} TECS2C_{}{{};

import( "Mruby2C_tsInitializerBridge.cdl" );
""".format(
            self.signature.get_namespace_path(),
            self.signature.get_namespace_path(),
            c2tecs,
            self.signature.get_name(), self.signature.get_name(),
            self.signature.get_name(),
            self.signature.get_name(), self.signature.get_name(),
        ))
