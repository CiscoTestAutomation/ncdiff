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
        self.node_url = self.device.convert_tag('', self.node.tag)[0]
        self._default_ns = {}

    @property
    def converted(self):
        if self.node.text is None:
            raise ConfigError("the node with tag {} is an identityref but no " \
                              "value" \
                              .format(self.node.tag))
        return self.convert(self.node.text, to_node=self.to_node)

    @property
    def default(self):
        if self.node.text is None:
            raise ConfigError("the node with tag {} is an identityref but no " \
                              "value" \
                              .format(self.node.tag))
        return self.convert(self.node.text, to_node=None)

    @property
    def default_ns(self):
        self._default_ns = {None: self.node_url}
        self.default
        return self._default_ns

    def parse_prefixed_id(self, id, node):
        match = re.search(Tag.COLON[0], id)
        if match:
            if match.group(1) in node.nsmap:
                return node.nsmap[match.group(1)], match.group(2)
            elif match.group(1) in [ns[0] for ns in self.device.namespaces]:
                name_to_url = {ns[0]: ns[2] for ns in self.device.namespaces}
                return name_to_url[match.group(1)], match.group(2)
            else:
                raise ConfigError("unknown prefix '{}' in the node with tag " \
                                  "{}" \
                                  .format(match.group(1), node.tag))
        else:
            # RFC7950 section 9.10.3 and RFC7951 section 6.8
            if None in node.nsmap:
                return node.nsmap[None], id
            else:
                raise ConfigError("fail to find default namespace of " \
                                  "the node with tag {}" \
                                  .format(node.tag))

    def compose_prefixed_id(self, url, id, to_node=None):
        def url_to_name(url, ns):
            model_name = self.device.convert_ns(url,
                                                src=Tag.NAMESPACE,
                                                dst=Tag.NAME)
            if url not in ns.values():
                ns[model_name] = url
            return model_name

        if to_node is None:
            # RFC7951 section 6.8
            if url == self.node_url:
                return id
            else:
                return '{}:{}'.format(url_to_name(url, self._default_ns), id)
        else:
            # RFC7950 section 9.10.3
            url_to_prefix = {v: k for k, v in to_node.nsmap.items()}
            if url in url_to_prefix:
                if url_to_prefix[url] is None:
                    return '{}'.format(id)
                else:
                    return '{}:{}'.format(url_to_prefix[url], id)
            else:
                raise ConfigError("URL '{}' is not found in to_node.nsmap " \
                                  "{}, where the to_node has tag {}" \
                                  .format(url, to_node.nsmap, to_node.tag))

    def convert(self, tag, to_node=None):
        url, id = self.parse_prefixed_id(tag, self.node)
        return self.compose_prefixed_id(url, id, to_node=to_node)

    def parse_instanceid(self, node, to_node=None):
        if node.text is None:
            raise ConfigError("the node with tag {} is an " \
                              "instance-identifier but no value" \
                              .format(node.tag))
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
        self.convert_str_list(to_node=self.to_node)
        return ''.join([p[2] for p in self.str_list])

    @property
    def default(self):
        self.str_list = [(self.node.text, 0, self.node.text)]
        self.parse_quote()
        self.parse_square_bracket()
        self.parse_element()
        self.convert_str_list()
        return ''.join([p[2] for p in self.str_list])

    def string(self, phase_num):
        return ''.join([p[0] for p in self.str_list
                        if p[1] == 0 or p[1] >= phase_num])

    def parse_prefixed_id(self, id, node):
        match = re.search(Tag.COLON[0], id)
        if match:
            if match.group(1) in node.nsmap:
                return node.nsmap[match.group(1)], match.group(2)
            elif match.group(1) in [ns[0] for ns in self.device.namespaces]:
                name_to_url = {ns[0]: ns[2] for ns in self.device.namespaces}
                return name_to_url[match.group(1)], match.group(2)
            else:
                raise ConfigError("unknown prefix '{}' in the node with tag " \
                                  "{}" \
                                  .format(match.group(1), node.tag))
        else:
            # RFC7950 section 9.13.2 and RFC7951 section 6.11
            return None, id

    def compose_prefixed_id(self, url, id, to_node=None):
        def url_to_name(url, ns):
            model_name = self.device.convert_ns(url,
                                                src=Tag.NAMESPACE,
                                                dst=Tag.NAME)
            if url not in ns.values():
                ns[model_name] = url
            return model_name

        # RFC7950 section 9.13.2
        if to_node is None:
            return '{}:{}'.format(url_to_name(url, self._default_ns), id)
        else:
            url_to_prefix = {v: k for k, v in to_node.nsmap.items()
                                  if k is not None}
            if url in url_to_prefix:
                return '{}:{}'.format(url_to_prefix[url], id)
            else:
                raise ConfigError("URL '{}' is not found in to_node.nsmap {} " \
                                  "(default namespace cannot be used here), " \
                                  "where the to_node has tag {}" \
                                  .format(url, to_node.nsmap, to_node.tag))

    def convert_str_list(self, to_node=None):
        default_url = None
        new_str_list = []
        for piece in self.str_list:
            if piece[1] <= 1:
                new_str_list.append(piece)
            elif piece[1] == 2:
                if piece[0] == '[' or \
                   piece[0] == ']' or \
                   piece[0] == '=' or \
                   piece[0] == '.':
                    new_str_list.append((piece[0], piece[1], piece[0]))
                else:
                    url, id = self.parse_prefixed_id(piece[0], self.node)
                    if url is None:
                        url = default_url
                    if url is None:
                        raise ConfigError("in the instance-identifier node " \
                                          "with tag {}, the leftmost data " \
                                          "node name '{}' is not in " \
                                          "namespace-qualified form" \
                                          .format(self.node.tag, piece[0]))
                    else:
                        converted_id = self.compose_prefixed_id(url, id,
                                                                to_node=to_node)
                        new_str_list.append((piece[0], piece[1], converted_id))
            elif piece[1] == 3:
                url, id = self.parse_prefixed_id(piece[0], self.node)
                if url is not None:
                    default_url = url
                if default_url is None:
                    raise ConfigError("in the instance-identifier node " \
                                      "with tag {}, the leftmost data " \
                                      "node name '{}' is not in " \
                                      "namespace-qualified form" \
                                      .format(self.node.tag, piece[0]))
                else:
                    converted_id = self.compose_prefixed_id(default_url, id,
                                                            to_node=to_node)
                    new_str_list.append((piece[0], piece[1], converted_id))
        self.str_list = new_str_list

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

    @staticmethod
    def convert_literal(literal):
        converted_literal = literal[1:-1]
        converted_literal = re.sub("'", "''", converted_literal)
        return "'" + re.sub('""', '"', converted_literal) + "'"

    def parse_quote(self):
        string = self.string(1)
        start_idx = None
        start_escape = None
        for idx, char in enumerate(string):
            if start_idx is None and char == '=':
                start_idx = idx + 1
            elif start_idx is not None and idx == start_idx:
                if char != "'" and char != '"':
                    raise ConfigError("do not see a apostrophe or double " \
                                      "quote after '=' in the node with tag " \
                                      "{}" \
                                      .format(self.node.tag))
                else:
                    opening_quote = char
            elif start_idx is not None and idx > start_idx:
                if char == opening_quote:
                    if idx < len(string)-1 and string[idx+1] == opening_quote:
                        start_escape = idx
                        continue
                    end_escape = idx + 1
                    if start_escape is not None and \
                       (end_escape-start_escape)%2 == 0:
                        start_escape = None
                        continue
                    end_idx = idx + 1
                    if opening_quote == '"':
                        default_literal = \
                            self.convert_literal(string[start_idx:end_idx])
                    else:
                        default_literal = string[start_idx:end_idx]
                    self.cut(start_idx, end_idx, default_literal, 1)
                    start_idx = None
        if start_idx is not None:
            raise ConfigError('found opening apostrophe or double quote, but ' \
                              'not the closing one in the node with tag {}' \
                              .format(self.node.tag))

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
                            self.cut(start_idx+1, end_idx-2, tag, 2)
                        start_idx = None
                    else:
                        if re.search('^\[[1-9][0-9]*\]$', substring):
                            numbers = substring[1:-1]
                            self.cut(start_idx+1, end_idx-1, numbers, 2)
                        else:
                            tag = substring[1:-1]
                            self.cut(start_idx+1, end_idx-1, tag, 2)
                        start_idx = None
        if start_idx is not None:
            raise ConfigError('found opening square bracket, but not the ' \
                              'closing bracket in the node with tag {}' \
                              .format(self.node))

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
                    self.cut(start_idx, end_idx, tag, 3)
                start_idx = None
        if start_idx is not None:
            end_idx = idx + 1
            tag = string[start_idx:end_idx]
            if tag == '*':
                self.cut(start_idx, end_idx, '*', 3)
            else:
                self.cut(start_idx, end_idx, tag, 3)
