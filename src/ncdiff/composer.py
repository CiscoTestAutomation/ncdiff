import re
import json
import logging
from lxml import etree
from ncclient import xml_
from xml.etree import ElementTree

from .errors import ModelMissing

# create a logger for this module
logger = logging.getLogger(__name__)

config_tag = '{' + xml_.BASE_NS_1_0 + '}config'

class Tag(object):
    '''Tag

    A set of constants to define common notations of a node tag.
    '''

    NAME = 0
    PREFIX = 1
    NAMESPACE = 2

    STR = {}
    STR[NAME] = 'module name'
    STR[PREFIX] = 'module prefix'
    STR[NAMESPACE] = 'module URL'

    NO_OMIT = 10
    OMIT_BY_INHERITANCE = 11
    OMIT_BY_MODULE = 12

    # {namespace}tagname
    BRACE = ['^{(.+)}(.+)$', '{{{}}}{}']
    # namespace:tagname
    COLON = ['^(.+):(.+)$', '{}:{}']

    YTOOL = (PREFIX, OMIT_BY_MODULE, COLON)
    XPATH = (PREFIX, OMIT_BY_INHERITANCE, COLON)
    LXML_XPATH = (PREFIX, NO_OMIT, COLON)
    LXML_ETREE = (NAMESPACE, NO_OMIT, BRACE)
    JSON_NAME = (NAME, OMIT_BY_INHERITANCE, COLON)
    JSON_PREFIX = (PREFIX, OMIT_BY_INHERITANCE, COLON)


class Composer(object):
    '''Composer

    A base composer class, which is inherited by protocol composer classes, for
    example: RestconfComposer and gNMIComposer.

    Attributes
    ----------
    device : `object`
        An instance of yang.ncdiff.ModelDevice, which represents a modeled
        device.

    node : `Element`
        A config node or a schema node.

    path : `list`
        A list of ancestors, starting from the root of self.node.

    model_name : `str`
        Model name that self.node belongs to.

    model_ns : `str`
        Model URL that the root of self.node belongs to.

    is_config : `bool`
        True if self.node is a config node, False if self.node is a schema node.

    schema_node : `Element`
        Coresponding model schema node of self.node if self.node is a config
        node.

    keys : `Element`
        A list of key tags if self.node is type `list`.
    '''

    def __init__(self, device, node):
        '''
        __init__ instantiates a Composer instance.
        '''

        self.device = device
        self.node = node
        self._schema_node = None

    @property
    def path(self):
        path = list(reversed([a.tag for a in self.node.iterancestors()]))
        return path[1:] + [self.node.tag]

    @property
    def model_name(self):
        if self.path[0] in self.device.roots:
            return self.device.roots[self.path[0]]
        else:
            ret = re.search(Tag.BRACE[0], self.path[0])
            if ret:
                url_to_name = {i[2]: i[0] for i in self.device.namespaces
                               if i[1] is not None}
                if ret.group(1) in url_to_name:
                    raise ModelMissing("please load model '{}' by calling " \
                                       "method load_model() of device {}" \
                                       .format(url_to_name[ret.group(1)],
                                               self.device))
                else:
                    raise ModelMissing("unknown model url '{}'" \
                                       .format(ret.group(1)))
            else:
                raise ModelMissing("unknown model root '{}'" \
                                   .format(self.path[0]))

    @property
    def model_ns(self):
        return self.device.models[self.model_name].url

    @property
    def is_config(self):
        root = list(self.node.iterancestors())[-1]
        if root.tag == config_tag:
            return True
        else:
            return False

    @property
    def schema_node(self):
        if self._schema_node is None:
            if self.is_config:
                self._schema_node = self.device.get_schema_node(self.node)
            else:
                self._schema_node = self.node
        return self._schema_node

    @property
    def keys(self):
        if self.schema_node.get('type') == 'list':
            nodes = list(filter(lambda x: x.get('is_key'),
                                self.schema_node.getchildren()))
            return [n.tag for n in nodes]
        else:
            return []

    def get_xpath(self, type, instance=True):
        '''get_xpath

        High-level api: Delete four attributes from an Element node if they
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

        """
        This is the lxml xpath format
        This is the YTool xpath format
        >>> assert(schema_path == 'openconfig-interfaces/interfaces/'
                          'interface/oc-eth:ethernet/'
                          'oc-eth:config/oc-eth:port-speed')
        """

        def convert(default_ns, nodes, type):
            ret = ''
            for index, node in enumerate(nodes):
                default_ns, id = self.device.convert_tag(default_ns, node.tag,
                                                         dst=type)
                ret += '/' + id
                if self.is_config and type != Tag.YTOOL:
                    n = Composer(self.device, node)
                    if n.schema_node is not None:
                        if n.schema_node.get('type') == 'leaf-list' and \
                           not (index == len(nodes)-1 and not instance):
                            ret += '[text()="{}"]'.format(node.text)
                        elif n.schema_node.get('type') == 'list' and \
                             not (index == len(nodes)-1 and not instance):
                            for key in n.keys:
                                id = self.device.convert_tag(default_ns, key,
                                                             dst=type)[1]
                                ret += '[{}="{}"]'.format(id,
                                                          node.find(key).text)
            return ret

        nodes = list(reversed(list(self.node.iterancestors())))[1:] + \
                [self.node]
        if type == Tag.YTOOL:
            return self.model_name + convert(self.model_ns, nodes, type)
        else:
            return convert('', nodes, type)
