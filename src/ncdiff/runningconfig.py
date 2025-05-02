import re
import logging


# create a logger for this module
logger = logging.getLogger(__name__)

# Some no commands are not forgiving, e.g., "no license boot level
# network-advantage addon dna-advantage" is rejected, but "no license boot
# level" is acceptable. These cases are listed in SHORT_NO_COMMANDS.
SHORT_NO_COMMANDS = [
    'no license boot level ',
    'no transport input ',
    'no transport output ',
    'no ip address ',
    'no ipv6 address ',
]

# Normally two positive commands, when one contains the other, cannot coexist.
# For example:
# exception crashinfo
# exception crashinfo file bootflash:test
#
# Only the longer one is required:
# exception crashinfo file bootflash:test
#
# But there are special cases do not follow this rule. Both lines are required:
# snmp-server manager
# snmp-server manager session-timeout 100
#
# These cases can be recorded here.
COEXIST_SHORT_POSITIVE_COMMANDS = [
    'snmp-server manager',
]

# Some commands are orderless, e.g., "show running-config" output could be:
# aaa authentication login admin-con group tacacs+ local
# aaa authentication login admin-vty group tacacs+ local
#
# Or in other times it is displayed in a different order:
# aaa authentication login admin-vty group tacacs+ local
# aaa authentication login admin-con group tacacs+ local
#
# Since "aaa authentication login" is orderless at the the global config
# level, regexp and depth are defined as "^ *aaa authentication login " and 0.
#
# In another example, "show running-config" output could be:
# flow monitor meraki_monitor
#   exporter meraki_exporter
#   exporter customer_exporter
#   record meraki_record
#
# Or in other times it is displayed in a different order:
# flow monitor meraki_monitor
#   exporter customer_exporter
#   exporter meraki_exporter
#   record meraki_record
#
# Here the config "exporter" at the second level is orderless. so regexp and
# depth are defined as "^ *exporter " and 1.
ORDERLESS_COMMANDS = [
    (re.compile(r'^ *aaa authentication '), 0),
    (re.compile(r'^ *aaa accounting system default '), 0),
    (re.compile(r'^ *aaa group server '), 0),
    (re.compile(r'^ *radius server '), 0),
    (re.compile(r'^ *logging host '), 0),
    (re.compile(r'^ *flow exporter '), 0),
    (re.compile(r'^ *flow record '), 0),
    (re.compile(r'^ *flow monitor '), 0),
    (re.compile(r'^ *flow file-export '), 0),
    (re.compile(r'^ *exporter '), 1),
    (re.compile(r'^ *dot1x '), 0),
    (re.compile(r'^ *service-template '), 0),
    (re.compile(r'^ *redundancy'), 0),
    (re.compile(r'^ *username '), 0),
    (re.compile(r'^ *parameter-map type '), 0),
    (re.compile(r'^ *match ipv4 '), 1),
    (re.compile(r'^ *match ipv6 '), 1),
    (re.compile(r'^ *collect connection '), 1),
    (re.compile(r'^ *l2nat instance '), 0),
    (re.compile(r'^ *inside from host '), 1),
    (re.compile(r'^ *outside from host '), 1),
    (re.compile(r'^ *inside from network '), 1),
    (re.compile(r'^ *outside from network '), 1),
    (re.compile(r'^ *inside from range '), 1),
    (re.compile(r'^ *outside from range '), 1),
    (re.compile(r'^ *neighbor '), 1),
    (re.compile(r'^ *neighbor '), 2),
    (re.compile(r'^ *no neighbor '), 2),
    (re.compile(r'^ *crypto keyring '), 0),
    (re.compile(r'^ *ip helper-address '), 1),
    (re.compile(r'^ *route-target import '), 1),
    (re.compile(r'^ *route-target export '), 1),
    (re.compile(r'^ *dns-server '), 1),
    (re.compile(r'^ *default-router '), 1),
    (re.compile(r'^ *lease '), 1),
    (re.compile(r'^ *vlan group '), 0),
    (re.compile(r'^ *ip ospf message-digest-key '), 1),
    (re.compile(r'^ *ospfv3 neighbor '), 1),
    (re.compile(r'^ *ospfv3 \d+ ipv(\d) neighbor'), 1),
    (re.compile(r'^ *ospfv3 \d+ neighbor '), 1),
    (re.compile(r'^ *mobile-network pool '), 4),
    (re.compile(r'^ *mobile-network v6pool '), 4),
    (re.compile(r'^ *router '), 0),
    (re.compile(r'^ *area '), 1),
    (re.compile(r'^ *redistribute '), 1),
    (re.compile(r'^ *redistribute '), 2),
    (re.compile(r'^ *redistribute '), 3),
    (re.compile(r'^ *distribute-list prefix-list '), 1),
    (re.compile(r'^ *ip dns '), 0),
    (re.compile(r'^ *ip route '), 0),
    (re.compile(r'^ *ipv6 route '), 0),
    (re.compile(r'^ *ip multicast-routing '), 0),
    (re.compile(r'^ *ipv6 multicast-routing '), 0),
    (re.compile(r'^ *ip pim vrf '), 0),
    (re.compile(r'^ *ipv6 pim vrf '), 0),
    (re.compile(r'^ *ip access-list '), 0),
    (re.compile(r'^ *ipv6 access-list '), 0),
    (re.compile(r'^ *bandwidth remaining ratio '), 2),
    (re.compile(r'^ *ntp server '), 0),
    (re.compile(r'^ *mpls mldp static '), 0),
    (re.compile(r'^ *mpls ldp advertise-labels for '), 0),
    (re.compile(r'^ *device-tracking binding '), 0),
    (re.compile(r'^ *netconf-yang'), 0),
    (re.compile(r'^ *summary-address '), 1),
]

# Some commands can be overwritten without a no command. For example, changing
# from:
# username admin privilege 15 password 0 admin
# to:
# username admin privilege 15 password 7 15130F010D24
# There is no need to send a no command before sending the second line.
OVERWRITABLE_COMMANDS = [
    re.compile(r'^ *username \S+ privilege [0-9]+ password '),
    re.compile(r'^ *password '),
    re.compile(r'^ *description '),
    re.compile(r'^ *ip address( |$)'),
    re.compile(r'^ *ipv6 address( |$)'),
]

# Some commands look like a parent-child relation but actually they are
# siblings. One example is two lines of client config below:
# aaa server radius proxy
#  client 10.0.0.0 255.0.0.0
#   !
#   client 11.0.0.0 255.0.0.0
#   !
SIBLING_CAMMANDS = [
    re.compile(r'^ *client '),
]

# As for the client command above, its children does not have indentation:
# aaa server radius proxy
#  client 10.0.0.0 255.0.0.0
#   timer disconnect acct-stop 23
#   !
#   client 11.0.0.0 255.0.0.0
#   accounting port 34
#   timer disconnect acct-stop 22
#   !
#   client 12.0.0.0 255.0.0.0
#   accounting port 56
#   !
# Logically, "accounting port 34" and "timer disconnect acct-stop 22" are
# children of "client 11.0.0.0 255.0.0.0", but there is no indentation in the
# "show running-config" output. The sub-section is indicated by the expression
# mark.
MISSING_INDENT_COMMANDS = [
    r'^ *client ',
]

# Sometimes there are NVGEN issues that one config state having multiple
# running-config presentations:
# router lisp
#  locator-set RLOC
#   IPv4-interface Loopback1 priority 100 weight 50
#   exit
#  !
#  exit
# !
#
# This exact config may show up in a different way:
# router lisp
#  locator-set RLOC
#   IPv4-interface Loopback1 priority 100 weight 50
#   exit-locator-set
#  !
#  exit-router-lisp
# !
#
# To workaround this, we can define a tuple to replace "exit-locator-set" with
# "exit" for example.
REPLACING_COMMANDS = [
    ('exit-locator-set', 'exit'),
    ('exit-router-lisp', 'exit'),
    ('exit-address-family', ' exit-address-family'),
]


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
        common_key_list = []
        previous_index_1 = previous_index_2 = 0
        for k2 in key_list_2:
            if k2 in key_list_1[previous_index_1:]:
                common_key_list.append(k2)
                previous_index_1 += key_list_1[previous_index_1:].index(k2) + 1
                previous_index_2 += key_list_2[previous_index_2:].index(k2) + 1
        previous_index_1 = previous_index_2 = 0
        for key in common_key_list:
            current_index_1 = previous_index_1 + \
                key_list_1[previous_index_1:].index(key)
            current_index_2 = previous_index_2 + \
                key_list_2[previous_index_2:].index(key)

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
        A list from class ListDiff attribute diff, representing changes from
        running1 to running2.

    diff_reverse : `list`
        A list from class ListDiff attribute diff, representing changes from
        running2 to running1.

    cli : `str`
        CLIs that transits from running1 to running2.

    cli_reverse : `str`
        CLIs that transits from running2 to running1.
    '''

    def __init__(self, running1, running2):
        '''
        __init__ instantiates a RunningConfigDiff instance.
        '''

        self.running1 = running1
        self.running2 = running2
        self._diff_list = None
        self._diff_list_reverse = None

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
        return self.get_diff(reverse=False)

    @property
    def diff_reverse(self):
        return self.get_diff(reverse=True)

    @property
    def cli(self):
        return self.get_cli(reverse=False)

    @property
    def cli_reverse(self):
        return self.get_cli(reverse=True)

    def get_diff(self, reverse=False):
        if self._diff_list is None:
            list1, list2 = self.running2list(self.running1, self.running2)
            self.handle_sibling_cammands(list1)
            self.handle_sibling_cammands(list2)
            self._diff_list = ListDiff(list1, list2).diff
            self._diff_list_reverse = ListDiff(list2, list1).diff
        diff_list = self._diff_list_reverse if reverse else self._diff_list
        return diff_list if diff_list else None

    def get_cli(self, reverse=False):
        diff_list = self.get_diff(reverse=reverse)
        if diff_list:
            positive_str, negative_str = self.list2cli(diff_list)
            if positive_str:
                if negative_str:
                    return negative_str + '\n!\n' + positive_str
                else:
                    return positive_str
            else:
                return negative_str
        else:
            return ''

    def running2list(self, str_in_1, str_in_2):
        for cmd in REPLACING_COMMANDS:
            str_in_1 = str_in_1.replace(*cmd)
            str_in_2 = str_in_2.replace(*cmd)
        list_1 = self.config2list(str_in_1)
        list_2 = self.config2list(str_in_2)
        return self.handle_orderless(list_1, list_2, 0)

    def config2list(self, str_in):
        list_ret = []
        last_line = ''
        last_section = ''
        last_indentation = 0
        missing_indent = False
        for line in str_in.splitlines():
            if len(line.strip()) > 22 and \
               line[:22] == 'Building configuration':
                continue
            if len(line.strip()) > 21 and \
               line[:21] == 'Current configuration':
                continue
            if len(line.strip()) == 0:
                continue
            if missing_indent and line.rstrip() == '!':
                if last_line:
                    if last_indentation > 0:
                        list_ret.append((
                            last_line.rstrip(),
                            self.config2list(last_section),
                            '',
                        ))
                    else:
                        list_ret.append((last_line.rstrip(), None, ''))
                last_line = ''
                last_section = ''
                last_indentation = 0
                missing_indent = False
                continue
            if re.search('^ *!', line) or re.search('^ *%', line):
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
                if any(
                    [re.search(regx, line) for regx in MISSING_INDENT_COMMANDS]
                ):
                    missing_indent = True
                elif missing_indent:
                    current_indentation = 1
                    if last_indentation == 0:
                        last_indentation = current_indentation
                    last_section += line + '\n'
                    continue
                if last_line:
                    if last_indentation > 0:
                        list_ret.append((
                            last_line.rstrip(),
                            self.config2list(last_section),
                            '',
                        ))
                    else:
                        list_ret.append((last_line.rstrip(), None, ''))
                last_line = line
                last_section = ''
                last_indentation = 0
        if last_line:
            if last_indentation > 0:
                list_ret.append((
                    last_line.rstrip(), self.config2list(last_section), ''))
            else:
                list_ret.append((last_line.rstrip(), None, ''))
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

    def list2cli(self, list_in):
        if list_in is None:
            return ''
        positive_list = []
        negative_list = []
        positive_keys = [k for k, v, i in list_in if i == '+' and v is None]
        for k, v, i in list_in:
            if k == '':
                continue
            if v is None:
                if i == '+':
                    self.append_command(k, negative_list, positive_list)
                elif i == '-':
                    # In a case that a CLI is updated, no command is not
                    # needed:
                    # - service timestamps debug datetime msec
                    # + service timestamps debug datetime msec localtime
                    #   show-timezone
                    key_len = len(k)
                    matching_positive_keys = [
                        key for key in positive_keys if key[:key_len] == k]
                    if not matching_positive_keys:
                        self.append_command('no ' + k,
                                            negative_list, positive_list)
            else:
                if i == '':
                    positive_str, negative_str = self.list2cli(v)
                    if positive_str:
                        positive_list.append(
                            k + '\n' + self.indent(positive_str).rstrip())
                    if negative_str:
                        negative_list.append(
                            k + '\n' + self.indent(negative_str).rstrip())
                if i == '+':
                    positive_str = self.list2config(v, diff_type=None).rstrip()
                    if positive_str:
                        positive_list.append(k + '\n' + positive_str)
                    else:
                        positive_list.append(k)
                elif i == '-':
                    self.append_command('no ' + k,
                                        negative_list, positive_list)

        # Handle overwritable commands
        idx_positive_dict = {}
        idx_positive_list = []
        for regx in OVERWRITABLE_COMMANDS:
            for idx_positive, cmd in enumerate(positive_list):
                m = re.search(regx, cmd)
                if m:

                    # Remove matching negative CLIs
                    exact_cmd = 'no ' + m.group(0).lstrip()
                    len_exact_cmd = len(exact_cmd)
                    for idx_negative, line in enumerate(negative_list):
                        cmd_line = line.lstrip()
                        if (
                            len(cmd_line) >= len_exact_cmd and
                            cmd_line[:len_exact_cmd] == exact_cmd
                        ):
                            break
                    else:
                        idx_negative = None
                    if idx_negative is not None:
                        del negative_list[idx_negative]

                    # Overwrite previous matching positive CLIs
                    exact_cmd = m.group(0).strip()
                    if exact_cmd in idx_positive_dict:
                        idx_positive_list.append(idx_positive_dict[exact_cmd])
                    idx_positive_dict[exact_cmd] = idx_positive

        if idx_positive_list:
            for idx in sorted(idx_positive_list, reverse=True):
                del positive_list[idx]

        # Handle duplicate commands
        # Some commands their positive and negative lines are both appeared in
        # the "show running-config" output, e.g., "platform punt-keepalive
        # disable-kernel-core" and "no platform punt-keepalive
        # disable-kernel-core" are both visible. This treatment is required to
        # avoid two lines of the same CLI.
        for cmd_list in [positive_list, negative_list]:
            self.remove_duplicate_cammands(cmd_list)

        # Remove some unnecessary commands
        self.remove_unnecessary_negative_commands(negative_list)
        self.remove_unnecessary_positive_commands(positive_list)

        return '\n'.join(positive_list), '\n'.join(reversed(negative_list))

    @staticmethod
    def append_command(cmd, negative_list, positive_list):
        cmd, is_no_cmd = RunningConfigDiff.handle_command(cmd)
        if is_no_cmd:
            negative_list.append(cmd)
        else:
            positive_list.append(cmd)

    @staticmethod
    def handle_command(cmd):
        if cmd[:6] == 'no no ':
            return cmd[6:].strip(), False
        for short_cmd in SHORT_NO_COMMANDS:
            if cmd[:len(short_cmd)] == short_cmd:
                return short_cmd.strip(), True
        if cmd[:3] == 'no ':
            return cmd.strip(), True
        else:
            return cmd.strip(), False

    @staticmethod
    def handle_orderless(list1, list2, depth):
        # Find common lines that are orderless
        lines1 = [i[0] for i in list1]
        matches = {}
        for idx, item in enumerate(list2):
            result, match_type = RunningConfigDiff.match_orderless(item[0],
                                                                   depth)
            if result and item[0] in lines1:
                matches[item[0]] = match_type, idx

        # Romove common lines from list1 and save them in removed_items
        type_start_idx = {}
        to_be_removed = []
        for idx, line in enumerate(lines1):
            if line in matches:
                if matches[line][0] not in type_start_idx:
                    type_start_idx[matches[line][0]] = idx
                to_be_removed.append(idx)
        removed_items = {}
        for idx in reversed(to_be_removed):
            removed_items[list1[idx][0]] = list1[idx]
            del list1[idx]

        # Find common lines
        lines1 = [i[0] for i in list1]
        lines2 = [i[0] for i in list2]
        common_lines = []
        previous_idx_1 = previous_idx_2 = 0
        for line2 in lines2:
            if line2 in lines1[previous_idx_1:]:
                previous_idx_1 += lines1[previous_idx_1:].index(line2) + 1
                previous_idx_2 += lines2[previous_idx_2:].index(line2) + 1
                common_lines.append((previous_idx_1 - 1, previous_idx_2 - 1))

        # Insert common lines back to list1
        offset_idx_1 = 0
        previous_idx_2 = 0
        for line, (line_type, list2_idx) in matches.items():
            common_idx_1 = 0
            if len(common_lines) > 0 and list2_idx > common_lines[0][1]:
                for i, j in common_lines:
                    # if previous_idx_2 <= j and j < list2_idx:
                    if j < list2_idx:
                        common_idx_1 = i + 1
                        previous_idx_2 = j
                    if j > list2_idx:
                        break
            start_idx = max(common_idx_1 + offset_idx_1,
                            type_start_idx[line_type])
            list1.insert(start_idx, removed_items[line])
            offset_idx_1 = start_idx - common_idx_1 + 1

        # Find common lines that have children
        lines1 = {item[0]: idx for idx, item in enumerate(list1)
                  if isinstance(item[1], list) and len(item[1]) > 0}
        lines2 = {item[0]: idx for idx, item in enumerate(list2)
                  if isinstance(item[1], list) and len(item[1]) > 0}
        for line in set(lines1.keys()) & set(lines2.keys()):
            RunningConfigDiff.handle_orderless(list1[lines1[line]][1],
                                               list2[lines2[line]][1],
                                               depth + 1)

        return list1, list2

    @staticmethod
    def match_orderless(line, current_depth):
        for idx, (regx, depth) in enumerate(ORDERLESS_COMMANDS):
            if depth == current_depth and re.search(regx, line):
                return True, idx
        return False, None

    @staticmethod
    def remove_duplicate_cammands(config_list):
        indexes = []
        commands = set()
        for idx, line in enumerate(config_list):
            if line in commands:
                indexes.append(idx)
            else:
                commands.add(line)
        if indexes:
            for idx in reversed(indexes):
                del config_list[idx]

    @staticmethod
    def handle_sibling_cammands(config_list):
        length = len(config_list)
        lines_inserted = 0
        for i in range(length):
            idx = i + lines_inserted
            tup = config_list[idx]
            for regx in SIBLING_CAMMANDS:
                if re.search(regx, tup[0]) and tup[1] is not None:
                    siblings = []
                    indexes = []
                    for idx_c, tup_c in enumerate(tup[1]):
                        if re.search(regx, tup_c[0]):
                            indexes.append(idx_c)
                    for idx_c in reversed(indexes):
                        siblings.append(tup[1][idx_c])
                        del tup[1][idx_c]
                    if not tup[1]:
                        tup = config_list[idx] = (tup[0], None, tup[2])
                    j = 1
                    for sibling in reversed(siblings):
                        config_list.insert(i+j, sibling)
                        j += 1
                    break
            if tup[1] is not None:
                RunningConfigDiff.handle_sibling_cammands(tup[1])

    @staticmethod
    def remove_unnecessary_negative_commands(negative_list):
        cmds = [i for i, c in enumerate(negative_list)
                if '\n' not in c]
        indexes = set()
        for idx1_tmp, idx1 in enumerate(cmds):
            c1 = negative_list[idx1]
            for idx2_tmp in range(idx1_tmp + 1, len(cmds)):
                idx2 = cmds[idx2_tmp]
                c2 = negative_list[idx2]
                if c1 == c2 or len(c1) == len(c2):
                    continue
                if len(c1) < len(c2):
                    if c1 == c2[:len(c1)]:
                        indexes.add(idx2)
                elif c1[:len(c2)] == c2:
                    indexes.add(idx1)
        if indexes:
            for idx in sorted(indexes, reverse=True):
                del negative_list[idx]

    @staticmethod
    def remove_unnecessary_positive_commands(positive_list):
        cmds = [i for i, c in enumerate(positive_list)
                if '\n' not in c and c not in COEXIST_SHORT_POSITIVE_COMMANDS]
        indexes = set()
        for idx1_tmp, idx1 in enumerate(cmds):
            c1 = positive_list[idx1]
            for idx2_tmp in range(idx1_tmp + 1, len(cmds)):
                idx2 = cmds[idx2_tmp]
                c2 = positive_list[idx2]
                if c1 == c2 or len(c1) == len(c2):
                    continue
                if len(c1) < len(c2):
                    if c1 == c2[:len(c1)]:
                        indexes.add(idx1)
                elif c1[:len(c2)] == c2:
                    indexes.add(idx2)
        if indexes:
            for idx in sorted(indexes, reverse=True):
                del positive_list[idx]

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
