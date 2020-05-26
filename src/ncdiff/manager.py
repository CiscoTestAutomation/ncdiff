import os
import re
from functools import lru_cache

import six
import logging
from lxml import etree
from copy import deepcopy
from ncclient import manager, operations, transport, xml_
from ncclient.devices.default import DefaultDeviceHandler

from .model import Model, ModelDownloader, ModelCompiler
from .config import Config
from .errors import ModelError, ModelMissing, ConfigError
from .composer import Tag, Composer

# create a logger for this module
logger = logging.getLogger(__name__)

nc_url = xml_.BASE_NS_1_0
yang_url = 'urn:ietf:params:xml:ns:yang:1'
tailf_url= 'http://tail-f.com/ns/netconf/params/1.1'
ncEvent_url = xml_.NETCONF_NOTIFICATION_NS
config_tag = '{' + nc_url + '}config'
filter_tag = '{' + nc_url + '}filter'
special_prefixes = {
    nc_url: 'nc',
    yang_url: 'yang',
    tailf_url: 'tailf',
    ncEvent_url: 'ncEvent',
    }


def connect(*args, **kwargs):
    """
    Initialize a :class:`ModelDevice` over the SSH transport.
    For documentation of arguments see :meth:`ncclient.transport.SSHSession.connect`.
    The underlying :class:`ncclient.transport.SSHSession` is created with
        :data:`CAPABILITIES`. It is first instructed to
        :meth:`~ncclient.transport.SSHSession.load_known_hosts` and then
        all the provided arguments are passed directly to its implementation
        of :meth:`~ncclient.transport.SSHSession.connect`.
    """

    device_handler = DefaultDeviceHandler()
    session = transport.SSHSession(device_handler)
    if "hostkey_verify" not in kwargs or kwargs["hostkey_verify"]:
        session.load_known_hosts()

    try:
       session.connect(*args, **kwargs)
    except Exception as ex:
        if session.transport:
            session.close()
        raise
    return ModelDevice(session, device_handler, **kwargs)


class ModelDevice(manager.Manager):
    '''ModelDevice

    Abstraction of a device that supports NetConf protocol and YANG models.
    This is a subclass of yang.connector.Netconf with some enhancements.

    Attributes
    ----------
    namespaces : `list`
        A list of tuples. Each tuple has three elements: model name, model
        prefix, and model URL. This attribute is only available after
        scan_models() is called.

    models_loadable : `list`
        A list of models this ModelDevice instance supports. The information is
        retrived from attribute server_capabilities.

    models_loaded : `list`
        A list of models this ModelDevice instance has loaded. Loading a model
        means the ModelDevice instance has obtained schema infomation of the
        model.

    compiler : `ModelCompiler`
        An instance of ModelCompiler.

    models : `dict`
        A dictionary of loaded models. Dictionary keys are model names, and
        values are Model instances.

    roots : `dict`
        A dictionary of roots in loaded models. Dictionary keys are roots in
        `{url}tagname` notation, and values are model names.
    '''

    def __init__(self, session, device_handler, *args, **kwargs):
        '''
        __init__ instantiates a ModelDevice instance.
        '''

        manager.Manager.__init__(self, session = session,
                                       device_handler = device_handler)

        supported_args = ['timeout', 'async_mode' , 'raise_mode']
        for arg in supported_args:
            if arg in kwargs:
                setattr(self, kwarg, kwargs[arg])

        self.models = {}
        self.nodes = {}
        self.compiler = None
        self._models_loadable = None

    def __repr__(self):
        return '<{}.{} object at {}>'.format(self.__class__.__module__,
                                             self.__class__.__name__,
                                             hex(id(self)))

    @property
    @lru_cache(maxsize=1)
    # extremely expensive call, cache
    def namespaces(self):
        if self.compiler is None:
            raise ValueError('please first call scan_models() to build ' \
                             'up supported namespaces of a device')
        else:
            device_namespaces = []
            for m in self.compiler.dependencies.findall('./module'):
                device_namespaces.append((m.get('id'),
                                          m.get('prefix'),
                                          m.findtext('namespace')))
            return device_namespaces

    @property
    def models_loadable(self):
        if self._models_loadable is None:
            NC_MONITORING = xml_.NETCONF_MONITORING_NS
            YANG_LIB = 'urn:ietf:params:netconf:capability:yang-library'
            YANG_LIB_1_0 = YANG_LIB + ':1.0'
            NC_MONITORING_FILTER = """
                <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" type="subtree">
                  <netconf-state xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring">
                    <schemas/>
                  </netconf-state>
                </filter>
                """
            YANG_LIB_FILTER = """
                <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" type="subtree">
                  <modules-state xmlns="urn:ietf:params:xml:ns:yang:ietf-yang-library">
                    <module/>
                  </modules-state>
                </filter>
                """
            # RFC7895
            if [c for c in self.server_capabilities
                  if c[:len(NC_MONITORING)] == NC_MONITORING]:
                reply = super().execute(operations.retrieve.Get,
                                        filter=NC_MONITORING_FILTER)
                if not reply.ok:
                    raise ModelError("Error when getting " \
                                     "/netconf-state/schemas from YANG " \
                                     "module 'ietf-netconf-monitoring':\n{}" \
                                     .format(reply))
                n = {'nc': nc_url, 'ncm': NC_MONITORING}
                p = '/nc:rpc-reply/nc:data/ncm:netconf-state/ncm:schemas' \
                    '/ncm:schema/ncm:identifier'
                self._models_loadable = \
                    sorted([n.text for n in reply.data.xpath(p, namespaces=n)])
            # RFC7950 section 5.6.4
            elif [c for c in self.server_capabilities
                    if c[:len(YANG_LIB_1_0)] == YANG_LIB_1_0]:
                reply = super().execute(operations.retrieve.Get,
                                        filter=YANG_LIB_FILTER)
                if not reply.ok:
                    raise ModelError("Error when getting " \
                                     "/modules-state/module from YANG " \
                                     "module 'ietf-yang-library':\n{}" \
                                     .format(reply))
                n = {'nc': nc_url, 'yanglib': YANG_LIB}
                p = '/nc:rpc-reply/nc:data/yanglib:modules-state' \
                    '/yanglib:module/yanglib:name'
                self._models_loadable = \
                    sorted([n.text for n in reply.data.xpath(p, namespaces=n)])
            # RFC6020 section 5.6.4
            else:
                regexp_str = 'module=([a-zA-Z0-9-]+)\&{0,1}'
                modules = []
                for capability in iter(self.server_capabilities):
                    match = re.search(regexp_str, capability)
                    if match:
                        modules.append(match.group(1))
                self._models_loadable = sorted(modules)
        return self._models_loadable

    @property
    def models_loaded(self):
        return sorted(self.models.keys())

    @property
    def roots(self):
        roots = {}
        for model in self.models.values():
            roots.update({r: model.name for r in model.roots})
        return roots

    def scan_models(self, folder='./yang', download='check'):
        '''scan_models

        High-level api: Download models from the device by <get-schema>
        operation defined in RFC6022, and analyze dependencies among models
        using pyang package.

        Parameters
        ----------

        folder : `str`
            A path to a folder that stores YANG files downloaded.

        download : `str`
            A string is either `check` or `force`. If it is `check`, the content
            in the folder is compared with self.server_capabilities. Downloading
            will be skipped if the checking says good. If it is `force`,
            downloading starts without checking.

        Returns
        -------

        None
            Nothing returns.


        Code Example::

            >>> m = manager.connect(host='2.3.4.5', port=830,
                                    username='admin', password='admin',
                                    hostkey_verify=False, look_for_keys=False)
            >>> m.scan_models()
            ...
            >>>
        '''

        d = ModelDownloader(self, folder)
        if download == 'force':
            d.download_all(check_before_download=False)
        elif download == 'check':
            d.download_all(check_before_download=True)
        self.compiler = ModelCompiler(folder)

    def load_model(self, model):
        '''load_model

        High-level api: Load schema information by compiling the model using
        pyang package.

        Parameters
        ----------

        model : `str`
            Model name.

        Returns
        -------

        Model
            An instance of Model.


        Code Example::

            >>> m = manager.connect(host='2.3.4.5', port=830,
                                    username='admin', password='admin',
                                    hostkey_verify=False, look_for_keys=False)
            >>> m.scan_models()
            >>>
            >>> m1 = m.load_model('openconfig-system')
            >>> print(m1)
            ...
            >>>
        '''

        if os.path.isfile(model):
            file_name, file_ext = os.path.splitext(model)
            if file_ext.lower() == '.xml':
                logger.debug('Read model file {}'.format(model))
                with open(model, 'r') as f:
                    xml = f.read()
                parser = etree.XMLParser(remove_blank_text=True)
                tree = etree.XML(xml, parser)
            else:
                raise ValueError("'{}' is not a file with extension 'xml'" \
                                 .format(model))
        elif model in self.models_loadable:
            if self.compiler is None:
                raise ValueError('please first call scan_models() to build ' \
                                 'up supported namespaces of a device')
            else:
                m = self.compiler.compile(model)
        else:
            raise ValueError("argument 'model' {} needs to be either a model " \
                             "name or a compiled model xml file".format(model))
        if m.name in self.models:
            self.nodes = {k: v for k, v in self.nodes.items()
                          if self.roots[k.split(' ')[0]] != m.name}
            logger.info('Model {} is reloaded'.format(m.name))
        else:
            logger.info('Model {} is loaded'.format(m.name))
        self.models[m.name] = m
        return m

    def execute(self, operation, *args, **kwargs):
        '''execute

        High-level api: Supported operations are get, get_config, get_schema,
        dispatch, edit_config, copy_config, validate, commit, discard_changes,
        delete_config, lock, unlock, close_session, kill_session,
        poweroff_machine and reboot_machine. Since ModelDevice is a subclass of
        manager in ncclient package, any method supported by ncclient is
        available here. Refer to ncclient document for more details.
        '''

        def pop_models():
            models = kwargs.pop('models', None)
            if models is None:
                return None
            else:
                if isinstance(models, str):
                    return [models]
                else:
                    return models

        def check_models(models):
            missing_models = set(models) - set(self.models_loaded)
            if missing_models:
                raise ModelMissing('please load model {} by calling ' \
                                   'method load_model() of device {}' \
                                   .format(str(list(missing_models))[1:-1],
                                           self))

        def build_filter(models, roots):
            if 'filter' in kwargs:
                logger.warning("argument 'filter' is ignored as argument "
                               "'models' is specified")
            if isinstance(models, str):
                models = [models]
            check_models(models)
            filter_ele = etree.Element(filter_tag, type='subtree')
            for root in roots:
                etree.SubElement(filter_ele, root)
            filter_xml = etree.tostring(filter_ele,
                                        encoding='unicode',
                                        pretty_print=False)
            logger.debug("argument 'filter' is set to '{}'".format(filter_xml))
            return filter_ele

        def get_access_type(model_name, root):
            check_models([model_name])
            node = list(self.models[model_name].tree.iterchildren(tag=root))[0]
            return node.get('access')

        # allow for operation string type
        if type(operation) is str:
            try:
                cls = manager.OPERATIONS[operation]
            except KeyError:
                supported_operations = list(manager.OPERATIONS.keys())
                raise ValueError("supported operations are {}, but not '{}'" \
                                 .format(str(supported_operations)[1:-1],
                                         operation))
        else:
            cls = operation
        if cls == operations.retrieve.Get:
            models = pop_models()
            if models is not None:
                check_models(models)
                roots = [k for k, v in self.roots.items()
                         if v in models and
                            (get_access_type(v, k) == 'read-write' or
                             get_access_type(v, k) == 'read-only')]
                if not roots:
                    raise ValueError('no readable roots found in your ' \
                                     'models: {}'.format(str(models)[1:-1]))
                kwargs['filter'] = build_filter(models, roots)
        elif cls == operations.retrieve.GetConfig:
            if not args and 'source' not in kwargs:
                args = tuple(['running'])
            models = pop_models()
            if models is not None:
                check_models(models)
                roots = [k for k, v in self.roots.items()
                         if v in models and
                            get_access_type(v, k) == 'read-write']
                if not roots:
                    raise ValueError('no writable roots found in your ' \
                                     'models: {}'.format(str(models)[1:-1]))
                kwargs['filter'] = build_filter(models, roots)
        elif cls == operations.edit.EditConfig:
            if args and isinstance(args[0], Config):
                args_list = list(args)
                args_list[0] = args[0].ele
                args = tuple(args_list)
            if 'target' not in kwargs and \
               'urn:ietf:params:netconf:capability:candidate:1.0' not in \
               self.server_capabilities and \
               'urn:ietf:params:netconf:capability:writable-running:1.0' in \
               self.server_capabilities:
                kwargs['target'] = 'running'
        reply = super().execute(cls, *args, **kwargs)
        if isinstance(reply, operations.rpc.RPCReply):
            reply.ns = self._get_ns(reply._root)
        if getattr(transport, 'notify', None) and \
           isinstance(reply, transport.notify.Notification):
            reply.ns = self._get_ns(reply._root_ele)
        return reply

    def take_notification(self, block=True, timeout=None):
        '''take_notification

        High-level api: Receive notification messages.

        Parameters
        ----------

        block : `bool`
            True if this is a blocking call.

        timeout : `int`
            Timeout value in seconds.

        Returns
        -------

        Notification
            An instance of Notification in ncclient package.


        Code Example::

            >>> reply = m.take_notification(block=True, timeout=60)
            >>> assert(reply.ok)
            >>> print(reply)
            >>>
        '''

        reply = super().take_notification(block=block, timeout=timeout)
        if isinstance(reply, operations.rpc.RPCReply):
            reply.ns = self._get_ns(reply._root)
        if getattr(transport, 'notify', None) and \
           isinstance(reply, transport.notify.Notification):
            reply.ns = self._get_ns(reply._root_ele)
        return reply

    def extract_config(self, reply, type='netconf'):
        '''extract_config

        High-level api: Extract config from a rpc-reply of get-config or get
        message.

        Parameters
        ----------

        reply : `RPCReply`
            An instance of RPCReply in ncclient package. It has to be a
            successful reply in order to extract config, since there is no
            config data in an errored reply.

        Returns
        -------

        Config
            An instance of Config, which represents a config state of the
            device.


        Code Example::

            >>> reply = m.get_config(models='openconfig-interfaces')
            >>> assert(reply.ok)
            >>> config1 = m.extract_config(reply)
            >>>
            >>> reply = m.get(models='openconfig-interfaces')
            >>> assert(reply.ok)
            >>> config2 = m.extract_config(reply)
            >>>
            >>> config1 == config2
            True
            >>>
        '''

        def remove_read_only(parent):
            for child in parent.getchildren():
                schema_node = self.get_schema_node(child)
                if schema_node.get('access') == 'read-only':
                    parent.remove(child)
                elif len(child) > 0:
                    remove_read_only(child)

        config = Config(self, reply)
        remove_read_only(config.ele)
        config.validate_config()
        return config

    def get_schema_node(self, config_node):
        '''get_schema_node

        High-level api: Given an Element node in config, get_schema_node returns
        a schema node (defined in RFC 6020), which is an Element node in the
        schema tree.

        Parameters
        ----------

        config_node : `Element`
            An Element node in config tree.

        Returns
        -------

        Element
            A schema node.

        Raises
        ------

        ModelError
            If identifier is not unique in a namespace.

        ConfigError
            when nothing can be found.


        Code Example::

            >>> m.load_model('openconfig-interfaces')
            >>> reply = m.get_config(models='openconfig-interfaces')
            >>> config = m.extract_config(reply)
            >>> print(config)
            ...
            >>> config.ns
            ...
            >>> config_nodes = config.xpath('/nc:config/oc-if:interfaces/oc-if:interface[oc-if:name="GigabitEthernet0/0"]')
            >>> config_node = config_nodes[0]
            >>>
            >>> m.get_schema_node(config_node)
            <Element {http://openconfig.net/yang/interfaces}interface at 0xf11acfcc>
            >>>
        '''

        def get_child(parent, tag):
            children = [i for i in parent.iter(tag=tag) \
                        if i.attrib['type'] != 'choice' and \
                           i.attrib['type'] != 'case' and \
                           is_parent(parent, i)]
            if len(children) == 1:
                return children[0]
            elif len(children) > 1:
                if parent.getparent() is None:
                    raise ModelError("more than one root has tag '{}'" \
                                     .format(tag))
                else:
                    raise ModelError("node {} has more than one child with " \
                                     "tag '{}'" \
                                     .format(self.get_xpath(parent), tag))
            else:
                return None

        def is_parent(node1, node2):
            ancestors = {id(a): a for a in node2.iterancestors()}
            ids_1 = set([id(a) for a in node1.iterancestors()])
            ids_2 = set([id(a) for a in node2.iterancestors()])
            if not ids_1 < ids_2:
                return False
            for i in ids_2 - ids_1:
                if ancestors[i] is not node1 and \
                   ancestors[i].attrib['type'] != 'choice' and \
                   ancestors[i].attrib['type'] != 'case':
                    return False
            return True

        n = Composer(self, config_node)
        path = n.path
        config_path_str = ' '.join(path)
        if config_path_str in self.nodes:
            return self.nodes[config_path_str]
        if len(path) > 1:
            parent = self.get_schema_node(config_node.getparent())
            child = get_child(parent, config_node.tag)
            if child is None:
                raise ConfigError("unable to locate a child '{}' of {} in " \
                                  "schema tree" \
                                  .format(config_node.tag,
                                          self.get_xpath(parent)))
            self.nodes[config_path_str] = child
            return child
        else:
            tree = self.models[n.model_name].tree
            child = get_child(tree, config_node.tag)
            if child is None:
                raise ConfigError("unable to locate a root '{}' in {} schema " \
                                  "tree" \
                                  .format(config_node.tag, n.model_name))
            self.nodes[config_path_str] = child
            return child

    def get_model_name(self, node):
        '''get_model_name

        High-level api: Given an Element node in config tree or schema tree,
        get_model_name returns the model name that the node belongs to.

        Parameters
        ----------

        node : `Element`
            an Element node in config tree or schema tree.

        Returns
        -------

        str
            Model name.


        Code Example::

            >>> m.get_model_name(config_node)
            'openconfig-interfaces'
            >>>
        '''

        return Composer(self, node).model_name

    def get_xpath(self, node, type=Tag.XPATH, instance=True):
        '''get_xpath

        High-level api: Given a config or schema node, get_xpath returns an
        xpath of the node, which starts from the model root. Each identifier
        uses the `prefix:tagname` notation if argument 'type' is not specified.

        Parameters
        ----------

        node : `Element`
            A config or schema node.

        type : `tuple`
            A tuple constant defined in yang.ncdiff.Tag. Most commonly it could
            be Tag.XPATH or Tag.LXML_XPATH.

        instance : `bool`
            True if the xpath returned points to an instance. The xpath could
            point to a list or leaf-list when instance=False.

        Returns
        -------

        str
            An xpath of the config or schema node, which starts from the model
            root.


        Code Example::

            >>> m.get_xpath(config_node)
            '/oc-if:interfaces/interface[name="GigabitEthernet0/0"]'
            >>> m.get_xpath(config_node, type=Tag.LXML_XPATH)
            '/oc-if:interfaces/oc-if:interface[oc-if:name="GigabitEthernet0/0"]'
            >>>
            >>> m.get_xpath(schema_node)
            '/oc-if:interfaces/interface'
            >>>
        '''

        return Composer(self, node).get_xpath(type, instance=instance)

    def convert_tag(self, default_ns, tag, src=Tag.LXML_ETREE, dst=Tag.YTOOL):
        '''convert_tag

        High-level api: Convert a tag or an identifier from one notation to
        another. Notations are defined by tuple constants in yang.ncdiff.Tag.

        Parameters
        ----------

        default_ns : `str`
            The default namespace. Usually it's the namespace of parent node. It
            could be a model name, a model prefix, or a model URL, depending on
            your argument 'src'. An empty string is considered as none default
            namespace.

        tag : `str`
            A tag or an identifier of a config node or a schema node.

        src : `tuple`
            The type of notation the input tag is, which is a tuple constant
            defined in yang.ncdiff.Tag. Most commonly it could be Tag.XPATH or
            Tag.LXML_XPATH.

        dst : `tuple`
            The type of notation we want, which is a tuple constant defined in
            yang.ncdiff.Tag. Most commonly it could be Tag.XPATH or
            Tag.LXML_XPATH.

        Returns
        -------

        tuple
            A tuple that has two elements: The first element is the namespace of
            argument 'tag'. It could be a model name, a model prefix, or a model
            URL, depending on your argument 'src'. The second element is the
            converted tag or identifier, which is in notation specified by
            argument 'dst'.


        Code Example::

            >>> m.convert_tag('',
                              '{http://openconfig.net/yang/interfaces}interface',
                              dst=Tag.JSON_NAME)
            ('http://openconfig.net/yang/interfaces', 'openconfig-interfaces:interface')
            >>>
        '''

        def possible_part1():
            if src[0] == Tag.NAME:
                return [i[0] for i in self.namespaces]
            elif src[0] == Tag.PREFIX:
                return [i[1] for i in self.namespaces] + \
                       list(special_prefixes.values())
            else:
                return [i[2] for i in self.namespaces] + \
                       list(special_prefixes.keys())

        def split_tag(tag):
            ret = re.search(src[2][0], tag)
            if ret:
                if ret.group(1) in possible_part1():
                    return (ret.group(1), ret.group(2))
                else:
                    raise ValueError("namespace '{}' in tag '{}' cannot be " \
                                     "found in namespaces of any models" \
                                     .format(ret.group(1), tag))
            else:
                return ('', tag)

        def format_tag(tag_ns, tag_name):
            if tag_ns:
                return dst[2][1].format(tag_ns, tag_name)
            else:
                return tag_name

        def convert(ns):
            matches = [i for i in self.namespaces if i[src[0]] == ns]
            c = len(matches)
            if c > 1:
                raise ModelError("device supports more than one {} '{}': {}" \
                                 .format(Tag.STR[src[0]], ns, matches))
            if c == 1:
                return matches[0][dst[0]]
            if src[0] != Tag.NAME and dst[0] != Tag.NAME:
                special = [('', v, k) for k, v in special_prefixes.items()]
                matches = [i for i in special if i[src[0]] == ns]
                if len(matches) == 1:
                    return matches[0][dst[0]]
            raise ValueError("device does not support {} '{}' " \
                             "when parsing tag '{}'" \
                             .format(Tag.STR[src[0]], ns, tag))

        tag_ns, tag_name = split_tag(tag)
        if src[1] == Tag.NO_OMIT and not tag_ns:
            raise ValueError("tag '{}' does not contain prefix or namespace " \
                             "but it is supposed to be Tag.NO_OMIT" \
                             .format(tag))
        elif not tag_ns:
            tag_ns = default_ns
        if dst[1] == Tag.NO_OMIT:
            return tag_ns, format_tag(convert(tag_ns), tag_name)
        elif dst[1] == Tag.OMIT_BY_INHERITANCE:
            if default_ns == tag_ns:
                return tag_ns, format_tag('', tag_name)
            else:
                return tag_ns, format_tag(convert(tag_ns), tag_name)
        elif dst[1] == Tag.OMIT_BY_MODULE:
            if default_ns == tag_ns:
                return tag_ns, format_tag('', tag_name)
            else:
                return tag_ns, format_tag(convert(tag_ns), tag_name)
        else:
            raise ValueError("unknown value '{}' in class Tag".format(dst[1]))

    def convert_ns(self, ns, src=Tag.NAMESPACE, dst=Tag.NAME):
        '''convert_ns

        High-level api: Convert from one namespace format, model name, model
        prefix or model URL, to another namespace format.

        Parameters
        ----------

        ns : `str`
            A namespace, which can be model name, model prefix or model URL.

        src : `int`
            An int constant defined in class Tag, specifying the namespace
            format of ns.

        dst : `int`
            An int constant defined in class Tag, specifying the namespace
            format of return value.

        Returns
        -------

        str
            Converted namespace in a format specified by dst.
        '''

        matches = [t for t in self.namespaces if t[src] == ns]
        if len(matches) == 0:
            raise ValueError("{} '{}' is not claimed by this device" \
                             .format(Tag.STR[src], ns))
        if len(matches) > 1:
            raise ValueError("more than one {} '{}' are claimed by this " \
                             "device".format(Tag.STR[src], ns))
        return matches[0][dst]

    def _get_ns(self, reply):
        '''_get_ns

        Low-level api: Return a dict of nsmap.

        Parameters
        ----------

        reply : `Element`
            rpc-reply as an instance of Element.

        Returns
        -------

        dict
            A dict of nsmap.
        '''

        def get_prefix(url):
            if url in special_prefixes:
                return special_prefixes[url]
            for i in self.namespaces:
                if url == i[2]:
                    return i[1]
            return None

        root = reply.getroottree()
        urls = set()
        for node in root.iter():
            urls.update([u for p, u in node.nsmap.items()])
        ret = {url: get_prefix(url) for url in urls}
        i = 0
        for url in [url for url in ret if ret[url] is None]:
            logger.warning('{} cannot be found in namespaces of any ' \
                           'models'.format(url))
            ret[url] = 'ns{:02d}'.format(i)
            i += 1
        return {p: u for u, p in ret.items()}
