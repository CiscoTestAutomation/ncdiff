"""ncdiff module defines a set of classes that calculate diff of two
configs, and predict config when a diff is applied on a config. A config is the
payload of a Netconf get-config reply, and a diff is the payload of a
edit-config message."""

# metadata
__version__ = '20.5.1b0'
__author__ = 'Jonathan Yang <yuekyang@cisco.com>'
__contact__ = 'yang-python@cisco.com'
__copyright__ = 'Cisco Systems, Inc.'

# __import__('pkg_resources').declare_namespace(__name__)

import pprint
from lxml import etree
from ncclient import operations, transport
from collections import OrderedDict

from .model import Model, ModelDownloader, ModelCompiler, ModelDiff
from .config import Config, ConfigDelta
from .manager import ModelDevice
from .composer import Tag
from .runningconfig import RunningConfigDiff

def _repr_rpcreply(self):
    return '<{}.{} {} at {}>'.format(self.__class__.__module__,
                                     self.__class__.__name__,
                                     self._root.tag,
                                     hex(id(self)))

def _repr_notification(self):
    return '<{}.{} {} at {}>'.format(self.__class__.__module__,
                                     self.__class__.__name__,
                                     self._root_ele.tag,
                                     hex(id(self)))

def _str_rpcreply(self):
    self.parse()
    xml_str = etree.tostring(self._root, encoding='unicode')
    xml_ele = etree.XML(xml_str, etree.XMLParser(remove_blank_text=True))
    return etree.tostring(xml_ele, encoding='unicode', pretty_print=True)

def _str_notification(self):
    xml_str = etree.tostring(self._root_ele, encoding='unicode')
    xml_ele = etree.XML(xml_str, etree.XMLParser(remove_blank_text=True))
    return etree.tostring(xml_ele, encoding='unicode', pretty_print=True)

def _str_response(self):
    http_versions = {10: 'HTTP/1.0', 11: 'HTTP/1.1'}
    ret = '{} {}'.format(self.status_code, self.reason)
    if self.raw.version in http_versions:
        ret = http_versions[self.raw.version] + ' ' + ret
    for k, v in self.headers.items():
        ret += '\n{}: {}'.format(k, v)
    if self.text:
        ret += '\n\n' + self.text
    return ret

def xpath_rpcreply(self, *args, **kwargs):
    if 'namespaces' not in kwargs:
        kwargs['namespaces'] = self.ns
        return self._root.xpath(*args, **kwargs)
    else:
        return self._root.xpath(*args, **kwargs)

def xpath_notification(self, *args, **kwargs):
    if 'namespaces' not in kwargs:
        kwargs['namespaces'] = self.ns
        return self._root_ele.xpath(*args, **kwargs)
    else:
        return self._root_ele.xpath(*args, **kwargs)

def ns_help(self):
    pprint.pprint(self.ns)

operations.rpc.RPCReply.__repr__ = _repr_rpcreply
operations.rpc.RPCReply.__str__ = _str_rpcreply
operations.rpc.RPCReply.xpath = xpath_rpcreply
operations.rpc.RPCReply.ns_help = ns_help

if getattr(transport, 'notify', None):
    transport.notify.Notification.__repr__ = _repr_notification
    transport.notify.Notification.__str__ = _str_notification
    transport.notify.Notification.xpath = xpath_notification
    transport.notify.Notification.ns_help = ns_help

# below is a workaround of the bug in lxml:
# https://bugs.launchpad.net/lxml/+bug/1424232
def _append(self, element):
    def recreate(parent_src, parent_dst):
        for child_src in parent_src:
            child_dst = etree.SubElement(parent_dst,
                                         child_src.tag,
                                         attrib=child_src.attrib,
                                         nsmap=child_src.nsmap)
            child_dst.text = child_src.text
            if len(child_src) > 0:
                recreate(child_src, child_dst)

    child = etree.SubElement(self,
                             element.tag,
                             attrib=element.attrib,
                             nsmap=element.nsmap)
    child.text = element.text
    if len(element) > 0:
        recreate(element, child)

from ncclient.xml_ import new_ele, sub_ele, validated_element, qualify, to_xml

def request(self, config, format='xml', target='candidate', default_operation=None,
        test_option=None, error_option=None):
    """Loads all or part of the specified *config* to the *target* configuration datastore.
    *target* is the name of the configuration datastore being edited
    *config* is the configuration, which must be rooted in the `config` element. It can be specified either as a string or an :class:`~xml.etree.ElementTree.Element`.
    *default_operation* if specified must be one of { `"merge"`, `"replace"`, or `"none"` }
    *test_option* if specified must be one of { `"test_then_set"`, `"set"` }
    *error_option* if specified must be one of { `"stop-on-error"`, `"continue-on-error"`, `"rollback-on-error"` }
    The `"rollback-on-error"` *error_option* depends on the `:rollback-on-error` capability.
    """
    node = new_ele("edit-config")
    # node.append(util.datastore_or_url("target", target, self._assert))
    node.append(operations.util.datastore_or_url("target", target, self._assert))
    if error_option is not None:
        if error_option == "rollback-on-error":
            self._assert(":rollback-on-error")
        sub_ele(node, "error-option").text = error_option
    if test_option is not None:
        self._assert(':validate')
        sub_ele(node, "test-option").text = test_option
    if default_operation is not None:
    # TODO: check if it is a valid default-operation
        sub_ele(node, "default-operation").text = default_operation
# <<<<<<< HEAD
#         node.append(validated_element(config, ("config", qualify("config"))))
# =======
    if format == 'xml':
        # node.append(validated_element(config, ("config", qualify("config"))))
        _append(node, validated_element(config, ("config", qualify("config"))))
    if format == 'text':
        config_text = sub_ele(node, "config-text")
        sub_ele(config_text, "configuration-text").text = config
# >>>>>>> juniper
    return self._request(node)

def _wrap(self, subele):
    # internal use
    ele = new_ele("rpc", {"message-id": self._id},
                  **self._device_handler.get_xml_extra_prefix_kwargs())
    # ele.append(subele)
    _append(ele, subele)
    #print to_xml(ele)
    return to_xml(ele)

operations.edit.EditConfig.request = request
operations.rpc.RPC._wrap = _wrap
