#!/bin/env python
""" Unit tests for the ncdiff cisco-shared package. """

import os
import unittest
from ncdiff.composer import Tag
from ncdiff.model import ModelCompiler
from ncdiff.tailf import is_tailf_ordering, get_tailf_ordering
from ncdiff.tailf import is_symmetric_tailf_ordering


curr_dir = os.path.dirname(os.path.abspath(__file__))


def delete_xml_files(folder):
    for filename in os.listdir(folder):
        if filename.endswith(".xml"):
            file_path = os.path.join(folder, filename)
            os.remove(file_path)


class TestNative(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.compiler = ModelCompiler(os.path.join(curr_dir, 'yang'))
        delete_xml_files(cls.compiler.dir_yang)
        cls.native = cls.compiler.compile('Cisco-IOS-XE-native')
        # cls.oc_interfaces = cls.compiler.compile('openconfig-interfaces')

    def test_dependencies(self):
        self.assertIsNotNone(self.compiler.context)
        self.assertEqual(self.native.tree.tag, 'Cisco-IOS-XE-native')
        imports, includes, depends = \
            self.compiler._dependencies['Cisco-IOS-XE-native']
        self.assertIn('Cisco-IOS-XE-features', imports)
        self.assertIn('Cisco-IOS-XE-interfaces', includes)
        self.assertIn('Cisco-IOS-XE-sla', depends)
        self.assertIn('Cisco-IOS-XE-sla-ann', depends)

    def test_check_data_tree_xpath(self):
        # Line 52 in Cisco-IOS-XE-sla-ann.yang:
        # tailf:annotate-module Cisco-IOS-XE-sla {
        #   tailf:annotate-statement "grouping[name='config-ip-sla-grouping']" {
        #     tailf:annotate-statement "container[name='sla']" {
        #       tailf:annotate-statement "list[name='entry']" {
        #         tailf:annotate-statement "choice[name='sla-param'] " {
        #           tailf:annotate-statement "case[name='path-echo-case'] " {
        #             tailf:annotate-statement "container[name='path-echo']" {
        #               tailf:annotate-statement "leaf[name='source-ip']" {
        #                 tailf:cli-diff-create-after "/ios:native/ios:interface/ios:GigabitEthernet/ios-eth:carrier-delay/ios-eth:seconds" {
        #                   tailf:cli-when-target-set;
        #                 }
        #                 tailf:cli-diff-delete-before "/ios:native/ios:interface/ios:GigabitEthernet/ios-eth:carrier-delay/ios-eth:seconds" {
        #                   tailf:cli-when-target-delete;
        #                 }
        #               }
        #             }
        #           }
        #         }
        #       }
        #     }
        #   }
        # }
        stmt = self.compiler.context.get_module('Cisco-IOS-XE-sla')
        for arg in [
            "config-ip-sla-grouping",
            "sla",
            "entry",
            "sla-param",
            "path-echo-case",
            "path-echo",
            "source-ip",
        ]:
            stmts = [i for i in stmt.substmts if i.arg == arg]
            self.assertEqual(len(stmts), 1)
            stmt = stmts[0]
        stmts = [i for i in stmt.substmts
                 if i.keyword == ("tailf-common", "cli-diff-create-after")]
        self.assertEqual(len(stmts), 1)
        xpath_stmt = stmts[0]

        target = self.compiler.context.check_data_tree_xpath(xpath_stmt, stmt)

        module_stmt = self.compiler.context.get_module('Cisco-IOS-XE-native')
        stmts = [i for i in module_stmt.substmts if i.arg == "native"]
        self.assertEqual(len(stmts), 1)
        stmt = stmts[0]
        for arg in [
            "interface",
            "GigabitEthernet",
            "carrier-delay",
            "delay-choice",
            "seconds",
            "seconds",
        ]:
            stmts = [i for i in stmt.i_children if i.arg == arg]
            self.assertEqual(len(stmts), 1)
            stmt = stmts[0]

        self.assertIs(target, stmt)

    def test_check_schema_tree_xpath(self):
        # Line 75 in Cisco-IOS-XE-sla-ann.yang:
        # tailf:annotate "/ios:native/ios:ip/ios-sla:sla/ios-sla:entry/ios-sla:sla-param/ios-sla:path-echo-case/ios-sla:path-echo/ios-sla:dst-ip" {
        #   tailf:cli-diff-create-after "/ios:native/ios:interface/ios:GigabitEthernet/ios-eth:carrier-delay/ios-eth:seconds" {
        #     tailf:cli-when-target-delete;
        #   }
        #   tailf:cli-diff-delete-before "/ios:native/ios:interface/ios:GigabitEthernet/ios-eth:carrier-delay/ios-eth:seconds" {
        #     tailf:cli-when-target-create;
        #   }
        # }
        stmt = self.compiler.context.get_module('Cisco-IOS-XE-sla-ann')
        stmts = [i for i in stmt.substmts
                 if i.keyword == ("tailf-common", "annotate")]
        self.assertEqual(len(stmts), 1)
        annotating_stmt = stmts[0]

        target = self.compiler.context.check_schema_tree_xpath(annotating_stmt)

        module_stmt = self.compiler.context.get_module('Cisco-IOS-XE-native')
        stmts = [i for i in module_stmt.substmts if i.arg == "native"]
        self.assertEqual(len(stmts), 1)
        stmt = stmts[0]
        for arg in [
            "ip",
            "sla",
            "entry",
            "sla-param",
            "path-echo-case",
            "path-echo",
            "dst-ip",
        ]:
            stmts = [i for i in stmt.i_children if i.arg == arg]
            self.assertEqual(len(stmts), 1)
            stmt = stmts[0]

        self.assertIs(target, stmt)

    def test_get_xpath_from_schema_node(self):
        xpath = "/ios:native/ios:ip/ios-sla:sla/ios-sla:entry" \
            "/ios-sla:sla-param/ios-sla:path-echo-case/ios-sla:path-echo" \
            "/ios-sla:dst-ip"
        self.assertIsNotNone(self.native.tree)
        matches = self.native.tree.xpath(
            "/Cisco-IOS-XE-native" + xpath,
            namespaces=self.native.prefixes,
        )
        self.assertEqual(len(matches), 1)
        schema_node = matches[0]
        result_xpath = self.compiler.context.get_xpath_from_schema_node(
            schema_node, type=Tag.LXML_XPATH)
        self.assertEqual(result_xpath, xpath)

    def test_process_annotation_module_1(self):
        # Line 52 in Cisco-IOS-XE-sla-ann.yang:
        # tailf:annotate-module Cisco-IOS-XE-sla {
        #   tailf:annotate-statement "grouping[name='config-ip-sla-grouping']" {
        #     tailf:annotate-statement "container[name='sla']" {
        #       tailf:annotate-statement "list[name='entry']" {
        #         tailf:annotate-statement "choice[name='sla-param'] " {
        #           tailf:annotate-statement "case[name='path-echo-case'] " {
        #             tailf:annotate-statement "container[name='path-echo']" {
        #               tailf:annotate-statement "leaf[name='source-ip']" {
        #                 tailf:cli-diff-create-after "/ios:native/ios:interface/ios:GigabitEthernet/ios-eth:carrier-delay/ios-eth:seconds" {
        #                   tailf:cli-when-target-set;
        #                 }
        #                 tailf:cli-diff-delete-before "/ios:native/ios:interface/ios:GigabitEthernet/ios-eth:carrier-delay/ios-eth:seconds" {
        #                   tailf:cli-when-target-delete;
        #                 }
        #               }
        #             }
        #           }
        #         }
        #       }
        #     }
        #   }
        # }
        module_stmt = self.compiler.context.get_module('Cisco-IOS-XE-native')
        stmts = [i for i in module_stmt.substmts if i.arg == "native"]
        self.assertEqual(len(stmts), 1)
        stmt = stmts[0]
        for arg in [
            "ip",
            "sla",
            "entry",
            "sla-param",
            "path-echo-case",
            "path-echo",
            "source-ip",
        ]:
            stmts = [i for i in stmt.i_children if i.arg == arg]
            self.assertEqual(len(stmts), 1)
            stmt = stmts[0]

        stmts = [i for i in stmt.substmts
                 if i.keyword == ("tailf-common", "cli-diff-create-after") and
                 i.arg == "/ios:native/ios:interface/ios:GigabitEthernet"
                 "/ios-eth:carrier-delay/ios-eth:seconds"]
        self.assertEqual(len(stmts), 1)
        annotation = stmts[0]
        self.assertEqual(len(annotation.substmts), 1)
        annotation_substmt = annotation.substmts[0]
        self.assertEqual(
            annotation_substmt.keyword,
            ("tailf-common", "cli-when-target-set"),
        )

        stmts = [i for i in stmt.substmts
                 if i.keyword == ("tailf-common", "cli-diff-delete-before") and
                 i.arg == "/ios:native/ios:interface/ios:GigabitEthernet"
                 "/ios-eth:carrier-delay/ios-eth:seconds"]
        self.assertEqual(len(stmts), 1)
        annotation = stmts[0]
        self.assertEqual(len(annotation.substmts), 1)
        annotation_substmt = annotation.substmts[0]
        self.assertEqual(
            annotation_substmt.keyword,
            ("tailf-common", "cli-when-target-delete"),
        )

    def test_process_annotation_module_2(self):
        # Line 75 in Cisco-IOS-XE-sla-ann.yang:
        # tailf:annotate "/ios:native/ios:ip/ios-sla:sla/ios-sla:entry/ios-sla:sla-param/ios-sla:path-echo-case/ios-sla:path-echo/ios-sla:dst-ip" {
        #   tailf:cli-diff-create-after "/ios:native/ios:interface/ios:GigabitEthernet/ios-eth:carrier-delay/ios-eth:seconds" {
        #     tailf:cli-when-target-delete;
        #   }
        #   tailf:cli-diff-delete-before "/ios:native/ios:interface/ios:GigabitEthernet/ios-eth:carrier-delay/ios-eth:seconds" {
        #     tailf:cli-when-target-create;
        #   }
        # }
        module_stmt = self.compiler.context.get_module('Cisco-IOS-XE-native')
        stmts = [i for i in module_stmt.substmts if i.arg == "native"]
        self.assertEqual(len(stmts), 1)
        stmt = stmts[0]
        for arg in [
            "ip",
            "sla",
            "entry",
            "sla-param",
            "path-echo-case",
            "path-echo",
            "dst-ip",
        ]:
            stmts = [i for i in stmt.i_children if i.arg == arg]
            self.assertEqual(len(stmts), 1)
            stmt = stmts[0]

        stmts = [i for i in stmt.substmts
                 if i.keyword == ("tailf-common", "cli-diff-create-after") and
                 i.arg == "/ios:native/ios:interface/ios:GigabitEthernet"
                 "/ios-eth:carrier-delay/ios-eth:seconds"]
        self.assertEqual(len(stmts), 1)
        annotation = stmts[0]
        self.assertEqual(len(annotation.substmts), 1)
        annotation_substmt = annotation.substmts[0]
        self.assertEqual(
            annotation_substmt.keyword,
            ("tailf-common", "cli-when-target-delete"),
        )

        stmts = [i for i in stmt.substmts
                 if i.keyword == ("tailf-common", "cli-diff-delete-before") and
                 i.arg == "/ios:native/ios:interface/ios:GigabitEthernet"
                 "/ios-eth:carrier-delay/ios-eth:seconds"]
        self.assertEqual(len(stmts), 1)
        annotation = stmts[0]
        self.assertEqual(len(annotation.substmts), 1)
        annotation_substmt = annotation.substmts[0]
        self.assertEqual(
            annotation_substmt.keyword,
            ("tailf-common", "cli-when-target-create"),
        )

    def test_ordering_stmt_leafref(self):
        self.assertIn(
            'Cisco-IOS-XE-native',
            self.compiler.ordering_stmt_leafref,
        )

        # Line 159 in Cisco-IOS-XE-parser.yang:
        # leaf view-name {
        #   type leafref {
        #     path "../../../view-name-list/name";
        #   }
        # }
        module_stmt = self.compiler.context.get_module('Cisco-IOS-XE-native')
        stmts = [i for i in module_stmt.substmts if i.arg == "native"]
        self.assertEqual(len(stmts), 1)
        stmt = stmts[0]
        for arg in [
            "parser",
            "view",
            "view-name-superview-list",
            "view",
            "view-name",
        ]:
            stmts = [i for i in stmt.i_children if i.arg == arg]
            self.assertEqual(len(stmts), 1)
            stmt = stmts[0]
        leafref = stmt
        self.assertIn(
            leafref,
            self.compiler.ordering_stmt_leafref['Cisco-IOS-XE-native'],
        )
        leafref_stmt, target_stmt, ordering = \
            self.compiler.ordering_stmt_leafref['Cisco-IOS-XE-native'][leafref]

        type_stmt = leafref.search_one('type')
        self.assertIsNotNone(type_stmt)
        path_stmt = type_stmt.search_one('path')
        self.assertIsNotNone(path_stmt)
        target = self.compiler.context.check_data_tree_xpath(
            path_stmt, leafref)

        self.assertIs(leafref, leafref_stmt)
        self.assertIs(target, target_stmt)

    def test_ordering_stmt_tailf(self):
        self.assertIn('Cisco-IOS-XE-native', self.compiler.ordering_stmt_tailf)

        # Line 75 in Cisco-IOS-XE-sla-ann.yang:
        # tailf:annotate "/ios:native/ios:ip/ios-sla:sla/ios-sla:entry/ios-sla:sla-param/ios-sla:path-echo-case/ios-sla:path-echo/ios-sla:dst-ip" {
        #   tailf:cli-diff-create-after "/ios:native/ios:interface/ios:GigabitEthernet/ios-eth:carrier-delay/ios-eth:seconds" {
        #     tailf:cli-when-target-delete;
        #   }
        #   tailf:cli-diff-delete-before "/ios:native/ios:interface/ios:GigabitEthernet/ios-eth:carrier-delay/ios-eth:seconds" {
        #     tailf:cli-when-target-create;
        #   }
        # }
        module_stmt = self.compiler.context.get_module('Cisco-IOS-XE-native')
        stmts = [i for i in module_stmt.substmts if i.arg == "native"]
        self.assertEqual(len(stmts), 1)
        stmt = stmts[0]
        for arg in [
            "ip",
            "sla",
            "entry",
            "sla-param",
            "path-echo-case",
            "path-echo",
            "dst-ip",
        ]:
            stmts = [i for i in stmt.i_children if i.arg == arg]
            self.assertEqual(len(stmts), 1)
            stmt = stmts[0]
        node = stmt

        # tailf:cli-diff-create-after
        stmts = [i for i in node.substmts
                 if i.keyword == ("tailf-common", "cli-diff-create-after") and
                 i.arg == "/ios:native/ios:interface/ios:GigabitEthernet"
                 "/ios-eth:carrier-delay/ios-eth:seconds"]
        self.assertEqual(len(stmts), 1)
        annotation = stmts[0]
        self.assertEqual(len(annotation.substmts), 1)
        annotation_substmt = annotation.substmts[0]
        self.assertEqual(
            annotation_substmt.keyword,
            ("tailf-common", "cli-when-target-delete"),
        )
        self.assertIn(
            annotation,
            self.compiler.ordering_stmt_tailf['Cisco-IOS-XE-native'],
        )
        node_stmt, target_stmt, ordering = \
            self.compiler.ordering_stmt_tailf['Cisco-IOS-XE-native'][annotation]

        target = self.compiler.context.check_data_tree_xpath(
            annotation, node)

        self.assertIs(node_stmt, node)
        self.assertIs(target, target_stmt)

        # tailf:cli-diff-delete-before
        stmts = [i for i in node.substmts
                 if i.keyword == ("tailf-common", "cli-diff-delete-before") and
                 i.arg == "/ios:native/ios:interface/ios:GigabitEthernet"
                 "/ios-eth:carrier-delay/ios-eth:seconds"]
        self.assertEqual(len(stmts), 1)
        annotation = stmts[0]
        self.assertEqual(len(annotation.substmts), 1)
        annotation_substmt = annotation.substmts[0]
        self.assertEqual(
            annotation_substmt.keyword,
            ("tailf-common", "cli-when-target-create"),
        )
        self.assertIn(
            annotation,
            self.compiler.ordering_stmt_tailf['Cisco-IOS-XE-native'],
        )
        node_stmt, target_stmt, ordering = \
            self.compiler.ordering_stmt_tailf['Cisco-IOS-XE-native'][annotation]

        target = self.compiler.context.check_data_tree_xpath(
            annotation, node)

        self.assertIs(node_stmt, node)
        self.assertIs(target, target_stmt)

    def test_datatype_leafref(self):
        # Line 159 in Cisco-IOS-XE-parser.yang:
        # leaf view-name {
        #   type leafref {
        #     path "../../../view-name-list/name";
        #   }
        # }
        xpath = "/ios:native/ios:parser/ios:view" \
                "/ios:view-name-superview-list/ios:view/ios:view-name"
        matches = self.native.tree.xpath(
            "/Cisco-IOS-XE-native" + xpath,
            namespaces=self.native.prefixes,
        )
        self.assertEqual(len(matches), 1)
        schema_node = matches[0]
        datatype = schema_node.get("datatype", None)
        self.assertEqual(datatype, "leafref ../../../view-name-list/name")

    def test_has_tailf_ordering(self):
        # Line 75 in Cisco-IOS-XE-sla-ann.yang:
        # tailf:annotate "/ios:native/ios:ip/ios-sla:sla/ios-sla:entry/ios-sla:sla-param/ios-sla:path-echo-case/ios-sla:path-echo/ios-sla:dst-ip" {
        #   tailf:cli-diff-create-after "/ios:native/ios:interface/ios:GigabitEthernet/ios-eth:carrier-delay/ios-eth:seconds" {
        #     tailf:cli-when-target-delete;
        #   }
        #   tailf:cli-diff-delete-before "/ios:native/ios:interface/ios:GigabitEthernet/ios-eth:carrier-delay/ios-eth:seconds" {
        #     tailf:cli-when-target-create;
        #   }
        # }
        module_stmt = self.compiler.context.get_module('Cisco-IOS-XE-native')
        stmts = [i for i in module_stmt.substmts if i.arg == "native"]
        self.assertEqual(len(stmts), 1)
        stmt = stmts[0]
        for arg in [
            "ip",
            "sla",
            "entry",
            "sla-param",
            "path-echo-case",
            "path-echo",
            "dst-ip",
        ]:
            stmts = [i for i in stmt.i_children if i.arg == arg]
            self.assertEqual(len(stmts), 1)
            stmt = stmts[0]
        node = stmt
        func_result = is_tailf_ordering(node, self.compiler.context)
        self.assertFalse(func_result)

        stmts = [i for i in node.substmts
                 if i.keyword == ("tailf-common", "cli-diff-create-after") and
                 i.arg == "/ios:native/ios:interface/ios:GigabitEthernet"
                 "/ios-eth:carrier-delay/ios-eth:seconds"]
        self.assertEqual(len(stmts), 1)
        annotation = stmts[0]
        func_result = is_tailf_ordering(annotation, self.compiler.context)
        self.assertTrue(func_result)

    def test_get_tailf_ordering(self):
        # Line 75 in Cisco-IOS-XE-sla-ann.yang:
        # tailf:annotate "/ios:native/ios:ip/ios-sla:sla/ios-sla:entry/ios-sla:sla-param/ios-sla:path-echo-case/ios-sla:path-echo/ios-sla:dst-ip" {
        #   tailf:cli-diff-create-after "/ios:native/ios:interface/ios:GigabitEthernet/ios-eth:carrier-delay/ios-eth:seconds" {
        #     tailf:cli-when-target-delete;
        #   }
        #   tailf:cli-diff-delete-before "/ios:native/ios:interface/ios:GigabitEthernet/ios-eth:carrier-delay/ios-eth:seconds" {
        #     tailf:cli-when-target-create;
        #   }
        # }
        module_stmt = self.compiler.context.get_module('Cisco-IOS-XE-native')
        stmts = [i for i in module_stmt.substmts if i.arg == "native"]
        self.assertEqual(len(stmts), 1)
        stmt = stmts[0]
        for arg in [
            "ip",
            "sla",
            "entry",
            "sla-param",
            "path-echo-case",
            "path-echo",
            "dst-ip",
        ]:
            stmts = [i for i in stmt.i_children if i.arg == arg]
            self.assertEqual(len(stmts), 1)
            stmt = stmts[0]
        node = stmt

        stmts = [i for i in node.substmts
                 if i.keyword == ("tailf-common", "cli-diff-create-after") and
                 i.arg == "/ios:native/ios:interface/ios:GigabitEthernet"
                 "/ios-eth:carrier-delay/ios-eth:seconds"]
        self.assertEqual(len(stmts), 1)
        annotation = stmts[0]
        target = self.compiler.context.check_data_tree_xpath(
            annotation, node)
        ordering = get_tailf_ordering(self.compiler.context, annotation, target)
        self.assertEqual(ordering, [('create', 'after', 'delete')])

        stmts = [i for i in node.substmts
                 if i.keyword == ("tailf-common", "cli-diff-delete-before") and
                 i.arg == "/ios:native/ios:interface/ios:GigabitEthernet"
                 "/ios-eth:carrier-delay/ios-eth:seconds"]
        self.assertEqual(len(stmts), 1)
        annotation = stmts[0]
        target = self.compiler.context.check_data_tree_xpath(
            annotation, node)
        ordering = get_tailf_ordering(self.compiler.context, annotation, target)
        self.assertEqual(ordering, [('delete', 'before', 'create')])

    def test_is_symmetric_tailf_ordering(self):
        # Line 75 in Cisco-IOS-XE-sla-ann.yang:
        # tailf:annotate "/ios:native/ios:ip/ios-sla:sla/ios-sla:entry/ios-sla:sla-param/ios-sla:path-echo-case/ios-sla:path-echo/ios-sla:dst-ip" {
        #   tailf:cli-diff-create-after "/ios:native/ios:interface/ios:GigabitEthernet/ios-eth:carrier-delay/ios-eth:seconds" {
        #     tailf:cli-when-target-delete;
        #   }
        #   tailf:cli-diff-delete-before "/ios:native/ios:interface/ios:GigabitEthernet/ios-eth:carrier-delay/ios-eth:seconds" {
        #     tailf:cli-when-target-create;
        #   }
        # }
        module_stmt = self.compiler.context.get_module('Cisco-IOS-XE-native')
        stmts = [i for i in module_stmt.substmts if i.arg == "native"]
        self.assertEqual(len(stmts), 1)
        stmt = stmts[0]
        for arg in [
            "ip",
            "sla",
            "entry",
            "sla-param",
            "path-echo-case",
            "path-echo",
            "dst-ip",
        ]:
            stmts = [i for i in stmt.i_children if i.arg == arg]
            self.assertEqual(len(stmts), 1)
            stmt = stmts[0]
        node = stmt

        stmts = [i for i in node.substmts
                 if i.keyword == ("tailf-common", "cli-diff-create-after") and
                 i.arg == "/ios:native/ios:interface/ios:GigabitEthernet"
                 "/ios-eth:carrier-delay/ios-eth:seconds"]
        self.assertEqual(len(stmts), 1)
        annotation = stmts[0]
        target = self.compiler.context.check_data_tree_xpath(
            annotation, node)
        func_result = is_symmetric_tailf_ordering(self.compiler.context, annotation, target)
        self.assertFalse(func_result)


class TestOpenConfigInterfaces(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.compiler = ModelCompiler(os.path.join(curr_dir, 'yang'))
        delete_xml_files(cls.compiler.dir_yang)
        cls.oc_interfaces = cls.compiler.compile('openconfig-interfaces')

    def test_datatype_identityref(self):
        # Line 254 in Cisco-IOS-XE-interfaces.yang:
        # leaf type {
        #   type identityref {
        #     base ietf-if:interface-type;
        #   }
        #   mandatory true;
        #   description
        #     "[adapted from IETF interfaces model (RFC 7223)]

        #     The type of the interface.

        #     When an interface entry is created, a server MAY
        #     initialize the type leaf with a valid value, e.g., if it
        #     is possible to derive the type from the name of the
        #     interface.

        #     If a client tries to set the type of an interface to a
        #     value that can never be used by the system, e.g., if the
        #     type is not supported or if the type does not match the
        #     name of the interface, the server MUST reject the request.
        #     A NETCONF server MUST reply with an rpc-error with the
        #     error-tag 'invalid-value' in this case.";
        #   reference
        #     "RFC 2863: The Interfaces Group MIB - ifType";
        # }
        xpath = "/oc-if:interfaces/oc-if:interface/oc-if:config/oc-if:type"
        matches = self.oc_interfaces.tree.xpath(
            "/openconfig-interfaces" + xpath,
            namespaces=self.oc_interfaces.prefixes,
        )
        self.assertEqual(len(matches), 1)
        schema_node = matches[0]
        datatype = schema_node.get("datatype", None)
        self.assertEqual(datatype, "identityref ietf-if:interface-type")
