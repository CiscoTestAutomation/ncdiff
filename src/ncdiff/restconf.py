import re
import json
import logging
import requests
from lxml import etree
from copy import deepcopy
from xmljson import Parker
from ncclient import xml_
from xml.etree import ElementTree
from collections import OrderedDict, defaultdict
from urllib.parse import quote, unquote

from .composer import Tag, Composer
from .calculator import BaseCalculator

# create a logger for this module
logger = logging.getLogger(__name__)

nc_url = xml_.BASE_NS_1_0
config_tag = '{' + nc_url + '}config'
header_json = {'Content-type': 'application/yang-data+json',
               'Accept': 'application/yang-data+json, application/yang-data.errors+json'}


def _tostring(value):
    '''_tostring

    Convert value to XML compatible string.
    '''

    if value is True:
        return 'true'
    elif value is False:
        return 'false'
    elif value is None:
        return None
    else:
        return str(value)

def _fromstring(value):
    '''_fromstring

    Convert XML string value to None, boolean, int or float.
    '''

    if not value:
        return [None]
    std_value = value.strip().lower()
    if std_value == 'true':
        return True
    elif std_value == 'false':
        return False
    try:
        return int(std_value)
    except ValueError:
        pass
    try:
        return float(std_value)
    except ValueError:
        pass
    return value


class RestconfParser(object):
    '''RestconfParser

    A parser to convert a Restconf GET reply to an lxml Element object.

    Attributes
    ----------
    ele : `Element`
        An lxml Element object which is the root of the config tree.

    config_node : `Element`
        An Element node in the config tree, which is corresponding to the URL in
        the Restconf GET reply.

    xpath : `str`
        An xpath of attribute 'config_node', which is corresponding to the URL
        in the Restconf GET reply.
    '''

    def __init__(self, device, restconf_get_reply):
        self.device = device
        self.reply = restconf_get_reply
        self._config_node = None
        self._config_node_parent = None
        self._ele = None
        self._convert_tag = defaultdict(dict)

        self._name_to_prefix = {i[0]: i[1] for i in self.device.namespaces
                                if i[1] is not None}
        self._name_to_url = {i[0]: i[2] for i in self.device.namespaces
                             if i[1] is not None}

    @property
    def ele(self):
        if self._ele is None:
            pk = Parker(xml_tostring=_tostring, element=ElementTree.Element)
            for ele in pk.etree(self._json_data):
                self.parse_json(self.config_node_parent, ele)
            self._ele = self.root(self.config_node_parent)
        return self._ele

    @property
    def config_node(self):
        if self._config_node is None:
            self._config_node_parent, self._config_node = self.get_config_node()
        return self._config_node

    @property
    def xpath(self):
        if self.parse_url_piece(self._url_pieces[-1])[1]:
            return self.device.get_xpath(self.config_node,
                                         type=Tag.LXML_XPATH, instance=True)
        else:
            return self.device.get_xpath(self.config_node,
                                         type=Tag.LXML_XPATH, instance=False)

    @property
    def _url_pieces(self):
        regexp_str = '^https?://.+/data/(.*)'
        m = re.search(regexp_str, self.reply.url)
        if m:
            return m.group(1).split('/')
        else:
            raise ValueError("invalid url '{}'".format(url))

    @property
    def _json_data(self):
        return json.loads(self.reply.text, object_pairs_hook=OrderedDict)

    @property
    def config_node_parent(self):
        if self._config_node_parent is None:
            self._config_node_parent, self._config_node = self.get_config_node()
        return self._config_node_parent

    @staticmethod
    def get_ns(tag):
        m = re.search('{(.*)}.*', tag)
        return m.group(1)

    @staticmethod
    def parse_url_piece(url_piece):
        regexp_str = '(.*)=(.*)'
        m = re.search(regexp_str, url_piece)
        if m:
            return unquote(m.group(1)), \
                   [unquote(v) for v in m.group(2).split(',')]
        else:
            return unquote(url_piece), ''

    @staticmethod
    def root(node):
        ancestors = list(node.iterancestors())
        if ancestors:
            return ancestors[-1]
        else:
            return node

    @staticmethod
    def copy(node):
        def find_node(node1, node2):
            if node1 == node:
                return node2
            for child1, child2 in zip(node1.getchildren(), node2.getchildren()):
                if child1 == node:
                    return child2
                elif child1.getchildren():
                    ret = find_node(child1, child2)
                    if ret is not None:
                        return ret
            return None

        node1_root = RestconfParser.root(node)
        node2_root = deepcopy(node1_root)
        return find_node(node1_root, node2_root)

    def convert_tag(self, default_ns, tag, src=Tag.LXML_ETREE, dst=Tag.YTOOL):
        if src == Tag.JSON_NAME and dst == Tag.LXML_ETREE:
            if default_ns not in self._convert_tag or \
               tag not in self._convert_tag[default_ns]:
                self._convert_tag[default_ns][tag] = \
                    self.device.convert_tag(default_ns, tag, src=src, dst=dst)
            return self._convert_tag[default_ns][tag]
        else:
            return self.device.convert_tag(default_ns, tag, src=src, dst=dst)

    def get_name(self, text):
        if text is None:
            return '', None
        m = re.search('^(.*):(.*)$', text)
        if m:
            if m.group(1) in self.device.models_loadable:
                return m.group(1), m.group(2)
            else:
                return '', text
        else:
            return '', text

    def subelement(self, parent, tag, text):
        default_url = self.get_ns(tag)
        nsmap = {None: default_url}
        model_name, text_value = self.get_name(text)
        if model_name:
            model_url = self._name_to_url[model_name]
            if model_url == default_url:
                e = etree.SubElement(parent, tag, nsmap=nsmap)
                e.text = text_value
            else:
                nsmap.update({self._name_to_prefix[model_name]: model_url})
                e = etree.SubElement(parent, tag, nsmap=nsmap)
                e.text = '{}:{}'.format(self._name_to_prefix[model_name],
                                        text_value)
        else:
            e = etree.SubElement(parent, tag, nsmap=nsmap)
            e.text = text_value
        return e

    def parse_json(self, lxml_parent, xml_child, default_ns=''):
        default_ns, tag = self.convert_tag(default_ns, xml_child.tag,
                                           src=Tag.JSON_NAME,
                                           dst=Tag.LXML_ETREE)
        lxml_child = self.subelement(lxml_parent, tag, xml_child.text)
        for child in xml_child:
            self.parse_json(lxml_child, child, default_ns)

    def get_config_node(self):
        '''get_config_node

        High-level api: get_config_node returns an Element node in the config
        tree, which is corresponding to the URL in the Restconf GET reply.

        Returns
        -------

        Element
            A config node.
        '''

        default_ns = ''
        config_node = etree.Element(config_tag, nsmap={'nc': nc_url})
        for index, url_piece in enumerate(self._url_pieces):
            if index == len(self._url_pieces)-1:
                config_node_parent = self.copy(config_node)
            node_name, values = self.parse_url_piece(url_piece)
            default_ns, tag = self.convert_tag(default_ns, node_name,
                                               src=Tag.JSON_NAME,
                                               dst=Tag.LXML_ETREE)
            config_node = self.subelement(config_node, tag, None)
            schema_node = self.device.get_schema_node(config_node)
            if schema_node.get('type') == 'leaf-list' and len(values) > 0:
                model_name, text_value = self.get_name(values[0])
                if model_name:
                    prefix = self._name_to_prefix[model_name]
                    config_node.text = '{}:{}'.format(prefix, text_value)
                else:
                    config_node.text = text_value
            elif schema_node.get('type') == 'list' and len(values) > 0:
                key_tags = BaseCalculator._get_list_keys(schema_node)
                for key_tag, value in zip(key_tags, values):
                    key = self.subelement(config_node, key_tag, value)
        return config_node_parent, config_node


class RestconfComposer(Composer):
    '''RestconfComposer

    A composer to convert an lxml Element object to Restconf JSON format.
    '''

    def get_json(self, instance=True):
        '''get_json

        High-level api: get_json returns json_val of the config node.

        Parameters
        ----------

        instance : `bool`
            True if only one instance of list or leaf-list is required. False if
            all instances of list or leaf-list are needed.

        Returns
        -------

        str
            A string in JSON format.
        '''

        def get_json_instance(node):
            pk = Parker(xml_fromstring=_fromstring, dict_type=OrderedDict)
            default_ns = {}
            nodes = [node] + node.findall('.//')
            for item in nodes:
                parents = [p for p in node.findall('.//{}/..'.format(item.tag))
                          if item in p.findall('*')]
                if parents and id(parents[0]) in default_ns:
                    default_url = default_ns[id(parents[0])]
                    ns, tag = self.device.convert_tag(default_url, item.tag,
                                                      dst=Tag.JSON_NAME)
                else:
                    ns, tag = self.device.convert_tag('', item.tag,
                                                      dst=Tag.JSON_NAME)
                default_ns[id(item)] = ns
                item.tag = tag
            return pk.data(node, preserve_root=True)

        def convert_node(node):
            # lxml.etree does not allow tag name like oc-if:enable
            # so it is converted to xml.etree.ElementTree
            string = etree.tostring(node, encoding='unicode',
                                    pretty_print=False)
            return ElementTree.fromstring(string)

        if instance:
            return json.dumps(get_json_instance(convert_node(self.node)))
        else:
            nodes = [n for n in self.node.getparent() \
                                         .iterchildren(tag=self.node.tag)]
            if len(nodes) > 1:
                return json.dumps([get_json_instance(convert_node(n))
                                   for n in nodes])
            else:
                return json.dumps(get_json_instance(convert_node(nodes[0])))

    def get_url(self, instance=True):
        '''get_url

        High-level api: get_url returns a Restconf URL of the config node.

        Parameters
        ----------

        instance : `bool`
            True if the Restconf URL refers to only one instance of a list or
            leaf-list. False if the Restconf URL refers to all instances of a
            list or leaf-list.

        Returns
        -------

        str
            A Restconf URL.
        '''

        def convert(default_ns, nodes):
            ret = ''
            for node in nodes:
                default_ns, id = self.device.convert_tag(default_ns, node.tag,
                                                         dst=Tag.JSON_NAME)
                ret += '/' + quote(id)
                if self.is_config:
                    n = Composer(self.device, node)
                    if n.schema_node.get('type') == 'leaf-list':
                        if node != self.node or instance:
                            ret += '={}'.format(quote(node.text))
                    elif n.schema_node.get('type') == 'list':
                        if node != self.node or instance:
                            values = []
                            for key in n.keys:
                                values.append(quote(node.find(key).text))
                            ret += '={}'.format(','.join(values))
            return ret

        nodes = list(reversed(list(self.node.iterancestors())))[1:] + \
                [self.node]
        return '/restconf/data' + convert('', nodes)


class RestconfCalculator(BaseCalculator):
    '''RestconfCalculator

    A Restconf calculator to do subtraction and addition. A subtraction is to
    compute the delta between two Config instances in a form of Restconf
    Requests. An addition is to apply one Restconf Request to a Config instance
    (TBD).

    Attributes
    ----------
    sub : `list`
        A list of Restconf Requests which can achieve a transition from one
        config, i.e., self.etree2, to another config, i.e., self.etree1.
    '''

    def __init__(self, device, etree1, etree2, request=None):
        '''
        __init__ instantiates a RestconfCalculator instance.
        '''

        self.device = device
        self.etree1 = etree1
        self.etree2 = etree2
        self.request = request
        self.port = '443'

    @property
    def ip(self):
        return self.device.connection_info['ip']

    @property
    def sub(self):
        deletes, puts, patches = self.node_sub(self.etree1, self.etree2)
        return deletes + puts + patches

    def node_sub(self, node_self, node_other):
        '''node_sub

        High-level api: Compute the delta of two config nodes. This method is
        recursive. Assume two config nodes are different.

        Parameters
        ----------

        node_self : `Element`
            A config node in the destination config that is being processed.
            node_self cannot be a leaf node.

        node_other : `Element`
            A config node in the source config that is being processed.

        Returns
        -------

        tuple
            There are three elements in the tuple: a list of Restconf DELETE
            Requests, a list of Restconf PUT Requests, and a list of Restconf
            PATCH Requests.
        '''

        deletes = []
        puts = []
        patches = []

        # if a leaf-list node, delete the leaf-list totally
        # if a list node, by default delete the list instance
        # if a list node and delete_whole=True, delete the list totally
        def generate_delete(node, instance=True):
            composer = RestconfComposer(self.device, node)
            url = 'https://{}:{}'.format(self.ip, self.port)
            url += composer.get_url(instance=instance)
            deletes.append(requests.Request('DELETE', url, headers=header_json))

        # if a leaf-list node, replace the leaf-list totally
        # if a list node, replace the list totally
        def generate_put(node, instance=True):
            composer = RestconfComposer(self.device, node)
            url = 'https://{}:{}'.format(self.ip, self.port)
            url += composer.get_url(instance=instance)
            data_json = composer.get_json(instance=instance)
            puts.append(requests.Request('PUT', url, headers=header_json,
                                         data=data_json))

        # if a leaf-list node, update the leaf-list totally
        # if a list node, by default update the list instance
        # if a list node and update_whole=True, update the list totally
        def generate_patch(node, instance=True):
            composer = RestconfComposer(self.device, node)
            url = 'https://{}:{}'.format(self.ip, self.port)
            url += composer.get_url(instance=instance)
            data_json = composer.get_json(instance=instance)
            patches.append(requests.Request('PATCH', url, headers=header_json,
                                            data=data_json))

        # the sequence of list instances under node_self is different from the
        # one under node_other
        def list_seq_is_different(tag):
            s_list = [i for i in node_self.iterchildren(tag=tag)]
            o_list = [i for i in node_other.iterchildren(tag=tag)]
            if [self.device.get_xpath(n) for n in s_list] == \
               [self.device.get_xpath(n) for n in o_list]:
                return False
            else:
                return True

        # all list instances under node_self have peers under node_other, and
        # the sequence of list instances under node_self that have peers under
        # node_other is same as the sequence of list instances under node_other
        def list_seq_is_inclusive(tag):
            s_list = [i for i in node_self.iterchildren(tag=tag)]
            o_list = [i for i in node_other.iterchildren(tag=tag)]
            s_seq = [self.device.get_xpath(n) for n in s_list]
            o_seq = [self.device.get_xpath(n) for n in o_list]
            if set(s_seq) <= set(o_seq) and \
               [i for i in s_seq if i in o_seq] == o_seq:
                return True
            else:
                return False

        in_s_not_in_o, in_o_not_in_s, in_s_and_in_o = \
            self._group_kids(node_self, node_other)
        for child_s in in_s_not_in_o:
            schema_node = self.device.get_schema_node(child_s)
            if schema_node.get('type') == 'leaf' or \
               schema_node.get('type') == 'container':
                generate_patch(child_s)
            elif schema_node.get('type') == 'leaf-list' or \
                 schema_node.get('type') == 'list':
                if schema_node.get('ordered-by') == 'user':
                    return ([], [generate_put(node_self, instance=True)], [])
                else:
                    generate_put(child_s, instance=True)
        for child_o in in_o_not_in_s:
            schema_node = self.device.get_schema_node(child_o)
            if schema_node.get('type') == 'leaf' or \
               schema_node.get('type') == 'container':
                generate_delete(child_o)
            elif schema_node.get('type') == 'leaf-list' or \
                 schema_node.get('type') == 'list':
                if schema_node.get('ordered-by') == 'user':
                    if list_seq_is_inclusive(child_o.tag):
                        generate_delete(child_o, instance=True)
                    else:
                        return ([], [generate_put(node_self, instance=True)],
                                [])
                else:
                    generate_delete(child_o, instance=True)
        for child_s, child_o in in_s_and_in_o:
            schema_node = self.device.get_schema_node(child_s)
            if schema_node.get('type') == 'leaf':
                if child_s.text != child_o.text:
                    generate_patch(child_s)
            elif schema_node.get('type') == 'leaf-list':
                if schema_node.get('ordered-by') == 'user':
                    if list_seq_is_different(child_s.tag):
                        return ([], [generate_put(node_self, instance=True)],
                                [])
            elif schema_node.get('type') == 'container':
                if BaseCalculator(self.device, child_s, child_o).ne:
                    x, y, z = self.node_sub(child_s, child_o)
                    deletes += x
                    puts += y
                    patches += z
            elif schema_node.get('type') == 'list':
                if schema_node.get('ordered-by') == 'user':
                    if list_seq_is_different(child_s.tag):
                        return ([], [generate_put(node_self, instance=True)],
                                [])
                    else:
                        if BaseCalculator(self.device, child_s, child_o).ne:
                            x, y, z = self.node_sub(child_s, child_o)
                            deletes += x
                            puts += y
                            patches += z
                else:
                    if BaseCalculator(self.device, child_s, child_o).ne:
                        x, y, z = self.node_sub(child_s, child_o)
                        deletes += x
                        puts += y
                        patches += z
        return (deletes, puts, patches)
