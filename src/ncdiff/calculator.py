import logging
from functools import lru_cache

from ncclient import xml_

from .ref import IdentityRef, InstanceIdentifier
from .errors import ConfigError

# create a logger for this module
logger = logging.getLogger(__name__)

nc_url = xml_.BASE_NS_1_0
yang_url = 'urn:ietf:params:xml:ns:yang:1'
operation_tag = '{' + nc_url + '}operation'
insert_tag = '{' + yang_url + '}insert'
value_tag = '{' + yang_url + '}value'
key_tag = '{' + yang_url + '}key'


class BaseCalculator(object):
    '''BaseCalculator

    A set of methods to help calculate substruction and addition of two Config
    instances. This is a base class, which is inherited by protocol calculator
    classes, for example: NetconfCalculator and RestconfCalculator.

    Attributes
    ----------
    device : `object`
        An instance of yang.ncdiff.ModelDevice, which represents a modeled
        device.

    etree1 : `Element`
        A lxml Element which contains the config.

    etree2 : `Element`
        A lxml Element which contains the other config.
    '''

    def __init__(self, device, etree1, etree2):
        '''
        __init__ instantiates a BaseCalculator instance.
        '''

        self.device = device
        self.etree1 = etree1
        self.etree2 = etree2

    @staticmethod
    def _del_attrib(element):
        '''_del_attrib

        Low-level api: Delete four attributes from an Element node if they
        exist: operation, insert, value and key.

        Parameters
        ----------

        element : `Element`
            The Element node needs to be looked at.

        Returns
        -------

        Element
            The Element node is returned after processing.
        '''

        for ele in element.iter():
            for attribute in ele.attrib.keys():
                del ele.attrib[attribute]
        return element

    @staticmethod
    def _get_sequence(scope, tag, parent):
        '''_get_sequence

        Low-level api: Return a list of children of a parent with the same tag
        within the scope.

        Parameters
        ----------

        scope : `list`
            List members can be an element, or a tuple of two elements.

        tag : `str`
            Identifier in `{url}tagname` notation.

        parent : `Element`
            The parent node.

        Returns
        -------

        list
            A list of children with the same tag within the scope.
        '''

        new_scope = []
        for item in scope:
            if isinstance(item, tuple):
                one, two = item
                if one.getparent() == parent:
                    new_scope.append(one)
                else:
                    new_scope.append(two)
            else:
                new_scope.append(item)
        return [child for child in parent.iterchildren(tag=tag)
                if child in new_scope]

    def _pair_children(self, node_one, node_two):
        """_pair_children
         pair all children with their peers, resulting in a list of Tuples

         Parameters
        ----------
        node_one : `Element`
            An Element node in one Config instance.

        node_two : `Element`
            An Element node in the other Config instance.

        Returns
        -------

        list
            List of matching pairs, one of both items in the pair can be None

        """
        # Hash based approach, build two hashtables and match
        # keys are (tag, self-key)
        # self-key is
        #    text for leaf-list
        #    key tuple for list
        #    none for others

        def find_one_child(node, tag):
            """ Find exactly one child with the given tag"""
            s = list(node.iterchildren(tag=tag))
            if len(s) < 1:
                raise ConfigError("cannot find key '{}' in node {}" \
                                  .format(tag,
                                          self.device.get_xpath(node)))
            if len(s) > 1:
                raise ConfigError("not unique key '{}' in node {}" \
                                  .format(tag,
                                          self.device.get_xpath(node)))
            return s[0]

        def build_index_tuple(node, keys, s_node):
            """
            build a tuple containing the text of all fields listed in keys, taken from node

            s_node is passed to prevent it being looked up twice.
            """
            out = [self._parse_text(find_one_child(node, k), s_node) for k in keys]
            return tuple(out)

        type_for_tag = {}
        def get_type_for_tag(tag, child):
            """
            Given a child node with a given tag, find the type

            caches based on tag

            :return: a tuple, containing the s_node and node type
            """
            node_type = type_for_tag.get(tag, None)
            if node_type is not None:
                return node_type
            s_node = self.device.get_schema_node(child)
            node_type = s_node.get('type')

            result = (s_node, node_type)
            type_for_tag[tag] = result
            return result

        def build_unique_id(child):
            """
            Build the hash key for a node
            """
            tag = child.tag
            key = None
            s_node, node_type = get_type_for_tag(tag, child)
            if node_type == 'leaf-list':
                key = self._parse_text(child, s_node)
            elif node_type == 'list':
                keys = self._get_list_keys(s_node)
                key = build_index_tuple(child, keys, s_node)
            return (tag, key)

        # build the hashmap for node_one
        ones = {}
        for child in node_one.getchildren():
            key = build_unique_id(child)
            if key in ones:
                raise ConfigError('not unique peer of node {} {}' \
                    .format(child, ones[key]))
            ones[key] = child

        # build the hashmap for node_two
        twos = {}
        for child in node_two.getchildren():
            key = build_unique_id(child)
            if key in twos:
                raise ConfigError('not unique peer of node {} {}' \
                                  .format(child, twos[key]))
            twos[key] = child

        # make pairs, in order
        one_lookup = set(ones.keys())
        keys_in_order = list(ones.keys())
        keys_in_order.extend([two for two in twos.keys() if two not in one_lookup])
        return [(ones.get(uid, None), twos.get(uid, None)) for uid in keys_in_order]

    def _group_kids(self, node_one, node_two):
        '''_group_kids

        Low-level api: Consider an Element node in a Config instance. Now
        we have two Config instances and we want to compare two corresponding
        Element nodes. This method group children of these nodes in three
        categories: some only exist in node_one, some only exist in node_two,
        and some chiildren of node_one have peers in node_two.

        Parameters
        ----------

        node_one : `Element`
            An Element node in one Config instance.

        node_two : `Element`
            An Element node in the other Config instance.

        Returns
        -------

        tuple
            There are three elements in the tuple. The first element is a list
            of children of node_one that do not have any peers in node_two. The
            second element is a list of children of node_two that do not have
            any peers in node_one. The last element is a list of tuples, and
            each tuple represents a pair of peers.
        '''

        in_1_not_in_2 = []
        in_2_not_in_1 = []
        in_1_and_in_2 = []

        for one, two in self._pair_children(node_one, node_two):
            if one is None:
                in_2_not_in_1.append(two)
            elif two is None:
                in_1_not_in_2.append(one)
            else:
                in_1_and_in_2.append((one, two))

        return (in_1_not_in_2, in_2_not_in_1, in_1_and_in_2)

    @staticmethod
    def _get_list_keys(schema_node):
        '''_get_list_keys

        Low-level api: Given a schema node, in particular, a list type schema
        node, it returns a list of keys.

        Parameters
        ----------

        schema_node : `Element`
            A schema node.

        Returns
        -------

        list
            A list of tags of keys in `{url}tagname` notation.
        '''

        nodes = list(filter(lambda x: x.get('is_key'),
                            schema_node.getchildren()))
        return sorted([n.tag for n in nodes])

    def _get_peers(self, child_self, parent_other):
        '''_get_peers

        Low-level api: Given a config node, find peers under a parent node.

        Parameters
        ----------

        child_self : `Element`
            An Element node on this side.

        parent_other : `Element`
            An Element node on the other side.

        Returns
        -------

        list
            A list of children of parent_other who are peers of child_self.
        '''

        peers = parent_other.findall(child_self.tag)
        s_node = self.device.get_schema_node(child_self)
        if s_node.get('type') == 'leaf-list':
            return list(filter(lambda x:
                               self._same_text(child_self, x),
                               peers))
        elif s_node.get('type') == 'list':
            keys = self._get_list_keys(s_node)
            return list(filter(lambda x:
                               self._is_peer(keys, child_self, x),
                               peers))
        else:
            return peers

    def _is_peer(self, keys, node_self, node_other):
        '''_is_peer

        Low-level api: Return True if node_self and node_other are considered
        as peer with regards to a set of keys.

        Parameters
        ----------

        keys : `list`
            A list of keys in `{url}tagname` notation.

        node_self : `Element`
            An Element node on this side.

        node_other : `Element`
            An Element node on the other side.

        Returns
        -------

        list
            True if node_self is a peer of node_other, otherwise, return False.
        '''

        for key in keys:
            s = list(node_self.iterchildren(tag=key))
            o = list(node_other.iterchildren(tag=key))
            if len(s) < 1 or len(o) < 1:
                raise ConfigError("cannot find key '{}' in node {}" \
                                  .format(key,
                                          self.device.get_xpath(node_self)))
            if len(s) > 1 or len(o) > 1:
                raise ConfigError("not unique key '{}' in node {}" \
                                  .format(key,
                                          self.device.get_xpath(node_self)))
            if not self._same_text(s[0], o[0]):
                return False
        return True

    @lru_cache(maxsize=1024)
    # cache because this is an expensive call, often called multiple times on the same node in rapid succession
    def _parse_text(self, node, schema_node=None):
        '''_parse_text

        Low-level api: Return text if a node. Pharsing is required if the node
        data type is identityref or instance-identifier.

        Parameters
        ----------

        node : `Element`
            An Element node in data tree.

        Returns
        -------

        None or str
            None if the node does not have text, otherwise, text string of the
            node.
        '''

        if node.text is None:
            return None

        if schema_node is None:
            schema_node = self.device.get_schema_node(node)
        if schema_node.get('datatype') is not None and \
          (schema_node.get('datatype')[:11] == 'identityref' or schema_node.get('datatype')[:3] == '-> '):
            idref = IdentityRef(self.device, node)
            return idref.default
        elif schema_node.get('datatype') is not None and \
             schema_node.get('datatype') == 'instance-identifier':
            instanceid = InstanceIdentifier(self.device, node)
            return instanceid.default
        else:
            if schema_node.get("type") == "container":
                # prevent whitespace in container to cause problems
                return None
            return node.text

    def _same_text(self, node1, node2):
        '''_same_text

        Low-level api: Compare text values of two nodes.

        Parameters
        ----------

        node1 : `Element`
            An Element node in data tree.

        node2 : `Element`
            An Element node in data tree.

        Returns
        -------

        bool
            True if text values of two nodes are same, otherwise, False.
        '''

        if node1.text is None and node2.text is None:
            return True
        return self._parse_text(node1) == self._parse_text(node2)

    def _merge_text(self, from_node, to_node):
        '''_merge_text

        Low-level api: Set text value of to_node according to the text value of
        from_node.

        Parameters
        ----------

        from_node : `Element`
            An Element node in data tree.

        to_node : `Element`
            An Element node in data tree.

        Returns
        -------

        None
            There is no return of this method.
        '''

        if from_node.text is None:
            to_node.text = None
            return
        schema_node = self.device.get_schema_node(from_node)
        if schema_node.get('datatype') is not None and \
           schema_node.get('datatype')[:11] == 'identityref':
            idref = IdentityRef(self.device,
                                from_node, to_node=to_node)
            to_node.text = idref.converted
        elif schema_node.get('datatype') is not None and \
             schema_node.get('datatype') == 'instance-identifier':
            instanceid = InstanceIdentifier(self.device,
                                            from_node, to_node=to_node)
            to_node.text = instanceid.converted
        else:
            to_node.text = from_node.text

    @property
    def le(self):
        return self._node_le(self.etree1, self.etree2)

    @property
    def lt(self):
        return self._node_le(self.etree1, self.etree2) and \
               not self._node_le(self.etree2, self.etree1)

    @property
    def ge(self):
        return self._node_le(self.etree2, self.etree1)

    @property
    def gt(self):
        return self._node_le(self.etree2, self.etree1) and \
               not self._node_le(self.etree1, self.etree2)

    @property
    def eq(self):
        return self._node_le(self.etree1, self.etree2) and \
               self._node_le(self.etree2, self.etree1)

    @property
    def ne(self):
        return not self._node_le(self.etree1, self.etree2) or \
               not self._node_le(self.etree2, self.etree1)

    def _node_le(self, node_self, node_other):
        '''_node_le

        Low-level api: Return True if all descendants of one node exist in the
        other node. Otherwise False. This is a recursive method.

        Parameters
        ----------

        node_self : `Element`
            A node to be compared.

        node_other : `Element`
            Another node to be compared.

        Returns
        -------

        bool
            True if all descendants of node_self exist in node_other, otherwise
            False.
        '''

        for x in ['tag', 'tail']:
            if node_self.__getattribute__(x) != node_other.__getattribute__(x):
                return False
        if not self._same_text(node_self, node_other):
            return False
        for a in node_self.attrib:
            if a not in node_other.attrib or \
               node_self.attrib[a] != node_other.attrib[a]:
                return False
        for child, child_other in self._pair_children(node_self, node_other):
            if child is None:
                # only in other, meaningless
                continue
            if child_other is None:
                # only in other, false
                return False
            # both are present
            schma_node = self.device.get_schema_node(child)
            ordered_by = schma_node.get('ordered-by')
            child_type = schma_node.get('type')
            if ordered_by == 'user' and (
                    child_type == 'leaf-list' or
                    child_type == 'list'):
                elder_siblings = list(child.itersiblings(tag=child.tag,
                                                         preceding=True))
                if elder_siblings:
                    immediate_elder_sibling = elder_siblings[0]
                    peers_of_immediate_elder_sibling = \
                        self._get_peers(immediate_elder_sibling,
                                        node_other)
                    if len(peers_of_immediate_elder_sibling) < 1:
                        return False
                    elif len(peers_of_immediate_elder_sibling) > 1:
                        p = self.device.get_xpath(immediate_elder_sibling)
                        raise ConfigError('not unique peer of node {}' \
                                          .format(p))
                    elder_siblings_of_peer = \
                        list(child_other.itersiblings(tag=child.tag,
                                                   preceding=True))
                    if peers_of_immediate_elder_sibling[0] not in \
                            elder_siblings_of_peer:
                        return False
            if not self._node_le(child, child_other):
                return False

        return True
