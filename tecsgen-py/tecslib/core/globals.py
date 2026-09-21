# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) を Python へ移植したものの一部である．
#   ライセンスは tecsgen.py の冒頭を参照のこと．
#
#= tecsgen のグローバル変数
#
# Ruby 版の $xxx をこのモジュールの属性として持つ．参照側は
#   from tecslib.core import globals as G
# として G.gen のように書き，Ruby 版との対応を機械的に追えるようにする．
#
# 元の定義は tecsgen.rb の TECSGEN.initialize_global_var にある．

import os

from tecslib.rubylib.kconv import Kconv

# このファイルは tecslib/core にあるので，二つ上が tecsgen.py のあるディレクトリ
# (Ruby 版の $tecsgen_base_path に対応)
tecsgen_base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# tecscde / tecsflow から起動された場合に真になる (本移植では常に偽)
TECSCDE = False
TECSFLOW = False
IN_EXERB = False

# tecscde などが設定するバナー用の変数
title = None
tool_version = None

# コマンドライン引数　 (Makefile.templ へ出力)
arguments = ""
ARGV = []

unopt = False              # bool:   disable optimizing both call and entry port
unopt_entry = False        # bool:   disable optimizing entry port
gen_base = "gen"           # string: folder path to place generated files
gen = gen_base             # string: folder path to place generated files
generate_all_template = False  # bool:   generarete template files for all celltypes (if non cell exist or system celltypes)
generate_no_template = False   # bool:   generarete no template file (neither celltype code nor Makefile)
idx_is_id = False          # bool:   all components are idx_is_id
unique_id = False          # bool:   assign unique id to each cell (otherwise begin from 1 for each celltype)
debug = False              # bool:   tecsgen debug message
dryrun = False             # bool:   dryrun mode: syntax is checked, but not generate any files
show_tree = False          # bool:   show parsing tree
verbose = False            # bool:   verbose mode: show some messages
yydebug = False            # bool:   yydebug: parser debug mode
run_dir = os.getcwd()      # string: tecsgen/tecscde start up directory
base_dir = {}              # string=>bool: base dir for import_path (key:base_dir, val:actually used or specified directly)
import_path = ["."]        # string array : import/import_C path
import_path_opt = []       # [String]
library_path = [tecsgen_base_path]  # string array : path to dir where tecsgen.py placed
define = []                # string array : define
ram_initializer = False    # bool: generate ram initializer
region_list = {}           # string array : region path which is generated
generating_region = None   # Region:  Region to optimisze & generate code   # コマンドラインオプションではない
                           #          Cell#is_generate? にて参照される
unit_test = False          # bool:   unit test verification
kcode = None               # nil | String: Kanji code type "euc"|"sjis"|"none"|"utf8"
force_overwrite = False    # bool:  force overwrite all files if file contents not differ
no_banner = False          # bool:   not print banner
print_version = False      # bool:   print version
target = "tecs"            # String: target name, ARGV[0] から再設定する（"tecs" は仮のターゲット)
no_default_import_path = False  # bool: no default import path
c_suffix = "c"             # suffix for C progorams (for C++ source)
h_suffix = "h"             # suffix for C progoram headers (for C++ source)

# bool:   ROM support : generate CB separately
rom = not os.environ.get("TECSGEN_DEFAULT_RAM")

b_cpp_specified = False
cpp = "gcc -E -DTECSGEN"
if os.environ.get("TECS_CPP"):
    cpp = os.environ["TECS_CPP"]
    b_cpp_specified = True

if os.environ.get("TECSPATH"):
    tecspath = os.environ["TECSPATH"]
else:
    tecspath = "{}/tecs".format(tecsgen_base_path)

# 文字コードの設定
KCONV_CDL = Kconv.EUC        # const: NONE には ASCII を対応させる

# KCONV_TECSGEN を仮に設定する (tecs_lang.py ですぐに再設定される)
KCONV_TECSGEN = Kconv.UTF8   # const:
KCONV_CONSOLE = Kconv.BINARY

# tecs_lang.py が設定する
LANG_FILE = None
LANG_CONSOLE = None
CHARSET_FILE = None
CHARSET_CONSOLE = None
Ruby19_File_Encode = "ASCII-8BIT"


#=== ARGV に依存する変数を設定する
#argv:: [str]   : プログラム名を除いたコマンドライン引数
def initialize(argv):
    global ARGV, arguments
    ARGV = list(argv)
    arguments = ""
    for a in ARGV:
        arguments += " " + a


# version.py が設定する ($package, $version)
package = None
version = None
Copyright = None


#=== 未定義のグローバル変数を参照したことを分かりやすくする
def __getattr__(name):
    raise AttributeError(
        "tecsgen のグローバル変数 '{}' は定義されていない (tecslib/core/globals.py を参照)".format(name)
    )
