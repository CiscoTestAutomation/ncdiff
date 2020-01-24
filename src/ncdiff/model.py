import math
import os
import re
import logging
from lxml import etree
from copy import deepcopy
from ncclient import operations
from subprocess import PIPE, Popen

from .errors import ModelError

# create a logger for this module
logger = logging.getLogger(__name__)

class Model(object):
    '''Model

    Abstraction of a YANG module. It supports str() which returns a string
    similar to the output of 'pyang -f tree'.

    Attributes
    ----------
    name : `str`
        Model name.

    prefix : `str`
        Prefix of the model.

    prefixes : `dict`
        All prefixes used in the model. Dictionary keys are prefixes, and
        values are URLs.

    url : `str`
        URL of the model.

    urls : `dict`
        All URLs used in the model. Dictionary keys are URLs, and values are
        URLs.

    tree : `Element`
        The model tree as an Element object.

    roots : `list`
        All root nodes of the model. Each node is an Element object.

    width : `dict`
        This is used to facilitate pretty print of a model. Dictionary keys are
        nodes in the model tree, and values are indents.
    '''

    def __init__(self, tree):
        '''
        __init__ instantiates a Model instance.
        '''

        self.name = tree.attrib['name']
        ns = tree.findall('namespace')
        self.prefixes = {c.attrib['prefix']: c.text for c in ns}
        self.prefix = tree.attrib['prefix']
        self.url = self.prefixes[self.prefix]
        self.urls = {v: k for k, v in self.prefixes.items()}
        self.tree = self.convert_tree(tree)
        self.roots = [c.tag for c in self.tree.getchildren()]
        self.width = {}

    def __str__(self):
        return self.emit_tree(self.tree)

    def emit_tree(self, tree):
        '''emit_tree

        High-level api: Emit a string presentation of the model.

        Parameters
        ----------

        tree : `Element`
            The model.

        Returns
        -------

        str
            A string presentation of the model that is very similar to the
            output of 'pyang -f tree'
        '''

        ret = []
        ret.append('module: {}'.format(tree.tag))
        ret += self.emit_children(tree, type='other')
        rpc_lines = self.emit_children(tree, type='rpc')
        if rpc_lines:
            ret += ['', '  rpcs:'] + rpc_lines
        notification_lines = self.emit_children(tree, type='notification')
        if notification_lines:
            ret += ['', '  notifications:'] + notification_lines
        return '\n'.join(ret)

    def emit_children(self, tree, type='other'):
        '''emit_children

        High-level api: Emit a string presentation of a part of the model.

        Parameters
        ----------

        tree : `Element`
            The model.

        type : `str`
            Type of model content required. Its value can be 'other', 'rpc', or
            'notification'.

        Returns
        -------

        str
            A string presentation of the model that is very similar to the
            output of 'pyang -f tree'
        '''

        def is_type(element, type):
            type_info = element.get('type')
            if type == type_info:
                return True
            if type == 'rpc' or type == 'notification':
                return False
            if type_info == 'rpc' or type_info == 'notification':
                return False
            return True

        ret = []
        for root in [i for i in tree.getchildren() if is_type(i, type)]:
            for i in root.iter():
                line = self.get_depth_str(i, type=type)
                name_str = self.get_name_str(i)
                room_consumed = len(name_str)
                line += name_str
                if i.get('type') == 'anyxml' or \
                   i.get('type') == 'anydata' or \
                   i.get('datatype') is not None or \
                   i.get('if-feature') is not None:
                    line += self.get_datatype_str(i, room_consumed)
                ret.append(line)
        return ret

    def get_width(self, element):
        '''get_width

        High-level api: Calculate how much indent is needed for a node.

        Parameters
        ----------

        element : `Element`
            A node in model tree.

        Returns
        -------

        int
            Start position from the left margin.
        '''

        parent = element.getparent()
        if parent in self.width:
            return self.width[parent]
        ret = 0
        for sibling in parent.getchildren():
            w = len(self.get_name_str(sibling))
            if w > ret:
                ret = w
        self.width[parent] = math.ceil((ret + 3) / 3.0) * 3
        return self.width[parent]

    @staticmethod
    def get_depth_str(element, type='other'):
        '''get_depth_str

        High-level api: Produce a string that represents tree hierarchy.

        Parameters
        ----------

        element : `Element`
            A node in model tree.

        type : `str`
            Type of model content required. Its value can be 'other', 'rpc', or
            'notification'.

        Returns
        -------

        str
            A string that represents tree hierarchy.
        '''

        def following_siblings(element, type):
            if type == 'rpc' or type == 'notification':
                return [s for s in list(element.itersiblings()) \
                        if s.get('type') == type]
            else:
                return [s for s in list(element.itersiblings()) \
                        if s.get('type') != 'rpc' and \
                           s.get('type') != 'notification']

        ancestors = list(reversed(list(element.iterancestors())))
        ret = ' '
        for i, ancestor in enumerate(ancestors):
            if i == 1:
                if following_siblings(ancestor, type):
                    ret += '|  '
                else:
                    ret += '   '
            else:
                if ancestor.getnext() is None:
                    ret += '   '
                else:
                    ret += '|  '
        ret += '+--'
        return ret

    @staticmethod
    def get_flags_str(element):
        '''get_flags_str

        High-level api: Produce a string that represents the type of a node.

        Parameters
        ----------

        element : `Element`
            A node in model tree.

        Returns
        -------

        str
            A string that represents the type of a node.
        '''

        type_info = element.get('type')
        if type_info == 'rpc' or type_info == 'action':
            return '-x'
        elif type_info == 'notification':
            return '-n'
        access_info = element.get('access')
        if access_info is None:
            return ''
        elif access_info == 'write':
            return '-w'
        elif access_info == 'read-write':
            return 'rw'
        elif access_info == 'read-only':
            return 'ro'
        else:
            return '--'

    def get_name_str(self, element):
        '''get_name_str

        High-level api: Produce a string that represents the name of a node.

        Parameters
        ----------

        element : `Element`
            A node in model tree.

        Returns
        -------

        str
            A string that represents the name of a node.
        '''

        name = self.remove_model_prefix(self.url_to_prefix(element.tag))
        flags = self.get_flags_str(element)
        type_info = element.get('type')
        if type_info is None:
            pass
        elif type_info == 'choice':
            if element.get('mandatory') == 'true':
                return flags + ' ({})'.format(name)
            else:
                return flags + ' ({})?'.format(name)
        elif type_info == 'case':
            return ':({})'.format(name)
        elif type_info == 'container':
            return flags + ' {}'.format(name)
        elif type_info == 'leaf' or \
             type_info == 'anyxml' or \
             type_info == 'anydata':
            if element.get('mandatory') == 'true':
                return flags + ' {}'.format(name)
            else:
                return flags + ' {}?'.format(name)
        elif type_info == 'list':
            if element.get('key') is not None:
                return flags + ' {}* [{}]'.format(name, element.get('key'))
            else:
                return flags + ' {}*'.format(name)
        elif type_info == 'leaf-list':
            return flags + ' {}*'.format(name)
        else:
            return flags + ' {}'.format(name)

    def get_datatype_str(self, element, length):
        '''get_datatype_str

        High-level api: Produce a string that indicates the data type of a node.

        Parameters
        ----------

        element : `Element`
            A node in model tree.

        length : `int`
            String length that has been consumed.

        Returns
        -------

        str
            A string that indicates the data type of a node.
        '''

        spaces = ' '*(self.get_width(element) - length)
        type_info = element.get('type')
        ret = ''
        if type_info == 'anyxml' or type_info == 'anydata':
            ret = spaces + '<{}>'.format(type_info)
        elif element.get('datatype') is not None:
            ret = spaces + element.get('datatype')
        if element.get('if-feature') is not None:
            return ret + ' {' + element.get('if-feature') + '}?'
        else:
            return ret

    def prefix_to_url(self, id):
        '''prefix_to_url

        High-level api: Convert an identifier from `prefix:tagname` notation to
        `{namespace}tagname` notation. If the identifier does not have a
        prefix, it is assumed that the whole identifier is a tag name.

        Parameters
        ----------

        id : `str`
            Identifier in `prefix:tagname` notation.

        Returns
        -------

        str
            Identifier in `{namespace}tagname` notation.
        '''

        parts = id.split(':')
        if len(parts) > 1:
            return '{' + self.prefixes[parts[0]] + '}' + parts[1]
        else:
            return '{' + self.url + '}' + id

    def url_to_prefix(self, id):
        '''url_to_prefix

        High-level api: Convert an identifier from `{namespace}tagname` notation
        to `prefix:tagname` notation. If the identifier does not have a
        namespace, it is assumed that the whole identifier is a tag name.

        Parameters
        ----------

        id : `str`
            Identifier in `{namespace}tagname` notation.

        Returns
        -------

        str
            Identifier in `prefix:tagname` notation.
        '''

        ret = re.search('^{(.+)}(.+)$', id)
        if ret:
            return self.urls[ret.group(1)] + ':' + ret.group(2)
        else:
            return id

    def remove_model_prefix(self, id):
        '''remove_model_prefix

        High-level api: If prefix is the model prefix, return tagname without
        prefix. If prefix is not the model prefix, simply return the identifier
        without modification.

        Parameters
        ----------

        id : `str`
            Identifier in `prefix:tagname` notation.

        Returns
        -------

        str
            Identifier in `prefix:tagname` notation if prefix is not the model
            prefix. Or identifier in `tagname` notation if prefix is the model
            prefix.
        '''

        reg_str = '^' + self.prefix + ':(.+)$'
        ret = re.search(reg_str, id)
        if ret:
            return ret.group(1)
        else:
            return id

    def convert_tree(self, element1, element2=None):
        '''convert_tree

        High-level api: Convert cxml tree to an internal schema tree. This
        method is recursive.

        Parameters
        ----------

        element1 : `Element`
            The node to be converted.

        element2 : `Element`
            A new node being constructed.

        Returns
        -------

        Element
            This is element2 after convertion.
        '''

        if element2 is None:
            attributes = deepcopy(element1.attrib)
            tag = attributes['name']
            del attributes['name']
            element2 = etree.Element(tag, attributes)
        for e1 in element1.findall('node'):
            attributes = deepcopy(e1.attrib)
            tag = self.prefix_to_url(attributes['name'])
            del attributes['name']
            e2 = etree.SubElement(element2, tag, attributes)
            self.convert_tree(e1, e2)
        return element2


class ModelDownloader(object):
    '''ModelDownloader

    Abstraction of a Netconf schema downloader.

    Attributes
    ----------
    device : `ModelDevice`
        Model name.

    pyang_plugins : `str`
        Path to pyang plugins.

    dir_yang : `str`
        Path to yang files.

    yang_capabilities : `str`
        Path to capabilities.txt file in the folder of yang files.

    need_download : `bool`
        True if the content of capabilities.txt file disagrees with device
        capabilities exchange. False otherwise.
    '''

    def __init__(self, nc_device, folder):
        '''
        __init__ instantiates a ModelDownloader instance.
        '''

        self.device = nc_device
        self.pyang_plugins = os.path.dirname(__file__) + '/plugins'
        self.dir_yang = os.path.abspath(folder)
        if not os.path.isdir(self.dir_yang):
            os.makedirs(self.dir_yang)
        self.yang_capabilities = self.dir_yang + '/capabilities.txt'

    @property
    def need_download(self):
        if os.path.isfile(self.yang_capabilities):
            with open(self.yang_capabilities, 'r') as f:
                c = f.read()
            if c == '\n'.join(sorted(list(self.device.server_capabilities))):
                return False
        return True

    def download_all(self, check_before_download=True):
        '''download_all

        High-level api: Convert cxml tree to an internal schema tree. This
        method is recursive.

        Parameters
        ----------

        check_before_download : `bool`
            True if checking capabilities.txt file is required.

        Returns
        -------

        None
            Nothing returns.
        '''

        # check the content of self.yang_capabilities
        if check_before_download:
            if not self.need_download:
                logger.info('Skip downloading as the content of {} matches ' \
                            'device hello message' \
                            .format(self.yang_capabilities))
                return

        # clean up folder self.dir_yang
        for root, dirs, files in os.walk(self.dir_yang):
            for f in files:
                os.remove(os.path.join(root, f))

        # download all
        self.to_be_downloaded = set(self.device.models_loadable)
        self.downloaded = set()
        while self.to_be_downloaded:
            self.download(self.to_be_downloaded.pop())

        # write self.yang_capabilities
        capabilities = '\n'.join(sorted(list(self.device.server_capabilities)))
        with open(self.yang_capabilities, 'wb') as f:
            f.write(capabilities.encode('utf-8'))

    def download(self, module):
        '''download

        High-level api: Download a module schema.

        Parameters
        ----------

        module : `str`
            Module name that will be downloaded.

        Returns
        -------

        None
            Nothing returns.
        '''

        import_r = '^[ |\t]+import[ |\t]+([a-zA-Z0-9-]+)[ |\t]+[;{][ |\t]*$'
        include_r = '^[ |\t]+include[ |\t]+([a-zA-Z0-9-]+)[ |\t]*[;{][ |\t]*$'

        logger.debug('Downloading {}.yang...'.format(module))
        try:
            from .manager import ModelDevice
            reply = super(ModelDevice, self.device) \
                    .execute(operations.retrieve.GetSchema, module)
        except operations.rpc.RPCError:
            logger.warning("Module or submodule '{}' cannot be downloaded" \
                           .format(module))
            return
        if reply.ok:
            fname = self.dir_yang + '/' + module + '.yang'
            with open(fname, 'wb') as f:
                f.write(reply.data.encode('utf-8'))
            self.downloaded.add(module)
            imports = set()
            includes = set()
            for line in reply.data.splitlines():
                match = re.search(import_r, line)
                if match:
                    imports.add(match.group(1).strip())
                    continue
                match = re.search(include_r, line)
                if match:
                    includes.add(match.group(1).strip())
                    continue
            s = (imports | includes) - self.downloaded - self.to_be_downloaded
            if s:
                logger.info('{} requires submodules: {}' \
                            .format(module, ', '.join(s)))
                self.to_be_downloaded.update(s)
        else:
            logger.warning("module or submodule '{}' cannot be downloaded:\n{}" \
                           .format(module, reply._raw))


class ModelCompiler(object):
    '''ModelCompiler

    Abstraction of a YANG file compiler.

    Attributes
    ----------
    pyang_plugins : `str`
        Path to pyang plugins.

    dir_yang : `str`
        Path to yang files.

    dependencies : `Element`
        Dependency infomation stored in an Element object.
    '''

    def __init__(self, folder):
        '''
        __init__ instantiates a ModelCompiler instance.
        '''

        self.pyang_plugins = os.path.dirname(__file__) + '/plugins'
        self.dir_yang = os.path.abspath(folder)
        self.pyang_errors = {}
        self.build_dependencies()

    def _xml_from_cache(self, name):
        cached_name = os.path.join(self.dir_yang, f"{name}.xml")
        if os.path.exists(cached_name):
            with(open(cached_name, "r", encoding="utf-8")) as fh:
                parser = etree.XMLParser(remove_blank_text=True)
                tree = etree.XML(fh.read(), parser)
                return tree
        return None

    def _to_cache(self, name, value):
        cached_name = os.path.join(self.dir_yang, f"{name}.xml")
        with open(cached_name, "wb") as fh:
            fh.write(value)

    def build_dependencies(self):
        '''build_dependencies

        High-level api: Briefly compile all yang files and find out dependency
        infomation of all modules.

        Returns
        -------

        None
            Nothing returns.
        '''

        from_cache = self._xml_from_cache("$dependencies")
        if from_cache is not None:
            self.dependencies = from_cache
            return

        cmd_list = ['pyang', '--plugindir', self.pyang_plugins]
        cmd_list += ['-p', self.dir_yang]
        cmd_list += ['-f', 'pyimport']
        cmd_list += [self.dir_yang + '/*.yang']
        logger.info('Building dependencies: {}'.format(' '.join(cmd_list)))
        p = Popen(' '.join(cmd_list), shell=True, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        logger.info('pyang return code is {}'.format(p.returncode))
        self.pyang_errors['all'] = stderr.replace(b'"\\\n"', b'"\\n"').decode()
        logger.warning(self.pyang_errors['all'])
        parser = etree.XMLParser(remove_blank_text=True)

        self._to_cache("$dependencies",stdout)

        self.dependencies = etree.XML(stdout.decode(), parser)

    def get_dependencies(self, module):
        '''get_dependencies

        High-level api: Get dependency infomationa of a module.

        Parameters
        ----------

        module : `str`
            Module name that is inquired about.

        Returns
        -------

        tuple
            A tuple with two elements: a set of imports and a set of depends.
        '''

        imports = set()
        for m in list(filter(lambda i: i.get('id') == module,
                             self.dependencies.findall('./module'))):
            imports.update(set(i.get('module')
                               for i in m.findall('./imports/import')))
        depends = set()
        for m in self.dependencies.getchildren():
            if list(filter(lambda i: i.get('module') == module,
                           m.findall('./imports/import'))):
                depends.add(m.get('id'))
            if list(filter(lambda i: i.get('module') == module,
                           m.findall('./includes/include'))):
                depends.add(m.get('id'))
        return (imports, depends)

    def compile(self, module):
        '''compile

        High-level api: Compile a module.

        Parameters
        ----------

        module : `str`
            Module name that is inquired about.

        Returns
        -------

        Model
            A Model object.
        '''
        cached_tree = self._xml_from_cache(module)

        if cached_tree is not None:
            m = Model(cached_tree)
            return m

        imports, depends = self.get_dependencies(module)
        file_list = list(imports | depends) + [module]
        cmd_list = ['pyang', '-f', 'cxml', '--plugindir', self.pyang_plugins]
        cmd_list += ['-p', self.dir_yang]
        cmd_list += [self.dir_yang + '/' + f + '.yang' for f in file_list]
        logger.info('Compiling {}.yang: {}'.format(module,
                                                   ' '.join(cmd_list)))
        p = Popen(' '.join(cmd_list), shell=True, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        logger.info('pyang return code is {}'.format(p.returncode))
        self.pyang_errors[module] = stderr.replace(b'"\\\n"', b'"\\n"').decode()
        if p.returncode == 0:
            logger.debug(self.pyang_errors[module])
        else:
            logger.error(self.pyang_errors[module])
        parser = etree.XMLParser(remove_blank_text=True)

        self._to_cache(module, stdout)

        out = stdout.decode()
        tree = etree.XML(out, parser)
        return Model(tree)


class ModelDiff(object):
    '''ModelDiff

    Abstraction of differences between two Model instances. It supports str()
    which returns a string illustrating the differences between model1 and
    model2.

    Attributes
    ----------
    model1 : `Model`
        First Model instance.

    model2 : `Model`
        Second Model instance.

    tree : `Element`
        The model difference tree as an Element object.

    added : `str`
        A string presentation of added nodes from model1 to model2.

    deleted : `str`
        A string presentation of deleted nodes from model1 to model2.

    modified : `str`
        A string presentation of modified nodes from model1 to model2.

    width : `dict`
        This is used to facilitate pretty print of a model. Dictionary keys are
        nodes in the model tree, and values are indents.
    '''

    __str__ = Model.__str__
    emit_tree = Model.emit_tree
    get_width = Model.get_width

    def __init__(self, model1, model2):
        '''
        __init__ instantiates a Model instance.
        '''

        self.model1 = model1
        self.model2 = model2
        self.width = {}
        if model1.tree.tag == model2.tree.tag:
            self.tree = etree.Element(model1.tree.tag)
            if id(self.model1) != id(self.model2):
                self.compare_nodes(model1.tree, model2.tree, self.tree)
        else:
            raise ValueError("cannot generate diff of different modules: " \
                             "'{}' vs '{}'" \
                             .format(model1.tree.tag, model2.tree.tag))

    def __bool__(self):
        if self.tree.getchildren():
            return True
        else:
            return False

    @property
    def added(self):
        tree_added = deepcopy(self.tree)
        if self.trim(tree_added, 'added'):
            return None
        else:
            return self.emit_tree(tree_added)

    @property
    def deleted(self):
        tree_deleted = deepcopy(self.tree)
        if self.trim(tree_deleted, 'deleted'):
            return None
        else:
            return self.emit_tree(tree_deleted)

    @property
    def modified(self):
        tree_modified = deepcopy(self.tree)
        if self.trim(tree_modified, 'modified'):
            return None
        else:
            return self.emit_tree(tree_modified)

    def compare(self, xpath):
        '''compare

        High-level api: Return a string presentation of comparison between the
        node in model1 and model2.

        Parameters
        ----------

        xpath : `str`
            XPATH to locate a node.

        Returns
        -------

        str
            A string presentation of comparison.
        '''

        def print_node(node_list):
            if not node_list:
                return 'None'
            node = node_list[0]
            ret = ["tag: '{}'".format(node.tag),
                   "text: {}".format(print_value(node.text)),
                   "attributes:"]
            for a, v in node.attrib.items():
                ret.append("  {} = {}".format(a, print_value(v)))
            return '\n'.join(ret)

        def print_value(value):
            if value is None:
                return 'None'
            else:
                return "'{}'".format(value)

        prefixes = deepcopy(self.model1.prefixes)
        prefixes.update(self.model2.prefixes)
        node1_list = self.model1.tree.xpath(xpath, namespaces=prefixes)
        node2_list = self.model2.tree.xpath(xpath, namespaces=prefixes)
        return '\n'.join(['-'*21 + ' XPATH ' + '-'*21,
                          "'{}'".format(xpath),
                          '-'*20 + ' MODEL 1 ' + '-'*20,
                          print_node(node1_list),
                          '-'*20 + ' MODEL 2 ' + '-'*20,
                          print_node(node2_list),
                          '-'*49,
                          ''])

    def emit_children(self, tree, type='other'):
        '''emit_children

        High-level api: Emit a string presentation of a part of the model.

        Parameters
        ----------

        tree : `Element`
            The model.

        type : `str`
            Type of model content required. Its value can be 'other', 'rpc', or
            'notification'.

        Returns
        -------

        str
            A string presentation of the model that is very similar to the
            output of 'pyang -f tree'.
        '''

        def is_type(element, type):
            type_info = element.get('type')
            if type == type_info:
                return True
            if type == 'rpc' or type == 'notification':
                return False
            if type_info == 'rpc' or type_info == 'notification':
                return False
            return True

        ret = []
        for root in [i for i in tree.getchildren() if is_type(i, type)]:
            for i in root.iter():
                line = Model.get_depth_str(i, type=type)
                name_str = self.get_name_str(i)
                room_consumed = len(name_str)
                line += name_str
                if i.get('diff') is not None:
                    line += self.get_diff_str(i, room_consumed)
                ret.append(line)
        return ret

    def get_name_str(self, element):
        '''get_name_str

        High-level api: Produce a string that represents the name of a node.

        Parameters
        ----------

        element : `Element`
            A node in model tree.

        Returns
        -------

        str
            A string that represents the name of a node.
        '''

        if element.get('diff') == 'added':
            return self.model2.get_name_str(element)
        else:
            return self.model1.get_name_str(element)

    def get_diff_str(self, element, length):
        '''get_diff_str

        High-level api: Produce a string that indicates the difference between
        two models.

        Parameters
        ----------

        element : `Element`
            A node in model tree.

        length : `int`
            String length that has been consumed.

        Returns
        -------

        str
            A string that indicates the difference between two models.
        '''

        spaces = ' '*(self.get_width(element) - length)
        return spaces + element.get('diff')

    @staticmethod
    def compare_nodes(node1, node2, ret):
        '''compare_nodes

        High-level api: Compare node1 and node2 and put the result in ret.

        Parameters
        ----------

        node1 : `Element`
            A node in a model tree.

        node2 : `Element`
            A node in another model tree.

        ret : `Element`
            A node in self.tree.

        Returns
        -------

        None
            Nothing returns.
        '''

        for child in node2.getchildren():
            peer = ModelDiff.get_peer(child.tag, node1)
            if peer is None:
                ModelDiff.copy_subtree(ret, child, 'added')
            else:
                if ModelDiff.node_equal(peer, child):
                    continue
                else:
                    if child.attrib['type'] in ['leaf-list', 'leaf']:
                        ModelDiff.copy_node(ret, child, 'modified')
                    else:
                        ret_child = ModelDiff.copy_node(ret, child, '')
                        ModelDiff.compare_nodes(peer, child, ret_child)
        for child in node1.getchildren():
            peer = ModelDiff.get_peer(child.tag, node2)
            if peer is None:
                ModelDiff.copy_subtree(ret, child, 'deleted')

    @staticmethod
    def copy_subtree(ret, element, msg):
        '''copy_subtree

        High-level api: Copy element as a subtree and put it as a child of ret.

        Parameters
        ----------

        element : `Element`
            A node in a model tree.

        msg : `str`
            Message to be added.

        ret : `Element`
            A node in self.tree.

        Returns
        -------

        None
            Nothing returns.
        '''

        sub_element = ModelDiff.process_attrib(deepcopy(element), msg)
        ret.append(sub_element)
        return sub_element

    @staticmethod
    def copy_node(ret, element, msg):
        '''copy_node

        High-level api: Copy element as a node without its children and put it
        as a child of ret.

        Parameters
        ----------

        element : `Element`
            A node in a model tree.

        msg : `str`
            Message to be added.

        ret : `Element`
            A node in self.tree.

        Returns
        -------

        None
            Nothing returns.
        '''
        sub_element = etree.SubElement(ret, element.tag, attrib=element.attrib)
        ModelDiff.process_attrib(sub_element, msg)
        return sub_element

    @staticmethod
    def process_attrib(element, msg):
        '''process_attrib

        High-level api: Delete four attributes from an ElementTree node if they
        exist: operation, insert, etc. Then a new attribute 'diff' is added.

        Parameters
        ----------

        element : `Element`
            A node needs to be looked at.

        msg : `str`
            Message to be added in attribute 'diff'.

        Returns
        -------

        Element
            Argument 'element' is returned after processing.
        '''

        known_attrib = ['type', 'access', 'mandatory', 'presence', 'values',
                        'key', 'is_key', 'prefix', 'datatype', 'if-feature',
                        'ordered-by', 'default']
        for node in element.iter():
            for attrib in node.attrib.keys():
                if attrib not in known_attrib:
                    del node.attrib[attrib]
            if msg:
                node.attrib['diff'] = msg
        return element

    @staticmethod
    def get_peer(tag, node):
        '''get_peer

        High-level api: Find all children under the node with the tag.

        Parameters
        ----------

        tag : `str`
            A tag in `{namespace}tagname` notaion.

        node : `Element`
            A node to be looked at.

        Returns
        -------

        Element or None
            None if not found. An Element object when found.
        '''

        peers = node.findall(tag)
        if len(peers) < 1:
            return None
        elif len(peers) > 1:
            raise ModelError("not unique tag '{}'".format(tag))
        else:
            return peers[0]

    @staticmethod
    def node_equal(node1, node2):
        '''node_equal

        High-level api: Evaluate whether two nodes are equal.

        Parameters
        ----------

        node1 : `Element`
            A node in a model tree.

        node2 : `Element`
            A node in another model tree.

        Returns
        -------

        bool
            True if node1 and node2 are equal.
        '''

        if ModelDiff.node_less(node1, node2) and \
           ModelDiff.node_less(node2, node1):
            return True
        else:
            return False

    @staticmethod
    def node_less(node1, node2):
        '''node_less

        Low-level api: Return True if all descendants of node1 exist in node2.
        Otherwise False. This is a recursive method.

        Parameters
        ----------

        node1 : `Element`
            A node in a model tree.

        node2 : `Element`
            A node in another model tree.

        Returns
        -------

        bool
            True if all descendants of node1 exist in node2, otherwise False.
        '''

        for x in ['tag', 'text']:
            if node1.__getattribute__(x) != node2.__getattribute__(x):
                return False
        for a in node1.attrib:
            if a not in node2.attrib or \
               node1.attrib[a] != node2.attrib[a]:
                return False
        for child in node1.getchildren():
            peers = node2.findall(child.tag)
            if len(peers) < 1:
                return False
            elif len(peers) > 1:
                raise ModelError("not unique peer '{}'".format(child.tag))
            else:
                if not ModelDiff.node_less(child, peers[0]):
                    return False
        return True

    @staticmethod
    def trim(parent, msg):
        '''trim

        Low-level api: Return True if parent has no child after trimming. The
        trimming to filter out one type of diff: added, deleted, or modified.

        Parameters
        ----------

        parent : `Element`
            A node in a model tree.

        msg : `str`
            A type of diff: added, deleted, or modified.

        Returns
        -------

        bool
            True if parent has no child after trimming.
        '''

        for child in list(parent):
            diff = child.get('diff')
            type = child.get('type')
            if diff and diff != msg:
                parent.remove(child)
            elif type == 'container' or \
                 type == 'list' or \
                 type == 'choice' or \
                 type == 'case':
                if ModelDiff.trim(child, msg):
                    parent.remove(child)
        return len(list(parent)) == 0
