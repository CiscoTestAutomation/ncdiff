import logging
from ncclient import xml_

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

        for tag in operation_tag, insert_tag, value_tag, key_tag:
            if element.get(tag):
                del element.attrib[tag]
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
        for child in node_one.getchildren():
            peers = self._get_peers(child, node_two)
            if len(peers) < 1:
                # child in self but not in other
                in_1_not_in_2.append(child)
            elif len(peers) > 1:
                # one child in self matches multiple children in other
                raise ConfigError('not unique peer of node {}' \
                                  .format(self.device.get_xpath(child)))
            else:
                # child matches one peer in other
                in_1_and_in_2.append((child, peers[0]))
        for child in node_two.getchildren():
            peers = self._get_peers(child, node_one)
            if len(peers) < 1:
                # child in other but not in self
                in_2_not_in_1.append(child)
            elif len(peers) > 1:
                # one child in other matches multiple children in self
                raise ConfigError('not unique peer of node {}' \
                                  .format(self.device.get_xpath(child)))
            else:
                # child in self matches one peer in self
                pass
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
        return [n.tag for n in nodes]

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
                               child_self.text == x.text,
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
            if s[0].text != o[0].text:
                return False
        return True

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

        for x in ['tag', 'text', 'tail']:
            if node_self.__getattribute__(x) != node_other.__getattribute__(x):
                return False
        for a in node_self.attrib:
            if a not in node_other.attrib or \
               node_self.attrib[a] != node_other.attrib[a]:
                return False
        for child in node_self.getchildren():
            peers = self._get_peers(child, node_other)
            if len(peers) < 1:
                return False
            elif len(peers) > 1:
                raise ConfigError('not unique peer of node {}' \
                                  .format(self.device.get_xpath(child)))
            else:
                schma_node = self.device.get_schema_node(child)
                if schma_node.get('ordered-by') == 'user' and \
                   schma_node.get('type') == 'leaf-list' or \
                   schma_node.get('ordered-by') == 'user' and \
                   schma_node.get('type') == 'list':
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
                            list(peers[0].itersiblings(tag=child.tag,
                                                       preceding=True))
                        if peers_of_immediate_elder_sibling[0] not in \
                           elder_siblings_of_peer:
                            return False
                if not self._node_le(child, peers[0]):
                    return False
        return True
