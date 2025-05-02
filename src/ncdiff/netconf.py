import re
import json
import logging
from lxml import etree
from copy import deepcopy
from ncclient import operations, xml_

from .errors import ConfigDeltaError, ModelError
from .calculator import BaseCalculator

# create a logger for this module
logger = logging.getLogger(__name__)

nc_url = xml_.BASE_NS_1_0
yang_url = 'urn:ietf:params:xml:ns:yang:1'
config_tag = '{' + nc_url + '}config'
filter_tag = '{' + nc_url + '}filter'
operation_tag = '{' + nc_url + '}operation'
insert_tag = '{' + yang_url + '}insert'
value_tag = '{' + yang_url + '}value'
key_tag = '{' + yang_url + '}key'


def _inserterror(direction, path, attr_name, attr_value=None):
    if attr_value:
        raise ConfigDeltaError("attribute wrong: try to insert the node "
                               "{} {} another node, which cannot be found "
                               "by attribute '{}={}'"
                               .format(path, direction, attr_name, attr_value))
    else:
        raise ConfigDeltaError("attribute missing: try to insert the node "
                               "{} {} another node, but it does not have "
                               "attribute '{}'"
                               .format(path, direction, attr_name))


def _copy_element(new_parent, element):
    new_child = etree.SubElement(new_parent, element.tag,
                                 attrib=element.attrib,
                                 nsmap=element.nsmap)
    if element.text is not None:
        new_child.text = element.text
    for subelement in element:
        _copy_element(new_child, subelement)


def _copy_elements(new_parent, elements):
    for element in elements:
        _copy_element(new_parent, element)


class NetconfParser(object):
    '''NetconfParser

    A parser to convert a reply of get-config to an lxml Element object.

    Attributes
    ----------
    ele : `Element`
        An lxml Element object which is the root of the config tree.
    '''

    def __init__(self, device, get_reply):
        self.device = device
        self.reply = get_reply
        self._ele = None

    @property
    def ele(self):
        if self._ele is None:
            if isinstance(self.reply, str):
                parser = etree.XMLParser(remove_blank_text=True)
                self._ele = self.retrieve_config(etree.XML(self.reply, parser))
            elif etree.iselement(self.reply):
                self._ele = self.retrieve_config(self.reply)
            elif isinstance(self.reply, operations.rpc.RPCReply):
                self._ele = self.retrieve_config(self.reply._root)
        return self._ele

    @staticmethod
    def retrieve_config(element):
        '''retrieve_config

        High-level api: Retrive config from rpc-reply.

        Parameters
        ----------

        element : `Element`
            A rpc-reply or content of Config instance.

        Returns
        -------

        Element
            A new element which represents config data.
        '''

        if not etree.iselement(element):
            raise TypeError("argument 'element' must be Element not '{}'"
                            .format(type(element)))
        ret = etree.Element(config_tag, nsmap={'nc': nc_url})
        _copy_elements(ret, element.xpath('/nc:rpc-reply/nc:data/*',
                       namespaces={'nc': nc_url}))
        _copy_elements(ret, element.xpath('/nc:data/*',
                       namespaces={'nc': nc_url}))
        _copy_elements(ret, element.xpath('/nc:config/*',
                       namespaces={'nc': nc_url}))
        _copy_elements(ret, element.xpath('/nc:rpc/nc:edit-config/nc:config/*',
                       namespaces={'nc': nc_url}))
        _copy_elements(ret, element.xpath('/nc:edit-config/nc:config/*',
                       namespaces={'nc': nc_url}))
        return ret


class NetconfCalculator(BaseCalculator):
    '''NetconfCalculator

    A Netconf calculator to do subtraction and addition. A subtraction is to
    compute the delta between two Config instances in a form of Netconf
    edit-config. An addition is to apply one Netconf edit-config to a Config
    instance.

    Attributes
    ----------
    sub : `Element`
        Content of a Netconf edit-config which can achieve a transition from
        one config, i.e., self.etree2, to another config, i.e., self.etree1.

    add : `Element`
        Content of a Config instance.

    preferred_create : `str`
        Preferred operation of creating a new element. Choice of 'merge',
        'create' or 'replace'.

    preferred_replace : `str`
        Preferred operation of replacing an existing element. Choice of
        'merge' or 'replace'.

    preferred_delete : `str`
        Preferred operation of deleting an existing element. Choice of
        'delete' or 'remove'.

    diff_type : `str`
        Choice of 'minimum' 'minimum-replace', or 'replace'. This value has impact on attribute
        nc. In general, there are two options to construct nc. The first
        option is to find out minimal changes between config_src and
        config_dst. Then attribute nc will reflect what needs to be modified.
        The second option is to use 'replace' operation in Netconf. More
        customers prefer 'replace' operation as it is more deterministic.

    replace_depth : `int`
        Specify the deepest level of replace operation when diff_type is
        'replace'. Replace operation might be needed earlier before we reach
        the specified level, depending on situations. Consider roots in a YANG
        module are level 0, their children are level 1, and so on so forth.
        The default value of replace_depth is 0.

    replace_xpath: `str`
        Specify the xpath of the node to be replaced when diff_type is
        'minimum-replace'. The default value of replace_xpath is None.
    '''

    def __init__(self, device, etree1, etree2,
                 preferred_create='merge',
                 preferred_replace='merge',
                 preferred_delete='delete',
                 diff_type='minimum', replace_depth=0, replace_xpath=None):
        '''
        __init__ instantiates a NetconfCalculator instance.
        '''

        BaseCalculator.__init__(self, device, etree1, etree2)
        self.device = device
        self.diff_type = diff_type
        self.replace_depth = replace_depth
        self.replace_xpath = replace_xpath
        if preferred_create in ['merge', 'create', 'replace']:
            self.preferred_create = preferred_create
        else:
            raise ValueError("only 'merge', 'create' or 'replace' are valid "
                             "values of 'preferred_create'")
        if preferred_replace in ['merge', 'replace']:
            self.preferred_replace = preferred_replace
        else:
            raise ValueError("only 'merge' or 'replace' are valid "
                             "values of 'preferred_replace'")
        if preferred_delete in ['delete', 'remove']:
            self.preferred_delete = preferred_delete
        else:
            raise ValueError("only 'delete' or 'remove' are valid "
                             "values of 'preferred_delete'")

    @property
    def add(self):
        ele1 = deepcopy(self.etree1)
        ele2 = deepcopy(self.etree2)
        self.node_add(ele1, ele2)
        return ele1

    @property
    def sub(self):
        ele1 = deepcopy(self.etree1)
        ele2 = deepcopy(self.etree2)
        if self.diff_type == 'replace' and self.replace_depth == 0:
            self.get_config_replace(ele1, ele2)
        else:
            self.node_sub(ele1, ele2, depth=0)
        # add attribute at depth if diff_type is 'minimum-replace'
        if self.diff_type == 'minimum-replace' and self.replace_xpath:
            namespaces = self.device._get_ns(ele1)
            logger.debug("Namespaces:\n{}".format(json.dumps(namespaces, indent=2)))
            self.add_attribute_by_xpath(ele1, self.replace_xpath, 'operation', 'replace', namespaces)
        elif self.diff_type == 'minimum-replace':
            self.add_attribute_at_depth(ele1, self.replace_depth+1, 'operation', 'replace')
        return ele1

    def add_attribute_at_depth(self, root, depth, attribute, value):
        '''add_attribute_at_depth
        High-level api: Add an attribute to all nodes at a specified depth.
        Parameters
        ----------
        root : `Element`
            The root of a config tree.
        depth : `int`
            The depth of nodes to be added with an attribute.
        attribute : `str`
            The name of the attribute to be added.
        value : `str`
            The value of the attribute to be added.
        Returns
        -------
        None
        '''
        # Initialize current_depth as -1
        current_depth = -1

        # Create a list with the root node and its depth (0)
        nodes_to_visit = [(root, current_depth + 1)]

        # While there are nodes to visit
        while nodes_to_visit:
            # Pop the first node and its depth from the list
            node, current_depth = nodes_to_visit.pop(0)

            # If the current node's depth matches the specified depth
            if current_depth == depth:
                # Add the attribute to the node
                node.set(attribute, value)
            # Add the attribute to the node
            nodes_to_visit.extend((child, current_depth + 1) for child in node)

    # Not used. Saved for further use-case
    def find_by_tags(self, root, tags):
        '''
        Finds all nodes matching a list of tags.
        Parameters
        ----------
        root : `Element`
            The root of a config tree.
        tags : `list` of `str`
            The list of tags specifying the nodes to be found.
        Returns
        -------
        `list` of `Element`
            The list of matching nodes.
        '''
        # Start with the root element
        nodes = [root]

        # Traverse the tree for each tag
        for tag in tags:
            new_nodes = []
            for node in nodes:
                new_nodes.extend(node.findall('.//{}'.format(tag)))
            nodes = new_nodes

        return nodes

    # Not used. Saved for further use-case
    def add_attribute_by_tags(self, root, tags, attribute, value):
        '''add_attribute_by_tags
        '''
        nodes = self.find_by_tags(self, root, tags)

        for node in nodes:
            node.set(attribute, value)

    def add_attribute_by_xpath(self, root, xpath, attribute, value, namespaces=None):
        '''
        Adds an attribute to all nodes matching an XPath expression.
        Parameters
        ----------
        root : `Element`
            The root of a config tree.
        xpath : `str`
            The XPath expression specifying the nodes to be modified.
        attribute : `str`
            The name of the attribute to be added.
        value : `str`
            The value of the attribute to be added.
        namespaces : `dict`, optional
            The namespace prefix-URI mapping, by default None
        Returns
        -------
        None
        '''
        # Find all nodes matching the XPath expression
        nodes = root.xpath(xpath, namespaces=namespaces)

        # Add the attribute to all matching nodes
        for node in nodes:
            node.set(attribute, value)

    def get_config_replace(self, node_self, node_other):
        '''get_config_replace

        High-level api: Build an edit-config using operation='replace'. It
        will be mostly from self.etree1.

        Parameters
        ----------

        None

        Returns
        -------

        Element
            An element represnting an edit-config.
        '''

        in_s_not_in_o, in_o_not_in_s, in_s_and_in_o = \
            self._group_kids(node_self, node_other)
        ordered_by_user = {}

        for child_self in in_s_not_in_o:
            child_self.set(operation_tag, 'replace')
            s_node = self.device.get_schema_node(child_self)
            if s_node.get('type') == 'leaf-list':
                if (
                    s_node.get('ordered-by') == 'user' and
                    s_node.tag not in ordered_by_user
                ):
                    ordered_by_user[s_node.tag] = 'leaf-list'
            elif s_node.get('type') == 'list':
                keys = self._get_list_keys(s_node)
                if (
                    s_node.get('ordered-by') == 'user' and
                    s_node.tag not in ordered_by_user
                ):
                    ordered_by_user[s_node.tag] = keys

        for child_other in in_o_not_in_s:
            child_self = etree.Element(child_other.tag,
                                       {operation_tag: self.preferred_delete},
                                       nsmap=child_other.nsmap)
            siblings = list(node_self.iterchildren(tag=child_other.tag))
            if siblings:
                siblings[-1].addnext(child_self)
            else:
                node_self.append(child_self)
            s_node = self.device.get_schema_node(child_other)
            if s_node.get('type') == 'leaf-list':
                self._merge_text(child_other, child_self)
            elif s_node.get('type') == 'list':
                keys = self._get_list_keys(s_node)
                for key in keys:
                    key_node = child_other.find(key)
                    e = etree.SubElement(
                        child_self, key, nsmap=key_node.nsmap)
                    e.text = key_node.text

        for child_self, child_other in in_s_and_in_o:
            child_self.set(operation_tag, 'replace')
            child_other.set(operation_tag, 'replace')
            s_node = self.device.get_schema_node(child_self)
            if s_node.get('type') == 'leaf':
                if self._same_text(child_self, child_other):
                    if s_node.get('is_key'):
                        child_self.attrib.pop(operation_tag)
                    else:
                        node_self.remove(child_self)
            elif s_node.get('type') == 'leaf-list':
                if s_node.get('ordered-by') == 'user':
                    if s_node.tag not in ordered_by_user:
                        ordered_by_user[s_node.tag] = 'leaf-list'
                else:
                    node_self.remove(child_self)
            elif s_node.get('type') == 'container':
                if (
                    self._node_le(child_self, child_other) and
                    self._node_le(child_other, child_self)
                ):
                    node_self.remove(child_self)
            elif s_node.get('type') == 'list':
                if (
                    s_node.get('ordered-by') == 'user' and
                    s_node.tag not in ordered_by_user
                ):
                    ordered_by_user[s_node.tag] = self._get_list_keys(s_node)
                if (
                    self._node_le(child_self, child_other) and
                    self._node_le(child_other, child_self)
                ):
                    if s_node.get('ordered-by') != 'user':
                        node_self.remove(child_self)
            else:
                path = self.device.get_xpath(s_node)
                raise ModelError("unknown schema node type: type of node {}"
                                 "is '{}'".format(path, s_node.get('type')))

        for tag in ordered_by_user:
            scope_o = in_s_not_in_o + in_s_and_in_o
            sequence = self._get_sequence(scope_o, tag, node_self)
            for i, item in enumerate(sequence):
                # modifying the namespace mapping of a node is not possible
                # in lxml. See https://bugs.launchpad.net/lxml/+bug/555602
                # if 'yang' not in item.nsmap:
                #     item.nsmap['yang'] = yang_url
                if i == 0:
                    item.set(insert_tag, 'first')
                else:
                    item.set(insert_tag, 'after')
                    precursor = sequence[i - 1]
                    if ordered_by_user[tag] == 'leaf-list':
                        item.set(value_tag, precursor.text)
                    else:
                        keys = ordered_by_user[tag]
                        key_nodes = {k: precursor.find(k) for k in keys}
                        ids = {
                            k: self._url_to_prefix(n, k)
                            for k, n in key_nodes.items()
                        }
                        id_list = [
                            "[{}='{}']".format(ids[k], key_nodes[k].text)
                            for k in keys
                        ]
                        item.set(key_tag, ''.join(id_list))

    def node_add(self, node_sum, node_other):
        '''node_add

        High-level api: Combine two configs or apply an instance of ConfigDelta
        to a config. This method is recursive. node_sum will be modified during
        the process, and it becomes the result at the end.

        Parameters
        ----------

        node_sum : `Element`
            A config node in a config tree.

        node_other : `Element`
            A config node in another config tree.

        Returns
        -------

        None
            There is no return of this method.
        '''

        supported_node_type = [
            'leaf',
            'leaf-list',
            'container',
            'list',
            ]
        in_s_not_in_o, in_o_not_in_s, in_s_and_in_o = \
            self._group_kids(node_sum, node_other)
        for child_self in in_s_not_in_o:
            pass

        for child_other in in_o_not_in_s:
            this_operation = child_other.get(operation_tag, default='merge')

            # delete
            if this_operation == 'delete':
                raise ConfigDeltaError(
                    'data-missing: try to delete node {} but it does not '
                    'exist in config'.format(
                        self.device.get_xpath(child_other)
                    )
                )

            # remove
            elif this_operation == 'remove':
                pass

            # merge, create, replace or none
            elif (
                this_operation == 'merge' or
                this_operation == 'replace' or
                this_operation == 'create'
            ):
                s_node = self.device.get_schema_node(child_other)
                if s_node.get('type') in supported_node_type:
                    getattr(
                        self,
                        '_node_add_without_peer_{}'.format(
                            s_node.get('type').replace('-', '')
                        )
                    )(node_sum, child_other)

            else:
                raise ConfigDeltaError(
                    "unknown operation: node {} contains operation "
                    "'{}'".format(
                        self.device.get_xpath(child_other),
                        this_operation
                    )
                )

        for child_self, child_other in in_s_and_in_o:
            s_node = self.device.get_schema_node(child_self)
            if s_node.get('type') in supported_node_type:
                getattr(
                    self,
                    '_node_add_with_peer_{}'.format(
                        s_node.get('type').replace('-', '')
                    )
                )(child_self, child_other)

            if not list(child_self):
                if (
                    s_node.get('type') == 'container' and
                    s_node.get('presence') != 'true'
                ):
                    node_sum.remove(child_self)

    def _node_add_without_peer_leaf(self, node_sum, child_other):
        '''_node_add_without_peer_leaf

        Low-level api: Apply delta child_other to node_sum when there is no
        peer of child_other can be found under node_sum. child_other is a leaf
        node. Element node_sum will be modified during the process.

        Parameters
        ----------

        node_sum : `Element`
            A config node in a config tree.

        child_other : `Element`
            A child of a config node in another config tree. This child has no
            peer under node_sum.

        Returns
        -------

        None
            There is no return of this method.
        '''

        e = deepcopy(child_other)
        node_sum.append(self._del_attrib(e))

    def _node_add_without_peer_leaflist(self, node_sum, child_other):
        '''_node_add_without_peer_leaflist

        Low-level api: Apply delta child_other to node_sum when there is no
        peer of child_other can be found under node_sum. child_other is a
        leaf-list node. Element node_sum will be modified during the process.

        Parameters
        ----------

        node_sum : `Element`
            A config node in a config tree.

        child_other : `Element`
            A child of a config node in another config tree. This child has no
            peer under node_sum.

        Returns
        -------

        None
            There is no return of this method.
        '''

        s_node = self.device.get_schema_node(child_other)
        e = deepcopy(child_other)
        scope = node_sum.getchildren()
        siblings = self._get_sequence(scope, child_other.tag, node_sum)
        if s_node.get('ordered-by') == 'user' and \
           child_other.get(insert_tag) is not None:
            if child_other.get(insert_tag) == 'first':
                if siblings:
                    siblings[0].addprevious(self._del_attrib(e))
                else:
                    node_sum.append(self._del_attrib(e))
            elif child_other.get(insert_tag) == 'last':
                if siblings:
                    siblings[-1].addnext(self._del_attrib(e))
                else:
                    node_sum.append(self._del_attrib(e))
            elif child_other.get(insert_tag) == 'before':
                if child_other.get(value_tag) is None:
                    _inserterror('before', self.device.get_xpath(child_other),
                                 'value')
                siblings = node_sum.findall(child_other.tag)
                sibling = [s for s in siblings
                           if s.text == child_other.get(value_tag)]
                if not sibling:
                    path = self.device.get_xpath(child_other)
                    value = child_other.get(value_tag)
                    _inserterror('before', path, 'value', value)
                sibling[0].addprevious(self._del_attrib(e))
            elif child_other.get(insert_tag) == 'after':
                if child_other.get(value_tag) is None:
                    _inserterror('after', self.device.get_xpath(child_other),
                                 'value')
                siblings = node_sum.findall(child_other.tag)
                sibling = [s for s in siblings
                           if s.text == child_other.get(value_tag)]
                if not sibling:
                    path = self.device.get_xpath(child_other)
                    value = child_other.get(value_tag)
                    _inserterror('after', path, 'value', value)
                sibling[0].addnext(self._del_attrib(e))
        else:
            if siblings:
                siblings[-1].addnext(self._del_attrib(e))
            else:
                node_sum.append(self._del_attrib(e))

    def _node_add_without_peer_container(self, node_sum, child_other):
        '''_node_add_without_peer_container

        Low-level api: Apply delta child_other to node_sum when there is no
        peer of child_other can be found under node_sum. child_other is a
        container node. Element node_sum will be modified during the process.

        Parameters
        ----------

        node_sum : `Element`
            A config node in a config tree.

        child_other : `Element`
            A child of a config node in another config tree. This child has no
            peer under node_sum.

        Returns
        -------

        None
            There is no return of this method.
        '''

        this_operation = child_other.get(operation_tag, default='merge')
        if this_operation == 'merge':
            e = etree.SubElement(node_sum, child_other.tag,
                                 nsmap=child_other.nsmap)
            self.node_add(e, child_other)
        elif (
            this_operation == 'replace' or
            this_operation == 'create'
        ):
            node_sum.append(self._del_attrib(deepcopy(child_other)))

    def _node_add_without_peer_list(self, node_sum, child_other):
        '''_node_add_without_peer_list

        Low-level api: Apply delta child_other to node_sum when there is no
        peer of child_other can be found under node_sum. child_other is a list
        node. Element node_sum will be modified during the process.

        Parameters
        ----------

        node_sum : `Element`
            A config node in a config tree.

        child_other : `Element`
            A child of a config node in another config tree. This child has no
            peer under node_sum.

        Returns
        -------

        None
            There is no return of this method.
        '''

        s_node = self.device.get_schema_node(child_other)
        this_operation = child_other.get(operation_tag, default='merge')
        if this_operation == 'merge':
            e = etree.Element(child_other.tag, nsmap=child_other.nsmap)
            for list_key_tag in self._get_list_keys(s_node):
                key_ele_other = child_other.find(list_key_tag)
                key_ele_self = deepcopy(key_ele_other)
                e.append(self._del_attrib(key_ele_self))
        elif (
            this_operation == 'replace' or
            this_operation == 'create'
        ):
            e = self._del_attrib(deepcopy(child_other))
        scope = node_sum.getchildren()
        siblings = self._get_sequence(scope, child_other.tag, node_sum)
        if s_node.get('ordered-by') == 'user' and \
           child_other.get(insert_tag) is not None:
            if child_other.get(insert_tag) == 'first':
                if siblings:
                    siblings[0].addprevious(e)
                else:
                    node_sum.append(e)
            elif child_other.get(insert_tag) == 'last':
                if siblings:
                    siblings[-1].addnext(e)
                else:
                    node_sum.append(e)
            elif child_other.get(insert_tag) == 'before':
                if child_other.get(key_tag) is None:
                    _inserterror('before', self.device.get_xpath(child_other),
                                 'key')
                sibling = node_sum.find(child_other.tag +
                                        child_other.get(key_tag),
                                        namespaces=child_other.nsmap)
                if sibling is None:
                    path = self.device.get_xpath(child_other)
                    key = child_other.get(key_tag)
                    _inserterror('before', path, 'key', key)
                sibling.addprevious(e)
            elif child_other.get(insert_tag) == 'after':
                if child_other.get(key_tag) is None:
                    _inserterror('after', self.device.get_xpath(child_other),
                                 'key')
                sibling = node_sum.find(child_other.tag +
                                        child_other.get(key_tag),
                                        namespaces=child_other.nsmap)
                if sibling is None:
                    path = self.device.get_xpath(child_other)
                    key = child_other.get(key_tag)
                    _inserterror('after', path, 'key', key)
                sibling.addnext(e)
        else:
            if siblings:
                siblings[-1].addnext(e)
            else:
                node_sum.append(e)
        if this_operation == 'merge':
            self.node_add(e, child_other)

    def _node_add_with_peer_leaf(self, child_self, child_other):
        '''_node_add_with_peer_leaf

        Low-level api: Apply delta child_other to child_self when child_self is
        the peer of child_other. Element child_self and child_other are leaf
        nodes. Element child_self will be modified during the process. RFC6020
        section 7.6.7 is a reference of this method.

        Parameters
        ----------

        child_self : `Element`
            A child of a config node in a config tree.

        child_other : `Element`
            A child of a config node in another config tree. child_self is
            the peer of child_other.

        Returns
        -------

        None
            There is no return of this method.
        '''

        this_operation = child_other.get(operation_tag, default='merge')
        if this_operation == 'merge':
            self._merge_text(child_other, child_self)
        elif this_operation == 'replace':
            self._merge_text(child_other, child_self)
        elif this_operation == 'create':
            raise ConfigDeltaError('data-exists: try to create node {} but '
                                   'it already exists'
                                   .format(self.device.get_xpath(child_other)))
        elif (
            this_operation == 'delete' or
            this_operation == 'remove'
        ):
            parent_self = child_self.getparent()
            parent_self.remove(child_self)
        else:
            raise ConfigDeltaError("unknown operation: node {} contains "
                                   "operation '{}'"
                                   .format(self.device.get_xpath(child_other),
                                           this_operation))

    def _node_add_with_peer_leaflist(self, child_self, child_other):
        '''_node_add_with_peer_leaflist

        Low-level api: Apply delta child_other to child_self when child_self is
        the peer of child_other. Element child_self and child_other are
        leaf-list nodes. Element child_self will be modified during the
        process. RFC6020 section 7.7.7 is a reference of this method.

        Parameters
        ----------

        child_self : `Element`
            A child of a config node in a config tree.

        child_other : `Element`
            A child of a config node in another config tree. child_self is
            the peer of child_other.

        Returns
        -------

        None
            There is no return of this method.
        '''

        parent_self = child_self.getparent()
        s_node = self.device.get_schema_node(child_self)
        this_operation = child_other.get(operation_tag, default='merge')
        if this_operation == 'merge' or \
           this_operation == 'replace':
            if s_node.get('ordered-by') == 'user' and \
               child_other.get(insert_tag) is not None:
                if child_other.get(insert_tag) == 'first':
                    scope = parent_self.getchildren()
                    siblings = self._get_sequence(scope, child_other.tag,
                                                  parent_self)
                    if siblings[0] != child_self:
                        siblings[0].addprevious(child_self)
                elif child_other.get(insert_tag) == 'last':
                    scope = parent_self.getchildren()
                    siblings = self._get_sequence(scope, child_other.tag,
                                                  parent_self)
                    if siblings[-1] != child_self:
                        siblings[-1].addnext(child_self)
                elif child_other.get(insert_tag) == 'before':
                    if child_other.get(value_tag) is None:
                        _inserterror('before',
                                     self.device.get_xpath(child_other),
                                     'value')
                    siblings = parent_self.findall(child_other.tag)
                    sibling = [s for s in siblings
                               if s.text == child_other.get(value_tag)]
                    if not sibling:
                        path = self.device.get_xpath(child_other)
                        value = child_other.get(value_tag)
                        _inserterror('before', path, 'value', value)
                    if sibling[0] != child_self:
                        sibling[0].addprevious(child_self)
                elif child_other.get(insert_tag) == 'after':
                    if child_other.get(value_tag) is None:
                        _inserterror('after',
                                     self.device.get_xpath(child_other),
                                     'value')
                    siblings = parent_self.findall(child_other.tag)
                    sibling = [s for s in siblings
                               if s.text == child_other.get(value_tag)]
                    if not sibling:
                        path = self.device.get_xpath(child_other)
                        value = child_other.get(value_tag)
                        _inserterror('after', path, 'value', value)
                    if sibling[0] != child_self:
                        sibling[0].addnext(child_self)
        elif this_operation == 'create':
            raise ConfigDeltaError('data-exists: try to create node {} but '
                                   'it already exists'
                                   .format(self.device.get_xpath(child_other)))
        elif (
            this_operation == 'delete' or
            this_operation == 'remove'
        ):
            parent_self.remove(child_self)
        else:
            raise ConfigDeltaError("unknown operation: node {} contains "
                                   "operation '{}'"
                                   .format(self.device.get_xpath(child_other),
                                           this_operation))

    def _node_add_with_peer_container(self, child_self, child_other):
        '''_node_add_with_peer_container

        Low-level api: Apply delta child_other to child_self when child_self is
        the peer of child_other. Element child_self and child_other are
        container nodes. Element child_self will be modified during the
        process. RFC6020 section 7.5.8 is a reference of this method.

        Parameters
        ----------

        child_self : `Element`
            A child of a config node in a config tree.

        child_other : `Element`
            A child of a config node in another config tree. child_self is
            the peer of child_other.

        Returns
        -------

        None
            There is no return of this method.
        '''

        parent_self = child_self.getparent()
        this_operation = child_other.get(operation_tag, default='merge')
        if this_operation == 'merge':
            self.node_add(child_self, child_other)
        elif this_operation == 'replace':
            parent_self.replace(child_self,
                                self._del_attrib(deepcopy(child_other)))
        elif this_operation == 'create':
            raise ConfigDeltaError('data-exists: try to create node {} but '
                                   'it already exists'
                                   .format(self.device.get_xpath(child_other)))
        elif (
            this_operation == 'delete' or
            this_operation == 'remove'
        ):
            parent_self.remove(child_self)
        else:
            raise ConfigDeltaError("unknown operation: node {} contains "
                                   "operation '{}'"
                                   .format(self.device.get_xpath(child_other),
                                           this_operation))

    def _node_add_with_peer_list(self, child_self, child_other):
        '''_node_add_with_peer_list

        Low-level api: Apply delta child_other to child_self when child_self is
        the peer of child_other. Element child_self and child_other are list
        nodes. Element child_self will be modified during the process. RFC6020
        section 7.8.6 is a reference of this method.

        Parameters
        ----------

        child_self : `Element`
            A child of a config node in a config tree.

        child_other : `Element`
            A child of a config node in another config tree. child_self is
            the peer of child_other.

        Returns
        -------

        None
            There is no return of this method.
        '''

        parent_self = child_self.getparent()
        s_node = self.device.get_schema_node(child_self)
        this_operation = child_other.get(operation_tag, default='merge')
        if this_operation != 'delete' and \
           this_operation != 'remove' and \
           s_node.get('ordered-by') == 'user' and \
           child_other.get(insert_tag) is not None:
            if child_other.get(insert_tag) == 'first':
                scope = parent_self.getchildren()
                siblings = self._get_sequence(scope, child_other.tag,
                                              parent_self)
                if siblings[0] != child_self:
                    siblings[0].addprevious(child_self)
            elif child_other.get(insert_tag) == 'last':
                scope = parent_self.getchildren()
                siblings = self._get_sequence(scope, child_other.tag,
                                              parent_self)
                if siblings[-1] != child_self:
                    siblings[-1].addnext(child_self)
            elif child_other.get(insert_tag) == 'before':
                if child_other.get(key_tag) is None:
                    _inserterror('before', self.device.get_xpath(child_other),
                                 'key')
                sibling = parent_self.find(child_other.tag +
                                           child_other.get(key_tag),
                                           namespaces=child_other.nsmap)
                if sibling is None:
                    path = self.device.get_xpath(child_other)
                    key = child_other.get(key_tag)
                    _inserterror('before', path, 'key', key)
                if sibling != child_self:
                    sibling.addprevious(child_self)
            elif child_other.get(insert_tag) == 'after':
                if child_other.get(key_tag) is None:
                    _inserterror('after', self.device.get_xpath(child_other),
                                 'key')
                sibling = parent_self.find(child_other.tag +
                                           child_other.get(key_tag),
                                           namespaces=child_other.nsmap)
                if sibling is None:
                    path = self.device.get_xpath(child_other)
                    key = child_other.get(key_tag)
                    _inserterror('after', path, 'key', key)
                if sibling != child_self:
                    sibling.addnext(child_self)
        if this_operation == 'merge':
            self.node_add(child_self, child_other)
        elif this_operation == 'replace':
            parent_self.replace(child_self,
                                self._del_attrib(deepcopy(child_other)))
        elif this_operation == 'create':
            raise ConfigDeltaError('data-exists: try to create node {} but '
                                   'it already exists'
                                   .format(self.device.get_xpath(child_other)))
        elif (
            this_operation == 'delete' or
            this_operation == 'remove'
        ):
            parent_self.remove(child_self)
        else:
            raise ConfigDeltaError("unknown operation: node {} contains "
                                   "operation '{}'"
                                   .format(self.device.get_xpath(child_other),
                                           this_operation))

    def node_sub(self, node_self, node_other, depth=0):
        '''node_sub

        Low-level api: Compute the delta of two configs. This method is
        recursive. Assume two configs are different.

        Parameters
        ----------

        node_self : `Element`
            A config node in a config tree that is being processed. node_self
            cannot be a leaf node.

        node_other : `Element`
            A config node in another config tree that is being processed.

        depth : `int`
            Specify the current level of processing. In other words, how many
            hops from node_self to roots. Consider roots in a YANG module are
            level 0, their children are level 1, and so on so forth. The
            default value of depth is 0.

        Returns
        -------

        None
            There is no return of this method.
        '''

        if self.preferred_replace != 'merge':
            t_self = [
                c.tag for c in list(node_self)
                if self.device.get_schema_node(c).get('type') == 'leaf-list'
            ]
            t_other = [
                c.tag for c in list(node_other)
                if self.device.get_schema_node(c).get('type') == 'leaf-list'
            ]
            commonalities = set(t_self) & set(t_other)
            for commonality in commonalities:
                if not self._same_leaf_list(commonality,
                                            node_self,
                                            node_other):
                    node_self.set(operation_tag, 'replace')
                    node_other.set(operation_tag, 'replace')
                    return

        in_s_not_in_o, in_o_not_in_s, in_s_and_in_o = \
            self._group_kids(node_self, node_other)
        ordered_by_user = {}
        choice_nodes = {}
        for child_self in in_s_not_in_o:
            child_other = etree.Element(child_self.tag,
                                        {operation_tag: self.preferred_delete},
                                        nsmap=child_self.nsmap)
            if self.diff_type == 'replace':
                child_self.set(operation_tag, 'replace')
            elif self.preferred_create == 'replace':
                child_self.set(operation_tag, self.preferred_create)
            elif self.preferred_create == 'create':
                self.set_create_operation(child_self)
            siblings = list(node_other.iterchildren(tag=child_self.tag))
            if siblings:
                siblings[-1].addnext(child_other)
            else:
                node_other.append(child_other)
            s_node = self.device.get_schema_node(child_self)
            if s_node.get('type') == 'leaf-list':
                if s_node.get('ordered-by') == 'user' and \
                   s_node.tag not in ordered_by_user:
                    ordered_by_user[s_node.tag] = 'leaf-list'
                self._merge_text(child_self, child_other)
            elif s_node.get('type') == 'list':
                keys = self._get_list_keys(s_node)
                if s_node.get('ordered-by') == 'user' and \
                   s_node.tag not in ordered_by_user:
                    ordered_by_user[s_node.tag] = keys
                for key in keys:
                    key_node = child_self.find(key)
                    e = etree.SubElement(
                        child_other, key, nsmap=key_node.nsmap)
                    e.text = key_node.text
            if s_node.getparent().get('type') == 'case':
                # key: choice node, value: case node
                choice_nodes[s_node.getparent().getparent()] = \
                    s_node.getparent()
        for child_other in in_o_not_in_s:
            child_self = etree.Element(child_other.tag,
                                       {operation_tag: self.preferred_delete},
                                       nsmap=child_other.nsmap)
            if self.preferred_create == 'replace':
                child_other.set(operation_tag, self.preferred_create)
            elif self.preferred_create == 'create':
                self.set_create_operation(child_other)
            siblings = list(node_self.iterchildren(tag=child_other.tag))
            s_node = self.device.get_schema_node(child_other)
            if siblings:
                siblings[-1].addnext(child_self)
            else:
                # Append node if:
                # - Node not in case
                # - Node in case but choice node not in self
                # - Node in case and choice node in self and the same case also
                #   in self
                if s_node.getparent().get('type') == 'case':
                    choice_node = s_node.getparent().getparent()
                    if choice_node not in choice_nodes or \
                       s_node.getparent() == choice_nodes[choice_node]:
                        node_self.append(child_self)
                else:
                    node_self.append(child_self)
            if s_node.get('type') == 'leaf-list':
                if s_node.get('ordered-by') == 'user' and \
                   s_node.tag not in ordered_by_user:
                    ordered_by_user[s_node.tag] = 'leaf-list'
                self._merge_text(child_other, child_self)
            elif s_node.get('type') == 'list':
                keys = self._get_list_keys(s_node)
                if s_node.get('ordered-by') == 'user' and \
                   s_node.tag not in ordered_by_user:
                    ordered_by_user[s_node.tag] = keys
                for key in keys:
                    key_node = child_other.find(key)
                    e = etree.SubElement(child_self, key, nsmap=key_node.nsmap)
                    e.text = key_node.text
        for child_self, child_other in in_s_and_in_o:
            s_node = self.device.get_schema_node(child_self)
            if s_node.get('type') == 'leaf':
                if self._same_text(child_self, child_other):
                    if not s_node.get('is_key'):
                        node_self.remove(child_self)
                        node_other.remove(child_other)
                else:
                    if self.preferred_replace != 'merge':
                        child_self.set(operation_tag, self.preferred_replace)
                        child_other.set(operation_tag, self.preferred_replace)
            elif s_node.get('type') == 'leaf-list':
                if s_node.get('ordered-by') == 'user':
                    if s_node.tag not in ordered_by_user:
                        ordered_by_user[s_node.tag] = 'leaf-list'
                else:
                    node_self.remove(child_self)
                    node_other.remove(child_other)
            elif s_node.get('type') == 'container':
                if self._node_le(child_self, child_other) and \
                   self._node_le(child_other, child_self):
                    node_self.remove(child_self)
                    node_other.remove(child_other)
                else:
                    if (
                        self.diff_type == 'replace' and
                        self.replace_depth == depth + 1
                    ):
                        self.get_config_replace(child_self, child_other)
                    else:
                        self.node_sub(child_self, child_other, depth=depth+1)
            elif s_node.get('type') == 'list':
                if s_node.get('ordered-by') == 'user' and \
                   s_node.tag not in ordered_by_user:
                    ordered_by_user[s_node.tag] = self._get_list_keys(s_node)
                if self._node_le(child_self, child_other) and \
                   self._node_le(child_other, child_self):
                    if s_node.get('ordered-by') == 'user':
                        for child in child_self.getchildren():
                            schema_node = self.device.get_schema_node(child)
                            if not schema_node.get('is_key'):
                                child_self.remove(child)
                        for child in child_other.getchildren():
                            schema_node = self.device.get_schema_node(child)
                            if not schema_node.get('is_key'):
                                child_other.remove(child)
                    else:
                        node_self.remove(child_self)
                        node_other.remove(child_other)
                else:
                    if (
                        self.diff_type == 'replace' and
                        self.replace_depth == depth + 1
                    ):
                        self.get_config_replace(child_self, child_other)
                    else:
                        self.node_sub(child_self, child_other, depth=depth+1)
            else:
                path = self.device.get_xpath(s_node)
                raise ModelError("unknown schema node type: type of node {}"
                                 "is '{}'".format(path, s_node.get('type')))
        for tag in ordered_by_user:
            scope_s = in_s_not_in_o + in_s_and_in_o
            scope_o = in_o_not_in_s + in_s_and_in_o
            for sequence in (
                self._get_sequence(scope_s, tag, node_self),
                self._get_sequence(scope_o, tag, node_other),
            ):
                for item in sequence:
                    # modifying the namespace mapping of a node is not possible
                    # in lxml. See https://bugs.launchpad.net/lxml/+bug/555602
                    # if 'yang' not in item.nsmap:
                    #     item.nsmap['yang'] = yang_url
                    i = sequence.index(item)
                    if i == 0:
                        item.set(insert_tag, 'first')
                    else:
                        item.set(insert_tag, 'after')
                        precursor = sequence[i - 1]
                        if ordered_by_user[tag] == 'leaf-list':
                            item.set(value_tag, precursor.text)
                        else:
                            keys = ordered_by_user[tag]
                            key_nodes = {k: precursor.find(k) for k in keys}
                            ids = {
                                k: self._url_to_prefix(n, k)
                                for k, n in key_nodes.items()
                            }
                            id_list = [
                                "[{}='{}']".format(ids[k], key_nodes[k].text)
                                for k in keys
                            ]
                            item.set(key_tag, ''.join(id_list))

    def set_create_operation(self, node):
        '''set_create_operation

        Low-level api: Set the `operation` attribute of a node to `create` when
        it is not already set. This method is used when the preferred_create is
        `create`.

        Parameters
        ----------

        node : `Element`
            A config node in a config tree.

        Returns
        -------

        None
            There is no return of this method.
        '''

        schema_node = self.device.get_schema_node(node)

        # Create operation on non-presence containers is not allowed as per
        # ConfD implementation although the expected behavior is ambiguous in
        # RFC7950. More discussion can be found in the Tail-F ticket PS-47089.
        if (
            schema_node.get('type') == 'container' and
            schema_node.get('presence') != 'true'
        ):
            for child in node:
                self.set_create_operation(child)
        else:
            node.set(operation_tag, 'create')

    @staticmethod
    def _url_to_prefix(node, id):
        '''_url_to_prefix

        Low-level api: Convert an identifier from `{namespace}tagname` notation
        to `prefix:tagname` notation by looking at nsmap of the node. If the
        identifier does not have a namespace, the identifier is simply returned
        without modification.

        Parameters
        ----------

        node : `Element`
            A config node. Its identifier will be converted.

        id : `str`
            Identifier in `{namespace}tagname` notation.

        Returns
        -------

        str
            Identifier in `prefix:tagname` notation.
        '''

        prefixes = {v: k for k, v in node.nsmap.items()}
        ret = re.search('^{(.+)}(.+)$', id)
        if ret:
            if ret.group(1) in prefixes:
                if prefixes[ret.group(1)] is None:
                    return ret.group(2)
                else:
                    return prefixes[ret.group(1)] + ':' + ret.group(2)
        return id

    def _same_leaf_list(self, leaf_list_tag, parent_node_1, parent_node_2):
        '''_same_leaf_list

        Low-level api: Return True when two leaf-list's that are identified by
        leaf_list_tag are same.

        Parameters
        ----------

        leaf_list_tag : `str`
            A config node. Its identifier will be converted.

        parent_node_1 : `Element`
            One parent node. One or multiple leaf-list nodes are its children.

        parent_node_2 : `Element`
            The other parent node. One or multiple leaf-list nodes are its
            children.

        Returns
        -------

        bool
            True when the leaf-list nodes under two parent nodes are same.
            Otherwise False.
        '''

        list_1 = [c for c in list(parent_node_1) if c.tag == leaf_list_tag]
        list_2 = [c for c in list(parent_node_2) if c.tag == leaf_list_tag]
        s_node = self.device.get_schema_node((list_1 + list_2)[0])
        if s_node.get('ordered-by') == 'user':
            if (
                [self._parse_text(i, s_node) for i in list_1] ==
                [self._parse_text(i, s_node) for i in list_2]
            ):
                return True
            else:
                return False
        else:
            if (
                set([self._parse_text(i, s_node) for i in list_1]) ==
                set([self._parse_text(i, s_node) for i in list_2])
            ):
                return True
            else:
                return False
