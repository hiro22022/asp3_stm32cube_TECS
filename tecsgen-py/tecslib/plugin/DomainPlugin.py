# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#   DomainPlugin.rb の Python 移植

from tecslib.core.plugin import Plugin
from tecslib.rubylib.symbol import Sym


class DomainPlugin(Plugin):

    def __init__(self, region, domain_type_name, option):
        super().__init__()

    def add_through_plugin(self, join, current_region, next_region, through_type):
        return None

    def joinable(self, current_region, next_region, through_type):
        return False

    def get_kind(self):
        return Sym("kernel")

    def gen_factory(self, node_root):
        pass

    @classmethod
    def gen_post_code(cls, file):
        pass
