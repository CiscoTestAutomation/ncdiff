import re
import logging
from collections import OrderedDict

# create a logger for this module
logger = logging.getLogger(__name__)


class DictDiff(object):
    '''DictDiff

    Abstraction of diff between two dictionaries. If all keys and their values
    are same, two dictionaries are considered to be same. This class is
    intended to be used by class RunningConfigDiff.

    Attributes
    ----------
    diff : `OrderedDict`
        A nested OrderedDict. When a leaf has a value '+' or '-' it means the
        leaf is added or deleted. When a child OrderedDict has a key '' with
        a value '+' or '-', it means the child OrderedDict is added or deleted.
    '''

    def __init__(self, dict1, dict2):
        self.dict1 = dict1
        self.dict2 = dict2

    @property
    def diff(self):
        return self.compare(self.dict1, self.dict2)

    @staticmethod
    def compare(dict1, dict2):
        diff = OrderedDict()
        common_key_list = [k for k in dict1.keys() if k in dict2]
        key_list_1 = list(dict1.keys())
        key_list_2 = list(dict2.keys())
        previous_index_1 = previous_index_2 = 0
        for key in common_key_list:
            current_index_1 = key_list_1.index(key)
            for k in key_list_1[previous_index_1:current_index_1]:
                if isinstance(dict1[k], dict):
                    diff[k] = OrderedDict([('', '-')] + list(dict1[k].items()))
                else:
                    diff[k] = '-'
            previous_index_1 = current_index_1 + 1
            current_index_2 = key_list_2.index(key)
            for k in key_list_2[previous_index_2:current_index_2]:
                if isinstance(dict2[k], dict):
                    diff[k] = OrderedDict([('', '+')] + list(dict2[k].items()))
                else:
                    diff[k] = '+'
            previous_index_2 = current_index_2 + 1
            if dict1[key] != dict2[key]:
                if (
                    isinstance(dict1[key], dict) and
                    isinstance(dict2[key], dict)
                ):
                    diff[key] = DictDiff.compare(dict1[key], dict2[key])
                elif isinstance(dict1[key], dict):
                    diff[key] = OrderedDict(list(dict1[key].items()))
                    for k in dict1[key]:
                        if isinstance(dict1[key][k], dict):
                            diff[key][k][''] = '-'
                        else:
                            diff[key][k] = '-'
                elif isinstance(dict2[key], dict):
                    diff[key] = OrderedDict(list(dict2[key].items()))
                    for k in dict2[key]:
                        if isinstance(dict2[key][k], dict):
                            diff[key][k][''] = '+'
                        else:
                            diff[key][k] = '+'
        for k in key_list_1[previous_index_1:]:
            if isinstance(dict1[k], dict):
                diff[k] = OrderedDict([('', '-')] + list(dict1[k].items()))
            else:
                diff[k] = '-'
        for k in key_list_2[previous_index_2:]:
            if isinstance(dict2[k], dict):
                diff[k] = OrderedDict([('', '+')] + list(dict2[k].items()))
            else:
                diff[k] = '+'
        return diff


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

    diff : `OrderedDict`
        A OrderedDict from class DictDiff attribute diff.
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
        return self.dict2config(self.diff, diff_type=' ')

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
        if 'running-config' in diff_dict.diff:
            return diff_dict.diff['running-config']
        else:
            return None

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
                        dict_ret[last_line] = ' '
                last_line = line
                last_section = ''
                last_indentation = 0
        if last_indentation > 0:
            dict_ret[last_line] = self.config2dict(last_section)
        else:
            dict_ret[last_line] = ' '
        return dict_ret

    def dict2config(self, dict_in, diff_type=None):
        str_ret = ''
        if dict_in is None:
            return str_ret
        for k, v in dict_in.items():
            if k == '':
                continue
            if diff_type == ' ':
                if isinstance(v, dict):
                    local_diff_type = v.get('', ' ')
                else:
                    local_diff_type = v
            else:
                local_diff_type = diff_type
            if diff_type is not None:
                str_ret += local_diff_type + ' ' + k + '\n'
            else:
                str_ret += k + '\n'
            if isinstance(v, dict):
                str_ret += self.indent(
                    self.dict2config(v, diff_type=local_diff_type),
                )
        return str_ret

    def indent(self, str_in):
        str_ret = ''
        for line in str_in.splitlines():
            if line:
                if line[0] in '-+':
                    diff_type = line[0]
                    line = line[1:]
                    str_ret += diff_type + '  ' + line + '\n'
                else:
                    str_ret += '  ' + line + '\n'
        return str_ret
