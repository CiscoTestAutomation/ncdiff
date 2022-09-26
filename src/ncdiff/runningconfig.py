import re
import logging

# create a logger for this module
logger = logging.getLogger(__name__)


class ListDiff(object):
    '''ListDiff

    Abstraction of diff between two lists. Each item in the list is a tuple.
    If all tuples are same, two lists are considered to be same. This class is
    intended to be used by class RunningConfigDiff.

    Attributes
    ----------
    diff : `list`
        A list whose items are tuples. The first item in the tuple is
        the config line and the second item is its next level config. If a
        config line does not have next level config, the second item value is
        None. Otherwise, the value is a list of tuples. The third item in the
        tuple has three possible values: '+' means the config is added; '-'
        means it is deleted; '' means it remiains unchnaged but for some reason
        it is needed (e.g., as a position reference).
    '''

    def __init__(self, list1, list2):
        self.list1 = list1
        self.list2 = list2

    @property
    def diff(self):
        return self.compare(self.list1, self.list2)

    @staticmethod
    def compare(list1, list2):
        diff_1 = []
        key_list_1 = [i[0] for i in list1]
        key_list_2 = [i[0] for i in list2]
        common_key_list = [k for k in key_list_1 if k in key_list_2]
        if common_key_list:
            common_1 = list(filter(lambda x: x in common_key_list, key_list_1))
            common_2 = list(filter(lambda x: x in common_key_list, key_list_2))
            common_key_list = []
            list1_index = 0
            for k2 in common_2:
                if k2 in common_1[list1_index:]:
                    common_key_list.append(k2)
                    list1_index = common_1.index(k2)

        previous_index_1 = previous_index_2 = 0
        for key in common_key_list:
            current_index_1 = key_list_1.index(key)
            current_index_2 = key_list_2.index(key)

            # Stuff in list1 before a common key but not in list2
            for k, v, i in list1[previous_index_1:current_index_1]:
                diff_1.append((k, v, '-'))

            # Stuff in list2 before a common key but not in list1
            for k, v, i in list2[previous_index_2:current_index_2]:
                diff_1.append((k, v, '+'))

            # Stuff of the common key itself
            if list1[current_index_1][1] == list2[current_index_2][1]:
                if list1[current_index_1][1] is None:
                    diff_1.append((key, None, '?'))
                else:
                    diff_1.append((key, [
                        (k, v, '')
                        for k, v, i in list1[current_index_1][1]], '?'))
            else:
                if (
                    list1[current_index_1][1] is not None and
                    list2[current_index_2][1] is not None
                ):
                    diff_1.append((key, ListDiff.compare(
                        list1[current_index_1][1],
                        list2[current_index_2][1],
                    ), ''))
                elif list1[current_index_1][1] is not None:
                    diff_1.append((key, [
                        (k, v, '-')
                        for k, v, i in list1[current_index_1][1]], ''))
                elif list2[current_index_2][1] is not None:
                    diff_1.append((key, [
                        (k, v, '+')
                        for k, v, i in list2[current_index_2][1]], ''))

            previous_index_1 = current_index_1 + 1
            previous_index_2 = current_index_2 + 1

        # Stuff after all common keys
        for k, v, i in list1[previous_index_1:]:
            diff_1.append((k, v, '-'))
        for k, v, i in list2[previous_index_2:]:
            diff_1.append((k, v, '+'))

        # Cleanup
        diff_2 = []
        keys_before = set()
        for index, item in enumerate(diff_1):
            key, value, info = item
            if info == '?':
                keys_after = set([k for k, v, i in diff_1[index+1:]])
                if keys_before & keys_after:
                    diff_2.append((key, value, ''))
            else:
                diff_2.append((key, value, info))
            keys_before.add(key)

        return diff_2


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

    diff : `list`
        A list from class ListDiff attribute diff.
    '''

    def __init__(self, running1, running2):
        '''
        __init__ instantiates a RunningConfigDiff instance.
        '''

        self.running1 = running1
        self.running2 = running2

    def __bool__(self):
        return bool(self.diff)

    def __str__(self):
        return self.list2config(self.diff, diff_type='')

    def __eq__(self, other):
        if str(self) == str(other):
            return True
        else:
            return False

    @property
    def diff(self):
        list1 = self.running2list(self.running1)
        list2 = self.running2list(self.running2)
        diff_list = ListDiff(list1, list2).diff
        if diff_list:
            return diff_list
        else:
            return None

    def running2list(self, str_in):
        str_in = str_in.replace('exit-address-family', ' exit-address-family')
        return self.config2list(str_in)

    def config2list(self, str_in):
        list_ret = []
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
                current_indentation = len(re.search('^ *', line).group(0))
                if last_indentation == 0:
                    last_indentation = current_indentation

                # There might be special cases. For example, the following
                # running-config:
                # ip dhcp class CLASS1
                #    relay agent information
                #  relay-information hex 01040101030402020102
                # should be considered as:
                # ip dhcp class CLASS1
                #    relay agent information
                #     relay-information hex 01040101030402020102
                if current_indentation < last_indentation:
                    last_section += ' ' * (last_indentation + 1) + \
                        line[current_indentation:] + '\n'
                else:
                    last_section += line[last_indentation:] + '\n'
            else:
                if last_line:
                    if last_indentation > 0:
                        list_ret.append((
                            last_line, self.config2list(last_section), ''))
                    else:
                        list_ret.append((last_line, None, ''))
                last_line = line
                last_section = ''
                last_indentation = 0
        if last_indentation > 0:
            list_ret.append((last_line, self.config2list(last_section), ''))
        else:
            list_ret.append((last_line, None, ''))
        return list_ret

    def list2config(self, list_in, diff_type=None):
        str_ret = ''
        if list_in is None:
            return str_ret
        for k, v, i in list_in:
            if k == '':
                continue
            if diff_type == '':
                local_diff_type = i
            else:
                local_diff_type = diff_type
            if diff_type is None:
                str_ret += '  ' + k + '\n'
            else:
                prefix = local_diff_type if local_diff_type != '' else ' '
                str_ret += prefix + ' ' + k + '\n'
            if v is not None:
                str_ret += self.indent(
                    self.list2config(v, diff_type=local_diff_type),
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
