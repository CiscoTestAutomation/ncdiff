import re
import logging
from copy import deepcopy
from collections import OrderedDict

# create a logger for this module
logger = logging.getLogger(__name__)


class DictDiff(object):
    '''DictDiff

    Abstraction of diff between two dictionaries. If all keys and their values
    are same, two dictionaries are considered to be same. This class is intended
    to be used by class RunningConfigDiff.

    Attributes
    ----------
    diff : `tuple`
        A tuple with two elements. First one is a dictionary that contains
        content in dict1 but not in dict2. Second one is a dictionary that
        contains content in dict2 but not in dict1.
    '''

    def __init__(self, dict1, dict2):
        self.dict1 = dict1
        self.dict2 = dict2

    @property
    def diff(self):
        diff1 = deepcopy(self.dict1)
        diff2 = deepcopy(self.dict2)
        self.simplify_single_dict(diff1, diff2)
        return (diff1, diff2)

    @staticmethod
    def simplify_single_dict(dict1, dict2):
        common_keys = set(dict1.keys()) & set(dict2.keys())
        for key in common_keys:
            if dict1[key] == dict2[key]:
                del dict1[key]
                del dict2[key]
            else:
                child1_is_dict = isinstance(dict1[key], dict)
                child2_is_dict = isinstance(dict2[key], dict)
                if child1_is_dict and child2_is_dict:
                    DictDiff.simplify_single_dict(dict1[key], dict2[key])
                    if not dict1[key]:
                        del dict1[key]
                    if not dict2[key]:
                        del dict2[key]
                elif child1_is_dict and not child2_is_dict:
                    del dict2[key]
                elif child2_is_dict and not child1_is_dict:
                    del dict1[key]


class RunningConfigDiff(object):
    '''RunningConfigDiff

    Abstraction of diff between two Cisco running-configs. It supports str()
    which returns a string showing the differences between running1 and
    running2.

    Attributes
    ----------
    running1 : `str`
        First Cisco running-config.

    running2 : `str`
        Second Cisco running-config.

    diff : `tuple`
        A tuple with two elements. First one is the running-config in running1
        but not in running2. Second one is the running-config in running2 but
        not in running1.
    '''

    def __init__(self, running1, running2):
        '''
        __init__ instantiates a RunningConfigDiff instance.
        '''

        self.running1 = running1
        self.running2 = running2

    def __bool__(self):
        diff1, diff2 = self.diff
        if diff1 or diff2:
            return True
        else:
            return False

    def __str__(self):
        diff1, diff2 = self.diff
        return '\n'.join(['-   ' + l for l in diff1.splitlines()] +
                         ['+   ' + l for l in diff2.splitlines()])

    def __eq__(self, other):
        if str(self) == str(other):
            return True
        else:
            return False

    @property
    def diff(self):
        dict1 = self.running2dict(self.running1)
        dict2 = self.running2dict(self.running2)
        diff_dict = DictDiff(dict1, dict2)
        diff1, diff2 = diff_dict.diff
        return (self.dict2running(diff1), self.dict2running(diff2))

    def running2dict(self, str_in):
        str_in = str_in.replace('exit-address-family', ' exit-address-family')
        dict_ret = OrderedDict()
        dict_ret['running-config'] = self.config2dict(str_in)
        return dict_ret

    def dict2running(self, dict_in):
        if dict_in:
            return self.dict2config(dict_in['running-config'])
        else:
            return ''

    def config2dict(self, str_in):
        dict_ret = OrderedDict()
        last_line = ''
        last_section = ''
        last_indentation = 0
        for line in str_in.splitlines():
            if len(line.strip()) > 22 and \
               line[:22] == 'Building configuration':
                continue
            if len(line.strip()) > 21 and \
               line[:21] == 'Current configuration':
                continue
            if len(line.strip()) == 0:
                continue
            if re.search('^ *!', line):
                continue
            if line[0] == ' ':
                if last_indentation == 0:
                    last_indentation = len(re.search('^ *', line).group(0))
                last_section += line[last_indentation:] + '\n'
            else:
                if last_line:
                    if last_indentation > 0:
                        dict_ret[last_line] = self.config2dict(last_section)
                    else:
                        dict_ret[last_line] = ''
                last_line = line
                last_section = ''
                last_indentation = 0
        if last_indentation > 0:
            dict_ret[last_line] = self.config2dict(last_section)
        else:
            dict_ret[last_line] = ''
        return dict_ret

    def dict2config(self, dict_in):
        str_ret = ''
        for k, v in dict_in.items():
            str_ret += k + '\n'
            if type(v) is OrderedDict:
                str_ret += self.indent(self.dict2config(v))
        return str_ret

    def indent(self, str_in):
        str_ret = ''
        for line in str_in.splitlines():
            str_ret += ' ' + line + '\n'
        return str_ret
