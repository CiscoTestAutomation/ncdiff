import math
import os
import re
import queue
import logging

from lxml import etree
from copy import deepcopy
from ncclient import operations
from threading import Thread, current_thread
from pyang import statements
try:
    from pyang.repository import FileRepository
except ImportError:
    from pyang import FileRepository
try:
    from pyang.context import Context
except ImportError:
    from pyang import Context

from .errors import ModelError


# create a logger for this module
logger = logging.getLogger(__name__)
logging.getLogger('ncclient.transport').setLevel(logging.WARNING)
logging.getLogger('ncclient.operations').setLevel(logging.WARNING)

PARSER = etree.XMLParser(encoding='utf-8', remove_blank_text=True)


def write_xml(filename, element):
    element_tree = etree.ElementTree(element)
    element_tree.write(
        filename,
        encoding='utf-8',
        xml_declaration=True,
        pretty_print=True,
        with_tail=False,
    )


def read_xml(filename):
    if os.path.isfile(filename):
        try:
            element_tree = etree.parse(filename, parser=PARSER)
            return element_tree.getroot()
        except Exception:
            return None
    else:
        return None


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
        prefixes.

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

        self.tree = tree
        self.name = tree.tag
        ns = tree.findall('namespace')
        self.prefixes = {c.attrib['prefix']: c.text for c in ns}
        self.prefix = tree.attrib['prefix']
        self.url = self.prefixes[self.prefix]
        self.urls = {v: k for k, v in self.prefixes.items()}
        self.convert_tree()
        self.width = {}

    def __str__(self):
        return self.emit_tree(self.tree)

    @property
    def roots(self):
        return [c.tag for c in self.tree]

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
        for root in [i for i in tree if is_type(i, type)]:
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
        for sibling in parent:
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
                return [s for s in list(element.itersiblings())
                        if s.get('type') == type]
            else:
                return [
                    s for s in list(element.itersiblings())
                    if (
                        s.get('type') != 'rpc' and
                        s.get('type') != 'notification'
                    )
                ]

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
        elif (
            type_info == 'leaf' or
            type_info == 'anyxml' or
            type_info == 'anydata'
        ):
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

        High-level api: Produce a string that indicates the data type of a
        node.

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

        High-level api: Convert an identifier from `{namespace}tagname`
        notation to `prefix:tagname` notation. If the identifier does not have
        a namespace, it is assumed that the whole identifier is a tag name.

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

    def convert_tree(self):
        '''convert_tree

        High-level api: Convert cxml tree to an internal schema tree.

        Parameters
        ----------

        None

        Returns
        -------

        Element
            This is the tree after convertion.
        '''

        for ns in self.tree.findall('namespace'):
            self.tree.remove(ns)


class DownloadWorker(Thread):

    def __init__(self, downloader):
        Thread.__init__(self)
        self.downloader = downloader

    def run(self):
        while not self.downloader.download_queue.empty():
            try:
                module = self.downloader.download_queue.get(timeout=0.01)
            except queue.Empty:
                pass
            else:
                try:
                    self.downloader.download(module)
                except Exception:
                    logger.exception('Got error while downloading')
                self.downloader.download_queue.task_done()
        logger.debug('Thread {} exits'.format(current_thread().name))


class ContextWorker(Thread):

    def __init__(self, context):
        Thread.__init__(self)
        self.context = context

    def run(self):
        varnames = Context.add_module.__code__.co_varnames
        while not self.context.modulefile_queue.empty():
            try:
                modulefile = self.context.modulefile_queue.get(timeout=0.01)
            except queue.Empty:
                pass
            else:
                with open(modulefile, 'r', encoding='utf-8') as f:
                    text = f.read()
                kwargs = {
                    'ref': modulefile,
                    'text': text,
                }
                if 'primary_module' in varnames:
                    kwargs['primary_module'] = True
                if 'format' in varnames:
                    kwargs['format'] = 'yang'
                if 'in_format' in varnames:
                    kwargs['in_format'] = 'yang'
                module_statement = self.context.add_module(**kwargs)
                if module_statement is not None:
                    self.context.update_dependencies(module_statement)
                self.context.modulefile_queue.task_done()
        logger.debug('Thread {} exits'.format(current_thread().name))


class CompilerContext(Context):

    def __init__(self, repository):
        Context.__init__(self, repository)
        self.dependencies = None
        self.modulefile_queue = None
        if 'prune' in dir(statements.Statement):
            self.num_threads = 2
        else:
            self.num_threads = 1

    def _get_latest_revision(self, modulename):
        latest = None
        for module_name, module_revision in self.modules:
            if module_name == modulename and (
                latest is None or module_revision > latest
            ):
                latest = module_revision
        return latest

    def get_statement(self, modulename, xpath=None):
        revision = self._get_latest_revision(modulename)
        if revision is None:
            return None
        if xpath is None:
            return self.modules[(modulename, revision)]

        # in order to follow the Xpath, the module is required to be validated
        node_statement = self.modules[(modulename, revision)]
        if node_statement.i_is_validated is not True:
            return None

        # xpath is given, so find the node statement
        xpath_list = xpath.split('/')

        # only absolute Xpaths are supported
        if len(xpath_list) < 2:
            return None
        if (
            xpath_list[0] == '' and xpath_list[1] == '' or
            xpath_list[0] != ''
        ):
            return None

        # find the node statement
        root_prefix = node_statement.i_prefix
        for n in xpath_list[1:]:
            node_statement = self.get_child(root_prefix, node_statement, n)
            if node_statement is None:
                return None
        return node_statement

    def get_child(self, root_prefix, parent, child_id):
        child_id_list = child_id.split(':')
        if len(child_id_list) > 1:
            children = [
                c for c in parent.i_children
                if c.arg == child_id_list[1] and
                c.i_module.i_prefix == child_id_list[0]
            ]
        elif len(child_id_list) == 1:
            children = [
                c for c in parent.i_children
                if c.arg == child_id_list[0] and
                c.i_module.i_prefix == root_prefix
            ]
        return children[0] if children else None

    def update_dependencies(self, module_statement):
        if self.dependencies is None:
            self.dependencies = etree.Element('modules')
        for m in [
            m for m in self.dependencies
            if m.attrib.get('id') == module_statement.arg
        ]:
            self.dependencies.remove(m)
        module_node = etree.SubElement(self.dependencies, 'module')
        module_node.set('id', module_statement.arg)
        module_node.set('type', module_statement.keyword)
        if module_statement.keyword == 'module':
            statement = module_statement.search_one('prefix')
            if statement is not None:
                module_node.set('prefix', statement.arg)
            statement = module_statement.search_one("namespace")
            if statement is not None:
                namespace = etree.SubElement(module_node, 'namespace')
                namespace.text = statement.arg
        if module_statement.keyword == 'submodule':
            statement = module_statement.search_one("belongs-to")
            if statement is not None:
                belongs_to = etree.SubElement(module_node, 'belongs-to')
                belongs_to.set('module', statement.arg)

        dependencies = set()
        for parent_node_name, child_node_name, attr_name in [
            ('includes', 'include', 'module'),
            ('imports', 'import', 'module'),
            ('revisions', 'revision', 'date'),
            ('augments', 'augment', 'xpath'),
            ('deviations', 'deviation', 'xpath'),
        ]:
            statements = module_statement.search(child_node_name)
            if statements:
                parent = etree.SubElement(module_node, parent_node_name)
                for statement in statements:
                    child = etree.SubElement(parent, child_node_name)
                    child.set(attr_name, statement.arg)
                    if child_node_name in ['include', 'import']:
                        dependencies.add(statement.arg)
                        if child_node_name == 'import':
                            child.set('prefix',
                                      statement.search_one('prefix').arg)

        for node_name in [
            'container',
            'leaf',
            'leaf-list',
            'list',
            'choice',
            'uses',
        ]:
            exposed_statements = []
            for stmt in module_statement.search(node_name):
                for substmt in stmt.substmts:
                    if (
                        'tailf' in substmt.keyword[0] and
                        len(substmt.keyword) == 2 and
                        substmt.keyword[1] == 'hidden'
                    ):
                        break
                else:
                    exposed_statements.append(stmt)
            if exposed_statements:
                parent = etree.SubElement(module_node, 'roots')
                break

        return dependencies

    def write_dependencies(self):
        dependencies_file = os.path.join(
            self.repository.dirs[0],
            'dependencies.xml',
        )
        write_xml(dependencies_file, self.dependencies)

    def read_dependencies(self):
        dependencies_file = os.path.join(
            self.repository.dirs[0],
            'dependencies.xml',
        )
        self.dependencies = read_xml(dependencies_file)

    def load_context(self):
        self.modulefile_queue = queue.Queue()
        for filename in os.listdir(self.repository.dirs[0]):
            if filename.lower().endswith('.yang'):
                filepath = os.path.join(self.repository.dirs[0], filename)
                self.modulefile_queue.put(filepath)
        for x in range(self.num_threads):
            worker = ContextWorker(self)
            worker.daemon = True
            worker.name = 'context_worker_{}'.format(x)
            worker.start()
        self.modulefile_queue.join()
        self.write_dependencies()

    def validate_context(self):
        revisions = {}
        for mudule_name, module_revision in self.modules:
            if mudule_name not in revisions or (
                mudule_name in revisions and
                revisions[mudule_name] < module_revision
            ):
                revisions[mudule_name] = module_revision
        self.sort_modules()
        self.validate()
        if 'prune' in dir(statements.Statement):
            for mudule_name, module_revision in revisions.items():
                self.modules[(mudule_name, module_revision)].prune()

    def sort_modules(self):
        submodules = {k: m for k, m in self.modules.items()
                      if m.keyword == "submodule"}
        for k in submodules:
            del self.modules[k]
        self.modules.update(submodules)

    def internal_reset(self):
        self.modules = {}
        self.revs = {}
        self.errors = []
        for mod, rev, handle in self.repository.get_modules_and_revisions(
                self):
            if mod not in self.revs:
                self.revs[mod] = []
            revs = self.revs[mod]
            revs.append((rev, handle))


class ModelDownloader(object):
    '''ModelDownloader

    Abstraction of a Netconf schema downloader.

    Attributes
    ----------
    device : `ModelDevice`
        Model name.

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
        self.dir_yang = os.path.abspath(folder)
        if not os.path.isdir(self.dir_yang):
            os.makedirs(self.dir_yang)
        self.yang_capabilities = os.path.join(
            self.dir_yang,
            'capabilities.txt',
        )
        repo = FileRepository(path=self.dir_yang)
        self.context = CompilerContext(repository=repo)
        self.download_queue = queue.Queue()
        self.num_threads = 2

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
        if check_before_download and not self.need_download:
            logger.info('Skip downloading as the content of {} '
                        'matches device hello message'
                        .format(self.yang_capabilities))
            return

        # clean up folder self.dir_yang
        for root, dirs, files in os.walk(self.dir_yang):
            for f in files:
                os.remove(os.path.join(root, f))

        # download all
        self.to_be_downloaded = set(self.device.models_loadable)
        self.context.dependencies = etree.Element('modules')
        for module in sorted(list(self.to_be_downloaded)):
            self.download_queue.put(module)
        for x in range(self.num_threads):
            worker = DownloadWorker(self)
            worker.daemon = True
            worker.name = 'download_worker_{}'.format(x)
            worker.start()
        self.download_queue.join()

        # write self.yang_capabilities
        capabilities = '\n'.join(sorted(list(self.device.server_capabilities)))
        with open(self.yang_capabilities, 'wb') as f:
            f.write(capabilities.encode('utf-8'))

        # write dependencies
        self.context.write_dependencies()

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

        logger.debug('Downloading {}.yang...'.format(module))
        try:
            from .manager import ModelDevice
            reply = super(ModelDevice, self.device).execute(
                operations.retrieve.GetSchema,
                module,
            )
        except operations.rpc.RPCError:
            logger.warning("Module or submodule '{}' cannot be downloaded"
                           .format(module))
            return
        if reply.ok:
            varnames = Context.add_module.__code__.co_varnames
            fname = os.path.join(self.dir_yang, module+'.yang')
            with open(fname, 'wb') as f:
                f.write(reply.data.encode('utf-8'))
            kwargs = {
                'ref': fname,
                'text': reply.data,
            }
            if 'primary_module' in varnames:
                kwargs['primary_module'] = True
            if 'format' in varnames:
                kwargs['format'] = 'yang'
            if 'in_format' in varnames:
                kwargs['in_format'] = 'yang'
            module_statement = self.context.add_module(**kwargs)
            dependencies = self.context.update_dependencies(module_statement)
            s = dependencies - self.to_be_downloaded
            if s:
                logger.info('{} requires submodules: {}'
                            .format(module, ', '.join(s)))
                self.to_be_downloaded.update(s)
                for m in s:
                    self.download_queue.put(m)
        else:
            logger.warning("module or submodule '{}' cannot be downloaded:\n{}"
                           .format(module, reply._raw))


class ModelCompiler(object):
    '''ModelCompiler

    Abstraction of a YANG file compiler.

    Attributes
    ----------
    dir_yang : `str`
        Path to yang files.

    dependencies : `Element`
        Dependency infomation stored in an Element object.

    context : `CompilerContext`
        A CompilerContext object that holds the context of all modules.

    module_prefixes : `dict`
        A dictionary that stores module prefixes. It is keyed by module names.

    module_namespaces : `dict`
        A dictionary that stores module namespaces. It is keyed by module
        names.

    identity_deps : `dict`
        A dictionary that stores module identities. It is keyed by bases.

    pyang_errors : `list`
        A list of tuples. Each tuple contains a pyang error.Position object,
        an error tag and a tuple of some error arguments. It is possible to
        call pyang.error.err_to_str() to print out detailed error messages.
    '''

    def __init__(self, folder):
        '''
        __init__ instantiates a ModelCompiler instance.
        '''

        self.dir_yang = os.path.abspath(folder)
        self.context = None
        self.module_prefixes = {}
        self.module_namespaces = {}
        self.identity_deps = {}
        self.build_dependencies()

    @property
    def pyang_errors(self):
        if self.context is None:
            return []
        else:
            return self.context.errors

    def _read_from_cache(self, name):
        cached_name = os.path.join(self.dir_yang, name + ".xml")
        return read_xml(cached_name)

    def _write_to_cache(self, name, element):
        cached_name = os.path.join(self.dir_yang, name + ".xml")
        write_xml(cached_name, element)

    def build_dependencies(self):
        '''build_dependencies

        High-level api: Briefly compile all yang files and find out dependency
        infomation of all modules.

        Returns
        -------

        None
            Nothing returns.
        '''

        if self.context is None:
            repo = FileRepository(path=self.dir_yang)
            self.context = CompilerContext(repository=repo)
        if self.context.dependencies is None:
            self.context.read_dependencies()
            if self.context.dependencies is None:
                self.context.load_context()

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

        if self.context is None or self.context.dependencies is None:
            self.build_dependencies()
        dependencies = self.context.dependencies

        imports = set()
        for m in list(filter(lambda i: i.get('id') == module,
                             dependencies.findall('./module'))):
            imports.update(set(i.get('module')
                               for i in m.findall('./imports/import')))
        depends = set()
        for m in dependencies:
            if list(filter(lambda i: i.get('module') == module,
                           m.findall('./imports/import'))):
                depends.add(m.get('id'))
            if list(filter(lambda i: i.get('module') == module,
                           m.findall('./includes/include'))):
                depends.add(m.get('id'))
        return (imports, depends)

    def compile(self, module):
        '''compile

        High-level api: Compile a module. The module cannot be a submodule.

        Parameters
        ----------

        module : `str`
            Module name that is inquired about.

        Returns
        -------

        Model
            A Model object.
        '''
        cached_tree = self._read_from_cache(module)

        if cached_tree is not None:
            return Model(cached_tree)

        varnames = Context.add_module.__code__.co_varnames
        imports, depends = self.get_dependencies(module)
        required_module_set = imports | depends
        required_module_set.add(module)
        self.context.internal_reset()
        for m in required_module_set:
            modulefile = os.path.join(self.context.repository.dirs[0],
                                      m + '.yang')
            if os.path.isfile(modulefile):
                with open(modulefile, 'r', encoding='utf-8') as f:
                    text = f.read()
                kwargs = {
                    'ref': modulefile,
                    'text': text,
                }
                if 'primary_module' in varnames:
                    kwargs['primary_module'] = True
                if 'format' in varnames:
                    kwargs['format'] = 'yang'
                if 'in_format' in varnames:
                    kwargs['in_format'] = 'yang'
                self.context.add_module(**kwargs)
        self.context.validate_context()
        vm = self.context.get_module(module)
        st = etree.Element(vm.arg)
        st.set('type', vm.keyword)
        statement = vm.search_one('prefix')
        if statement is None:
            raise ValueError("Module '{}' is a {} which belongs to '{}'. "
                             "Please compile '{}' instead."
                             .format(module, vm.keyword,
                                     vm.i_including_modulename,
                                     vm.i_including_modulename))
        else:
            st.set('prefix', statement.arg)

        for m_statement in self.context.modules.values():
            if m_statement.keyword == 'module':
                namespace = etree.SubElement(st, 'namespace')
                namespace.set('prefix', m_statement.i_prefix)
                statement = m_statement.search_one('namespace')
                if statement is not None:
                    namespace.text = statement.arg
                    self.module_namespaces[m_statement.i_modulename] = \
                        statement.arg
                    etree.register_namespace(
                        m_statement.i_prefix, statement.arg)

                # prepare self.module_prefixes
                self.module_prefixes[m_statement.i_modulename] = \
                    m_statement.i_prefix

                # prepare self.identity_deps
                for idn in m_statement.i_identities.values():
                    curr_idn = m_statement.arg + ':' + idn.arg
                    base_idn = idn.search_one("base")
                    if base_idn is None:
                        # identity does not have a base
                        self.identity_deps.setdefault(curr_idn, [])
                    else:
                        # identity has a base
                        base_idns = base_idn.arg.split(':')
                        if len(base_idns) > 1:
                            # base is located in another module
                            mn = m_statement.i_prefixes.get(base_idns[0])
                            b_idn = base_idns[1] if mn is None \
                                else mn[0] + ':' + base_idns[1]
                        else:
                            b_idn = module + ':' + base_idn.arg
                        if self.identity_deps.get(b_idn) is None:
                            self.identity_deps.setdefault(b_idn, [])
                        else:
                            self.identity_deps[b_idn].append(curr_idn)

        for child in vm.i_children:
            if child.keyword in statements.data_definition_keywords:
                self.depict_a_schema_node(vm, st, child)
        for child in vm.i_children:
            if child.keyword == 'rpc':
                self.depict_a_schema_node(vm, st, child, mode='rpc')
        for child in vm.i_children:
            if child.keyword == 'notification':
                self.depict_a_schema_node(vm, st, child, mode='notification')

        self._write_to_cache(module, st)

        return Model(st)

    def depict_a_schema_node(self, module, parent, child, mode=None):
        n = etree.SubElement(
            parent, '{' +
            self.module_namespaces[child.i_module.i_modulename] +
            '}' + child.arg)
        self.set_access(child, n, mode)
        n.set('type', child.keyword)
        sm = child.search_one('status')
        if sm is not None and sm.arg in ['deprecated', 'obsolete']:
            n.set('status', sm.arg)
        sm = child.search_one('default')
        if sm is not None:
            n.set('default', sm.arg)
        if child.keyword == 'list':
            sm = child.search_one('key')
            if sm is not None:
                n.set('key', sm.arg)
            sm = child.search_one('ordered-by')
            if sm is not None and sm.arg == 'user':
                n.set('ordered-by', 'user')
        elif child.keyword == 'container':
            sm = child.search_one('presence')
            if sm is not None:
                n.set('presence', 'true')
        elif child.keyword == 'choice':
            sm = child.search_one('mandatory')
            if sm is not None and sm.arg == 'true':
                n.set('mandatory', 'true')
            cases = [c.arg for c in child.search('case')]
            if cases:
                n.set('values', '|'.join(cases))
        elif child.keyword in ['leaf', 'leaf-list']:
            self.set_leaf_datatype_value(child, n)
            sm = child.search_one('mandatory')
            if (
                sm is not None and sm.arg == 'true' or
                hasattr(child, 'i_is_key')
            ):
                n.set('mandatory', 'true')

            if hasattr(child, 'i_is_key'):
                n.set('is_key', 'true')

            if child.keyword == 'leaf-list':
                sm = child.search_one('ordered-by')
                if sm is not None and sm.arg == 'user':
                    n.set('ordered-by', 'user')

        # Tailf annotations
        for ch in child.substmts:
            if (
                isinstance(ch.keyword, tuple) and
                'tailf' in ch.keyword[0]
            ):
                if (
                    ch.keyword[0] in self.module_namespaces and
                    len(ch.keyword) == 2
                ):
                    n.set(
                        etree.QName(self.module_namespaces[ch.keyword[0]],
                                    ch.keyword[1]),
                        ch.arg if ch.arg else '',
                    )
                else:
                    logger.warning("Special Tailf annotation at {}, "
                                   "keyword = {}"
                                   .format(ch.pos, ch.keyword))

        featurenames = [f.arg for f in child.search('if-feature')]
        if hasattr(child, 'i_augment'):
            featurenames.extend([
                f.arg for f in child.i_augment.search('if-feature')
                if f.arg not in featurenames
            ])
        if featurenames:
            n.set('if-feature', ' '.join(featurenames))

        if hasattr(child, 'i_children'):
            for c in child.i_children:
                if mode == 'rpc' and c.keyword in ['input', 'output']:
                    self.depict_a_schema_node(module, n, c, mode=c.keyword)
                else:
                    self.depict_a_schema_node(module, n, c, mode=mode)

    @staticmethod
    def set_access(statement, node, mode):
        if (
            mode in ['input', 'rpc'] or
            statement.keyword == 'rpc' or
            statement.keyword == ('tailf-common', 'action')
        ):
            node.set('access', 'write')
        elif (
            mode in ['output', 'notification'] or
            statement.keyword == 'notification'
        ):
            node.set('access', 'read-only')
        elif hasattr(statement, 'i_config') and statement.i_config:
            node.set('access', 'read-write')
        else:
            node.set('access', 'read-only')

    def set_leaf_datatype_value(self, leaf_statement, leaf_node):
        sm = leaf_statement.search_one('type')
        if sm is None:
            datatype = ''
        else:
            if sm.arg == 'leafref':
                p = sm.search_one('path')
                if p is not None:
                    # Try to make the path as compact as possible.
                    # Remove local prefixes, and only use prefix when
                    # there is a module change in the path.
                    target = []
                    curprefix = leaf_statement.i_module.i_prefix
                    for name in p.arg.split('/'):
                        if name.find(":") == -1:
                            prefix = curprefix
                        else:
                            [prefix, name] = name.split(':', 1)
                        if prefix == curprefix:
                            target.append(name)
                        else:
                            target.append(prefix + ':' + name)
                            curprefix = prefix
                    datatype = "-> %s" % "/".join(target)
                else:
                    datatype = sm.arg
            elif sm.arg == 'identityref':
                idn_base = sm.search_one('base')
                datatype = sm.arg + ":" + idn_base.arg
            else:
                datatype = sm.arg
            leaf_node.set('datatype', datatype)

            type_values = self.type_values(sm)
            if type_values:
                leaf_node.set('values', type_values)
            if sm.arg == 'union':
                leaf_node.set(
                    'unionmembertypes',
                    '|'.join([m.arg for m in sm.search('type')])
                )

    def type_values(self, type_statement):
        if type_statement is None:
            return ''
        if (
            type_statement.i_is_derived is False and
            type_statement.i_typedef is not None
        ):
            return self.type_values(
                type_statement.i_typedef.search_one('type'))
        if type_statement.arg == 'boolean':
            return 'true|false'
        if type_statement.arg == 'union':
            return self.type_union_values(type_statement)
        if type_statement.arg == 'enumeration':
            return '|'.join([e.arg for e in type_statement.search('enum')])
        if type_statement.arg == 'identityref':
            return self.type_identityref_values(type_statement)
        return ''

    def type_union_values(self, type_statement):
        vlist = []
        for type in type_statement.search('type'):
            v = self.type_values(type)
            if v:
                vlist.append(v)
        return '|'.join(vlist)

    def type_identityref_values(self, type_statement):
        base_idn = type_statement.search_one('base')
        if base_idn:
            # identity has a base
            base_idns = base_idn.arg.split(':')
            my_modulename = type_statement.i_module.i_modulename
            if len(base_idns) > 1:
                modulename = \
                    type_statement.i_module.i_prefixes.get(base_idns[0])
                if modulename is None:
                    return ''
                else:
                    idn_key = modulename[0] + ':' + base_idns[1]
            else:
                idn_key = my_modulename + ':' + base_idn.arg

            value_stmts = []
            values = self.identity_deps.get(idn_key, [])
            for value in values:
                ids = value.split(':')
                value_stmts.append(self.module_prefixes[ids[0]] + ':' + ids[1])
            if values:
                return '|'.join(value_stmts)
        return ''


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
            raise ValueError("cannot generate diff of different modules: "
                             "'{}' vs '{}'"
                             .format(model1.tree.tag, model2.tree.tag))

    def __bool__(self):
        if list(self.tree):
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
        for root in [i for i in tree if is_type(i, type)]:
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

        for child in node2:
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
        for child in node1:
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
        for child in node1:
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
            elif (
                type == 'container' or
                type == 'list' or
                type == 'choice' or
                type == 'case'
            ):
                if ModelDiff.trim(child, msg):
                    parent.remove(child)
        return len(list(parent)) == 0
