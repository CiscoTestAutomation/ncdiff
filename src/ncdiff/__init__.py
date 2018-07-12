"""ncdiff module defines a set of classes that calculate diff of two
configs, and predict config when a diff is applied on a config. A config is the
payload of a Netconf get-config reply, and a diff is the payload of a
edit-config message."""

# metadata
__version__ = '2.0.2'
__author__ = 'Jonathan Yang <yuekyang@cisco.com>'
__contact__ = 'yang-python@cisco.com'
__copyright__ = 'Cisco Systems, Inc. Cisco Confidential'

# __import__('pkg_resources').declare_namespace(__name__)

import json
import pprint
import requests
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

def _str_request(self):
    ret = '{} {}'.format(self.method, self.url)
    headers = {k.lower(): v.lower() for k, v in self.headers.items()}
    if 'content-type' in headers:
        ret += '\nContent-Type: {}'.format(headers['content-type'])
        if self.method in ['POST', 'PUT', 'PATCH']:
            if headers['content-type'] == 'application/yang-data+json':
                d = json.loads(self.data, object_pairs_hook=OrderedDict)
                ret += '\n\n{}'.format(json.dumps(d, indent=2))
            if headers['content-type'] == 'application/yang-data+xml':
                e = etree.XML(self.data,
                              etree.XMLParser(remove_blank_text=True))
                ret += '\n\n{}'.format(etree.tostring(e, encoding='unicode',
                                                      pretty_print=True))
    return ret

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

requests.Request.__str__ = _str_request
requests.Response.__str__ = _str_response
