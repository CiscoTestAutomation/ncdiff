import re
import json
import logging
from lxml import etree
from xmljson import Parker
from ncclient import xml_
from xml.etree import ElementTree
from collections import OrderedDict, defaultdict

from .composer import Tag, Composer
from .gnmi_pb2 import PathElem, Path, SetRequest, TypedValue, Update
from .calculator import BaseCalculator

# create a logger for this module
logger = logging.getLogger(__name__)

nc_url = xml_.BASE_NS_1_0
config_tag = '{' + nc_url + '}config'


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
        return None
    std_value = value.strip().lower()
    if std_value == 'true':
        return 'true'
    elif std_value == 'false':
        return 'false'
    try:
        return int(std_value)
    except ValueError:
        pass
    try:
        return float(std_value)
    except ValueError:
        pass
    return value


class gNMIParser(object):
    '''gNMIParser

    A parser to convert a gNMI GetResponse to an lxml Element object. gNMI
    specification can be found at
    https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md

    Attributes
    ----------
    ele : `Element`
        An lxml Element object which is the root of the config tree.

    config_nodes : `list`
        A list of config nodes. Each config node is an Element node in the
        config tree, which is corresponding to one 'update' in the gNMI
        GetResponse.

    xpaths : `list`
        A list of strings. Each string is an xpath of an Element node in the
        config tree, which is corresponding to one 'update' in the gNMI
        GetResponse.
    '''

    def __init__(self, device, gnmi_get_reply):
        self.device = device
        self.reply = gnmi_get_reply
        self._config_nodes = None
        self._ele = None
        self._convert_tag = defaultdict(dict)

        self._prefix_to_name = {i[1]: i[0] for i in self.device.namespaces
                                if i[1] is not None}
        self._prefix_to_url = {i[1]: i[2] for i in self.device.namespaces
                               if i[1] is not None}

    @property
    def ele(self):
        if self._ele is None:
            if len(self.config_nodes) > 0 and len(self.config_nodes[0]) > 0:
                self._ele = self.root(self.config_nodes[0][0])
        return self._ele

    @property
    def config_nodes(self):
        if self._config_nodes is None:
            self._config_nodes = self.get_config_nodes()
        return self._config_nodes

    @property
    def xpaths(self):
        xpaths = []
        if len(self.config_nodes) > 0 and len(self.config_nodes[0]) > 0:
            if len(self.config_nodes[0]) > 1:
                xpaths.append(self.device.get_xpath(self.config_nodes[0][0],
                                                    type=Tag.LXML_XPATH,
                                                    instance=False))
            else:
                xpaths.append(self.device.get_xpath(self.config_nodes[0][0],
                                                    type=Tag.LXML_XPATH,
                                                    instance=True))
        return xpaths

    @staticmethod
    def parse_value(value, type):
        json_val_str = value.json_val.decode()
        if not json_val_str:
            raise ValueError("'json_val' is empty")
        if type == 'leaf' or type == 'leaf-list':
            return json_val_str
        json_data = json.loads(json_val_str, object_pairs_hook=OrderedDict)
        pk = Parker(xml_tostring=_tostring, element=ElementTree.Element)
        return pk.etree(json_data)

    @staticmethod
    def get_ns(tag):
        m = re.search('{(.*)}.*', tag)
        return m.group(1)

    @staticmethod
    def root(node):
        ancestors = list(node.iterancestors())
        if ancestors:
            return ancestors[-1]
        else:
            return node

    def convert_tag(self, default_ns, tag, src=Tag.LXML_ETREE, dst=Tag.YTOOL):
        if src == Tag.JSON_NAME and dst == Tag.LXML_ETREE:
            if default_ns not in self._convert_tag or \
               tag not in self._convert_tag[default_ns]:
                self._convert_tag[default_ns][tag] = \
                    self.device.convert_tag(default_ns, tag, src=src, dst=dst)
            return self._convert_tag[default_ns][tag]
        else:
            return self.device.convert_tag(default_ns, tag, src=src, dst=dst)

    def get_config_nodes(self):
        '''get_config_nodes

        High-level api: get_config_nodes returns a list of config nodes. Each
        config node is an Element node in the config tree, which is
        corresponding to one 'update' in the gNMI GetResponse.

        Returns
        -------

        list
            A list of config nodes.
        '''

        config_nodes = []
        config_root = etree.Element(config_tag, nsmap={'nc': nc_url})
        for notification in self.reply.notification:
            updates = []
            for update in notification.update:
                updates.append(self.build_config_node(config_root,
                                                      notification.prefix,
                                                      update.path, update.val))
            config_nodes.append(updates)
        return config_nodes

    def parse_json(self, lxml_parent, xml_child, default_ns=''):
        default_ns, tag = self.convert_tag(default_ns, xml_child.tag,
                                           src=Tag.JSON_NAME,
                                           dst=Tag.LXML_ETREE)
        lxml_child = self.subelement(lxml_parent, tag, xml_child.text)
        for child in xml_child:
            self.parse_json(lxml_child, child, default_ns)

    def build_config_node(self, root, prefix, path, value):
        default_ns = ''
        absolute_path = list(prefix.elem) + list(path.elem)
        config_node = root
        for index, elem in enumerate(absolute_path):
            default_ns, tag = self.convert_tag(default_ns, elem.name,
                                               src=Tag.JSON_PREFIX,
                                               dst=Tag.LXML_ETREE)
            config_parent = config_node
            config_node = config_parent.find(tag)
            if config_node is None:
                config_node = self.subelement(config_parent, tag, None)
            schema_node = self.device.get_schema_node(config_node)
            if index == len(path.elem) - 1:
                if schema_node.get('type') == 'leaf':
                    config_parent.remove(config_node)
                    config_node = self.subelement(config_parent, tag,
                                                  self.parse_value(value,
                                                                   'leaf'))
                elif schema_node.get('type') == 'leaf-list':
                    text = self.parse_value(value, 'leaf-list')
                    instance = self.find_instance(config_parent, tag,
                                                  'leaf-list', text, default_ns)
                    if instance is not None:
                        config_parent.remove(instance)
                    config_node = self.subelement(config_parent, tag, text)
                elif schema_node.get('type') == 'container':
                    config_parent.remove(config_node)
                    config_node = self.subelement(config_parent, tag, None)
                    self.parse_json(config_node, self.parse_value(value,
                                                                  'container'))
                elif schema_node.get('type') == 'list' and len(elem.key) > 0:
                    instance = self.find_instance(config_parent, tag, 'list',
                                                  elem.key, default_ns)
                    if instance is not None:
                        config_parent.remove(instance)
                    config_node = self.subelement(config_parent, tag, None)
                    self.parse_json(config_node, self.parse_value(value,
                                                                  'list'))
            else:
                if schema_node.get('type') == 'list' and len(elem.key) > 0:
                    instance = self.find_instance(config_parent, tag,
                                                  'list', elem.key, default_ns)
                    if instance is None:
                        if len(config_node.getchildren()) > 0:
                            config_node = self.subelement(config_parent, tag,
                                                          None)
                        for key, val in elem.key.items():
                            default_name = self._prefix_to_name[default_ns]
                            k = self.convert_tag(default_name, key,
                                                 src=Tag.JSON_NAME,
                                                 dst=Tag.LXML_ETREE)[1]
                            v = self.convert_tag(default_ns, val.strip('"'),
                                                 src=Tag.JSON_PREFIX,
                                                 dst=Tag.JSON_PREFIX)[1]
                            key_node = self.subelement(config_node, k, v)
                    else:
                        config_node = instance
        return config_node

    def find_instance(self, parent, tag, type, keys, default_ns):
        if type == 'leaf-list':
            text = self.convert_tag(default_ns, keys,
                                    src=Tag.JSON_PREFIX,
                                    dst=Tag.JSON_PREFIX)[1]
            for child in parent.findall(tag):
                if child.text == text:
                    return child
            return None
        if type == 'list':
            converted_keys = {}
            for key, value in keys.items():
                k = self.convert_tag(self._prefix_to_name[default_ns], key,
                                     src=Tag.JSON_NAME,
                                     dst=Tag.LXML_ETREE)[1]
                v = self.convert_tag(default_ns, value,
                                     src=Tag.JSON_PREFIX,
                                     dst=Tag.JSON_PREFIX)[1]
                converted_keys[k] = v
            for child in parent.findall(tag):
                for key, value in converted_keys.items():
                    k = child.find(key)
                    if k is None or k.text != value:
                        break
                else:
                    return child
            return None
        return None

    def get_prefix(self, text):
        if text is None:
            return '', None
        m = re.search('^(.*):(.*)$', text)
        if m:
            if m.group(1) in self._prefix_to_name:
                return m.group(1), m.group(2)
            else:
                return '', text
        else:
            return '', text

    def subelement(self, parent, tag, text):
        model_prefix, text_value = self.get_prefix(text)
        if model_prefix:
            nsmap = {None: self.get_ns(tag),
                     model_prefix: self._prefix_to_url[model_prefix]}
            e = etree.SubElement(parent, tag, nsmap=nsmap)
            e.text = '{}:{}'.format(model_prefix, text_value)
        else:
            nsmap = {None: self.get_ns(tag)}
            e = etree.SubElement(parent, tag, nsmap=nsmap)
            e.text = text_value
        return e

    def parse_json(self, lxml_parent, xml_children, default_ns=''):
        if not isinstance(xml_children, list):
            xml_children = [xml_children]
        for xml_child in xml_children:
            my_ns, tag = self.convert_tag(default_ns, xml_child.tag,
                                          src=Tag.JSON_NAME,
                                          dst=Tag.LXML_ETREE)
            lxml_child = self.subelement(lxml_parent, tag, xml_child.text)
            for child in xml_child:
                self.parse_json(lxml_child, child, my_ns)


class gNMIComposer(Composer):
    '''gNMIComposer

    A composer to convert an lxml Element object to gNMI JSON format. gNMI
    adopts RFC 7951 when encoding data. One gNMIComposer instance abstracts
    a config node in config tree.
    '''

    def __init__(self, *args, **kwargs):
        super(gNMIComposer, self).__init__(*args, **kwargs)
        self._url_to_prefix = {i[2]: i[1] for i in self.device.namespaces
                               if i[1] is not None}

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
            nodes = node.findall('.//')
            for item in nodes:
                parents = [p for p in node.findall('.//{}/..'.format(item.tag))
                          if item in p.findall('*')]
                parent_id = id(parents[0])
                if parents and parent_id in default_ns:
                    ns, tag = self.device.convert_tag(default_ns[parent_id],
                                                      item.tag,
                                                      dst=Tag.JSON_NAME)
                else:
                    ns, tag = self.device.convert_tag('',
                                                      item.tag,
                                                      dst=Tag.JSON_NAME)
                default_ns[id(item)] = ns
                item.tag = tag
                if item.text:
                    text = self.device.convert_tag(self._url_to_prefix[ns],
                                                   item.text,
                                                   src=Tag.JSON_PREFIX,
                                                   dst=Tag.JSON_NAME)[1]
                    item.text = text
            return pk.data(node)

        def convert_node(node):
            # lxml.etree does not allow tag name like oc-if:enable
            # so it is converted to xml.etree.ElementTree
            string = etree.tostring(node, encoding='unicode',
                                    pretty_print=False)
            return ElementTree.fromstring(string)

        if instance:
            return json.dumps(get_json_instance(convert_node(self.node)))
        else:
            nodes = [n for n in
                     self.node.getparent().iterchildren(tag=self.node.tag)]
            if len(nodes) > 1:
                return json.dumps([get_json_instance(convert_node(n))
                                   for n in nodes])
            else:
                return json.dumps(get_json_instance(convert_node(nodes[0])))

    def get_path(self, instance=True):
        '''get_path

        High-level api: get_path returns gNMI path object of the config node.
        Note that gNMI Path can specify list instance but cannot specify
        leaf-list instance.

        Parameters
        ----------

        instance : `bool`
            True if the gNMI Path object refers to only one instance of a list.
            False if the gNMI Path object refers to all instances of a list.

        Returns
        -------

        Path
            An object of gNMI Path class.
        '''

        def get_name(node, default_ns):
            return self.device.convert_tag(default_ns,
                                           node.tag,
                                           dst=Tag.JSON_PREFIX)

        def get_keys(node, default_ns):
            keys = Composer(self.device, node).keys
            return {self.device.convert_tag(default_ns,
                                            key,
                                            dst=Tag.JSON_PREFIX)[1]:
                    node.find(key).text for key in keys}

        def get_pathelem(node, default_ns):
            ns, name = get_name(node, default_ns)
            schema_node = self.device.get_schema_node(node)
            if schema_node.get('type') == 'list' and \
               (node != self.node or instance):
                return ns, PathElem(name=name, key=get_keys(node, default_ns))
            else:
                return ns, PathElem(name=name)

        nodes = list(reversed(list(self.node.iterancestors())))[1:] + \
                [self.node]
        path_elems = []
        default_ns = ''
        for node in nodes:
            default_ns, path_elem = get_pathelem(node, default_ns)
            path_elems.append(path_elem)
        return Path(elem=path_elems, origin=None)


class gNMICalculator(BaseCalculator):
    '''gNMICalculator

    A gNMI calculator to do subtraction and addition. A subtraction is to
    compute the delta between two Config instances in a form of gNMI SetRequest.
    An addition is to apply one gNMI SetRequest to a Config instance (TBD).

    Attributes
    ----------
    sub : `SetRequest`
        A gNMI SetRequest which can achieve a transition from one config, i.e.,
        self.etree2, to another config, i.e., self.etree1.
    '''

    @property
    def sub(self):
        deletes, replaces, updates = self.node_sub(self.etree1, self.etree2)
        return SetRequest(prefix=None,
                          delete=deletes,
                          replace=replaces,
                          update=updates)

    def node_sub(self, node_self, node_other):
        '''node_sub

        High-level api: Compute the delta of two config nodes. This method is
        recursive, assuming two config nodes are different.

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
            There are three elements in the tuple: a list of gNMI Path
            instances that need to be deleted, a list of gNMI Update instances
            for replacement purpose, and a list of gNMI Update instances for
            merging purpose.
        '''

        paths_delete = []
        updates_replace = []
        updates_update = []
        done_list = []

        # if a leaf-list node, delete the leaf-list totally
        # if a list node, by default delete the list instance
        # if a list node and delete_whole=True, delete the list totally
        def generate_delete(node, instance=True):
            paths_delete.append(gNMIComposer(self.device, node) \
                        .get_path(instance=instance))

        # if a leaf-list node, replace the leaf-list totally
        # if a list node, replace the list totally
        def generate_replace(node, instance=True):
            n = gNMIComposer(self.device, node)
            json_value = n.get_json(instance=instance).encode()
            value = TypedValue(json_val=json_value)
            path = n.get_path(instance=instance)
            updates_replace.append(Update(path=path, val=value))

        # if a leaf-list node, update the leaf-list totally
        # if a list node, by default update the list instance
        # if a list node and update_whole=True, update the list totally
        def generate_update(node, instance=True):
            n = gNMIComposer(self.device, node)
            json_value = n.get_json(instance=instance).encode()
            value = TypedValue(json_val=json_value)
            path = n.get_path(instance=instance)
            updates_update.append(Update(path=path, val=value))

        # the leaf-list value sequence under node_self is different from the one
        # under node_other
        def leaf_list_seq_is_different(tag):
            if [i.text for i in node_self.iterchildren(tag=tag)] == \
               [i.text for i in node_other.iterchildren(tag=tag)]:
                return False
            else:
                return True

        # the leaf-list value set under node_self is different from the one
        # under node_other
        def leaf_list_set_is_different(tag):
            s_list = [i.text for i in node_self.iterchildren(tag=tag)]
            o_list = [i.text for i in node_other.iterchildren(tag=tag)]
            if set(s_list) == set(o_list):
                return False
            else:
                return True

        # the leaf-list or list under node_self is empty
        def list_is_empty(tag):
            if [i for i in node_self.iterchildren(tag=tag)]:
                return False
            else:
                return True

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
            if schema_node.get('type') == 'leaf':
                generate_update(child_s)
            elif schema_node.get('type') == 'leaf-list':
                if child_s.tag not in done_list:
                    generate_replace(child_s, instance=False)
                    done_list.append(child_s.tag)
            elif schema_node.get('type') == 'container':
                generate_update(child_s)
            elif schema_node.get('type') == 'list':
                if schema_node.get('ordered-by') == 'user':
                    if child_s.tag not in done_list:
                        generate_replace(child_s, instance=False)
                        done_list.append(child_s.tag)
                else:
                    generate_update(child_s, instance=True)
        for child_o in in_o_not_in_s:
            schema_node = self.device.get_schema_node(child_o)
            if schema_node.get('type') == 'leaf':
                generate_delete(child_o)
            elif schema_node.get('type') == 'leaf-list':
                if child_o.tag not in done_list:
                    if list_is_empty(child_o.tag):
                        generate_delete(child_o, instance=False)
                    else:
                        generate_replace(child_s, instance=False)
                    done_list.append(child_o.tag)
            elif schema_node.get('type') == 'container':
                generate_delete(child_o)
            elif schema_node.get('type') == 'list':
                if schema_node.get('ordered-by') == 'user':
                    if list_seq_is_inclusive(child_o.tag):
                        generate_delete(child_o, instance=True)
                    else:
                        if child_o.tag not in done_list:
                            generate_replace(child_o, instance=False)
                            done_list.append(child_o.tag)
                else:
                    if list_is_empty(child_o.tag):
                        if child_o.tag not in done_list:
                            generate_delete(child_o, instance=False)
                            done_list.append(child_o.tag)
                    else:
                        generate_delete(child_o, instance=True)
        for child_s, child_o in in_s_and_in_o:
            schema_node = self.device.get_schema_node(child_s)
            if schema_node.get('type') == 'leaf':
                if child_s.text != child_o.text:
                    generate_update(child_s)
            elif schema_node.get('type') == 'leaf-list':
                if child_s.tag not in done_list:
                    if schema_node.get('ordered-by') == 'user':
                        if leaf_list_seq_is_different(child_s.tag):
                            generate_replace(child_s, instance=False)
                    else:
                        if leaf_list_set_is_different(child_s.tag):
                            generate_replace(child_s, instance=False)
                    done_list.append(child_s.tag)
            elif schema_node.get('type') == 'container':
                if BaseCalculator(self.device, child_s, child_o).ne:
                    d, r, u = self.node_sub(child_s, child_o)
                    paths_delete += d
                    updates_replace += r
                    updates_update += u
            elif schema_node.get('type') == 'list':
                if schema_node.get('ordered-by') == 'user':
                    if list_seq_is_different(child_s.tag):
                        if child_s.tag not in done_list:
                            generate_replace(child_s, instance=False)
                            done_list.append(child_s.tag)
                        else:
                            if BaseCalculator(self.device, child_s, child_o).ne:
                                d, r, u = self.node_sub(child_s, child_o)
                                paths_delete += d
                                updates_replace += r
                                updates_update += u
                else:
                    if BaseCalculator(self.device, child_s, child_o).ne:
                        d, r, u = self.node_sub(child_s, child_o)
                        paths_delete += d
                        updates_replace += r
                        updates_update += u
        return (paths_delete, updates_replace, updates_update)
