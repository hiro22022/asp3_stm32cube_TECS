# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/componentobj/importable.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

import os

from tecslib.core import globals as G
from tecslib.core.toplevel import dbgPrint


#== Importable class
# this module is included by Import_C and Import
class Importable:
    #@last_base_dir::String

    #=== Importable#find_file
    #file::String : file name to find
    #return::String | Nil: path to file or nil if not found
    #find file in
    def find_file(self, file):
        for path in G.import_path:
            if path == ".":
                pt = file
            else:
                pt = "{}/{}".format(path, file)
            if os.path.exists(pt):
                if not G.base_dir.get(os.getcwd()):
                    G.base_dir[os.getcwd()] = True
                if G.verbose:
                    print("{} is found in {}\n".format(file, path), end="")
                self.last_base_dir = None
                dbgPrint("base_dir=. while searching {}\n".format(file))
                return pt

        for bd in G.base_dir.keys():
            for path in G.import_path:
                #        if path =~ /\A\// || path =~ /\A[a-zA-Z]:/
                pt = "{}/{}".format(path, file)
                #        else
                #          pt = "#{bd}/#{path}/#{file}"
                #        end
                try:
                    os.chdir(G.run_dir)
                    os.chdir(bd)
                    if os.path.exists(pt):
                        if G.verbose:
                            print("{} is found in {}/{}\n".format(file, bd, path), end="")
                        self.last_base_dir = bd
                        dbgPrint("base_dir={} while searching {}\n".format(bd, file))
                        G.base_dir[bd] = True
                        return pt
                except Exception:
                    pass
        self.last_base_dir = None
        dbgPrint("base_dir=. while searching {}\n".format(file))
        return None

    def get_base_dir(self):
        return self.last_base_dir
        for bd, flag in G.base_dir.items():
            if flag == True:
                return bd
        return None
