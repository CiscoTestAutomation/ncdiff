#!/bin/env python
""" Unit tests for the ncdiff cisco-shared package. """

import unittest
from ncdiff import RunningConfigDiff


class TestRunningConfig(unittest.TestCase):

    def setUp(self):
        pass

    def test_diff_1(self):
        config_1 = """
ip dhcp pool ABC
 network 10.0.20.0 255.255.255.0
 class CLASS1
  address range 10.0.20.1 10.0.20.100
 class CLASS2
  address range 10.0.20.101 10.0.20.200
 class CLASS3
  address range 10.0.20.201 10.0.20.254
!
ip dhcp pool dhcp_1
 network 172.16.1.0 255.255.255.0
 network 172.16.2.0 255.255.255.0 secondary
 network 172.16.3.0 255.255.255.0 secondary
 network 172.16.4.0 255.255.255.0 secondary
!
!
ip dhcp class CLASS1
   relay agent information
!
ip dhcp class CLASS2
   relay agent information
!
ip dhcp class CLASS3
   relay agent information
!
!
login on-success log
            """
        config_2 = """
ip dhcp pool dhcp_1
 network 172.16.1.0 255.255.255.0
 network 172.16.2.0 255.255.255.0 secondary
 network 172.16.3.0 255.255.255.0 secondary
 network 172.16.4.0 255.255.255.0 secondary
!
ip dhcp pool ABC
 network 10.0.20.0 255.255.255.0
 class CLASS1
  address range 10.0.20.1 10.0.20.100
 class CLASS2
  address range 10.0.20.101 10.0.20.200
 class CLASS3
  address range 10.0.20.201 10.0.20.254
!
!
ip dhcp class CLASS2
   relay agent information
 relay-information hex 01040101030402020102
 relay-information hex 01040102030402020102
!
ip dhcp class CLASS1
   relay agent information
 relay-information hex 01030a0b0c02*
 relay-information hex 01030a0b0c02050000000123
!
ip dhcp class CLASS3
   relay agent information
!
!
login on-success log
!
            """
        expected_diff = """
- ip dhcp pool ABC
-   network 10.0.20.0 255.255.255.0
-   class CLASS1
-     address range 10.0.20.1 10.0.20.100
-   class CLASS2
-     address range 10.0.20.101 10.0.20.200
-   class CLASS3
-     address range 10.0.20.201 10.0.20.254
  ip dhcp pool dhcp_1
    network 172.16.1.0 255.255.255.0
    network 172.16.2.0 255.255.255.0 secondary
    network 172.16.3.0 255.255.255.0 secondary
    network 172.16.4.0 255.255.255.0 secondary
- ip dhcp class CLASS1
-   relay agent information
+ ip dhcp pool ABC
+   network 10.0.20.0 255.255.255.0
+   class CLASS1
+     address range 10.0.20.1 10.0.20.100
+   class CLASS2
+     address range 10.0.20.101 10.0.20.200
+   class CLASS3
+     address range 10.0.20.201 10.0.20.254
  ip dhcp class CLASS2
    relay agent information
+     relay-information hex 01040101030402020102
+     relay-information hex 01040102030402020102
+ ip dhcp class CLASS1
+   relay agent information
+     relay-information hex 01030a0b0c02*
+     relay-information hex 01030a0b0c02050000000123
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        actual_diff = str(running_diff).strip()
        expected_diff = expected_diff.strip()
        actual_lines = actual_diff.split('\n')
        expected_lines = expected_diff.split('\n')
        self.assertEqual(len(actual_lines), len(expected_lines))
        for actual_line, expected_line in zip(actual_lines, expected_lines):
            self.assertEqual(actual_line, expected_line)

    def test_diff_2(self):
        config_1 = """
aa bb cc
        """
        config_2 = """
aa bb cc
  ee ff rr
!
        """
        expected_diff = """
  aa bb cc
+   ee ff rr
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertTrue(running_diff)
        actual_diff = str(running_diff).strip()
        expected_diff = expected_diff.strip()
        actual_lines = actual_diff.split('\n')
        expected_lines = expected_diff.split('\n')
        self.assertEqual(len(actual_lines), len(expected_lines))
        for actual_line, expected_line in zip(actual_lines, expected_lines):
            self.assertEqual(actual_line, expected_line)

    def test_diff_3(self):
        config_1 = """
aa bb cc
  ee ff rr
!
        """
        config_2 = """
aa bb cc
        """
        expected_diff = """
  aa bb cc
-   ee ff rr
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertTrue(running_diff)
        actual_diff = str(running_diff).strip()
        expected_diff = expected_diff.strip()
        actual_lines = actual_diff.split('\n')
        expected_lines = expected_diff.split('\n')
        self.assertEqual(len(actual_lines), len(expected_lines))
        for actual_line, expected_line in zip(actual_lines, expected_lines):
            self.assertEqual(actual_line, expected_line)

    def test_diff_4(self):
        config_1 = """
vrf definition genericstring
 !
 address-family ipv4
 exit-address-family
 !
 address-family ipv6
 exit-address-family
!
        """
        config_2 = """
vrf definition genericstring
 !
 address-family ipv4
 exit-address-family
 !
 address-family ipv6
 exit-address-family
!
        """
        expected_diff = ""
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertFalse(running_diff)
        actual_diff = str(running_diff).strip()
        expected_diff = expected_diff.strip()
        actual_lines = actual_diff.split('\n')
        expected_lines = expected_diff.split('\n')
        self.assertEqual(len(actual_lines), len(expected_lines))
        for actual_line, expected_line in zip(actual_lines, expected_lines):
            self.assertEqual(actual_line, expected_line)

    def test_diff_5(self):
        config_1 = """
vrf definition genericstring
 !
 address-family ipv4
 exit-address-family
 !
 address-family ipv6
 exit-address-family
!
        """
        config_2 = """
vrf definition generic
 !
 address-family ipv4
 exit-address-family
 !
 address-family ipv6
 exit-address-family
!
        """
        expected_diff = """
- vrf definition genericstring
-   address-family ipv4
-     exit-address-family
-   address-family ipv6
-     exit-address-family
+ vrf definition generic
+   address-family ipv4
+     exit-address-family
+   address-family ipv6
+     exit-address-family
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertTrue(running_diff)
        actual_diff = str(running_diff).strip()
        expected_diff = expected_diff.strip()
        actual_lines = actual_diff.split('\n')
        expected_lines = expected_diff.split('\n')
        self.assertEqual(len(actual_lines), len(expected_lines))
        for actual_line, expected_line in zip(actual_lines, expected_lines):
            self.assertEqual(actual_line, expected_line)

    def test_cli_short_no_commands(self):
        config_1 = """
vrf definition genericstring
 !
 address-family ipv4
 exit-address-family
 !
 address-family ipv6
 exit-address-family
!
license boot level network-advantage addon dna-advantage
        """
        config_2 = """
vrf definition generic
 !
 address-family ipv4
 exit-address-family
 !
 address-family ipv6
 exit-address-family
!
        """
        expected_cli = """
no license boot level
no vrf definition genericstring
!
vrf definition generic
  address-family ipv4
    exit-address-family
  address-family ipv6
    exit-address-family
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertTrue(running_diff)
        actual_cli = running_diff.cli.strip()
        expected_cli = expected_cli.strip()
        actual_lines = actual_cli.split('\n')
        expected_lines = expected_cli.split('\n')
        self.assertEqual(len(actual_lines), len(expected_lines))
        for actual_line, expected_line in zip(actual_lines, expected_lines):
            self.assertEqual(actual_line.strip(), expected_line.strip())

    def test_cli_orderless_commands(self):
        config_1 = """
license boot level network-advantage addon dna-advantage
!
aaa authentication login admin-con group tacacs+ local
aaa authentication login admin-vty group tacacs+ local
        """
        config_2 = """
aaa authentication login admin-vty group tacacs+ local
aaa authentication login admin-con group tacacs+ local
        """
        expected_cli = """
no license boot level
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertTrue(running_diff)
        actual_cli = running_diff.cli.strip()
        expected_cli = expected_cli.strip()
        actual_lines = actual_cli.split('\n')
        expected_lines = expected_cli.split('\n')
        self.assertEqual(len(actual_lines), len(expected_lines))
        for actual_line, expected_line in zip(actual_lines, expected_lines):
            self.assertEqual(actual_line.strip(), expected_line.strip())

    def test_cli_overwritable_commands(self):
        config_1 = """
line vty 0 4
 exec-timeout 0 0
 password 0 lab
 transport input all
!
        """
        config_2 = """
line vty 0 4
 exec-timeout 0 0
 password 7 082D4D4C
 transport input all
!
        """
        expected_cli = """
line vty 0 4
 password 7 082D4D4C
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertTrue(running_diff)
        actual_cli = running_diff.cli.strip()
        expected_cli = expected_cli.strip()
        actual_lines = actual_cli.split('\n')
        expected_lines = expected_cli.split('\n')
        self.assertEqual(len(actual_lines), len(expected_lines))
        for actual_line, expected_line in zip(actual_lines, expected_lines):
            self.assertEqual(actual_line.strip(), expected_line.strip())

    def test_cli_doubleface_commands(self):
        config_1 = """
no platform punt-keepalive disable-kernel-core
!
        """
        config_2 = """
platform punt-keepalive disable-kernel-core
        """
        expected_cli = """
platform punt-keepalive disable-kernel-core
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertTrue(running_diff)
        actual_cli = running_diff.cli.strip()
        expected_cli = expected_cli.strip()
        actual_lines = actual_cli.split('\n')
        expected_lines = expected_cli.split('\n')
        self.assertEqual(len(actual_lines), len(expected_lines))
        for actual_line, expected_line in zip(actual_lines, expected_lines):
            self.assertEqual(actual_line.strip(), expected_line.strip())

    def test_cli_sibling_commands(self):
        config_1 = """
aaa server radius proxy
 client 10.0.0.0 255.0.0.0
  timer disconnect acct-stop 23
  !
  client 11.0.0.0 255.0.0.0
  accounting port 34
  !
  client 12.0.0.0 255.0.0.0
  accounting port 56
  !
abc def
  aaa server radius proxy
    client 10.0.0.0 255.0.0.0
      ert tyt
      client 11.0.0.0 255.0.0.0
        kdjfg kjkfdg
      client 12.0.0.0 255.0.0.0
        gdfh lijdf
        """
        config_2 = """
aaa server radius proxy
 client 11.0.0.0 255.0.0.0
  accounting port 34
  !
  client 13.0.0.0 255.0.0.0
  accounting port 77
  !
abc def
  aaa server radius proxy
    client 11.0.0.0 255.0.0.0
      kdjfg ttttt
      client 13.0.0.0 255.0.0.0
        gdfh lijdf
        """
        expected_cli = """
abc def
  aaa server radius proxy
    no client 12.0.0.0 255.0.0.0
    client 11.0.0.0 255.0.0.0
      no kdjfg kjkfdg
    no client 10.0.0.0 255.0.0.0
aaa server radius proxy
  no client 12.0.0.0 255.0.0.0
  no client 10.0.0.0 255.0.0.0
!
aaa server radius proxy
  client 13.0.0.0 255.0.0.0
    accounting port 77
abc def
  aaa server radius proxy
    client 11.0.0.0 255.0.0.0
      kdjfg ttttt
    client 13.0.0.0 255.0.0.0
      gdfh lijdf
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertTrue(running_diff)
        actual_cli = running_diff.cli.strip()
        expected_cli = expected_cli.strip()
        actual_lines = actual_cli.split('\n')
        expected_lines = expected_cli.split('\n')
        self.assertEqual(len(actual_lines), len(expected_lines))
        for actual_line, expected_line in zip(actual_lines, expected_lines):
            self.assertEqual(actual_line.strip(), expected_line.strip())

    def test_cli_ip_address(self):
        config_1 = """
interface GigabitEthernet8/0/1
!
interface Vlan69
 ip address 192.168.100.1 255.255.255.0
!
interface Vlan70
 ip address 192.168.101.1 255.255.255.0
        """
        config_2 = """
ip dhcp pool Test
 network 1.1.0.0 255.255.0.0
!
interface GigabitEthernet8/0/1
 no switchport
 ip address dhcp
 shutdown
!
interface Vlan69
 no ip address
 ipv6 address 2001:FACE::1/64
 ipv6 enable
 ipv6 dhcp relay destination 2001:1234::2
!
interface Vlan70
 no ip address
 ipv6 address 2001:1234::1/64
 ipv6 enable
        """
        expected_cli = """
interface Vlan70
  no ip address
interface Vlan69
  no ip address
interface GigabitEthernet8/0/1
  no switchport
!
ip dhcp pool Test
  network 1.1.0.0 255.255.0.0
interface GigabitEthernet8/0/1
  ip address dhcp
  shutdown
interface Vlan69
  ipv6 address 2001:FACE::1/64
  ipv6 enable
  ipv6 dhcp relay destination 2001:1234::2
interface Vlan70
  ipv6 address 2001:1234::1/64
  ipv6 enable
        """
        expected_reverse_cli = """
interface Vlan70
  no ipv6 enable
  no ipv6 address
interface Vlan69
  no ipv6 dhcp relay destination 2001:1234::2
  no ipv6 enable
  no ipv6 address
interface GigabitEthernet8/0/1
  no shutdown
  no ip address
no ip dhcp pool Test
!
interface GigabitEthernet8/0/1
  switchport
interface Vlan69
  ip address 192.168.100.1 255.255.255.0
interface Vlan70
  ip address 192.168.101.1 255.255.255.0
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertTrue(running_diff)
        actual_cli = running_diff.cli.strip()
        expected_cli = expected_cli.strip()
        actual_lines = actual_cli.split('\n')
        expected_lines = expected_cli.split('\n')
        self.assertEqual(len(actual_lines), len(expected_lines))
        for actual_line, expected_line in zip(actual_lines, expected_lines):
            self.assertEqual(actual_line.strip(), expected_line.strip())

        actual_reverse_cli = running_diff.cli_reverse.strip()
        expected_reverse_cli = expected_reverse_cli.strip()
        actual_lines = actual_reverse_cli.split('\n')
        expected_lines = expected_reverse_cli.split('\n')
        self.assertEqual(len(actual_lines), len(expected_lines))
        for actual_line, expected_line in zip(actual_lines, expected_lines):
            self.assertEqual(actual_line.strip(), expected_line.strip())

    def test_cli_logging_host(self):
        config_1 = """
logging host 10.15.118.120
logging host 10.200.159.168
logging host 10.200.209.215
        """
        config_2 = """
logging host 10.200.209.215
logging host 10.15.118.120
logging host 10.200.159.168
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertFalse(running_diff)
        self.assertEqual(running_diff.diff, None)
        self.assertEqual(running_diff.diff_reverse, None)
        self.assertEqual(running_diff.cli, '')
        self.assertEqual(running_diff.cli_reverse, '')

    def test_cli_flow_mon(self):
        config_1 = """
flow monitor eta-mon
flow monitor meraki_monitor
  exporter meraki_exporter
  exporter customer_exporter
  record meraki_record
flow monitor meraki_monitor_ipv6
  exporter meraki_exporter
  exporter customer_exporter
  record meraki_record_ipv6
        """
        config_2 = """
flow monitor meraki_monitor
  exporter meraki_exporter
  exporter customer_exporter
  record meraki_record
flow monitor meraki_monitor_ipv6
  exporter meraki_exporter
  exporter customer_exporter
  record meraki_record_ipv6
flow monitor eta-mon
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertFalse(running_diff)
        self.assertEqual(running_diff.diff, None)
        self.assertEqual(running_diff.diff_reverse, None)
        self.assertEqual(running_diff.cli, '')
        self.assertEqual(running_diff.cli_reverse, '')

    def test_cli_service_template_1(self):
        config_1 = """
login on-success log
!
flow monitor eta-mon
flow monitor meraki_monitor
  exporter meraki_exporter
  exporter customer_exporter
  record meraki_record
flow monitor meraki_monitor_ipv6
  exporter meraki_exporter
  exporter customer_exporter
  record meraki_record_ipv6
!
access-session mac-move deny
!
crypto pki trustpoint SLA-TrustPoint
 enrollment pkcs12
 revocation-check crl
 hash sha256
!
service-template DEFAULT_LINKSEC_POLICY_MUST_SECURE
  linksec policy must-secure
service-template DEFAULT_LINKSEC_POLICY_SHOULD_SECURE
  linksec policy should-secure
service-template DEFAULT_CRITICAL_VOICE_TEMPLATE
  voice vlan
service-template DEFAULT_CRITICAL_DATA_TEMPLATE
service-template webauth-global-inactive
  inactivity-timer 3600
service-template eap-seen
service-template aaa-unreachable-flag
service-template bounce-port-flag
service-template secure-connect-ap-aaa-down
service-template secure-connect-break-flag
service-template secure-connect-failed-flag
service-template secure-connect-in-progress-flag
service-template secure-connect-success-flag
        """
        config_2 = """
login on-success log
!
flow monitor meraki_monitor
  exporter meraki_exporter
  exporter customer_exporter
  record meraki_record
flow monitor meraki_monitor_ipv6
  exporter meraki_exporter
  exporter customer_exporter
  record meraki_record_ipv6
flow monitor eta-mon
!
crypto pki trustpoint SLA-TrustPoint
 enrollment pkcs12
 revocation-check crl
 hash sha256
!
service-template DEFAULT_CRITICAL_DATA_TEMPLATE
service-template DEFAULT_CRITICAL_VOICE_TEMPLATE
  voice vlan
  aaa bbb ccc
service-template DEFAULT_LINKSEC_POLICY_MUST_SECURE
  linksec policy must-secure
service-template DEFAULT_LINKSEC_POLICY_SHOULD_SECURE
  linksec policy should-secure
service-template aaa-unreachable-flag
service-template bounce-port-flag
service-template eap-seen
service-template secure-connect-ap-aaa-down
service-template secure-connect-break-flag
service-template secure-connect-failed-flag
service-template secure-connect-in-progress-flag
service-template secure-connect-success-flag
service-template webauth-global-inactive
  inactivity-timer 3600
        """
        expected_diff = """
- access-session mac-move deny
  service-template DEFAULT_CRITICAL_VOICE_TEMPLATE
+   aaa bbb ccc
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertTrue(running_diff)
        actual_diff = str(running_diff).strip()
        expected_diff = expected_diff.strip()
        actual_lines = actual_diff.split('\n')
        expected_lines = expected_diff.split('\n')
        self.assertEqual(len(actual_lines), len(expected_lines))
        for actual_line, expected_line in zip(actual_lines, expected_lines):
            self.assertEqual(actual_line.strip(), expected_line.strip())

    def test_cli_service_template_2(self):
        config_1 = """
login on-success log
!
flow monitor eta-mon
flow monitor meraki_monitor
  exporter meraki_exporter
  exporter customer_exporter
  record meraki_record
flow monitor meraki_monitor_ipv6
  exporter meraki_exporter
  exporter customer_exporter
  record meraki_record_ipv6
!
crypto pki trustpoint SLA-TrustPoint
 enrollment pkcs12
 revocation-check crl
 hash sha256
!
service-template DEFAULT_LINKSEC_POLICY_MUST_SECURE
  linksec policy must-secure
service-template DEFAULT_LINKSEC_POLICY_SHOULD_SECURE
  linksec policy should-secure
service-template DEFAULT_CRITICAL_VOICE_TEMPLATE
  voice vlan
service-template DEFAULT_CRITICAL_DATA_TEMPLATE
service-template webauth-global-inactive
  inactivity-timer 3600
service-template eap-seen
service-template aaa-unreachable-flag
service-template bounce-port-flag
service-template secure-connect-ap-aaa-down
service-template secure-connect-break-flag
service-template secure-connect-failed-flag
service-template secure-connect-in-progress-flag
service-template secure-connect-success-flag
        """
        config_2 = """
login on-success log
!
flow monitor meraki_monitor
  exporter meraki_exporter
  exporter customer_exporter
  record meraki_record
flow monitor meraki_monitor_ipv6
  exporter meraki_exporter
  exporter customer_exporter
  record meraki_record_ipv6
flow monitor eta-mon
!
crypto pki trustpoint SLA-TrustPoint
 enrollment pkcs12
 revocation-check crl
 hash sha256
!
service-template DEFAULT_CRITICAL_DATA_TEMPLATE
service-template DEFAULT_CRITICAL_VOICE_TEMPLATE
  voice vlan
service-template DEFAULT_LINKSEC_POLICY_MUST_SECURE
  linksec policy must-secure
service-template DEFAULT_LINKSEC_POLICY_SHOULD_SECURE
  linksec policy should-secure
service-template aaa-unreachable-flag
service-template bounce-port-flag
service-template eap-seen
service-template secure-connect-ap-aaa-down
service-template secure-connect-break-flag
service-template secure-connect-failed-flag
service-template secure-connect-in-progress-flag
service-template secure-connect-success-flag
service-template webauth-global-inactive
  inactivity-timer 3600
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertFalse(running_diff)
        self.assertEqual(running_diff.diff, None)
        self.assertEqual(running_diff.diff_reverse, None)
        self.assertEqual(running_diff.cli, '')
        self.assertEqual(running_diff.cli_reverse, '')

    def test_cli_service_template_3(self):
        config_1 = """
login on-success log
!
flow monitor eta-mon
flow monitor meraki_monitor
  exporter meraki_exporter
  exporter customer_exporter
  record meraki_record
flow monitor meraki_monitor_ipv6
  exporter meraki_exporter
  exporter customer_exporter
  record meraki_record_ipv6
!
access-session mac-move deny
!
crypto pki trustpoint SLA-TrustPoint
 enrollment pkcs12
 revocation-check crl
 hash sha256
!
service-template DEFAULT_LINKSEC_POLICY_MUST_SECURE
  linksec policy must-secure
service-template DEFAULT_LINKSEC_POLICY_SHOULD_SECURE
  linksec policy should-secure
service-template DEFAULT_CRITICAL_VOICE_TEMPLATE
  voice vlan
service-template DEFAULT_CRITICAL_DATA_TEMPLATE
service-template webauth-global-inactive
  inactivity-timer 3600
service-template eap-seen
service-template aaa-unreachable-flag
service-template bounce-port-flag
service-template secure-connect-ap-aaa-down
service-template secure-connect-break-flag
service-template secure-connect-failed-flag
service-template secure-connect-in-progress-flag
service-template secure-connect-success-flag
        """
        config_2 = """
login on-success log
!
flow monitor meraki_monitor
  exporter meraki_exporter
  exporter customer_exporter
  record meraki_record
flow monitor meraki_monitor_ipv6
  exporter meraki_exporter
  exporter customer_exporter
  record meraki_record_ipv6
flow monitor eta-mon
!
crypto pki trustpoint SLA-TrustPoint
 enrollment pkcs12
 revocation-check crl
 hash sha256
!
service-template DEFAULT_CRITICAL_DATA_TEMPLATE
service-template DEFAULT_CRITICAL_VOICE_TEMPLATE_NEW
  voice vlan
service-template DEFAULT_LINKSEC_POLICY_MUST_SECURE
  linksec policy must-secure
service-template DEFAULT_LINKSEC_POLICY_SHOULD_SECURE
  linksec policy should-secure
service-template aaa-unreachable-flag
service-template bounce-port-flag
service-template eap-seen
service-template secure-connect-ap-aaa-down
service-template secure-connect-break-flag
service-template secure-connect-failed-flag
service-template secure-connect-in-progress-flag
service-template secure-connect-success-flag
service-template webauth-global-inactive
  inactivity-timer 3600
        """
        expected_diff = """
- access-session mac-move deny
+ service-template DEFAULT_CRITICAL_VOICE_TEMPLATE_NEW
+   voice vlan
- service-template DEFAULT_CRITICAL_VOICE_TEMPLATE
-   voice vlan
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertTrue(running_diff)
        actual_diff = str(running_diff).strip()
        expected_diff = expected_diff.strip()
        actual_lines = actual_diff.split('\n')
        expected_lines = expected_diff.split('\n')
        self.assertEqual(len(actual_lines), len(expected_lines))
        for actual_line, expected_line in zip(actual_lines, expected_lines):
            self.assertEqual(actual_line.strip(), expected_line.strip())

    def test_cli_aaa_group_server_radius(self):
        config_1 = """
aaa group server radius testing-10.5.0.110-1812
  server name 10.5.0.110_1812_0
aaa group server radius testing-6.0.0.2-1812
  server name 6.0.0.2_1812_0
aaa group server radius radius-group-0
  server name 6.0.0.2_1812_0
aaa group server radius radius-group-1
  server name 10.5.0.110_1812_0
aaa group server radius radius-group-2
  server name 10.5.0.110_1812_0
aaa group server radius radius-group-3
  server name 10.5.0.110_1812_0
aaa group server radius testing-10.5.0.110-0
  server name 10.5.0.110_0_1813
aaa group server radius radius-group-4
  server name 10.5.0.110_1812_0
        """
        config_2 = """
aaa group server radius radius-group-0
  server name 6.0.0.2_1812_0
aaa group server radius radius-group-1
  server name 10.5.0.110_1812_0
aaa group server radius radius-group-2
  server name 10.5.0.110_1812_0
aaa group server radius radius-group-3
  server name 10.5.0.110_1812_0
aaa group server radius radius-group-4
  server name 10.5.0.110_1812_0
aaa group server radius testing-10.5.0.110-0
  server name 10.5.0.110_0_1813
aaa group server radius testing-10.5.0.110-1812
  server name 10.5.0.110_1812_0
aaa group server radius testing-6.0.0.2-1812
  server name 6.0.0.2_1812_0
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertFalse(running_diff)
        self.assertEqual(running_diff.diff, None)
        self.assertEqual(running_diff.diff_reverse, None)
        self.assertEqual(running_diff.cli, '')
        self.assertEqual(running_diff.cli_reverse, '')

    def test_service_template_2(self):
        config_1 = """
service-template DEFAULT_LINKSEC_POLICY_MUST_SECURE
  linksec policy must-secure
service-template DEFAULT_LINKSEC_POLICY_SHOULD_SECURE
  linksec policy should-secure
service-template DEFAULT_CRITICAL_VOICE_TEMPLATE
  voice vlan
service-template DEFAULT_CRITICAL_DATA_TEMPLATE
service-template webauth-global-inactive
  inactivity-timer 3600
service-template eap-seen
service-template aaa-unreachable-flag
service-template bounce-port-flag
service-template secure-connect-ap-aaa-down
service-template secure-connect-break-flag
service-template secure-connect-failed-flag
service-template secure-connect-in-progress-flag
service-template secure-connect-success-flag
service-template failed-vlan-2
  vlan 98
service-template guest-vlan-0
  vlan 900
        """
        config_2 = """
service-template DEFAULT_CRITICAL_DATA_TEMPLATE
service-template DEFAULT_CRITICAL_VOICE_TEMPLATE
  voice vlan
service-template DEFAULT_LINKSEC_POLICY_MUST_SECURE
  linksec policy must-secure
service-template DEFAULT_LINKSEC_POLICY_SHOULD_SECURE
  linksec policy should-secure
service-template aaa-unreachable-flag
service-template bounce-port-flag
service-template eap-seen
service-template failed-vlan-2
  vlan 98
service-template guest-vlan-0
  vlan 900
service-template secure-connect-ap-aaa-down
service-template secure-connect-break-flag
service-template secure-connect-failed-flag
service-template secure-connect-in-progress-flag
service-template secure-connect-success-flag
service-template webauth-global-inactive
  inactivity-timer 3600
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertFalse(running_diff)
        self.assertEqual(running_diff.diff, None)
        self.assertEqual(running_diff.diff_reverse, None)
        self.assertEqual(running_diff.cli, '')
        self.assertEqual(running_diff.cli_reverse, '')

    def test_l2nat_instance_1(self):
        config_1 = """
l2nat instance test
  inside from host 3.3.3.2 to 6.6.6.2
  inside from host 3.3.3.1 to 6.6.6.1
        """
        config_2 = """
l2nat instance test
  inside from host 3.3.3.1 to 6.6.6.1
  inside from host 3.3.3.2 to 6.6.6.2
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertFalse(running_diff)
        self.assertEqual(running_diff.diff, None)
        self.assertEqual(running_diff.diff_reverse, None)
        self.assertEqual(running_diff.cli, '')
        self.assertEqual(running_diff.cli_reverse, '')

    def test_l2nat_instance_2(self):
        config_1 = """
l2nat instance test
  inside from network 2.2.2.0 to 3.3.3.0 mask 255.255.255.0
  outside from network 4.4.4.0 to 5.5.5.0 mask 255.255.255.0
        """
        config_2 = """
l2nat instance test
  outside from network 4.4.4.0 to 5.5.5.0 mask 255.255.255.0
  inside from network 2.2.2.0 to 3.3.3.0 mask 255.255.255.0
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertFalse(running_diff)
        self.assertEqual(running_diff.diff, None)
        self.assertEqual(running_diff.diff_reverse, None)
        self.assertEqual(running_diff.cli, '')
        self.assertEqual(running_diff.cli_reverse, '')

    def test_l2nat_instance_3(self):
        config_1 = """
l2nat instance test
  inside from range 2.2.2.1 to 3.3.3.1 5
  outside from range 3.3.3.10 to 2.2.2.10 5
        """
        config_2 = """
l2nat instance test
  outside from range 3.3.3.10 to 2.2.2.10 5
  inside from range 2.2.2.1 to 3.3.3.1 5
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertFalse(running_diff)
        self.assertEqual(running_diff.diff, None)
        self.assertEqual(running_diff.diff_reverse, None)
        self.assertEqual(running_diff.cli, '')
        self.assertEqual(running_diff.cli_reverse, '')

    def test_flow_exporter(self):
        config_1 = """
flow exporter meraki_exporter
  destination 1.1.3.2
  transport udp 9995
flow exporter customer_exporter
  destination 10.7.253.22
  transport udp 2055
  export-protocol ipfix
  option interface-table timeout 3600
  option exporter-stats timeout 300
  option application-table timeout 3600
        """
        config_2 = """
flow exporter customer_exporter
  destination 10.7.253.22
  transport udp 2055
  export-protocol ipfix
  option interface-table timeout 3600
  option exporter-stats timeout 300
  option application-table timeout 3600
flow exporter meraki_exporter
  destination 1.1.3.2
  transport udp 9995
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertFalse(running_diff)
        self.assertEqual(running_diff.diff, None)
        self.assertEqual(running_diff.diff_reverse, None)
        self.assertEqual(running_diff.cli, '')
        self.assertEqual(running_diff.cli_reverse, '')

    def test_exporter(self):
        config_1 = """
flow monitor meraki_monitor
  exporter meraki_exporter
  exporter customer_exporter
        """
        config_2 = """
flow monitor meraki_monitor
  exporter customer_exporter
  exporter meraki_exporter
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertFalse(running_diff)
        self.assertEqual(running_diff.diff, None)
        self.assertEqual(running_diff.diff_reverse, None)
        self.assertEqual(running_diff.cli, '')
        self.assertEqual(running_diff.cli_reverse, '')

    def test_username(self):
        config_1 = """
username guestshell privilege 0 password 7 03034E0E151B32444B0515
username priv01 password 7 1209171E045B5D
        """
        config_2 = """
username priv01 password 7 1209171E045B5D
username guestshell privilege 0 password 7 03034E0E151B32444B0515
        """
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertFalse(running_diff)
        self.assertEqual(running_diff.diff, None)
        self.assertEqual(running_diff.diff_reverse, None)
        self.assertEqual(running_diff.cli, '')
        self.assertEqual(running_diff.cli_reverse, '')

    def test_flow_record(self):
        config_1 = """
flow record fr_1
  match ipv6 protocol
flow record fr_ipv4
  match ipv4 protocol
  match ipv4 version
  collect connection initiator
  collect connection new-connections
  collect connection server counter bytes network long
  collect connection server counter packets long
flow record fr_ipv6
  match ipv6 protocol
  match ipv6 version
  collect connection initiator
  collect connection new-connections
  collect connection server counter bytes network long
  collect connection server counter packets long
"""
        config_2 = """
flow record fr_ipv4
  match ipv4 version
  match ipv4 protocol
  collect connection server counter bytes network long
  collect connection server counter packets long
  collect connection initiator
  collect connection new-connections
flow record fr_ipv6
  match ipv6 version
  match ipv6 protocol
  collect connection server counter bytes network long
  collect connection server counter packets long
  collect connection initiator
  collect connection new-connections
flow record fr_1
  match ipv6 protocol
"""
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertFalse(running_diff)
        self.assertEqual(running_diff.diff, None)
        self.assertEqual(running_diff.diff_reverse, None)
        self.assertEqual(running_diff.cli, '')
        self.assertEqual(running_diff.cli_reverse, '')

    def test_neighbor(self):
        config_1 = """
router bgp 1.1
  neighbor T1-ASN64901 peer-group
  neighbor T1-ASN64901 remote-as 64901
  neighbor T1-ASN64901 timers 5 15
  neighbor T1-ASN2.101 peer-group
  neighbor T1-ASN2.101 remote-as 2.101
  neighbor 68.121.245.1 peer-group T1-ASN1.101
  neighbor 68.121.245.1 description ba8344-627f8e-agg-t1-a-1
  neighbor 68.121.245.13 peer-group T1-ASN1.101
  neighbor 68.121.245.13 description ba8344-627f8e-agg-t1-a-4
  neighbor 68.121.245.53 peer-group T1-ASN1.107
  neighbor 68.121.245.53 description ba8344-627f8e-agg-t1-a-14
  neighbor 68.121.245.57 peer-group T1-ASN1.108
  neighbor 68.121.245.57 description ba8344-627f8e-agg-t1-a-15
  address-family ipv4
    neighbor T1-ASN64901 send-community both
    neighbor T1-ASN64901 advertisement-interval 1
    neighbor T1-ASN64901 allowas-in
    neighbor T1-ASN2.101 send-community both
    neighbor T1-ASN2.101 advertisement-interval 1
    neighbor T1-ASN2.101 allowas-in
    no neighbor 68.121.245.2 activate
    no neighbor 68.121.245.1 activate
"""
        config_2 = """
router bgp 1.1
  neighbor T1-ASN2.101 peer-group
  neighbor T1-ASN2.101 remote-as 2.101
  neighbor T1-ASN64901 peer-group
  neighbor T1-ASN64901 remote-as 64901
  neighbor T1-ASN64901 timers 5 15
  neighbor 68.121.245.1 peer-group T1-ASN1.101
  neighbor 68.121.245.1 description ba8344-627f8e-agg-t1-a-1
  neighbor 68.121.245.13 peer-group T1-ASN1.101
  neighbor 68.121.245.13 description ba8344-627f8e-agg-t1-a-4
  neighbor 68.121.245.53 peer-group T1-ASN1.107
  neighbor 68.121.245.53 description ba8344-627f8e-agg-t1-a-14
  neighbor 68.121.245.57 peer-group T1-ASN1.108
  neighbor 68.121.245.57 description ba8344-627f8e-agg-t1-a-15
  address-family ipv4
    neighbor T1-ASN2.101 send-community both
    neighbor T1-ASN2.101 advertisement-interval 1
    neighbor T1-ASN2.101 allowas-in
    no neighbor 68.121.245.1 activate
    no neighbor 68.121.245.2 activate
    neighbor T1-ASN64901 send-community both
    neighbor T1-ASN64901 advertisement-interval 1
    neighbor T1-ASN64901 allowas-in
"""
        running_diff = RunningConfigDiff(
            running1=config_1,
            running2=config_2,
        )
        self.assertFalse(running_diff)
        self.assertEqual(running_diff.diff, None)
        self.assertEqual(running_diff.diff_reverse, None)
        self.assertEqual(running_diff.cli, '')
        self.assertEqual(running_diff.cli_reverse, '')
