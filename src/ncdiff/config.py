import re
import time
import pprint
import logging
from lxml import etree
from copy import deepcopy
from ncclient import operations, xml_

from .model import ModelDiff
from .errors import ConfigError, ModelMissing, ModelIncompatible
from .netconf import NetconfParser, NetconfCalculator
from .composer import Composer
from .calculator import BaseCalculator

# create a logger for this module
logger = logging.getLogger(__name__)

nc_url = xml_.BASE_NS_1_0
yang_url = 'urn:ietf:params:xml:ns:yang:1'
config_tag = '{' + nc_url + '}config'
filter_tag = '{' + nc_url + '}filter'
operation_tag = '{' + nc_url + '}operation'
key_tag = '{' + yang_url + '}key'
value_tag = '{' + yang_url + '}value'
insert_tag = '{' + yang_url + '}insert'

def _cmperror(x, y):
    raise TypeError("can't compare '%s' to '%s'" % (
                    type(x).__name__, type(y).__name__))


class Config(object):
    '''Config

    Abstraction of a config state of a device.

    Attributes
    ----------
    device : `object`
        An instance of yang.ncdiff.ModelDevice, which represents a modeled
        device.

    ele : `Element`
        A lxml Element which contains the config.

    xml : `str`
        A string presentation of self.ele, not in pretty-print.

    ns : `dict`
        A dictionary of namespaces used by the config. Keys are prefixes and
        values are URLs.

    models : `list`
        A list of model names that self.roots belong to.

    roots : `dict`
        A dictionary of roots of self.ele. Dictionary keys are tags of roots in
        `{url}tagname` notation, and values are corresponding model names.
    '''

    def __init__(self, ncdevice, config=None, validate=True):
        '''
        __init__ instantiates a Config instance.
        '''

        self.device = ncdevice
        self.parser = None
        if config is None:
            self.ele = etree.Element(config_tag, nsmap={'nc': nc_url})
        elif isinstance(config, operations.rpc.RPCReply) or \
             isinstance(config, str) or \
             etree.iselement(config):
            self.parser = NetconfParser(self.device, config)
            self.ele = self.parser.ele
        elif isinstance(config, Config):
            self.ele = config.ele
        else:
            raise TypeError("argument 'config' must be None, XML string, " \
                            "or Element, but not '{}'" \
                            .format(type(config)))
        if validate:
            self.validate_config()

    def __repr__(self):
        return '<{}.{} {} at {}>'.format(self.__class__.__module__,
                                             self.__class__.__name__,
                                             self.ele.tag,
                                             hex(id(self)))

    def __str__(self):
        return etree.tostring(self.ele,
                              encoding='unicode',
                              pretty_print=True)

    def __bool__(self):
        d = Config(self.device, None, False)
        if self == d:
            return False
        else:
            return True

    def __add__(self, other):
        if isinstance(other, Config):
            if ConfigCompatibility(self, other).is_compatible:
                return Config(self.device,
                              NetconfCalculator(self.device,
                                                self.ele, other.ele).add, False)
        elif isinstance(other, ConfigDelta):
            if ConfigCompatibility(self, other).is_compatible:
                return Config(self.device,
                              NetconfCalculator(self.device,
                                                self.ele, other.nc).add, False)
        elif etree.iselement(other):
            return Config(self.device,
                          NetconfCalculator(self.device, self.ele, other).add, False)
        elif isinstance(other, Request):
            return Config(self.device,
                          RestconfCalculator(self.device, self.ele, other).add, False)
        elif isinstance(other, SetRequest):
            return Config(self.device,
                          gNMICalculator(self.device, self.ele, other).add, False)
        else:
            return NotImplemented

    def __sub__(self, other):
        if type(other) == Config:
            return ConfigDelta(config_src=other, config_dst=self)
        elif isinstance(other, ConfigDelta):
            return self.__add__(-other)
        else:
            return NotImplemented

    def __le__(self, other):
        if isinstance(other, Config):
            return BaseCalculator(self.device, self.ele, other.ele).le
        else:
            _cmperror(self, other)

    def __lt__(self, other):
        if isinstance(other, Config):
            return BaseCalculator(self.device, self.ele, other.ele).lt
        else:
            _cmperror(self, other)

    def __ge__(self, other):
        if isinstance(other, Config):
            return BaseCalculator(self.device, self.ele, other.ele).ge
        else:
            _cmperror(self, other)

    def __gt__(self, other):
        if isinstance(other, Config):
            return BaseCalculator(self.device, self.ele, other.ele).gt
        else:
            _cmperror(self, other)

    def __eq__(self, other):
        if isinstance(other, Config):
            return BaseCalculator(self.device, self.ele, other.ele).eq
        else:
            _cmperror(self, other)

    def __ne__(self, other):
        if isinstance(other, Config):
            return BaseCalculator(self.device, self.ele, other.ele).ne
        else:
            _cmperror(self, other)

    @property
    def xml(self):
        return etree.tostring(self.ele,
                              encoding='unicode',
                              pretty_print=False)

    @property
    def ns(self):
        return self.device._get_ns(self.ele)

    @property
    def models(self):
        return sorted(list(set([v for k, v in self.roots.items()])))

    @property
    def roots(self):
        roots = {}
        for child in self.ele.getchildren():
            if child.tag in self.device.roots:
                roots[child.tag] = self.device.roots[child.tag]
            else:
                ret = re.search('^{(.+)}(.+)$', child.tag)
                if not ret:
                    raise ConfigError("unknown root including URL '{}'" \
                                      .format(child.tag))
                url_to_name = {i[2]: i[0] for i in self.device.namespaces
                               if i[1] is not None}
                if ret.group(1) in url_to_name:
                    raise ModelMissing("please load model '{0}' by calling " \
                                       "method load_model('{0}') of device " \
                                       "{1}" \
                                       .format(url_to_name[ret.group(1)],
                                               self.device))
                else:
                    raise ConfigError("unknown model URL '{}'" \
                                      .format(ret.group(1)))
        return roots

    def get_schema_node(self, node):
        '''get_schema_node

        High-level api: Return schema node of a config node.

        Parameters
        ----------

        node : `Element`
            An Element node in config tree.

        Returns
        -------

        Element
            A schema node of the config node.
        '''

        return self.device.get_schema_node(node)

    def get_model_name(self, node):
        '''get_model_name

        High-level api: Return model name of a config node.

        Parameters
        ----------

        node : `Element`
            An Element node in config tree.

        Returns
        -------

        Element
            Model name the config node belongs to.
        '''

        return self.device.get_model_name(node)

    def validate_config(self):
        '''validate_config

        High-level api: Validate config against models. ConfigError is raised
        if the config has issues.

        Returns
        -------

        None
            There is no return of this method.

        Raises
        ------

        ConfigError
            If config contains error.
        '''

        self.roots
        for child in self.ele.getchildren():
            self._validate_node(child)

            # clean up empty NP containers
            child_schema_node = self.device.get_schema_node(child)
            if len(child) == 0 and \
               child_schema_node.get('type') == 'container' and \
               child_schema_node.get('presence') != 'true':
                self.ele.remove(child)

    def ns_help(self):
        '''ns_help

        High-level api: Print known namespaces to make writing xpath easier.

        Returns
        -------

        None
            There is no return of this method.
        '''

        pprint.pprint(self.ns)

    def xpath(self, *args, **kwargs):
        '''xpath

        High-level api: It is a wrapper of xpath method in lxml package. If
        namespaces is not given, self.ns is used by default.

        Returns
        -------

        boolean or float or str or list
            Refer to http://lxml.de/xpathxslt.html#xpath-return-values
        '''

        if 'namespaces' not in kwargs:
            kwargs['namespaces'] = {i[1]: i[2] for i in self.device.namespaces
                                    if i[1] is not None}
        return self.ele.xpath(*args, **kwargs)

    def filter(self, *args, **kwargs):
        '''filter

        High-level api: Filter the config using xpath method. If namespaces is
        not given, self.ns is used by default.

        Returns
        -------

        Config
            A new Config instance which has less content according to your
            filter xpath expression.
        '''

        ancestors = set()
        filtrates = set()
        config = type(self)(self.device,  deepcopy(self.ele))
        results = config.xpath(*args, **kwargs)
        if isinstance(results, list):
            for node in results:
                if etree.iselement(node):
                    ancestors |= set(list(node.iterancestors()))
                    filtrates.add(node)
            if filtrates:
                config._node_filter(config.ele, ancestors, filtrates)
            else:
                config.ele = etree.Element(config_tag, nsmap={'nc': nc_url})
        return config

    def _validate_node(self, node):
        '''_validate_node

        Low-level api: Validate one config node. This is a recursive method. An
        exception will be raised if validation fails.

        Parameters
        ----------

        node : `Element`
            An Element node in config tree.

        Returns
        -------

        None
            There is no return of this method.
        '''

        c = Composer(self.device, node)
        if c.schema_node is None:
            p = self.device.get_xpath(node, instance=False)
            raise ConfigError('schema node of the config node not ' \
                              'found: {}'.format(p))
        if c.schema_node.get('type') == 'list':
            for key in c.keys:
                if node.find(key) is None:
                    p = self.device.get_xpath(node, instance=False)
                    raise ConfigError("missing key '{}' of the config " \
                                      "node {}".format(key, p))
        for tag in operation_tag, insert_tag, value_tag, key_tag:
            if node.get(tag):
                raise ConfigError("the config node contains invalid " \
                                  "attribute '{}': {}" \
                                  .format(tag, self.device.get_xpath(node)))

        for child in node.getchildren():
            if len(child) > 0:
                self._validate_node(child)

            # clean up empty NP containers
            child_schema_node = self.device.get_schema_node(child)
            if child_schema_node is None:
                raise ConfigError("schema node of the config node {} cannot " \
                                  "be found:\n{}" \
                                  .format(self.device.get_xpath(child), self))
            if len(child) == 0 and \
               child_schema_node.get('type') == 'container' and \
               child_schema_node.get('presence') != 'true':
                node.remove(child)

    def _node_filter(self, node, ancestors, filtrates):
        '''_node_filter

        Low-level api: Remove unrelated nodes in config. This is a recursive
        method.

        Parameters
        ----------

        node : `Element`
            A node to be processed.

        ancestors : `list`
            A list of ancestors of filtrates.

        filtrates : `list`
            A list of filtrates which are result of xpath evaluation.

        Returns
        -------

        None
            There is no return of this method.
        '''

        if node in filtrates:
            return
        elif node in ancestors:
            if node.tag != config_tag:
                s_node = self.get_schema_node(node)
            if node.tag != config_tag and \
               s_node.get('type') == 'list':
                for child in node.getchildren():
                    s_node = self.get_schema_node(child)
                    if s_node.get('is_key') or child in filtrates:
                        continue
                    elif child in ancestors:
                        self._node_filter(child, ancestors, filtrates)
                    else:
                        node.remove(child)
            else:
                for child in node.getchildren():
                    if child in filtrates:
                        continue
                    elif child in ancestors:
                        self._node_filter(child, ancestors, filtrates)
                    else:
                        node.remove(child)
        else:
            node.getparent().remove(node)


class ConfigDelta(object):
    '''ConfigDelta

    Abstraction of a delta of two Config instances. This delta could be
    considered as a config state transition, from a source state to a
    destination state.

    Attributes
    ----------
    config_src : `Config`
        An instance of yang.ncdiff.Config, which is the source config state of
        a transition.

    config_dst : `Config`
        An instance of yang.ncdiff.Config, which is the destination config state
        of a transition.

    nc : `Element`
        A lxml Element which contains the delta. This attribute can be used by
        ncclient edit_config() directly. It is the Netconf presentation of a
        ConfigDelta instance.

    ns : `dict`
        A dictionary of namespaces used by the attribute 'nc'. Keys are prefixes
        and values are URLs.

    models : `list`
        A list of model names that self.roots belong to.

    roots : `dict`
        A dictionary of roots of self.nc. Dictionary keys are tags of roots in
        `{url}tagname` notation, and values are corresponding model names.

    preferred_create : `str`
        Preferred operation of creating a new element. Choice of 'merge',
        'create' or 'replace'.

    preferred_replace : `str`
        Preferred operation of replacing an existing element. Choice of
        'merge' or 'replace'.

    preferred_delete : `str`
        Preferred operation of deleting an existing element. Choice of
        'delete' or 'remove'.
    '''

    def __init__(self, config_src, config_dst=None, delta=None,
                 preferred_create='merge',
                 preferred_replace='merge',
                 preferred_delete='delete'):
        '''
        __init__ instantiates a ConfigDelta instance.
        '''

        if not isinstance(config_src, Config):
            raise TypeError("argument 'config_src' must be " \
                            "yang.ncdiff.Config, but not '{}'" \
                            .format(type(config_src)))
        if preferred_create in ['merge', 'create', 'replace']:
            self.preferred_create = preferred_create
        else:
            raise ValueError("only 'merge', 'create' or 'replace' are valid " \
                             "values of 'preferred_create'")
        if preferred_replace in ['merge', 'replace']:
            self.preferred_replace = preferred_replace
        else:
            raise ValueError("only 'merge' or 'replace' are valid " \
                             "values of 'preferred_replace'")
        if preferred_delete in ['delete', 'remove']:
            self.preferred_delete = preferred_delete
        else:
            raise ValueError("only 'delete' or 'remove' are valid " \
                             "values of 'preferred_delete'")
        self.config_src = config_src
        if delta is not None:
            if isinstance(delta, str) or etree.iselement(delta):
                delta = NetconfParser(self.device, delta).ele
            else:
                raise TypeError("argument 'delta' must be XML string, " \
                                "Element, but not '{}'" \
                                .format(type(delta)))
        if not isinstance(config_dst, Config) and config_dst is not None:
            raise TypeError("argument 'config_dst' must be " \
                            "yang.ncdiff.Config or None, but not '{}'" \
                            .format(type(config_dst)))
        self.config_dst = config_dst
        if self.config_dst is None and delta is None:
            self.config_dst = self.config_src
        if delta is not None:
            if self.config_dst is not None:
                logger.warning("argument 'config_dst' is ignored as 'delta' " \
                               "is provided")
            self.config_dst = self.config_src + delta
        else:
            ConfigCompatibility(self.config_src, self.config_dst).is_compatible

    @property
    def device(self):
        return self.config_src.device

    @property
    def nc(self):
        return NetconfCalculator(self.device,
                                 self.config_dst.ele, self.config_src.ele,
                                 preferred_create=self.preferred_create,
                                 preferred_replace=self.preferred_replace,
                                 preferred_delete=self.preferred_delete).sub

    @property
    def ns(self):
        return self.device._get_ns(self.nc)

    @property
    def models(self):
        return sorted(list(set(self.config_src.models + \
                               self.config_dst.models)))

    @property
    def roots(self):
        roots = {}
        roots.update(self.config_src.roots)
        roots.update(self.config_dst.roots)
        return roots

    def __str__(self):
        return etree.tostring(self.nc, encoding='unicode', pretty_print=True)

    def __neg__(self):
        return ConfigDelta(config_src=self.config_dst,
                           config_dst=self.config_src)

    def __pos__(self):
        return self

    def __bool__(self):
        if self.config_src == self.config_dst:
            return False
        else:
            return True

    def __add__(self, other):
        if isinstance(other, Config):
            return other + self.nc

    def __sub__(self, other):
        return NotImplemented

    def __lt__(self, other):
        _cmperror(self, other)

    def __gt__(self, other):
        _cmperror(self, other)

    def __le__(self, other):
        _cmperror(self, other)

    def __ge__(self, other):
        _cmperror(self, other)

    def __eq__(self, other):
        _cmperror(self, other)

    def __ne__(self, other):
        _cmperror(self, other)


class ConfigCompatibility(object):
    '''ConfigCompatibility

    A class to check model compatibility between two Config instances. The
    prerequisite of calculating ConfigDelta is that two instances of Config are
    based on same model schema definations.

    Attributes
    ----------
    config1 : `object`
        An instance of Config.

    config2 : `Element`
        Another instance of Config.

    models : `list`
        A list of model names that are in self.config1 and self.config2.

    models_compatible : `str`
        True if all models in self.models are same in self.config1 as in
        self.config2.

    namespaces_compatible : `dict`
        True if all models in self.models have same prefix and URL in
        self.config1 as in self.config2.

    is_compatible : `dict`
        True if self.models_compatible is True and self.namespaces_compatible is
        True.
    '''

    def __init__(self, config1, config2):
        '''
        __init__ instantiates a ConfigCompatibility instance.
        '''

        self.config1 = config1
        self.config2 = config2

    @property
    def models(self):
        return sorted(list(set(self.config1.models + self.config2.models)))

    @property
    def models_compatible(self):

        def check_models(models):
            for device in [self.config1.device, self.config2.device]:
                missing_models = set(models) - set(device.models_loaded)
                if missing_models:
                    raise ModelMissing('please load model {} by calling ' \
                                       'method load_model() of device {}' \
                                       .format(str(list(missing_models))[1:-1],
                                               device))

        check_models(self.models)
        for model in self.models:
            diff = ModelDiff(self.config1.device.models[model],
                             self.config2.device.models[model])
            if diff:
                logger.debug(str(self))
                raise ModelIncompatible("model '{}' on device {} is " \
                                        "different from the one on device {}" \
                                        .format(model, self.config1.device,
                                                       self.config2.device))
        return True

    @property
    def namespaces_compatible(self):
        if self.config1.device == self.config2.device:
            return True

        def check_models(models):
            for device in [self.config1.device, self.config2.device]:
                missing_models = set(models) - set(device.models_loadable)
                if missing_models:
                    raise ModelMissing('model {} does not exist on device {}' \
                                       .format(str(list(missing_models))[1:-1],
                                               device))

        check_models(self.models)
        for model in self.models:
            prefix1 = [i[1] for i in self.config1.device.namespaces
                       if i[0] == model][0]
            prefix2 = [i[1] for i in self.config2.device.namespaces
                       if i[0] == model][0]
            if prefix1 != prefix2:
                raise ModelIncompatible("model '{}' uses prefix '{}' on " \
                                        "device {}, but uses prefix '{}' on " \
                                        "device {}" \
                                        .format(model,
                                                prefix1, self.config1.device,
                                                prefix2, self.config2.device))
            url1 = [i[2] for i in self.config1.device.namespaces
                    if i[0] == model][0]
            url2 = [i[2] for i in self.config2.device.namespaces
                    if i[0] == model][0]
            if url1 != url2:
                raise ModelIncompatible("model '{}' uses url '{}' on device " \
                                        "{}, but uses url '{}' on device {}" \
                                        .format(model,
                                                url1, self.config1.device,
                                                url2, self.config2.device))
        return True

    @property
    def is_compatible(self):
        return self.namespaces_compatible and self.models_compatible
