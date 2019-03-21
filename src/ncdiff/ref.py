import re

from .errors import ConfigError
from .composer import Tag


class IdentityRef(object):
    '''IdentityRef

    A class to process YANG built-in type identityref.

    Attributes
    ----------
    device : `object`
        An instance of yang.ncdiff.ModelDevice, which represents a modeled
        device.

    node : `Element`
        A data node of type identityref.

    to_node : `Element`
        Another data node of type identityref.

    converted : `str`
        Converted text value of node, based on to_node.nsmap.
    '''

    def __init__(self, device, node, to_node=None):
        '''
        __init__ instantiates a IdentityRef instance.
        '''

        self.device = device
        self.node = node
        self.to_node = to_node

    @property
    def converted(self):
        if self.node.text is None:
            raise ConfigError("node {} is an identityref but no value" \
                              .format(self.device.get_xpath(self.node)))
        return self.convert(self.node.text, to_node=self.to_node)

    @property
    def default(self):
        if self.node.text is None:
            raise ConfigError("node {} is an identityref but no value" \
                              .format(self.device.get_xpath(self.node)))
        return self.convert(self.node.text, to_node=None)

    def parse_prefixed_id(self, id, node):
        match = re.search(Tag.COLON[0], id)
        if match:
            if match.group(1) in node.nsmap:
                return node.nsmap[match.group(1)], match.group(2)
            else:
                raise ConfigError("unknown prefix '{}' in node {}" \
                                  .format(match.group(1),
                                          self.device.get_xpath(node)))
        else:
            if None in node.nsmap:
                return node.nsmap[None], id
            else:
                raise ConfigError("fail to find default namespace of " \
                                  "node {}" \
                                  .format(self.device.get_xpath(node)))

    def compose_prefixed_id(self, url, id, to_node=None):
        def url_to_name(url):
            return self.device.convert_ns(url,
                                          src=Tag.NAMESPACE,
                                          dst=Tag.NAME)

        if to_node is None:
            return '{}:{}'.format(url_to_name(url), id)
        else:
            url_to_prefix = {v: k for k, v in to_node.nsmap.items()}
            if url in url_to_prefix:
                if url_to_prefix[url] is None:
                    return '{}'.format(id)
                else:
                    return '{}:{}'.format(url_to_prefix[url], id)
            else:
                raise ConfigError("URL '{}' is not found in to_node.nsmap " \
                                  "{}, where to_node is {}" \
                                  .format(url, to_node.nsmap,
                                          self.device.get_xpath(to_node)))

    def convert(self, tag, to_node=None):
        url, id = self.parse_prefixed_id(tag, self.node)
        return self.compose_prefixed_id(url, id, to_node=to_node)

    def parse_instanceid(self, node, to_node=None):
        if node.text is None:
            raise ConfigError("node {} is an instance-identifier but no value" \
                              .format(self.device.get_xpath(node)))
        tag = ''
        new_instanceid = ''
        expecting = '*./'
        for char in node.text:
            if char in '/.[]=*':
                new_instanceid += char
                if tag:
                    url, id = self.parse_prefixed_id(tag, node)
                    tag = ''
                    new_instanceid += self.compose_prefixed_id(url, id,
                                                               to_node=to_node)
            else:
                tag += char
        if tag:
            url, id = self.parse_prefixed_id(tag, node)
            new_instanceid += self.compose_prefixed_id(url, id,
                                                       to_node=to_node)
        return new_instanceid


class InstanceIdentifier(IdentityRef):
    '''InstanceIdentifier

    A class to process YANG built-in type instance-identifier.

    Attributes
    ----------
    device : `object`
        An instance of yang.ncdiff.ModelDevice, which represents a modeled
        device.

    node : `Element`
        A data node of type instance-identifier.

    to_node : `Element`
        Another data node of type instance-identifier.

    converted : `str`
        Converted text value of node, based on to_node.nsmap.
    '''

    def __init__(self, device, node, to_node=None):
        '''
        __init__ instantiates a InstanceIdentifier instance.
        '''

        IdentityRef.__init__(self, device, node, to_node=to_node)
        self.str_list = [(self.node.text, 0, self.node.text)]

    @property
    def converted(self):
        self.str_list = [(self.node.text, 0, self.node.text)]
        self.parse_quote()
        self.parse_square_bracket(to_node=self.to_node)
        self.parse_element(to_node=self.to_node)
        return ''.join([p[2] for p in self.str_list])

    @property
    def default(self):
        self.str_list = [(self.node.text, 0, self.node.text)]
        self.parse_quote()
        self.parse_square_bracket()
        self.parse_element()
        return ''.join([p[2] for p in self.str_list])

    def string(self, phase_num):
        return ''.join([p[0] for p in self.str_list
                        if p[1] == 0 or p[1] >= phase_num])

    def cut(self, start_idx, end_idx, converted_str, phase_num):
        def this_piece(idx, start_idx, end_idx, converted_str, phase_num):
            string = self.str_list[idx][0]
            original_phase_num = self.str_list[idx][1]
            ret = [(string[:start_idx], original_phase_num, string[:start_idx]),
                   (string[start_idx:end_idx], phase_num, converted_str),
                   (string[end_idx:], original_phase_num, string[end_idx:])]
            return [piece for piece in ret if piece[0]]

        def all_pieces(idx, start_idx, end_idx, converted_str, phase_num):
            return self.str_list[:idx] + \
                   this_piece(idx, start_idx, end_idx,
                              converted_str, phase_num) + \
                   self.str_list[idx+1:]

        str_len = end_idx - start_idx
        position = 0
        for idx, piece in enumerate(self.str_list):
            if piece[1] == 0 or piece[1] == phase_num:
                end_position = position + len(piece[0])
                if start_idx >= position and end_idx <= end_position:
                    self.str_list = all_pieces(idx,
                                               start_idx-position,
                                               end_idx-position,
                                               converted_str,
                                               phase_num)
                    return
                position += len(piece[0])

    def parse_quote(self):
        string = self.string(1)
        start_idx = None
        for idx, char in enumerate(string):
            if start_idx is None and char == '=':
                start_idx = idx + 1
            elif start_idx is not None and idx == start_idx:
                if char != "'":
                    raise ConfigError("do not see a single quote after '=' " \
                                      "in node {}" \
                                      .format(self.device.get_xpath(self.node)))
            elif start_idx is not None and idx > start_idx:
                if char == "'":
                    end_idx = idx + 1
                    self.cut(start_idx, end_idx, string[start_idx:end_idx], 1)
                    start_idx = None
        if start_idx is not None:
            raise ConfigError('found opening single quote, but not the ' \
                              'closing quote in node {}' \
                              .format(self.device.get_xpath(self.node)))

    def parse_square_bracket(self, to_node=None):
        string = self.string(2)
        start_idx = None
        for idx, char in enumerate(string):
            if start_idx is None and char == '[':
                start_idx = idx
            elif start_idx is not None and idx > start_idx:
                if char == "]":
                    end_idx = idx + 1
                    substring = string[start_idx:end_idx]
                    self.cut(start_idx, start_idx+1, '[', 2)
                    self.cut(end_idx-1, end_idx, ']', 2)
                    if substring[-2] == '=':
                        tag = substring[1:-2]
                        self.cut(end_idx-2, end_idx-1, '=', 2)
                        if tag == '.':
                            self.cut(start_idx+1, end_idx-2, '.', 2)
                        else:
                            self.cut(start_idx+1, end_idx-2,
                                     self.convert(tag, to_node=to_node), 2)
                        start_idx = None
                    else:
                        if re.search('^\[[1-9][0-9]*\]$', substring):
                            numbers = substring[1:-1]
                            self.cut(start_idx+1, end_idx-1, numbers, 2)
                        else:
                            tag = substring[1:-1]
                            self.cut(start_idx+1, end_idx-1,
                                     self.convert(tag, to_node=to_node), 2)
                        start_idx = None
        if start_idx is not None:
            raise ConfigError('found opening square bracket, but not the ' \
                              'closing bracket in node {}' \
                              .format(self.device.get_xpath(self.node)))

    def parse_element(self, to_node=None):
        SEPARATORS = "./"
        string = self.string(3)
        start_idx = None
        for idx, char in enumerate(string):
            if start_idx is None and char not in SEPARATORS:
                start_idx = idx
            elif start_idx is not None and char in SEPARATORS:
                end_idx = idx
                tag = string[start_idx:end_idx]
                if tag == '*':
                    self.cut(start_idx, end_idx, '*', 3)
                else:
                    self.cut(start_idx, end_idx,
                             self.convert(tag, to_node=to_node), 3)
                start_idx = None
        if start_idx is not None:
            end_idx = idx + 1
            tag = string[start_idx:end_idx]
            if tag == '*':
                self.cut(start_idx, end_idx, '*', 3)
            else:
                self.cut(start_idx, end_idx,
                         self.convert(tag, to_node=to_node), 3)
