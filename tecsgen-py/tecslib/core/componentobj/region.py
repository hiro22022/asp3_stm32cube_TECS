# -*- coding: utf-8 -*-
#
#  TECS Generator (Python port)
#      Generator for TOPPERS Embedded Component System
#
#   Copyright (C) 2008-2021 by TOPPERS Project TECS WG
#
#   このファイルは tecsgen (Ruby 版) の tecslib/core/componentobj/region.rb を
#   Python へ移植したものである．ライセンスは tecsgen.py の冒頭を参照のこと．

from tecslib.core.componentobj.namespace import Namespace
from tecslib.core.toplevel import dbgPrint
from tecslib.rubylib.symbol import Sym


#== Region クラス
#
# Region は Namespace を継承している
# root region は特殊で、root namespace と同じである
#
# cell は region に属する
# region に属する cell のリストは Namespace クラスのインスタンス変数として記憶される
#
class Region(Namespace):
# @name:: string
# @in_through_list:: [ [ plugin_name, plugin_arg ], ... ] : plungin_name = nil の時 in 禁止
# @out_through_list:: [ [ plugin_name, plugin_arg ], ... ] : plungin_name = nil の時 out 禁止
# @to_through_list:: [ [ dst_region, plugin_name, plugin_arg ], ... ]
# @from_through_list:: [ [ src_region, plugin_name, plugin_arg ], ... ]
# @cell_port_throug_plugin_list:: { "#{cell_name}.#{port_name}" => through_generated_list の要素 }
#    この region から cell_name.port_name への through プラグインで生成されたオブジェクト
# @region_type::Symbol|Nil : :NODE, :LINKUNIT, :DOMAIN, :CLASS
# @region_type_param::Symbol|Nil : domain, class の名前. node, linkunit では nil
# @link_root:: Region : linkUnit の根っことなる region (node, linkunit が指定された region)
# @node_root:: Region : node の根っことなる region (node が指定された region)
# @family_line:: [ @region_root, ...,@region_me ]  家系
# @in_through_count:: Integer :  n 番目の in_through 結合 (n>=0)
# @out_through_count:: Integer : n 番目の out_through 結合 (n>=0)
# @to_through_count:: { :RegionName => Integer }: RegionName への n 番目の to_through 結合 (n>=0)
# @from_through_count:: { :RegionName => Integer }: RegionName への n 番目の from_through 結合 (n>=0)
# @domain_type::DomainType : domain 指定されていない場合、nil
# @domain_root::Region : domain 指定されていなる Region (root の場合 nil)
# @class_type::ClassType : class 指定されていない場合、nil
# @class_root::Region : class 指定されていなる Region (root の場合 nil)

    in_through_list = []
    out_through_list = []
    to_through_list = []
    from_through_list = []
    region_type = None
    region_type_param = None
    domain_name = None
    domain_option = None    # Token が入る
    class_name = None
    class_option = None    # Token が入る

    link_roots = []
    node_roots = []

    def __init__(self, name):
        if name != "::":
            object = Namespace.get_current().find_inst(name)    #1
        else:
            # root リージョン
            object = None
            Region.region_type = Sym("NODE")

        self.in_through_list = Region.in_through_list
        self.out_through_list = Region.out_through_list
        self.to_through_list = Region.to_through_list
        self.from_through_list = Region.from_through_list
        self.region_type = Region.region_type
        self.region_type_param = Region.region_type_param

        Region.in_through_list = []
        Region.out_through_list = []
        Region.to_through_list = []
        Region.from_through_list = []
        Region.region_type = None
        Region.region_type_param = None

        self.in_through_count = -1
        self.out_through_count = -1
        self.to_through_count = {}
        self.from_through_count = {}

        super().__init__(name)
        self.set_region_roots()

        if Region.domain_name:
            dbgPrint("Region={} domain_type={} option={}\n".format(
                name, Region.domain_name, Region.domain_option))
            from tecslib.core.syntaxobj.cdlstring import CDLString
            from tecslib.core.componentobj.domaintype import DomainType
            domain_option = CDLString.remove_dquote(str(Region.domain_option))
            self.domain_type = DomainType(self, Region.domain_name, domain_option, self.node_root)
            Region.domain_name = None
            Region.domain_option = None
        else:
            self.domain_type = None

        if Region.class_name:
            dbgPrint("Region={} class_type={} option={}\n".format(
                name, Region.class_name, Region.class_option))
            from tecslib.core.componentobj.classtype import ClassType
            from tecslib.core.bnf import Token
            if isinstance(Region.class_option, Token):
                from tecslib.core.syntaxobj.cdlstring import CDLString
                class_option = CDLString.remove_dquote(str(Region.class_option))
            else:
                class_option = Region.class_option  # :global
            self.class_type = ClassType(self, Region.class_name, class_option, self.node_root)
            Region.class_name = None
            Region.class_option = None
        else:
            self.class_type = None

        if object:

            if type(object) is Region:
                dbgPrint("Region.new: re-appear {}\n".format(self.name))

                # # Region path が前回出現と一致するか？
                # if @@region_stack[ @@region_stack_sp - 1 ] then
                #   my_path = @@region_stack[ @@region_stack_sp - 1 ].get_path_string.to_s + "." + @name.to_s
                # else
                #   my_path = @name.to_s
                # end
                # if my_path != object.get_path_string then
                #   cdl_error( "S1139 $1: region path mismatch. previous path: $2" , my_path, object.get_path_string )
                # end

                # 再出現
                # @@region_stack[@@region_stack_sp] = object

                # 再出現時に specifier が指定されているか？
                if (len(self.in_through_list) != 0 or len(self.out_through_list) != 0 or
                        len(self.to_through_list) != 0 or len(self.from_through_list) != 0 or
                        self.region_type is not None or self.domain_type is not None or
                        self.class_type is not None):
                    self.cdl_error("S1140 $1: region specifier must place at first appearence", name)
                return

            else:
                # エラー用ダミー定義

                # 異なる同名のオブジェクトが定義済み
                self.cdl_error("S1141 $1 duplication, previous one : $2", name, object.__class__)
                # @@region_stack[@@region_stack_sp] = self    # エラー時暫定 region
        else:
            # 初出現
            dbgPrint("Region.new: {}\n".format(self.name))
            self.set_region_family_line()

            if self.region_type == Sym("NODE"):
                dbgPrint("new Node: {}\n".format(self.name))
                Region.node_roots.append(self)
            if self.region_type == Sym("NODE") or self.region_type == Sym("LINKUNIT"):
                dbgPrint("new LinkRoot: {}\n".format(self.name))
                Region.link_roots.append(self)

        self.cell_port_throug_plugin_list = {}

# p @name
# p @in_through_list
# p @out_through_list
# p @to_through_list

    @classmethod
    def end_of_parse(cls):
        ns = Namespace.get_current()
        ns.create_domain_plugin()
        ns.create_class_plugin()
        # Region.end_of_parse クラスメソッドが Namespace#end_of_parse を隠すため
        # インスタンス側は pop_inst を直接呼ぶ（Ruby ではクラス／インスタンスが別）
        ns.pop_inst()

    @classmethod
    def new_in_through(cls, plugin_name=None, plugin_arg=None):
        cls.in_through_list.append([plugin_name, plugin_arg])

    @classmethod
    def new_out_through(cls, plugin_name=None, plugin_arg=None):
        cls.out_through_list.append([plugin_name, plugin_arg])

    @classmethod
    def new_to_through(cls, dst_region, plugin_name, plugin_arg):
        # p "New to_through #{dst_region}"
        cls.to_through_list.append([dst_region, plugin_name, plugin_arg])

    @classmethod
    def new_from_through(cls, src_region, plugin_name, plugin_arg):
        # p "New to_through #{dst_region}"
        cls.from_through_list.append([src_region, plugin_name, plugin_arg])

    @classmethod
    def set_type(cls, type_, param=None):
        if cls.region_type:
            from tecslib.core.bnf import Generator
            Generator.error("S1178 $1 region type specifier duplicate, previous $2", type_, cls.region_type)
        cls.region_type = type_
        cls.region_type_param = param

    @classmethod
    def set_domain(cls, name, option):
        if cls.domain_name:
            from tecslib.core.bnf import Generator
            Generator.error("S9999 $1 domain specifier duplicate, previous $2", name, cls.domain_name)
        elif cls.class_name:
            from tecslib.core.bnf import Generator
            Generator.error("S9999 $1 domain & class specifier are incompatible $2", name, cls.class_name)
        cls.domain_name = name
        cls.domain_option = option

    @classmethod
    def set_class(cls, name, option):
        if cls.class_name:
            from tecslib.core.bnf import Generator
            Generator.error("S9999 $1 class specifier duplicate, previous $2", name, cls.class_name)
        elif cls.domain_name:
            from tecslib.core.bnf import Generator
            Generator.error("S9999 $1 class & domain specifier are incompatible $2", name, cls.domain_name)
        cls.class_name = name
        cls.class_option = option

    #== Region ルートリージョンを得る
    # ルートリージョンは、ルートネームスペースと同じである
    @classmethod
    def get_root(cls):
        return Namespace.get_root()

    def set_region_roots(self):
        # root namespace (root region) の region type は :NODE
        # if @name == "::" then
        #   @region_type = :NODE
        # end
        dbgPrint("Region#set_region_roots name={}\n".format(self.name))
        if self.region_type == Sym("NODE"):
            self.node_root = self
        else:
            self.node_root = self.owner.get_node_root()
        if self.region_type == Sym("NODE") or self.region_type == Sym("LINKUNIT"):
            self.link_root = self
        else:
            self.link_root = self.owner.get_link_root()

    def set_region_family_line(self):
        dbgPrint("set_region_family_line: Region: {}  \n".format(self.name))
            #---- Domain ----
        if self.domain_type is not None or self.owner is None or self.region_type == Sym("NODE"):
            self.domain_root = self
        else:
            self.domain_root = self.owner.get_domain_root()

        if self.domain_type:
            # ルートリージョンが最初から @domain_type 設定されることはないの
            # で @owner == nil を調べる必要はない
            self.owner.set_domain_type(self.domain_type)

        #---- Class ----
        if self.class_type is not None or self.owner is None or self.region_type == Sym("NODE"):
            self.class_root = self
        else:
            self.class_root = self.owner.get_class_root()

        if self.class_type:
            # ルートリージョンが最初から @class_type 設定されることはないの
            # で @owner == nil を調べる必要はない
            self.owner.set_class_type(self.class_type)

        #---- Faily Line ----
        if self.owner:
            self.family_line = list(self.owner.get_family_line()) + [self]
        else:
            self.family_line = [self]    # root region

    #== Region#ドメインを設定する
    #ドメインタイプが指定されたリージョンの親リージョンにドメインタイプを設定する
    # 親リージョンは、既にドメインタイプが指定されていなければ、OutOfDomain とする
    def set_domain_type(self, domain_type):
        if self.region_type == Sym("NODE"):
            if self.domain_type:
                if self.domain_type.get_name() != domain_type.get_name():
                    self.cdl_error("S9999 '$1' node root cannot belong to both $2 and $3",
                                   self.name, self.domain_type.get_name(), domain_type.get_name())
            else:
                from tecslib.core.componentobj.domaintype import DomainType
                self.domain_type = DomainType(self, domain_type.get_name(), "OutOfDomain", self.node_root)
                self.domain_type.create_domain_plugin()
        elif self.domain_type is None:
            self.owner.set_domain_type(domain_type)

    #== Region#クラスを設定する
    #クラスが指定されたリージョンの親リージョンにクラスを設定する
    # 親リージョンは、既にクラスが指定されていなければ、OutOfClass とする
    def set_class_type(self, class_type):
        if self.region_type == Sym("NODE"):
            if self.class_type:
                if self.class_type.get_name() != class_type.get_name():
                    self.cdl_error("S9999 '$1' node root cannot belong to both $2 and $3",
                                   self.name, self.class_type.get_name(), class_type.get_name())
            else:
                from tecslib.core.componentobj.classtype import ClassType
                self.class_type = ClassType(self, class_type.get_name(), Sym("root"), self.node_root)
                self.class_type.create_class_plugin()
        elif self.class_type is None:
            self.owner.set_class_type(class_type)

    @classmethod
    def get_node_roots(cls):
        return cls.node_roots

    @classmethod
    def get_link_roots(cls):
        return cls.link_roots

    def get_family_line(self):
        return self.family_line

    def get_in_through_list(self):
        return self.in_through_list

    def get_out_through_list(self):
        return self.out_through_list

    def get_to_through_list(self):
        return self.to_through_list

    def get_from_through_list(self):
        return self.from_through_list

    def get_node_root(self):
        return self.node_root

    def get_link_root(self):
        return self.link_root

    #== REgion# DomainType を返す
    # Region がドメインルートでない場合 nil を返す
    def get_domain_type(self):
        return self.domain_type

    #== Region# domain の根っことなる region を得る
    # Region のインスタンスを返す
    # domain 指定子があれば、そのリージョンがドメインルートである
    # なければ、親リージョンのドメインルートとする
    def get_domain_root(self):
        return self.domain_root

    #== REgion# ClassType を返す
    # Region がクラスルートでない場合 nil を返す
    def get_class_type(self):
        return self.class_type

    def get_class_root(self):
        return self.class_root

    def get_path_string(self):
        pstring = ""
        delim = ""
        for p in self.family_line:
            pstring = "{}{}{}".format(pstring, delim, p.get_name())
            delim = "."
        dbgPrint("get_path_string: {}\n".format(pstring))
        return pstring

    def get_region_type(self):
        return self.region_type

    def get_name(self):
        return self.name

    #== Region.ルートリージョン
    # ルートリージョンは、namespace のルートと同じインスタンス
    @classmethod
    def get_root(cls):
        return Namespace.get_root()

    def next_in_through_count(self):
        self.in_through_count += 1

    def next_out_through_count(self):
        self.out_through_count += 1

    def next_to_through_count(self, symRegionName):
        if self.to_through_count.get(symRegionName) is None:
            self.to_through_count[symRegionName] = 0
        else:
            self.to_through_count[symRegionName] += 1

    def next_from_through_count(self, symRegionName):
        if self.from_through_count.get(symRegionName) is None:
            self.from_through_count[symRegionName] = 0
        else:
            self.from_through_count[symRegionName] += 1

    #=== Region# 構文解析中の region を得る
    # 構文解析中 Namespace (あるいは子クラスの Region) の上位をたどって Region を見つける
    # cell が namespace 下におくことができなければ、ループをまわす必要はない
    @classmethod
    def get_current(cls):
        # @@region_stack[@@region_stack_sp]
        region = Namespace.get_current()
        while True:
            if type(region) is Region:
                break
            region = region.get_owner()
        return region

    #=== Region# through プラグインで、この region から cell_name.port_name へのプラグインオブジェクトを登録
    # mikan namesppace 対応 (cell_name)
    def add_cell_port_through_plugin(self, cell_name, port_name, subscript, through_plugin_object):
        if subscript:
            subscript = '[' + str(subscript) + ']'
        self.cell_port_throug_plugin_list["{}.{}".format(cell_name, port_name) + (subscript or "")] = through_plugin_object

    def find_cell_port_through_plugin(self, cell_name, port_name, subscript):
        if subscript:
            subscript = '[' + str(subscript) + ']'
        return self.cell_port_throug_plugin_list.get("{}.{}".format(cell_name, port_name) + (subscript or ""))

    def create_domain_plugin(self):
        if self.domain_type:
            self.domain_type.create_domain_plugin()

    def create_class_plugin(self):
        if self.class_type:
            self.class_type.create_class_plugin()

    #=== Region# to_region への距離（unreachable な場合 nil)
    # mikan Cell#check_region とRegion へたどり着くまでの処理に共通性が高い
    # region#distance は require で用いられる
    def distance(self, to_region):

        r1 = self                   # 出発 region
        r2 = to_region              # 目的 region
        dist = 0

        if r1 is not r2:      # 同一 region なら呼出し可能

            # mikan namespace 対応
            f1 = r1.get_family_line()
            len1 = len(f1)
            f2 = r2.get_family_line()
            len2 = len(f2)

            # 不一致になるところ（兄弟）を探す
            i = 1  # i = 0 は :RootRegion なので必ず一致
            while i < len1 and i < len2:
                if f1[i] != f2[i]:
                    break
                i += 1

            sibling_level = i     # 兄弟となるレベル、もしくはどちらか一方が終わったレベル

            # p "sibling_level: #{i}"
            # p "from: #{f1[i].get_name}" if f1[i]
            # p "to: #{f2[i].get_name}" if f2[i]

            # 呼び側について呼び元のレベルから兄弟レベルまで（out_through をチェックおよび挿入）
            i = len1 - 1
            while i >= sibling_level:
                dbgPrint("going out from {} level={}\n".format(f1[i].get_name(), i))
                # print "DOMAIN: going out from #{f1[i].get_name} level=#{i}\n"
                domain_type = f1[i].get_domain_type()
                class_type = f1[i].get_class_type()
                dbgPrint("distance: region={} domain_type={} class_type={}".format(
                    f1[i].get_name(), domain_type, class_type))
                join_ok = False
                if domain_type:
                    if not domain_type.joinable(f1[i], f1[i - 1], Sym("OUT_THROUGH")):
                        return None
                    join_ok = True
                elif class_type:
                    if not class_type.joinable(f1[i], f1[i - 1], Sym("OUT_THROUGH")):
                        return None
                    join_ok = True
                if not join_ok:
                    out_through_list = f1[i].get_out_through_list()   # [ plugin_name, plugin_arg ]
                    if len(out_through_list) == 0:
                        return None
                i -= 1
                dist += 1

            # 兄弟レベルにおいて（to_through をチェックおよび挿入）
            # Ruby の Array#[] は範囲外で nil
            f1_sib = f1[sibling_level] if sibling_level < len(f1) else None
            f2_sib = f2[sibling_level] if sibling_level < len(f2) else None
            if f1_sib and f2_sib:
                dbgPrint("going from {} to {}\n".format(
                    f1_sib.get_name(), f2_sib.get_name()))
                # print "DOMAIN: going from #{f1[sibling_level].get_name} to #{f2[sibling_level].get_name}\n"
                domain_type = f1_sib.get_domain_type()
                class_type = f1_sib.get_class_type()
                join_ok = False
                if domain_type:
                    if not domain_type.joinable(f1[i], f1[i - 1], Sym("TO_THROUGH")):
                        return None
                    join_ok = True
                elif class_type:
                    if not class_type.joinable(f1[i], f1[i - 1], Sym("TO_THROUGH")):
                        return None
                    join_ok = True
                if not join_ok:
                    found = 0
                    for t in f1_sib.get_to_through_list():
                        if t[0][0] == f2_sib.get_name():   # region 名が一致するか ?
                            found = 1
                    for t in f2_sib.get_from_through_list():
                        if t[0][0] == f1_sib.get_name():   # region 名が一致するか ?
                            found = 1
                    if found == 0:
                        return None
                dist += 1

            # 受け側について兄弟レベルから受け側のレベルまで（in_through をチェックおよび挿入）
            i = sibling_level
            while i < len2:
                dbgPrint("going in to {} level={}\n".format(f2[i].get_name(), i))
                # print "DOMAIN: going in to #{f2[i].get_name} level=#{i}\n"
                domain_type = f2[i].get_domain_type()
                class_type = f2[i].get_class_type()
                join_ok = False
                if domain_type:
                    if not domain_type.joinable(f2[i - 1], f2[i], Sym("IN_THROUGH")):
                        return None
                    join_ok = True
                elif class_type:
                    if not class_type.joinable(f2[i - 1], f2[i], Sym("IN_THROUGH")):
                        return None
                    join_ok = True
                if not join_ok:
                    in_through_list = f2[i].get_in_through_list()   # [ plugin_name, plugin_arg ]
                    if len(in_through_list) == 0:
                        return None
                i += 1
                dist += 1

        dbgPrint("dsitance={} from {} to {}\n".format(dist, r1.get_name(), r2.get_name()))
        # print "dsitance=#{dist} from #{r1.get_name} to #{r2.get_name}\n"

        return dist

    # Regin# self は、region の子リージョンか？
    def is_sub_region_of(self, region):
        while region is not self:
            if region.is_root():
                return True
            region = region.get_owner()
        return False

    def is_node_root(self):
        return self in Region.node_roots

    def is_link_root(self):
        return self in Region.link_roots

    def is_class_root(self):
        return self.region_type == Sym("NODE")

    def is_domain_root(self):
        return self.region_type == Sym("NODE")

    def show_tree(self, indent):
        super().show_tree(indent)
        print("  " * (indent + 1), end="")
        print("path: {}".format(self.get_path_string()))
        print("  " * (indent + 1), end="")
        namespace = getattr(self, 'namespace', None)
        from tecslib.rubylib import rb
        owner_name = self.owner.get_name() if self.owner else "nil"
        print("namespace: {}  owner: {}.{}".format(
            namespace.get_name() if namespace else "nil",
            rb.class_name(self.owner),
            owner_name))
        if self.domain_type:
            self.domain_type.show_tree(indent + 1)
        print("  " * (indent + 1), end="")
        print("domain_root={} class_root={}".format(
            self.domain_root.get_name(), self.class_root.get_name()))
