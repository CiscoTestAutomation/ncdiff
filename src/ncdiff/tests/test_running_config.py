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
