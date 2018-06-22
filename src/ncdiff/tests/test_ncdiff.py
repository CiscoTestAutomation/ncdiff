#!/bin/env python
""" Unit tests for the ncdiff cisco-shared package. """

import unittest
from lxml import etree
from ncdiff.manager import ModelDevice
from ncdiff.config import Config, ConfigDelta
from ncdiff.errors import ConfigDeltaError

from ncclient import operations
from ncclient.manager import Manager
from ncclient.devices.default import DefaultDeviceHandler



def my_execute(*args, **kwargs):
    reply_xml = """<rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101"><data><network-instances xmlns="http://openconfig.net/yang/network-instance"><network-instance><name>Mgmt-intf</name><config><name>Mgmt-intf</name><type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:L3VRF</type><enabled-address-families xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</enabled-address-families><enabled-address-families xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</enabled-address-families></config><interfaces><interface><id>GigabitEthernet0</id><config><id>GigabitEthernet0</id><interface>GigabitEthernet0</interface></config></interface></interfaces><tables><table><protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol><address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family><config><protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol><address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family></config></table><table><protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol><address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family><config><protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol><address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family></config></table><table><protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol><address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family><config><protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol><address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family></config></table><table><protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol><address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family><config><protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol><address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family></config></table></tables><protocols><protocol><identifier xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</identifier><name>100</name><config><identifier xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</identifier><name>100</name></config><bgp><global><graceful-restart><config><enabled>false</enabled></config></graceful-restart><route-selection-options><config><always-compare-med>false</always-compare-med></config></route-selection-options></global></bgp></protocol><protocol><identifier xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</identifier><name>DEFAULT</name><config><identifier xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</identifier><name>DEFAULT</name></config><static-routes><static><prefix>0.0.0.0/0</prefix><config><prefix>0.0.0.0/0</prefix></config><next-hops><next-hop><index>5.28.0.1</index><config><index>5.28.0.1</index><next-hop>5.28.0.1</next-hop></config></next-hop></next-hops></static></static-routes></protocol><protocol><identifier xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</identifier><name>DEFAULT</name><config><identifier xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</identifier><name>DEFAULT</name></config></protocol></protocols></network-instance></network-instances></data></rpc-reply>"""
    reply = operations.rpc.RPCReply(reply_xml)
    reply.parse()
    return reply

Manager.execute = my_execute


class MySSHSession():

    def __init__(self):
        self._is_stopped = False
        self._connected = False
        self._server_capabilities = server_capabilities

    @property
    def connected(self):
        return self._connected

    def connect(self, host=None, port=None, username=None, password=None, hostkey_verify=None):
        self._connected = True

    def close(self):
        self._connected = False

    def send(self, message):
        pass

    def get_listener_instance(self, cls):
        pass

    def add_listener(self, listener):
        pass

    def is_alive(self):
        return True


server_capabilities = [
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-UNIFIED-FIREWALL-MIB?module=CISCO-UNIFIED-FIREWALL-MIB&revision=2005-09-22',
'urn:ietf:params:xml:ns:yang:smiv2:IANA-RTPROTO-MIB?module=IANA-RTPROTO-MIB&revision=2000-09-26',
'http://openconfig.net/yang/packet-match-types?module=openconfig-packet-match-types&revision=2017-04-26',
'urn:ietf:params:xml:ns:yang:smiv2:PerfHist-TC-MIB?module=PerfHist-TC-MIB&revision=1998-11-07',
'urn:ietf:params:xml:ns:yang:smiv2:INET-ADDRESS-MIB?module=INET-ADDRESS-MIB&revision=2005-02-04',
'http://cisco.com/ns/yang/Cisco-IOS-XE-arp?module=Cisco-IOS-XE-arp&revision=2017-11-07',
'urn:ietf:params:xml:ns:yang:smiv2:EtherLike-MIB?module=EtherLike-MIB&revision=2003-09-19',
'urn:ietf:params:xml:ns:yang:smiv2:RFC-1212?module=RFC-1212',
'urn:ietf:params:xml:ns:yang:ietf-diffserv-target?module=ietf-diffserv-target&revision=2015-04-07&features=target-inline-policy-config',
'urn:ietf:params:xml:ns:yang:smiv2:RMON2-MIB?module=RMON2-MIB&revision=1996-05-27',
'http://cisco.com/ns/yang/cisco-xe-bgp-policy-deviation?module=cisco-xe-openconfig-bgp-policy-deviation&revision=2017-07-24',
'http://openconfig.net/yang/system/procmon?module=openconfig-procmon&revision=2017-09-18',
'http://cisco.com/ns/yang/Cisco-IOS-XE-spanning-tree?module=Cisco-IOS-XE-spanning-tree&revision=2017-11-27',
'http://openconfig.net/yang/rib/bgp-types?module=openconfig-rib-bgp-types&revision=2016-04-11',
'http://cisco.com/ns/yang/cisco-xe-openconfig-acl-ext?module=cisco-xe-openconfig-acl-ext&revision=2017-03-30',
'urn:ietf:params:xml:ns:yang:smiv2:RFC1315-MIB?module=RFC1315-MIB',
'http://cisco.com/ns/yang/Cisco-IOS-XE-ospfv3?module=Cisco-IOS-XE-ospfv3&revision=2017-11-27',
'http://cisco.com/ns/yang/cisco-xe-routing-policy-deviation?module=cisco-xe-openconfig-routing-policy-deviation&revision=2017-03-30',
'http://cisco.com/ns/yang/Cisco-IOS-XE-device-hardware-oper?module=Cisco-IOS-XE-device-hardware-oper&revision=2017-11-01',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-IPSEC-FLOW-MONITOR-MIB?module=CISCO-IPSEC-FLOW-MONITOR-MIB&revision=2007-10-24',
'http://openconfig.net/yang/cisco-xe-openconfig-if-ip-deviation?module=cisco-xe-openconfig-if-ip-deviation&revision=2017-03-04',
'http://cisco.com/ns/yang/Cisco-IOS-XE-qos?module=Cisco-IOS-XE-qos&revision=2017-02-07',
'http://cisco.com/ns/yang/Cisco-IOS-XE-fib-oper?module=Cisco-IOS-XE-fib-oper&revision=2017-07-04',
'http://cisco.com/ns/yang/Cisco-IOS-XE-crypto?module=Cisco-IOS-XE-crypto&revision=2017-11-27',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-SIP-UA-MIB?module=CISCO-SIP-UA-MIB&revision=2004-02-19',
'urn:ietf:params:xml:ns:netconf:base:1.0?module=ietf-netconf&revision=2011-06-01',
'http://cisco.com/ns/yang/Cisco-IOS-XE-isis?module=Cisco-IOS-XE-isis&revision=2017-11-27',
'http://cisco.com/ns/yang/cisco-xe-openconfig-spanning-tree-deviation?module=cisco-xe-openconfig-spanning-tree-deviation&revision=2017-08-21',
'urn:ietf:params:xml:ns:yang:smiv2:ENTITY-MIB?module=ENTITY-MIB&revision=2005-08-10',
'urn:ietf:params:xml:ns:yang:smiv2:RMON-MIB?module=RMON-MIB&revision=2000-05-11',
'http://cisco.com/ns/yang/Cisco-IOS-XE-ptp?module=Cisco-IOS-XE-ptp&revision=2017-09-19',
'urn:ietf:params:xml:ns:yang:smiv2:IPMROUTE-STD-MIB?module=IPMROUTE-STD-MIB&revision=2000-09-22', 'urn:ietf:params:xml:ns:yang:smiv2:HCNUM-TC?module=HCNUM-TC&revision=2000-06-08',
'urn:ietf:params:netconf:capability:with-defaults:1.0?basic-mode=explicit&also-supported=report-all-tagged',
'urn:ietf:params:xml:ns:yang:smiv2:BRIDGE-MIB?module=BRIDGE-MIB&revision=2005-09-19',
'http://cisco.com/ns/yang/Cisco-IOS-XE-cdp-oper?module=Cisco-IOS-XE-cdp-oper&revision=2017-09-21',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-IPSEC-MIB?module=CISCO-IPSEC-MIB&revision=2000-08-07',
'urn:ietf:params:xml:ns:yang:smiv2:IANA-ADDRESS-FAMILY-NUMBERS-MIB?module=IANA-ADDRESS-FAMILY-NUMBERS-MIB&revision=2000-09-08',
'urn:cisco:params:xml:ns:yang:cisco-ethernet?module=cisco-ethernet&revision=2016-05-10',
'http://cisco.com/ns/yang/Cisco-IOS-XE-bfd-oper?module=Cisco-IOS-XE-bfd-oper&revision=2017-09-10', 'urn:ietf:params:xml:ns:yang:smiv2:UDP-MIB?module=UDP-MIB&revision=2005-05-20',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-RF-MIB?module=CISCO-RF-MIB&revision=2005-09-01',
'urn:ietf:params:xml:ns:yang:smiv2:DIFFSERV-DSCP-TC?module=DIFFSERV-DSCP-TC&revision=2002-05-09',
'urn:ietf:params:xml:ns:yang:ietf-ipv6-unicast-routing?module=ietf-ipv6-unicast-routing&revision=2015-05-25&deviations=cisco-xe-ietf-ipv6-unicast-routing-deviation',
'http://cisco.com/ns/yang/Cisco-IOS-XE-udld?module=Cisco-IOS-XE-udld&revision=2017-11-27',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-IPSLA-ECHO-MIB?module=CISCO-IPSLA-ECHO-MIB&revision=2007-08-16',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-CBP-TC-MIB?module=CISCO-CBP-TC-MIB&revision=2008-06-24',
'http://cisco.com/ns/yang/Cisco-IOS-XE-environment-oper?module=Cisco-IOS-XE-environment-oper&revision=2017-10-23',
'urn:ietf:params:xml:ns:yang:smiv2:OSPF-TRAP-MIB?module=OSPF-TRAP-MIB&revision=2006-11-10',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-IP-LOCAL-POOL-MIB?module=CISCO-IP-LOCAL-POOL-MIB&revision=2007-11-12',
'urn:ietf:params:xml:ns:yang:ietf-diffserv-action?module=ietf-diffserv-action&revision=2015-04-07&features=priority-rate-burst-support,hierarchial-policy-support,aqm-red-support',
'http://openconfig.net/yang/rib/bgp?module=openconfig-rib-bgp&revision=2017-03-07',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-ENTITY-EXT-MIB?module=CISCO-ENTITY-EXT-MIB&revision=2008-11-24',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-CBP-TARGET-MIB?module=CISCO-CBP-TARGET-MIB&revision=2006-05-24',
'http://cisco.com/ns/yang/Cisco-IOS-XE-ppp-oper?module=Cisco-IOS-XE-ppp-oper&revision=2017-11-01',
'urn:cisco:params:xml:ns:yang:cisco-qos-common?module=cisco-qos-common&revision=2015-05-09',
'urn:ietf:params:xml:ns:yang:smiv2:SNMP-FRAMEWORK-MIB?module=SNMP-FRAMEWORK-MIB&revision=2002-10-14',
'urn:ietf:params:xml:ns:yang:ietf-yang-library?module=ietf-yang-library&revision=2016-06-21',
'http://openconfig.net/yang/openconfig-ext?module=openconfig-extensions&revision=2017-04-11',
'http://openconfig.net/yang/wavelength-router?module=openconfig-wavelength-router&revision=2016-03-31',
'http://cisco.com/ns/yang/Cisco-IOS-XE-acl-oper?module=Cisco-IOS-XE-acl-oper&revision=2017-02-07',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-NBAR-PROTOCOL-DISCOVERY-MIB?module=CISCO-NBAR-PROTOCOL-DISCOVERY-MIB&revision=2002-08-16',
'http://cisco.com/ns/yang/Cisco-IOS-XE-ipv6-oper?module=Cisco-IOS-XE-ipv6-oper&revision=2017-11-01',
'http://cisco.com/ns/yang/Cisco-IOS-XE-diagnostics?module=Cisco-IOS-XE-diagnostics&revision=2017-02-07',
'http://cisco.com/ns/yang/Cisco-IOS-XE-multicast?module=Cisco-IOS-XE-multicast&revision=2017-11-27',
'http://cisco.com/ns/yang/Cisco-IOS-XE-trustsec-oper?module=Cisco-IOS-XE-trustsec-oper&revision=2017-02-07',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-CEF-TC?module=CISCO-CEF-TC&revision=2005-09-30',
'http://cisco.com/ns/cisco-xe-openconfig-acl-deviation?module=cisco-xe-openconfig-acl-deviation&revision=2017-08-25',
'http://cisco.com/ns/yang/cisco-xe-ietf-event-notifications-deviation?module=cisco-xe-ietf-event-notifications-deviation&revision=2017-08-22',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-SYSLOG-MIB?module=CISCO-SYSLOG-MIB&revision=2005-12-03',
'urn:ietf:params:xml:ns:yang:smiv2:EXPRESSION-MIB?module=EXPRESSION-MIB&revision=2005-11-24',
'http://cisco.com/ns/yang/Cisco-IOS-XE-vtp?module=Cisco-IOS-XE-vtp&revision=2017-02-07',
'http://openconfig.net/yang/aaa/types?module=openconfig-aaa-types&revision=2017-09-18',
'urn:ietf:params:xml:ns:yang:smiv2:DIFFSERV-MIB?module=DIFFSERV-MIB&revision=2002-02-07',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-OSPF-MIB?module=CISCO-OSPF-MIB&revision=2003-07-18',
'http://cisco.com/ns/yang/Cisco-IOS-XE-nhrp?module=Cisco-IOS-XE-nhrp&revision=2017-02-07',
'http://cisco.com/yang/cisco-odm?module=cisco-odm&revision=2017-04-25',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-AAA-SESSION-MIB?module=CISCO-AAA-SESSION-MIB&revision=2006-03-21',
'http://openconfig.net/yang/platform?module=openconfig-platform&revision=2016-12-22&deviations=cisco-xe-openconfig-platform-deviation',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-TC?module=CISCO-TC&revision=2011-11-11',
'http://cisco.com/ns/yang/Cisco-IOS-XE-ntp-oper?module=Cisco-IOS-XE-ntp-oper&revision=2017-11-01',
'http://cisco.com/yang/cisco-self-mgmt?module=cisco-self-mgmt&revision=2016-05-14',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-FLASH-MIB?module=CISCO-FLASH-MIB&revision=2013-08-06',
'http://cisco.com/ns/yang/Cisco-IOS-XE-switch?module=Cisco-IOS-XE-switch&revision=2017-11-27&deviations=Cisco-IOS-XE-switch-deviation',
'http://cisco.com/ns/yang/cisco-xe-openconfig-platform-deviation?module=cisco-xe-openconfig-platform-deviation&revision=2017-09-01',
'http://cisco.com/yang/cisco-dmi-aaa?module=cisco-dmi-aaa&revision=2017-05-17',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-VLAN-IFTABLE-RELATIONSHIP-MIB?module=CISCO-VLAN-IFTABLE-RELATIONSHIP-MIB&revision=2013-07-15',
'urn:ietf:params:netconf:capability:yang-library:1.0?revision=2016-06-21&module-set-id=f47eea7ecf2253450bb07d0f78ca7104',
'http://cisco.com/ns/yang/Cisco-IOS-XE-eem?module=Cisco-IOS-XE-eem&revision=2017-11-20',
'http://cisco.com/ns/yang/Cisco-IOS-XE-cfm-oper?module=Cisco-IOS-XE-cfm-oper&revision=2017-06-06',
'http://cisco.com/ns/yang/Cisco-IOS-XE-avb?module=Cisco-IOS-XE-avb&revision=2017-09-19',
'http://openconfig.net/yang/oc-mapping-acl?module=oc-mapping-acl&revision=2017-05-26',
'http://cisco.com/ns/yang/Cisco-IOS-XE-aaa-oper?module=Cisco-IOS-XE-aaa-oper&revision=2017-11-01',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-CONFIG-COPY-MIB?module=CISCO-CONFIG-COPY-MIB&revision=2005-04-06',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-CBP-TARGET-TC-MIB?module=CISCO-CBP-TARGET-TC-MIB&revision=2006-03-24',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-DOT3-OAM-MIB?module=CISCO-DOT3-OAM-MIB&revision=2006-05-31',
'http://cisco.com/ns/yang/Cisco-IOS-XE-switch-deviation?module=Cisco-IOS-XE-switch-deviation&revision=2016-12-01',
'http://tail-f.com/yang/netconf-monitoring?module=tailf-netconf-monitoring&revision=2016-11-24',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-VTP-MIB?module=CISCO-VTP-MIB&revision=2013-10-14',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-BGP4-MIB?module=CISCO-BGP4-MIB&revision=2010-09-30',
'http://openconfig.net/yang/network-instance-types?module=openconfig-network-instance-types&revision=2016-12-15',
'http://cisco.com/ns/yang/Cisco-IOS-XE-checkpoint-archive-oper?module=Cisco-IOS-XE-checkpoint-archive-oper&revision=2017-04-01', 'urn:ietf:params:netconf:capability:xpath:1.0',
'http://cisco.com/ns/yang/Cisco-IOS-XE-sanet?module=Cisco-IOS-XE-sanet&revision=2017-11-27',
'urn:ietf:params:xml:ns:yang:ietf-interfaces-ext?module=ietf-interfaces-ext',
'urn:ietf:params:xml:ns:yang:ietf-interfaces?module=ietf-interfaces&revision=2014-05-08&features=pre-provisioning,if-mib,arbitrary-names',
'urn:ietf:params:netconf:capability:writable-running:1.0',
'http://openconfig.net/yang/bgp-policy?module=openconfig-bgp-policy&revision=2016-06-21&deviations=cisco-xe-openconfig-bgp-policy-deviation',
'http://cisco.com/ns/yang/Cisco-IOS-XE-policy?module=Cisco-IOS-XE-policy&revision=2017-11-27&deviations=Cisco-IOS-XE-switch-deviation',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-IPSLA-JITTER-MIB?module=CISCO-IPSLA-JITTER-MIB&revision=2007-07-24', 'http://cisco.com/ns/yang/Cisco-IOS-XE-dot1x?module=Cisco-IOS-XE-dot1x&revision=2017-11-27',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-VLAN-MEMBERSHIP-MIB?module=CISCO-VLAN-MEMBERSHIP-MIB&revision=2007-12-14', 'urn:ietf:params:xml:ns:yang:cisco-policy-filters?module=cisco-policy-filters&revision=2016-03-30',
'urn:ietf:params:netconf:capability:notification:1.0',
'http://cisco.com/ns/yang/Cisco-IOS-XE-lisp-oper?module=Cisco-IOS-XE-lisp-oper&revision=2017-10-25',
'urn:ietf:params:xml:ns:yang:smiv2:IF-MIB?module=IF-MIB&revision=2000-06-14',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-ENTITY-SENSOR-MIB?module=CISCO-ENTITY-SENSOR-MIB&revision=2015-01-15',
'http://cisco.com/ns/yang/cisco-xe-openconfig-platform-ext?module=cisco-xe-openconfig-platform-ext&revision=2017-05-11',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-CDP-MIB?module=CISCO-CDP-MIB&revision=2005-03-21',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-PING-MIB?module=CISCO-PING-MIB&revision=2001-08-28',
'http://cisco.com/ns/yang/Cisco-IOS-XE-bgp?module=Cisco-IOS-XE-bgp&revision=2017-11-09',
'http://openconfig.net/yang/local-routing?module=openconfig-local-routing&revision=2016-05-11',
'urn:ietf:params:xml:ns:yang:ietf-diffserv-policy?module=ietf-diffserv-policy&revision=2015-04-07&features=policy-template-support,hierarchial-policy-support',
'http://cisco.com/ns/yang/Cisco-IOS-XE-igmp?module=Cisco-IOS-XE-igmp&revision=2017-11-27',
'\n        urn:ietf:params:netconf:capability:notification:1.1\n      ',
'http://cisco.com/ns/yang/Cisco-IOS-XE-vstack?module=Cisco-IOS-XE-vstack&revision=2017-02-07',
'http://cisco.com/ns/yang/Cisco-IOS-XE-mpls-ldp?module=Cisco-IOS-XE-mpls-ldp&revision=2017-02-07&features=mpls-ldp-nsr,mpls-ldp-iccp,mpls-ldp-extended,mpls-ldp-bgp',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-IMAGE-MIB?module=CISCO-IMAGE-MIB&revision=1995-08-15',
'http://cisco.com/ns/yang/Cisco-IOS-XE-ppp?module=Cisco-IOS-XE-ppp&revision=2017-11-29',
'urn:ietf:params:xml:ns:yang:ietf-inet-types?module=ietf-inet-types&revision=2013-07-15',
'urn:ietf:params:xml:ns:yang:ietf-restconf-monitoring?module=ietf-restconf-monitoring&revision=2016-08-15',
'urn:ietf:params:xml:ns:yang:smiv2:DISMAN-EVENT-MIB?module=DISMAN-EVENT-MIB&revision=2000-10-16',
'urn:ietf:params:xml:ns:yang:smiv2:NOTIFICATION-LOG-MIB?module=NOTIFICATION-LOG-MIB&revision=2000-11-27',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-IGMP-FILTER-MIB?module=CISCO-IGMP-FILTER-MIB&revision=2005-11-29',
'urn:ietf:params:xml:ns:yang:ietf-routing?module=ietf-routing&revision=2015-05-25&features=router-id,multiple-ribs&deviations=cisco-xe-ietf-routing-deviation',
'http://cisco.com/ns/yang/cisco-xe-openconfig-network-instance-deviation?module=cisco-xe-openconfig-network-instance-deviation&revision=2017-02-14',
'http://cisco.com/ns/yang/Cisco-IOS-XE-dhcp?module=Cisco-IOS-XE-dhcp&revision=2017-11-27',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-VPDN-MGMT-MIB?module=CISCO-VPDN-MGMT-MIB&revision=2009-06-16',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-SMI?module=CISCO-SMI&revision=2012-08-29',
'http://cisco.com/ns/yang/Cisco-IOS-XE-interface-common?module=Cisco-IOS-XE-interface-common&revision=2017-11-27',
'urn:ietf:params:xml:ns:yang:smiv2:IP-FORWARD-MIB?module=IP-FORWARD-MIB&revision=1996-09-19',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-MEDIA-GATEWAY-MIB?module=CISCO-MEDIA-GATEWAY-MIB&revision=2009-02-25',
'http://openconfig.net/yang/interfaces/ip?module=openconfig-if-ip&revision=2016-12-22&deviations=cisco-xe-openconfig-if-ip-deviation,cisco-xe-openconfig-interfaces-deviation',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-IP-TAP-MIB?module=CISCO-IP-TAP-MIB&revision=2004-03-11',
'urn:ietf:params:xml:ns:yang:smiv2:BGP4-MIB?module=BGP4-MIB&revision=1994-05-05',
'http://openconfig.net/yang/routing-policy?module=openconfig-routing-policy&revision=2016-05-12&deviations=cisco-xe-openconfig-routing-policy-deviation',
'http://cisco.com/ns/yang/Cisco-IOS-XE-mdt-cfg?module=Cisco-IOS-XE-mdt-cfg&revision=2017-09-20',
'urn:ietf:params:xml:ns:yang:ietf-event-notifications?module=ietf-event-notifications&revision=2016-10-27&features=json,configured-subscriptions&deviations=cisco-xe-ietf-event-notifications-deviation,cisco-xe-ietf-yang-push-deviation',
'http://cisco.com/ns/yang/Cisco-IOS-XE-vlan?module=Cisco-IOS-XE-vlan&revision=2017-10-02',
'http://cisco.com/ns/yang/Cisco-IOS-XE-device-sensor?module=Cisco-IOS-XE-device-sensor&revision=2017-02-07',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-ST-TC?module=CISCO-ST-TC&revision=2012-08-08',
'http://openconfig.net/yang/cisco-xe-openconfig-interfaces-deviation?module=cisco-xe-openconfig-interfaces-deviation&revision=2017-10-30',
'http://cisco.com/ns/yang/Cisco-IOS-XE-route-map?module=Cisco-IOS-XE-route-map&revision=2017-07-27',
'http://cisco.com/ns/genet/genet-state?module=genet-state',
'urn:ietf:params:xml:ns:yang:ietf-ipv4-unicast-routing?module=ietf-ipv4-unicast-routing&revision=2015-05-25&deviations=cisco-xe-ietf-ipv4-unicast-routing-deviation',
'http://openconfig.net/yang/aaa?module=openconfig-aaa&revision=2017-09-18',
'http://cisco.com/ns/yang/Cisco-IOS-XE-coap?module=Cisco-IOS-XE-coap&revision=2017-02-07',
'http://cisco.com/ns/yang/Cisco-IOS-XE-acl?module=Cisco-IOS-XE-acl&revision=2017-08-01',
'urn:ietf:params:xml:ns:yang:smiv2:SNMP-TARGET-MIB?module=SNMP-TARGET-MIB&revision=1998-08-04',
'http://cisco.com/ns/yang/Cisco-IOS-XE-mpls?module=Cisco-IOS-XE-mpls&revision=2017-11-27',
'http://openconfig.net/yang/network-instance?module=openconfig-network-instance&revision=2017-01-13&deviations=cisco-xe-openconfig-bgp-deviation,cisco-xe-openconfig-network-instance-deviation',
'http://openconfig.net/yang/lldp?module=openconfig-lldp&revision=2016-05-16',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-DATA-COLLECTION-MIB?module=CISCO-DATA-COLLECTION-MIB&revision=2002-10-30',
'http://cisco.com/ns/yang/Cisco-IOS-XE-flow?module=Cisco-IOS-XE-flow&revision=2017-11-27',
'http://cisco.com/ns/yang/cisco-xe-openconfig-vlan-deviation?module=cisco-xe-openconfig-vlan-deviation&revision=2017-03-17',
'urn:ietf:params:xml:ns:yang:smiv2:RFC1213-MIB?module=RFC1213-MIB',
'http://cisco.com/ns/yang/Cisco-IOS-XE-types?module=Cisco-IOS-XE-types&revision=2017-11-27',
'urn:ietf:params:xml:ns:yang:ietf-yang-smiv2?module=ietf-yang-smiv2&revision=2012-06-22',
'http://cisco.com/ns/yang/Cisco-IOS-XE-icmp?module=Cisco-IOS-XE-icmp&revision=2017-11-27',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-ENTITY-QFP-MIB?module=CISCO-ENTITY-QFP-MIB&revision=2014-06-18',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-IP-URPF-MIB?module=CISCO-IP-URPF-MIB&revision=2011-12-29',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-TAP2-MIB?module=CISCO-TAP2-MIB&revision=2009-11-06',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-BULK-FILE-MIB?module=CISCO-BULK-FILE-MIB&revision=2002-06-10',
'urn:cisco:params:xml:ns:yang:cisco-routing-ext?module=cisco-routing-ext&revision=2016-07-09',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-AAA-SERVER-MIB?module=CISCO-AAA-SERVER-MIB&revision=2003-11-17',
'http://cisco.com/ns/yang/Cisco-IOS-XE-service-routing?module=Cisco-IOS-XE-service-routing&revision=2017-07-24',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-PTP-MIB?module=CISCO-PTP-MIB&revision=2011-01-28',
'http://cisco.com/ns/yang/Cisco-IOS-XE-mpls-fwd-oper?module=Cisco-IOS-XE-mpls-fwd-oper&revision=2017-02-07',
'urn:ietf:params:xml:ns:yang:smiv2:TOKENRING-MIB?module=TOKENRING-MIB&revision=1994-10-23',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-DYNAMIC-TEMPLATE-TC-MIB?module=CISCO-DYNAMIC-TEMPLATE-TC-MIB&revision=2012-01-27',
'urn:ietf:params:xml:ns:yang:iana-crypt-hash?module=iana-crypt-hash&revision=2014-08-06&features=crypt-hash-sha-512,crypt-hash-sha-256,crypt-hash-md5',
'http://openconfig.net/yang/network-instance-l3?module=openconfig-network-instance-l3&revision=2017-01-13',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-ENTITY-VENDORTYPE-OID-MIB?module=CISCO-ENTITY-VENDORTYPE-OID-MIB&revision=2014-12-09',
'http://openconfig.net/yang/openconfig-types?module=openconfig-types&revision=2017-08-16',
'http://cisco.com/ns/yang/cisco-xe-openconfig-interfaces-ext?module=cisco-xe-openconfig-interfaces-ext&revision=2017-03-05',
'urn:ietf:params:netconf:capability:rollback-on-error:1.0',
'http://openconfig.net/yang/transport-types?module=openconfig-transport-types&revision=2016-06-17',
'urn:ietf:params:xml:ns:yang:smiv2:ENTITY-STATE-MIB?module=ENTITY-STATE-MIB&revision=2005-11-22',
'http://cisco.com/ns/yang/Cisco-IOS-XE-device-tracking?module=Cisco-IOS-XE-device-tracking&revision=2017-06-07',
'http://cisco.com/ns/yang/Cisco-IOS-XE-mka?module=Cisco-IOS-XE-mka&revision=2017-11-27',
'urn:ietf:params:xml:ns:yang:common-mpls-static?module=common-mpls-static&revision=2015-07-22&deviations=common-mpls-static-devs',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-CONTEXT-MAPPING-MIB?module=CISCO-CONTEXT-MAPPING-MIB&revision=2008-11-22',
'http://cisco.com/ns/cisco-xe-ietf-ip-deviation?module=cisco-xe-ietf-ip-deviation&revision=2016-08-10',
'http://cisco.com/ns/yang/Cisco-IOS-XE-bfd?module=Cisco-IOS-XE-bfd&revision=2017-11-27',
'http://openconfig.net/yang/lldp/types?module=openconfig-lldp-types&revision=2016-05-16',
'http://cisco.com/ns/yang/Cisco-IOS-XE-bgp-common-oper?module=Cisco-IOS-XE-bgp-common-oper&revision=2017-02-07',
'urn:ietf:params:xml:ns:yang:cisco-policy?module=cisco-policy&revision=2016-03-30',
'http://cisco.com/ns/yang/Cisco-IOS-XE-platform?module=Cisco-IOS-XE-platform&revision=2017-06-02',
'http://cisco.com/ns/yang/cisco-xe-openconfig-vlan-ext?module=cisco-xe-openconfig-vlan-ext&revision=2017-06-14&deviations=cisco-xe-openconfig-vlan-deviation',
'http://tail-f.com/yang/common-monitoring?module=tailf-common-monitoring&revision=2013-06-14',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-UBE-MIB?module=CISCO-UBE-MIB&revision=2010-11-29',
'http://cisco.com/ns/yang/Cisco-IOS-XE-power?module=Cisco-IOS-XE-power&revision=2017-11-27',
'urn:ietf:params:xml:ns:yang:smiv2:SNMPv2-TC?module=SNMPv2-TC',
'urn:ietf:params:xml:ns:yang:ietf-yang-types?module=ietf-yang-types&revision=2013-07-15',
'http://openconfig.net/yang/vlan-types?module=openconfig-vlan-types&revision=2016-05-26',
'urn:ietf:params:xml:ns:yang:smiv2:DRAFT-MSDP-MIB?module=DRAFT-MSDP-MIB&revision=1999-12-16',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-HSRP-EXT-MIB?module=CISCO-HSRP-EXT-MIB&revision=2010-09-02',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-RTTMON-TC-MIB?module=CISCO-RTTMON-TC-MIB&revision=2012-05-25',
'urn:ietf:params:xml:ns:yang:smiv2:RFC1155-SMI?module=RFC1155-SMI',
'http://tail-f.com/yang/confd-monitoring?module=tailf-confd-monitoring&revision=2013-06-14',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-NETSYNC-MIB?module=CISCO-NETSYNC-MIB&revision=2010-10-15',
'http://cisco.com/ns/yang/Cisco-IOS-XE-efp-oper?module=Cisco-IOS-XE-efp-oper&revision=2017-02-07',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-STP-EXTENSIONS-MIB?module=CISCO-STP-EXTENSIONS-MIB&revision=2013-03-07',
'http://cisco.com/ns/yang/Cisco-IOS-XE-features?module=Cisco-IOS-XE-features&revision=2017-02-07&features=vlan,table-map,switching-platform,qos-qsm,private-vlan,parameter-map,l2vpn,l2,dot1x,crypto',
'http://openconfig.net/yang/vlan?module=openconfig-vlan&revision=2016-05-26&deviations=cisco-xe-openconfig-vlan-deviation',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-IETF-BFD-MIB?module=CISCO-IETF-BFD-MIB&revision=2011-04-16',
'http://cisco.com/ns/yang/Cisco-IOS-XE-process-memory-oper?module=Cisco-IOS-XE-process-memory-oper&revision=2017-02-07',
'urn:ietf:params:xml:ns:yang:smiv2:P-BRIDGE-MIB?module=P-BRIDGE-MIB&revision=2006-01-09',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-EIGRP-MIB?module=CISCO-EIGRP-MIB&revision=2004-11-16',
'urn:ietf:params:xml:ns:yang:common-mpls-types?module=common-mpls-types&revision=2015-05-28',
'urn:ietf:params:xml:ns:yang:smiv2:VPN-TC-STD-MIB?module=VPN-TC-STD-MIB&revision=2005-11-15',
'http://cisco.com/ns/yang/Cisco-IOS-XE-aaa?module=Cisco-IOS-XE-aaa&revision=2017-11-16',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-PIM-MIB?module=CISCO-PIM-MIB&revision=2000-11-02',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-ETHERLIKE-EXT-MIB?module=CISCO-ETHERLIKE-EXT-MIB&revision=2010-06-04', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-ENTITY-FRU-CONTROL-MIB?module=CISCO-ENTITY-FRU-CONTROL-MIB&revision=2013-08-19',
'http://cisco.com/ns/yang/Cisco-IOS-XE-call-home?module=Cisco-IOS-XE-call-home&revision=2017-02-07',
'urn:ietf:params:xml:ns:yang:smiv2:INT-SERV-MIB?module=INT-SERV-MIB&revision=1997-10-03',
'http://cisco.com/ns/yang/Cisco-IOS-XE-http?module=Cisco-IOS-XE-http&revision=2017-02-07',
'http://cisco.com/ns/yang/Cisco-IOS-XE-sla?module=Cisco-IOS-XE-sla&revision=2017-08-31',
'http://cisco.com/ns/yang/Cisco-IOS-XE-tunnel?module=Cisco-IOS-XE-tunnel&revision=2017-08-28',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-CONFIG-MAN-MIB?module=CISCO-CONFIG-MAN-MIB&revision=2007-04-27',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-IETF-ISIS-MIB?module=CISCO-IETF-ISIS-MIB&revision=2005-08-16',
'http://cisco.com/ns/yang/Cisco-IOS-XE-memory-oper?module=Cisco-IOS-XE-memory-oper&revision=2017-04-01',
'urn:ietf:params:xml:ns:yang:ietf-diffserv-classifier?module=ietf-diffserv-classifier&revision=2015-04-07&features=policy-inline-classifier-config',
'http://cisco.com/ns/yang/Cisco-IOS-XE-l3vpn?module=Cisco-IOS-XE-l3vpn&revision=2017-02-07',
'http://cisco.com/ns/yang/Cisco-IOS-XE-ospf-oper?module=Cisco-IOS-XE-ospf-oper&revision=2017-10-10',
'urn:ietf:params:xml:ns:yang:smiv2:SNMPv2-MIB?module=SNMPv2-MIB&revision=2002-10-16',
'http://openconfig.net/yang/lacp?module=openconfig-lacp&revision=2016-05-26',
'http://cisco.com/ns/nvo/devs?module=nvo-devs&revision=2015-09-11',
'http://cisco.com/ns/yang/cisco-xe-openconfig-if-ethernet-ext?module=cisco-xe-openconfig-if-ethernet-ext&revision=2017-10-30',
'http://cisco.com/ns/yang/Cisco-IOS-XE-bgp-oper?module=Cisco-IOS-XE-bgp-oper&revision=2017-09-25',
'urn:ietf:params:xml:ns:yang:ietf-ospf?module=ietf-ospf&revision=2015-03-09&features=ttl-security,te-rid,router-id,remote-lfa,prefix-suppression,ospfv3-authentication-ipsec,nsr,node-flag,multi-topology,multi-area-adj,mtu-ignore,max-lsa,max-ecmp,lls,lfa,ldp-igp-sync,ldp-igp-autoconfig,interface-inheritance,instance-inheritance,graceful-restart,fast-reroute,demand-circuit,bfd,auto-cost,area-inheritance,admin-control&deviations=cisco-xe-ietf-ospf-deviation',
'urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring?module=ietf-netconf-monitoring&revision=2010-10-04',
'urn:ietf:params:xml:ns:yang:smiv2:TCP-MIB?module=TCP-MIB&revision=2005-02-18', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-ENHANCED-MEMPOOL-MIB?module=CISCO-ENHANCED-MEMPOOL-MIB&revision=2008-12-05',
'http://openconfig.net/yang/oc-mapping-network-instance?module=oc-mapping-network-instance&revision=2017-01-17',
'http://cisco.com/ns/yang/Cisco-IOS-XE-bgp-route-oper?module=Cisco-IOS-XE-bgp-route-oper&revision=2017-09-25',
'http://cisco.com/ns/yang/Cisco-IOS-XE-vlan-oper?module=Cisco-IOS-XE-vlan-oper&revision=2017-05-05',
'http://cisco.com/ns/yang/Cisco-IOS-XE-nd?module=Cisco-IOS-XE-nd&revision=2017-11-27',
'urn:ietf:params:xml:ns:yang:smiv2:IPV6-FLOW-LABEL-MIB?module=IPV6-FLOW-LABEL-MIB&revision=2003-08-28',
'http://cisco.com/ns/yang/cisco-xe-openconfig-spanning-tree-ext?module=cisco-xe-openconfig-spanning-tree-ext&revision=2017-10-24',
'http://cisco.com/ns/yang/Cisco-IOS-XE-rip?module=Cisco-IOS-XE-rip&revision=2017-11-27',
'urn:ietf:params:netconf:base:1.1',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-LICENSE-MGMT-MIB?module=CISCO-LICENSE-MGMT-MIB&revision=2012-04-19',
'http://cisco.com/ns/yang/Cisco-IOS-XE-native?module=Cisco-IOS-XE-native&revision=2017-10-24&deviations=Cisco-IOS-XE-switch-deviation',
'urn:ietf:params:xml:ns:yang:smiv2:CISCO-DYNAMIC-TEMPLATE-MIB?module=CISCO-DYNAMIC-TEMPLATE-MIB&revision=2007-09-06',
'http://cisco.com/ns/cisco-xe-ietf-routing-deviation?module=cisco-xe-ietf-routing-deviation&revision=2016-07-09', 'http://cisco.com/ns/yang/ios-xe/template?module=Cisco-IOS-XE-template&revision=2017-11-06', 'http://openconfig.net/yang/cisco-xe-openconfig-if-ethernet-deviation?module=cisco-xe-openconfig-if-ethernet-deviation&revision=2017-11-01', 'http://cisco.com/ns/yang/Cisco-IOS-XE-track?module=Cisco-IOS-XE-track&revision=2017-04-28', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-EMBEDDED-EVENT-MGR-MIB?module=CISCO-EMBEDDED-EVENT-MGR-MIB&revision=2006-11-07', 'http://cisco.com/ns/yang/Cisco-IOS-XE-common-types?module=Cisco-IOS-XE-common-types&revision=2017-09-25', 'http://cisco.com/ns/yang/Cisco-IOS-XE-mvrp?module=Cisco-IOS-XE-mvrp&revision=2017-11-27', 'http://cisco.com/ns/yang/Cisco-IOS-XE-interfaces-oper?module=Cisco-IOS-XE-interfaces-oper&revision=2017-10-10', 'urn:ietf:params:xml:ns:yang:smiv2:Q-BRIDGE-MIB?module=Q-BRIDGE-MIB&revision=2006-01-09', 'http://cisco.com/ns/yang/Cisco-IOS-XE-wccp?module=Cisco-IOS-XE-wccp&revision=2017-11-27', 'http://cisco.com/ns/yang/Cisco-IOS-XE-lldp-oper?module=Cisco-IOS-XE-lldp-oper&revision=2017-02-07', 'urn:ietf:params:xml:ns:yang:nvo?module=nvo&revision=2015-06-02&deviations=nvo-devs', 'http://openconfig.net/yang/interfaces/aggregate?module=openconfig-if-aggregate&revision=2016-12-22&deviations=cisco-xe-openconfig-interfaces-deviation', 'urn:ietf:params:xml:ns:yang:ietf-key-chain?module=ietf-key-chain&revision=2015-02-24&features=independent-send-accept-lifetime,hex-key-string,accept-tolerance', 'urn:ietf:params:xml:ns:yang:smiv2:ETHER-WIS?module=ETHER-WIS&revision=2003-09-19', 'urn:cisco:params:xml:ns:yang:pim?module=pim&revision=2014-06-27&features=bsr,auto-rp', 'http://cisco.com/ns/yang/Cisco-IOS-XE-mld?module=Cisco-IOS-XE-mld&revision=2017-02-07', 'urn:ietf:params:xml:ns:yang:smiv2:ENTITY-SENSOR-MIB?module=ENTITY-SENSOR-MIB&revision=2002-12-16', 'urn:ietf:params:netconf:capability:validate:1.1', 'http://cisco.com/ns/yang/Cisco-IOS-XE-mmode?module=Cisco-IOS-XE-mmode&revision=2017-06-15', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-ENVMON-MIB?module=CISCO-ENVMON-MIB&revision=2003-12-01', 'http://openconfig.net/yang/optical-amplfier?module=openconfig-optical-amplifier&revision=2016-03-31', 'urn:ietf:params:xml:ns:yang:smiv2:DISMAN-EXPRESSION-MIB?module=DISMAN-EXPRESSION-MIB&revision=2000-10-16', 'http://openconfig.net/yang/types/yang?module=openconfig-yang-types&revision=2017-07-30', 'urn:ietf:params:xml:ns:yang:cisco-ospf?module=cisco-ospf&revision=2016-03-30&features=graceful-shutdown,flood-reduction,database-filter', 'http://openconfig.net/yang/spanning-tree?module=openconfig-spanning-tree&revision=2017-07-14&deviations=cisco-xe-openconfig-spanning-tree-deviation', 'http://openconfig.net/yang/bgp?module=openconfig-bgp&revision=2016-06-21', 'urn:ietf:params:xml:ns:yang:smiv2:TOKEN-RING-RMON-MIB?module=TOKEN-RING-RMON-MIB', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-ENTITY-ALARM-MIB?module=CISCO-ENTITY-ALARM-MIB&revision=1999-07-06', 'http://cisco.com/ns/yang/Cisco-IOS-XE-ethernet?module=Cisco-IOS-XE-ethernet&revision=2017-11-27', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-QOS-PIB-MIB?module=CISCO-QOS-PIB-MIB&revision=2007-08-29', 'http://cisco.com/ns/yang/Cisco-IOS-XE-ospf?module=Cisco-IOS-XE-ospf&revision=2017-11-27', 'urn:ietf:params:xml:ns:yang:smiv2:MPLS-VPN-MIB?module=MPLS-VPN-MIB&revision=2001-10-15', 'http://cisco.com/ns/yang/Cisco-IOS-XE-nat-oper?module=Cisco-IOS-XE-nat-oper&revision=2017-11-01', 'http://tail-f.com/ns/common/query?module=tailf-common-query&revision=2017-04-27', 'http://openconfig.net/yang/oc-mapping-stp?module=oc-mapping-stp&revision=2017-02-07', 'http://cisco.com/ns/yang/cisco-xe-openconfig-bgp-deviation?module=cisco-xe-openconfig-bgp-deviation&revision=2017-05-24', 'http://openconfig.net/yang/bgp-types?module=openconfig-bgp-types&revision=2016-06-21', 'http://openconfig.net/yang/policy-types?module=openconfig-policy-types&revision=2016-05-12', 'http://tail-f.com/ns/netconf/extensions', 'http://openconfig.net/yang/interfaces/ip-ext?module=openconfig-if-ip-ext&revision=2016-12-22', 'urn:ietf:params:xml:ns:yang:smiv2:LLDP-MIB?module=LLDP-MIB&revision=2005-05-06', 'http://cisco.com/ns/yang/cisco-xe-ietf-yang-push-deviation?module=cisco-xe-ietf-yang-push-deviation&revision=2017-08-22', 'urn:ietf:params:xml:ns:yang:smiv2:TUNNEL-MIB?module=TUNNEL-MIB&revision=2005-05-16', 'http://cisco.com/ns/yang/Cisco-IOS-XE-ntp?module=Cisco-IOS-XE-ntp&revision=2017-11-27', 'http://cisco.com/ns/yang/Cisco-IOS-XE-mdt-common-defs?module=Cisco-IOS-XE-mdt-common-defs&revision=2017-07-01', 'urn:ietf:params:xml:ns:yang:ietf-yang-push?module=ietf-yang-push&revision=2016-10-28&features=on-change&deviations=cisco-xe-ietf-yang-push-deviation', 'http://openconfig.net/yang/transport-line-common?module=openconfig-transport-line-common&revision=2016-03-31', 'urn:ietf:params:xml:ns:yang:smiv2:OSPF-MIB?module=OSPF-MIB&revision=2006-11-10', 'http://cisco.com/ns/yang/cisco-xe-openconfig-rib-bgp-ext?module=cisco-xe-openconfig-rib-bgp-ext&revision=2016-11-30', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-RTTMON-MIB?module=CISCO-RTTMON-MIB&revision=2012-08-16', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-HSRP-MIB?module=CISCO-HSRP-MIB&revision=2010-09-06', 'http://openconfig.net/yang/types/inet?module=openconfig-inet-types&revision=2017-08-24', 'http://cisco.com/ns/yang/Cisco-IOS-XE-lldp?module=Cisco-IOS-XE-lldp&revision=2017-11-27', 'http://cisco.com/ns/yang/Cisco-IOS-XE-cts?module=Cisco-IOS-XE-cts&revision=2017-11-27', 'http://cisco.com/ns/yang/Cisco-IOS-XE-snmp?module=Cisco-IOS-XE-snmp&revision=2017-11-27', 'urn:ietf:params:xml:ns:yang:ietf-netconf-with-defaults?module=ietf-netconf-with-defaults&revision=2011-06-01', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-PRODUCTS-MIB?module=CISCO-PRODUCTS-MIB&revision=2014-11-06', 'http://cisco.com/ns/cisco-xe-ietf-ospf-deviation?module=cisco-xe-ietf-ospf-deviation&revision=2015-09-11', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-IMAGE-LICENSE-MGMT-MIB?module=CISCO-IMAGE-LICENSE-MGMT-MIB&revision=2007-10-16', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-FIREWALL-TC?module=CISCO-FIREWALL-TC&revision=2006-03-03', 'urn:ietf:params:xml:ns:yang:smiv2:IP-MIB?module=IP-MIB&revision=2006-02-02', 'http://cisco.com/ns/yang/Cisco-IOS-XE-virtual-service-oper?module=Cisco-IOS-XE-virtual-service-oper&revision=2017-09-25', 'urn:ietf:params:xml:ns:yang:cisco-policy-target?module=cisco-policy-target&revision=2016-03-30', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-IPSLA-TC-MIB?module=CISCO-IPSLA-TC-MIB&revision=2007-03-23', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-IF-EXTENSION-MIB?module=CISCO-IF-EXTENSION-MIB&revision=2013-03-13', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-FTP-CLIENT-MIB?module=CISCO-FTP-CLIENT-MIB&revision=2006-03-31', 'http://cisco.com/ns/yang/Cisco-IOS-XE-nbar?module=Cisco-IOS-XE-nbar&revision=2017-11-27', 'http://openconfig.net/yang/rib/bgp-ext?module=openconfig-rib-bgp-ext&revision=2016-04-11', 'urn:ietf:params:netconf:capability:interleave:1.0', 'http://cisco.com/ns/yang/Cisco-IOS-XE-process-cpu-oper?module=Cisco-IOS-XE-process-cpu-oper&revision=2017-02-07', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-IPMROUTE-MIB?module=CISCO-IPMROUTE-MIB&revision=2005-03-07', 'urn:ietf:params:netconf:base:1.0', 'urn:ietf:params:xml:ns:yang:c3pl-types?module=policy-types&revision=2013-10-07&features=protocol-name-support,match-wlan-user-priority-support,match-vpls-support,match-vlan-support,match-vlan-inner-support,match-src-mac-support,match-security-group-support,match-qos-group-support,match-prec-support,match-packet-length-support,match-mpls-exp-top-support,match-mpls-exp-imp-support,match-metadata-support,match-ipv6-acl-support,match-ipv6-acl-name-support,match-ipv4-acl-support,match-ipv4-acl-name-support,match-ip-rtp-support,match-input-interface-support,match-fr-dlci-support,match-fr-de-support,match-flow-record-support,match-flow-ip-support,match-dst-mac-support,match-discard-class-support,match-dei-support,match-dei-inner-support,match-cos-support,match-cos-inner-support,match-class-map-support,match-atm-vci-support,match-atm-clp-support,match-application-support', 'http://cisco.com/ns/yang/Cisco-IOS-XE-tcam-oper?module=Cisco-IOS-XE-tcam-oper&revision=2017-06-06', 'http://cisco.com/ns/yang/Cisco-IOS-XE-eigrp?module=Cisco-IOS-XE-eigrp&revision=2017-09-21', 'http://cisco.com/ns/cisco-xe-ietf-ipv4-unicast-routing-deviation?module=cisco-xe-ietf-ipv4-unicast-routing-deviation&revision=2015-09-11', 'http://cisco.com/ns/yang/Cisco-IOS-XE-platform-software-oper?module=Cisco-IOS-XE-platform-software-oper&revision=2017-10-10', 'http://cisco.com/ns/yang/Cisco-IOS-XE-ezpm?module=Cisco-IOS-XE-ezpm&revision=2017-11-27', 'http://cisco.com/ns/yang/Cisco-IOS-XE-service-discovery?module=Cisco-IOS-XE-service-discovery&revision=2017-02-07', 'http://cisco.com/ns/yang/Cisco-IOS-XE-rsvp?module=Cisco-IOS-XE-rsvp&revision=2017-11-27', 'http://cisco.com/yang/cisco-ia?module=cisco-ia&revision=2017-03-02', 'urn:ietf:params:xml:ns:yang:ietf-netconf-notifications?module=ietf-netconf-notifications&revision=2012-02-06', 'http://cisco.com/ns/yang/Cisco-IOS-XE-stackwise-virtual?module=Cisco-IOS-XE-stackwise-virtual&revision=2017-06-05', 'http://openconfig.net/yang/interfaces/ethernet?module=openconfig-if-ethernet&revision=2016-12-22&deviations=cisco-xe-openconfig-if-ethernet-deviation,cisco-xe-openconfig-interfaces-deviation', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-CEF-MIB?module=CISCO-CEF-MIB&revision=2006-01-30', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-ETHER-CFM-MIB?module=CISCO-ETHER-CFM-MIB&revision=2004-12-28', 'http://cisco.com/ns/mpls-static/devs?module=common-mpls-static-devs&revision=2015-09-11', 'http://cisco.com/ns/yang/Cisco-IOS-XE-object-group?module=Cisco-IOS-XE-object-group&revision=2017-07-31', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-OSPF-TRAP-MIB?module=CISCO-OSPF-TRAP-MIB&revision=2003-07-18', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-IPSLA-AUTOMEASURE-MIB?module=CISCO-IPSLA-AUTOMEASURE-MIB&revision=2007-06-13', 'http://cisco.com/ns/yang/Cisco-IOS-XE-ios-events-oper?module=Cisco-IOS-XE-ios-events-oper&revision=2017-10-10', 'urn:ietf:params:xml:ns:yang:iana-if-type?module=iana-if-type&revision=2014-05-08', 'urn:ietf:params:xml:ns:yang:smiv2:RFC-1215?module=RFC-1215', 'http://openconfig.net/yang/interfaces?module=openconfig-interfaces&revision=2016-12-22&deviations=cisco-xe-openconfig-interfaces-deviation', 'http://cisco.com/ns/yang/Cisco-IOS-XE-wsma?module=Cisco-IOS-XE-wsma&revision=2017-02-07', 'urn:ietf:params:xml:ns:yang:smiv2:INTEGRATED-SERVICES-MIB?module=INTEGRATED-SERVICES-MIB&revision=1995-11-03', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-RADIUS-EXT-MIB?module=CISCO-RADIUS-EXT-MIB&revision=2010-05-25', 'urn:ietf:params:netconf:capability:validate:1.0', 'http://tail-f.com/ns/netconf/actions/1.0', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-PROCESS-MIB?module=CISCO-PROCESS-MIB&revision=2011-06-23', 'http://cisco.com/ns/yang/Cisco-IOS-XE-spanning-tree-oper?module=Cisco-IOS-XE-spanning-tree-oper&revision=2017-08-10', 'http://cisco.com/ns/yang/Cisco-IOS-XE-l2vpn?module=Cisco-IOS-XE-l2vpn&revision=2017-11-27', 'http://cisco.com/ns/yang/Cisco-IOS-XE-cdp?module=Cisco-IOS-XE-cdp&revision=2017-11-27', 'http://cisco.com/ns/yang/Cisco-IOS-XE-ip-sla-oper?module=Cisco-IOS-XE-ip-sla-oper&revision=2017-09-25', 'http://openconfig.net/yang/acl?module=openconfig-acl&revision=2017-04-26&deviations=cisco-xe-openconfig-acl-deviation', 'http://openconfig.net/yang/spanning-tree/types?module=openconfig-spanning-tree-types&revision=2017-07-14', 'http://cisco.com/ns/cisco-xe-ietf-ipv6-unicast-routing-deviation?module=cisco-xe-ietf-ipv6-unicast-routing-deviation&revision=2015-09-11', 'urn:ietf:params:xml:ns:yang:smiv2:ENTITY-STATE-TC-MIB?module=ENTITY-STATE-TC-MIB&revision=2005-11-22', 'http://cisco.com/ns/yang/Cisco-IOS-XE-mdt-oper?module=Cisco-IOS-XE-mdt-oper&revision=2017-09-20', 'http://tail-f.com/yang/common?module=tailf-common&revision=2017-08-23', 'http://cisco.com/ns/yang/Cisco-IOS-XE-rpc?module=Cisco-IOS-XE-rpc&revision=2017-11-27', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-IPSEC-POLICY-MAP-MIB?module=CISCO-IPSEC-POLICY-MAP-MIB&revision=2000-08-17', 'urn:ietf:params:xml:ns:yang:policy-attr?module=policy-attr&revision=2015-04-27', 'http://cisco.com/ns/yang/Cisco-IOS-XE-dhcp-oper?module=Cisco-IOS-XE-dhcp-oper&revision=2017-11-01', 'http://cisco.com/ns/yang/Cisco-IOS-XE-cef?module=Cisco-IOS-XE-cef&revision=2017-05-19&features=asr1k-dpi', 'urn:ietf:params:xml:ns:yang:smiv2:IGMP-STD-MIB?module=IGMP-STD-MIB&revision=2000-09-28', 'urn:ietf:params:xml:ns:yang:ietf-ip?module=ietf-ip&revision=2014-06-16&features=ipv6-privacy-autoconf,ipv4-non-contiguous-netmasks&deviations=cisco-xe-ietf-ip-deviation', 'http://openconfig.net/yang/platform-types?module=openconfig-platform-types&revision=2017-08-16', 'http://cisco.com/ns/yang/Cisco-IOS-XE-lisp?module=Cisco-IOS-XE-lisp&revision=2017-11-27', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-NTP-MIB?module=CISCO-NTP-MIB&revision=2006-07-31', 'urn:ietf:params:xml:ns:yang:smiv2:PIM-MIB?module=PIM-MIB&revision=2000-09-28', 'urn:ietf:params:xml:ns:yang:smiv2:IANAifType-MIB?module=IANAifType-MIB&revision=2006-03-31', 'http://cisco.com/ns/yang/Cisco-IOS-XE-flow-monitor-oper?module=Cisco-IOS-XE-flow-monitor-oper&revision=2017-11-30', 'urn:ietf:params:xml:ns:yang:ietf-netconf-acm?module=ietf-netconf-acm&revision=2012-02-22', 'urn:ietf:params:xml:ns:yang:smiv2:NHRP-MIB?module=NHRP-MIB&revision=1999-08-26', 'urn:ietf:params:xml:ns:yang:smiv2:CISCO-BGP-POLICY-ACCOUNTING-MIB?module=CISCO-BGP-POLICY-ACCOUNTING-MIB&revision=2002-07-26', 'urn:ietf:params:xml:ns:yang:smiv2:SNMP-PROXY-MIB?module=SNMP-PROXY-MIB&revision=2002-10-14', 'http://openconfig.net/yang/header-fields?module=openconfig-packet-match&revision=2017-04-26', 'urn:cisco:params:xml:ns:yang:cisco-xe-ietf-yang-push-ext?module=cisco-xe-ietf-yang-push-ext&revision=2017-08-14', 'http://cisco.com/ns/yang/Cisco-IOS-XE-platform-oper?module=Cisco-IOS-XE-platform-oper&revision=2017-10-11']

nc_device = ModelDevice(MySSHSession(), DefaultDeviceHandler())
nc_device.scan_models(folder='./yang', download='no')
nc_device.load_model('openconfig-interfaces')
nc_device.load_model('openconfig-network-instance')
nc_device.load_model('Cisco-IOS-XE-native')


class TestNcDiff(unittest.TestCase):

    def setUp(self):
        self.d = nc_device
        self.parser = etree.XMLParser(remove_blank_text=True)

    def test_delta_1(self):
        xml1 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"
                       message-id="101">
              <data>
                <interfaces xmlns="http://openconfig.net/yang/interfaces">
                  <interface>
                    <name>GigabitEthernet1/0/1</name>
                    <config>
                      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:ethernetCsmacd</type>
                      <name>GigabitEthernet1/0/1</name>
                      <enabled>true</enabled>
                    </config>
                    <routed-vlan xmlns="http://openconfig.net/yang/vlan">
                      <ipv6 xmlns="http://openconfig.net/yang/interfaces/ip">
                        <config>
                          <enabled>false</enabled>
                        </config>
                      </ipv6>
                    </routed-vlan>
                  </interface>
                  <interface>
                    <name>GigabitEthernet1/0/10</name>
                    <config>
                      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:ethernetCsmacd</type>
                      <name>GigabitEthernet1/0/10</name>
                      <enabled>true</enabled>
                    </config>
                    <routed-vlan xmlns="http://openconfig.net/yang/vlan">
                      <ipv6 xmlns="http://openconfig.net/yang/interfaces/ip">
                        <config>
                          <enabled>false</enabled>
                        </config>
                      </ipv6>
                    </routed-vlan>
                  </interface>
                </interfaces>
              </data>
            </rpc-reply>
            """
        xml2 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"
                       message-id="101">
              <data>
                <interfaces xmlns="http://openconfig.net/yang/interfaces">
                  <interface>
                    <name>GigabitEthernet1/0/1</name>
                    <config>
                      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:ethernetCsmacd</type>
                      <name>GigabitEthernet1/0/1</name>
                      <enabled>true</enabled>
                    </config>
                    <ethernet xmlns="http://openconfig.net/yang/interfaces/ethernet">
                      <config>
                        <port-speed>SPEED_10MB</port-speed>
                      </config>
                    </ethernet>
                    <routed-vlan xmlns="http://openconfig.net/yang/vlan">
                      <ipv6 xmlns="http://openconfig.net/yang/interfaces/ip">
                        <config>
                          <enabled>false</enabled>
                        </config>
                      </ipv6>
                    </routed-vlan>
                  </interface>
                  <interface>
                    <name>GigabitEthernet1/0/10</name>
                    <config>
                      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:ethernetCsmacd</type>
                      <name>GigabitEthernet1/0/10</name>
                      <enabled>true</enabled>
                    </config>
                    <routed-vlan xmlns="http://openconfig.net/yang/vlan">
                      <ipv6 xmlns="http://openconfig.net/yang/interfaces/ip">
                        <config>
                          <enabled>false</enabled>
                        </config>
                      </ipv6>
                    </routed-vlan>
                  </interface>
                </interfaces>
              </data>
            </rpc-reply>
            """
        expected_delta1 = """
<nc:config xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
  <interfaces xmlns="http://openconfig.net/yang/interfaces">
    <interface>
      <name>GigabitEthernet1/0/1</name>
      <ethernet xmlns="http://openconfig.net/yang/interfaces/ethernet">
        <config>
          <port-speed>SPEED_10MB</port-speed>
        </config>
      </ethernet>
    </interface>
  </interfaces>
</nc:config>
            """
        expected_delta2 = """
<nc:config xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
  <interfaces xmlns="http://openconfig.net/yang/interfaces">
    <interface>
      <name>GigabitEthernet1/0/1</name>
      <ethernet xmlns="http://openconfig.net/yang/interfaces/ethernet" nc:operation="delete"/>
    </interface>
  </interfaces>
</nc:config>
            """
        config1 = Config(self.d, xml1)
        config2 = Config(self.d, xml2)
        delta1 = config2 - config1
        delta2 = config1 - config2
        self.assertEqual(str(delta1).strip(), expected_delta1.strip())
        self.assertEqual(str(delta2).strip(), expected_delta2.strip())

    def test_delta_2(self):
        xml1 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"
                       message-id="101">
              <data>
                <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
                  <router>
                    <bgp xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-bgp">
                      <id>10</id>
                      <bgp>
                        <router-id>10.8.55.30</router-id>
                        <log-neighbor-changes/>
                      </bgp>
                    </bgp>
                  </router>
                </native>
              </data>
            </rpc-reply>
            """
        xml2 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"
                       message-id="101">
              <data>
                <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
                  <router>
                    <bgp xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-bgp">
                      <id>10</id>
                      <bgp>
                        <router-id>10.8.55.30</router-id>
                        <log-neighbor-changes/>
                        <listen>
                          <limit>2100</limit>
                          <range>
                            <network-range>10.44.0.0/16</network-range>
                            <peer-group>INET1-SPOKES</peer-group>
                          </range>
                        </listen>
                      </bgp>
                      <address-family>
                        <no-vrf>
                          <ipv4>
                            <af-name>unicast</af-name>
                          </ipv4>
                        </no-vrf>
                      </address-family>
                    </bgp>
                  </router>
                </native>
              </data>
            </rpc-reply>
            """
        expected_delta1 = """
<nc:config xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
  <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
    <router>
      <bgp xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-bgp">
        <id>10</id>
        <bgp>
          <listen>
            <limit>2100</limit>
            <range>
              <network-range>10.44.0.0/16</network-range>
              <peer-group>INET1-SPOKES</peer-group>
            </range>
          </listen>
        </bgp>
        <address-family>
          <no-vrf>
            <ipv4>
              <af-name>unicast</af-name>
            </ipv4>
          </no-vrf>
        </address-family>
      </bgp>
    </router>
  </native>
</nc:config>
            """
        expected_delta2 = """
<nc:config xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
  <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
    <router>
      <bgp xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-bgp">
        <id>10</id>
        <bgp>
          <listen nc:operation="delete"/>
        </bgp>
        <address-family nc:operation="delete"/>
      </bgp>
    </router>
  </native>
</nc:config>
            """
        config1 = Config(self.d, xml1)
        config2 = Config(self.d, xml2)
        delta1 = config2 - config1
        delta2 = -delta1
        self.assertEqual(str(delta1).strip(), expected_delta1.strip())
        self.assertEqual(str(delta2).strip(), expected_delta2.strip())

    def test_delta_3(self):
        config_xml1 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <table-connections>
                      <table-connection>
                        <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                        <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                          <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                          <import-policy>ROUTEMAP1</import-policy>
                          <import-policy>ROUTEMAP2</import-policy>
                          <default-import-policy>REJECT_ROUTE</default-import-policy>
                        </config>
                      </table-connection>
                    </table-connections>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        config_xml2 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <table-connections>
                      <table-connection>
                        <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                        <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                          <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                          <import-policy>ROUTEMAP1</import-policy>
                          <import-policy>ROUTEMAP3</import-policy>
                          <import-policy>ROUTEMAP0</import-policy>
                          <import-policy>ROUTEMAP2</import-policy>
                          <default-import-policy>REJECT_ROUTE</default-import-policy>
                        </config>
                      </table-connection>
                    </table-connections>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        config1 = Config(self.d, config_xml1)
        config2 = Config(self.d, config_xml2)
        # modify schema node
        nodes = config1.xpath('.//oc-netinst:network-instance'
                              '/oc-netinst:table-connections'
                              '/oc-netinst:table-connection'
                              '/oc-netinst:config/oc-netinst:import-policy')
        node = nodes[0]
        schema_node = config1.get_schema_node(node)
        schema_node.set('ordered-by', 'user')
        delta1 = config2 - config1
        config3 = config1 + delta1
        self.assertEqual(config2, config3)
        self.assertTrue(config2 <= config3)
        self.assertTrue(config2 >= config3)
        delta2 = config1 - config2
        config4 = config2 + delta2
        self.assertEqual(config1, config4)

    def test_delta_4(self):
        config_xml1 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <tables>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                    </tables>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        config_xml2 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <tables>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                    </tables>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        config1 = Config(self.d, config_xml1)
        config2 = Config(self.d, config_xml2)
        # modify schema node
        nodes = config1.xpath('.//oc-netinst:network-instance'
                              '/oc-netinst:tables/oc-netinst:table')
        node = nodes[0]
        schema_node = config1.get_schema_node(node)
        schema_node.set('ordered-by', 'user')
        delta1 = config2 - config1
        config3 = config1 + delta1
        self.assertEqual(config2, config3)
        self.assertTrue(config2 <= config3)
        self.assertTrue(config2 >= config3)
        delta2 = config1 - config2
        config4 = config2 + delta2
        self.assertEqual(config1, config4)

    def test_delta_5(self):
        config_xml1 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <tables>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                    </tables>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        config_xml2 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <tables>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV44</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                    </tables>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        config1 = Config(self.d, config_xml1)
        config2 = Config(self.d, config_xml2)
        # modify schema node
        nodes = config1.xpath('.//oc-netinst:network-instance'
                              '/oc-netinst:tables/oc-netinst:table')
        node = nodes[0]
        schema_node = config1.get_schema_node(node)
        schema_node.set('ordered-by', 'user')
        delta1 = ConfigDelta(config_src=config1, config_dst=config2,
                             preferred_create='create',
                             preferred_replace='replace',
                             preferred_delete='remove')
        config3 = config1 + delta1
        self.assertEqual(config2, config3)
        self.assertTrue(config2 <= config3)
        self.assertTrue(config2 >= config3)
        delta2 = config1 - config2
        config4 = config2 + delta2
        self.assertEqual(config1, config4)

    def test_delta_6(self):
        config_xml1 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <table-connections>
                      <table-connection>
                        <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                        <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                          <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                          <import-policy>ROUTEMAP1</import-policy>
                          <import-policy>ROUTEMAP2</import-policy>
                          <default-import-policy>REJECT_ROUTE</default-import-policy>
                        </config>
                      </table-connection>
                    </table-connections>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        config_xml2 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <table-connections>
                      <table-connection>
                        <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                        <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                          <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                          <import-policy>ROUTEMAP1</import-policy>
                          <import-policy>ROUTEMAP3</import-policy>
                          <import-policy>ROUTEMAP0</import-policy>
                          <import-policy>ROUTEMAP2</import-policy>
                          <default-import-policy>REJECT_ROUTE</default-import-policy>
                        </config>
                      </table-connection>
                    </table-connections>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        config1 = Config(self.d, config_xml1)
        config2 = Config(self.d, config_xml2)

        # modify schema node
        nodes = config1.xpath('.//oc-netinst:network-instance'
                              '/oc-netinst:table-connections'
                              '/oc-netinst:table-connection'
                              '/oc-netinst:config/oc-netinst:import-policy')
        node = nodes[0]
        schema_node = config1.get_schema_node(node)
        schema_node.set('ordered-by', 'user')

        delta1 = ConfigDelta(config_src=config1, config_dst=config2,
                             preferred_create='create',
                             preferred_replace='replace',
                             preferred_delete='remove')
        config3 = config1 + delta1
        self.assertEqual(config2, config3)
        self.assertTrue(config2 <= config3)
        self.assertTrue(config2 >= config3)
        delta2 = config1 - config2
        config4 = config2 + delta2
        self.assertEqual(config1, config4)

    def test_xpath_1(self):
        xml = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"
                       message-id="101">
              <data>
                <interfaces xmlns="http://openconfig.net/yang/interfaces">
                  <interface>
                    <name>GigabitEthernet1/0/1</name>
                    <config>
                      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:ethernetCsmacd</type>
                      <name>GigabitEthernet1/0/1</name>
                      <enabled>true</enabled>
                    </config>
                    <ethernet xmlns="http://openconfig.net/yang/interfaces/ethernet">
                      <config>
                        <port-speed>SPEED_10MB</port-speed>
                      </config>
                    </ethernet>
                    <routed-vlan xmlns="http://openconfig.net/yang/vlan">
                      <ipv6 xmlns="http://openconfig.net/yang/interfaces/ip">
                        <config>
                          <enabled>false</enabled>
                        </config>
                      </ipv6>
                    </routed-vlan>
                  </interface>
                  <interface>
                    <name>GigabitEthernet1/0/10</name>
                    <config>
                      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:ethernetCsmacd</type>
                      <name>GigabitEthernet1/0/10</name>
                      <enabled>true</enabled>
                    </config>
                    <routed-vlan xmlns="http://openconfig.net/yang/vlan">
                      <ipv6 xmlns="http://openconfig.net/yang/interfaces/ip">
                        <config>
                          <enabled>false</enabled>
                        </config>
                      </ipv6>
                    </routed-vlan>
                  </interface>
                </interfaces>
              </data>
            </rpc-reply>
            """
        config = Config(self.d, xml)
        result = config.xpath('/nc:config/oc-if:interfaces/oc-if:interface'
                              '[oc-if:name="GigabitEthernet1/0/1"]'
                              '/oc-eth:ethernet/oc-eth:config'
                              '/oc-eth:port-speed/text()')
        self.assertEqual(result, ['SPEED_10MB'])

    def test_filter_1(self):
        xml1 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"
                       message-id="101">
              <data>
                <interfaces xmlns="http://openconfig.net/yang/interfaces">
                  <interface>
                    <name>GigabitEthernet0/0/1</name>
                    <config>
                      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:ethernetCsmacd</type>
                      <name>GigabitEthernet0/0/1</name>
                      <enabled>true</enabled>
                    </config>
                    <ethernet xmlns="http://openconfig.net/yang/interfaces/ethernet">
                      <config>
                        <port-speed>SPEED_10MB</port-speed>
                      </config>
                    </ethernet>
                    <routed-vlan xmlns="http://openconfig.net/yang/vlan">
                      <ipv6 xmlns="http://openconfig.net/yang/interfaces/ip">
                        <config>
                          <enabled>false</enabled>
                        </config>
                      </ipv6>
                    </routed-vlan>
                  </interface>
                  <interface>
                    <name>GigabitEthernet1/0/10</name>
                    <config>
                      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:ethernetCsmacd</type>
                      <name>GigabitEthernet1/0/10</name>
                      <enabled>true</enabled>
                    </config>
                    <routed-vlan xmlns="http://openconfig.net/yang/vlan">
                      <ipv6 xmlns="http://openconfig.net/yang/interfaces/ip">
                        <config>
                          <enabled>false</enabled>
                        </config>
                      </ipv6>
                    </routed-vlan>
                  </interface>
                </interfaces>
              </data>
            </rpc-reply>
            """
        xml2 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"
                       message-id="101">
              <data>
                <interfaces xmlns="http://openconfig.net/yang/interfaces">
                  <interface>
                    <name>GigabitEthernet1/0/10</name>
                    <config>
                      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:ethernetCsmacd</type>
                      <name>GigabitEthernet1/0/10</name>
                      <enabled>true</enabled>
                    </config>
                    <routed-vlan xmlns="http://openconfig.net/yang/vlan">
                      <ipv6 xmlns="http://openconfig.net/yang/interfaces/ip">
                        <config>
                          <enabled>false</enabled>
                        </config>
                      </ipv6>
                    </routed-vlan>
                  </interface>
                </interfaces>
              </data>
            </rpc-reply>
            """
        config1 = Config(self.d, xml1)
        config2 = Config(self.d, xml2)
        config3 = config1.filter('/nc:config/oc-if:interfaces/oc-if:interface'
                                 '[oc-if:name="GigabitEthernet1/0/10"]')
        self.assertEqual(config2, config3)

    def test_filter_2(self):
        xml1 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"
                       message-id="101">
              <data>
                <interfaces xmlns="http://openconfig.net/yang/interfaces">
                  <interface>
                    <name>GigabitEthernet0/0/1</name>
                    <config>
                      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:ethernetCsmacd</type>
                      <name>GigabitEthernet0/0/1</name>
                      <enabled>true</enabled>
                    </config>
                    <ethernet xmlns="http://openconfig.net/yang/interfaces/ethernet">
                      <config>
                        <port-speed>SPEED_10MB</port-speed>
                      </config>
                    </ethernet>
                    <routed-vlan xmlns="http://openconfig.net/yang/vlan">
                      <ipv6 xmlns="http://openconfig.net/yang/interfaces/ip">
                        <config>
                          <enabled>false</enabled>
                        </config>
                      </ipv6>
                    </routed-vlan>
                  </interface>
                  <interface>
                    <name>GigabitEthernet1/0/10</name>
                    <config>
                      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:ethernetCsmacd</type>
                      <name>GigabitEthernet1/0/10</name>
                      <enabled>true</enabled>
                    </config>
                    <routed-vlan xmlns="http://openconfig.net/yang/vlan">
                      <ipv6 xmlns="http://openconfig.net/yang/interfaces/ip">
                        <config>
                          <enabled>false</enabled>
                        </config>
                      </ipv6>
                    </routed-vlan>
                  </interface>
                </interfaces>
              </data>
            </rpc-reply>
            """
        xml2 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"
                       message-id="101">
              <data>
                <interfaces xmlns="http://openconfig.net/yang/interfaces">
                  <interface>
                    <name>GigabitEthernet1/0/10</name>
                    <config>
                      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:ethernetCsmacd</type>
                      <name>GigabitEthernet1/0/10</name>
                      <enabled>true</enabled>
                    </config>
                    <routed-vlan xmlns="http://openconfig.net/yang/vlan">
                      <ipv6 xmlns="http://openconfig.net/yang/interfaces/ip">
                        <config>
                          <enabled>false</enabled>
                        </config>
                      </ipv6>
                    </routed-vlan>
                  </interface>
                </interfaces>
              </data>
            </rpc-reply>
            """
        config1 = Config(self.d, xml1)
        config2 = Config(self.d, xml2)
        config3 = config1.filter('/nc:config/oc-if:interfaces/oc-if:interface'
                                 '[starts-with(oc-if:name/text(), '
                                 '"GigabitEthernet1")]')
        self.assertEqual(config2, config3)

    def test_add_1(self):
        config_xml1 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <tables>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                    </tables>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        config_xml2 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <tables>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                    </tables>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        delta_xml1 = """
<nc:config xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0"
           xmlns:yang="urn:ietf:params:xml:ns:yang:1">
  <network-instances xmlns="http://openconfig.net/yang/network-instance">
    <network-instance>
      <name>default</name>
      <config>
        <name>default</name>
        <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
        <description>default-vrf [read-only]</description>
      </config>
      <tables>
        <table yang:insert="first">
          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
          <config>
            <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
            <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
          </config>
        </table>
      </tables>
    </network-instance>
  </network-instances>
</nc:config>
            """
        delta_xml2 = """
<nc:config xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0"
           xmlns:yang="urn:ietf:params:xml:ns:yang:1">
  <network-instances xmlns="http://openconfig.net/yang/network-instance">
    <network-instance>
      <name>default</name>
      <config>
        <name>default</name>
        <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
        <description>default-vrf [read-only]</description>
      </config>
      <tables>
        <table nc:operation="delete">
          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
        </table>
      </tables>
    </network-instance>
  </network-instances>
</nc:config>
            """
        config1 = Config(self.d, config_xml1)
        config2 = Config(self.d, config_xml2)

        # modify schema node
        nodes = config1.xpath('.//oc-netinst:network-instance'
                              '/oc-netinst:tables/oc-netinst:table')
        node = nodes[0]
        schema_node = config1.get_schema_node(node)
        schema_node.set('ordered-by', 'user')

        delta1 = ConfigDelta(config1, delta=delta_xml1)
        config3 = config1 + delta1
        self.assertEqual(config2, config3)
        delta2 = ConfigDelta(config2, delta=delta_xml2)
        config4 = config2 + delta2
        self.assertEqual(config1, config4)

    def test_add_2(self):
        config_xml1 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <tables>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                    </tables>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        config_xml2 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <tables>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                    </tables>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        delta_xml1 = """
            <xc:config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0"
                       xmlns:yang="urn:ietf:params:xml:ns:yang:1">
              <network-instances xmlns="http://openconfig.net/yang/network-instance">
                <network-instance>
                  <name>default</name>
                  <config>
                    <name>default</name>
                    <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                    <description>default-vrf [read-only]</description>
                  </config>
                  <tables>
                    <table yang:insert="last">
                      <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
                      <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                      <config>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                      </config>
                    </table>
                  </tables>
                </network-instance>
              </network-instances>
            </xc:config>
            """
        delta_xml2 = """
            <xc:config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0"
                       xmlns:yang="urn:ietf:params:xml:ns:yang:1">
              <network-instances xmlns="http://openconfig.net/yang/network-instance">
                <network-instance>
                  <name>default</name>
                  <config>
                    <name>default</name>
                    <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                    <description>default-vrf [read-only]</description>
                  </config>
                  <tables>
                    <table xc:operation="delete">
                      <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
                      <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                    </table>
                  </tables>
                </network-instance>
              </network-instances>
            </xc:config>
            """
        config1 = Config(self.d, config_xml1)
        config2 = Config(self.d, config_xml2)

        # modify schema node
        nodes = config1.xpath('.//oc-netinst:network-instance'
                              '/oc-netinst:tables/oc-netinst:table')
        node = nodes[0]
        schema_node = config1.get_schema_node(node)
        schema_node.set('ordered-by', 'user')

        delta1 = ConfigDelta(config1, delta=delta_xml1)
        config3 = config1 + delta1
        self.assertEqual(config2, config3)
        delta2 = ConfigDelta(config2, delta=delta_xml2)
        config4 = config2 + delta2
        self.assertEqual(config1, config4)

    def test_add_3(self):
        config_xml1 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <tables>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                    </tables>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        config_xml2 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <tables>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                    </tables>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        delta_xml1 = """
            <xc:config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0"
                       xmlns:yang="urn:ietf:params:xml:ns:yang:1">
              <network-instances xmlns="http://openconfig.net/yang/network-instance">
                <network-instance>
                  <name>default</name>
                  <config>
                    <name>default</name>
                    <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                    <description>default-vrf [read-only]</description>
                  </config>
                  <tables>
                    <table xmlns:oc-pol-types="http://openconfig.net/yang/policy-types"
                           xmlns:oc-types="http://openconfig.net/yang/openconfig-types"
                           xc:operation="create"
                           yang:insert="after"
                           yang:key="[protocol='oc-pol-types:STATIC'][address-family='oc-types:IPV4']">
                      <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
                      <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                      <config>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                      </config>
                    </table>
                    <table xc:operation="replace"
                           yang:insert="after"
                           yang:key="[protocol='oc-pol-types:DIRECTLY_CONNECTED'][address-family='oc-types:IPV4']">
                      <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                      <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                      <config>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                      </config>
                    </table>
                  </tables>
                </network-instance>
              </network-instances>
            </xc:config>
            """
        delta_xml2 = """
            <xc:config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0"
                       xmlns:yang="urn:ietf:params:xml:ns:yang:1">
              <network-instances xmlns="http://openconfig.net/yang/network-instance">
                <network-instance>
                  <name>default</name>
                  <config>
                    <name>default</name>
                    <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                    <description>default-vrf [read-only]</description>
                  </config>
                  <tables>
                    <table xc:operation="delete">
                      <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
                      <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                    </table>
                  </tables>
                </network-instance>
              </network-instances>
            </xc:config>
            """
        config1 = Config(self.d, config_xml1)
        config2 = Config(self.d, config_xml2)

        # modify schema node
        nodes = config1.xpath('.//oc-netinst:network-instance'
                              '/oc-netinst:tables/oc-netinst:table')
        node = nodes[0]
        schema_node = config1.get_schema_node(node)
        schema_node.set('ordered-by', 'user')

        delta = ConfigDelta(config1, delta=delta_xml1)
        config3 = config1 + delta
        self.assertEqual(config2, config3)
        config4 = config3 - delta
        self.assertEqual(config1, config4)

    def test_add_4(self):
        config_xml1 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <tables>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                    </tables>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        config_xml2 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <tables>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        </config>
                      </table>
                      <table>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        <config>
                          <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:STATIC</protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV6</address-family>
                        </config>
                      </table>
                    </tables>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        delta_xml1 = """
            <xc:config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0"
                       xmlns:yang="urn:ietf:params:xml:ns:yang:1">
              <network-instances xmlns="http://openconfig.net/yang/network-instance">
                <network-instance>
                  <name>default</name>
                  <config>
                    <name>default</name>
                    <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                    <description>default-vrf [read-only]</description>
                  </config>
                  <tables>
                    <table xmlns:oc-pol-types="http://openconfig.net/yang/policy-types"
                           xmlns:oc-types="http://openconfig.net/yang/openconfig-types"
                           yang:insert="before"
                           yang:key="[protocol='oc-pol-types:STATIC'][address-family='oc-types:IPV4']">
                      <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
                      <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                      <config>
                        <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                      </config>
                    </table>
                  </tables>
                </network-instance>
              </network-instances>
            </xc:config>
            """
        delta_xml2 = """
            <xc:config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0"
                       xmlns:yang="urn:ietf:params:xml:ns:yang:1">
              <network-instances xmlns="http://openconfig.net/yang/network-instance">
                <network-instance>
                  <name>default</name>
                  <config>
                    <name>default</name>
                    <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                    <description>default-vrf [read-only]</description>
                  </config>
                  <tables>
                    <table xc:operation="delete">
                      <protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</protocol>
                      <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                    </table>
                  </tables>
                </network-instance>
              </network-instances>
            </xc:config>
            """
        config1 = Config(self.d, config_xml1)
        config2 = Config(self.d, config_xml2)

        # modify schema node
        nodes = config1.xpath('.//oc-netinst:network-instance'
                              '/oc-netinst:tables/oc-netinst:table')
        node = nodes[0]
        schema_node = config1.get_schema_node(node)
        schema_node.set('ordered-by', 'user')

        delta1 = ConfigDelta(config1, delta=delta_xml1)
        config3 = config1 + delta1
        self.assertEqual(config2, config3)
        delta2 = ConfigDelta(config2, delta=delta_xml2)
        config4 = config2 + delta2
        self.assertEqual(config1, config4)

    def test_add_5(self):
        config_xml1 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <table-connections>
                      <table-connection>
                        <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                        <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                          <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                          <import-policy>ROUTEMAP1</import-policy>
                          <import-policy>ROUTEMAP2</import-policy>
                          <default-import-policy>REJECT_ROUTE</default-import-policy>
                        </config>
                      </table-connection>
                    </table-connections>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        config_xml2 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <table-connections>
                      <table-connection>
                        <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                        <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                          <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                          <import-policy>ROUTEMAP0</import-policy>
                          <import-policy>ROUTEMAP1</import-policy>
                          <import-policy>ROUTEMAP2</import-policy>
                          <import-policy>ROUTEMAP3</import-policy>
                          <default-import-policy>REJECT_ROUTE</default-import-policy>
                        </config>
                      </table-connection>
                    </table-connections>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        delta_xml1 = """
            <xc:config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0"
                       xmlns:yang="urn:ietf:params:xml:ns:yang:1">
              <network-instances xmlns="http://openconfig.net/yang/network-instance">
                <network-instance>
                  <name>default</name>
                  <table-connections>
                    <table-connection>
                      <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                      <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                      <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                      <config>
                        <import-policy yang:insert="first">ROUTEMAP0</import-policy>
                        <import-policy yang:insert="last">ROUTEMAP3</import-policy>
                      </config>
                    </table-connection>
                  </table-connections>
                </network-instance>
              </network-instances>
            </xc:config>
            """
        delta_xml2 = """
            <xc:config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0"
                       xmlns:yang="urn:ietf:params:xml:ns:yang:1">
              <network-instances xmlns="http://openconfig.net/yang/network-instance">
                <network-instance>
                  <name>default</name>
                  <table-connections>
                    <table-connection>
                      <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                      <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                      <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                      <config>
                        <import-policy xc:operation="delete">ROUTEMAP0</import-policy>
                        <import-policy xc:operation="delete">ROUTEMAP3</import-policy>
                      </config>
                    </table-connection>
                  </table-connections>
                </network-instance>
              </network-instances>
            </xc:config>
            """
        config1 = Config(self.d, config_xml1)
        config2 = Config(self.d, config_xml2)

        # modify schema node
        nodes = config1.xpath('.//oc-netinst:network-instance'
                              '/oc-netinst:table-connections'
                              '/oc-netinst:table-connection'
                              '/oc-netinst:config/oc-netinst:import-policy')
        node = nodes[0]
        schema_node = config1.get_schema_node(node)
        schema_node.set('ordered-by', 'user')

        delta1 = ConfigDelta(config1, delta=delta_xml1)
        config3 = config1 + delta1
        self.assertEqual(config2, config3)
        delta2 = ConfigDelta(config2, delta=delta_xml2)
        config4 = config2 + delta2
        self.assertEqual(config1, config4)

    def test_add_6(self):
        config_xml1 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <table-connections>
                      <table-connection>
                        <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                        <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                          <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                          <import-policy>ROUTEMAP1</import-policy>
                          <import-policy>ROUTEMAP2</import-policy>
                          <default-import-policy>REJECT_ROUTE</default-import-policy>
                        </config>
                      </table-connection>
                    </table-connections>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        config_xml2 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <table-connections>
                      <table-connection>
                        <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                        <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                          <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                          <import-policy>ROUTEMAP1</import-policy>
                          <import-policy>ROUTEMAP3</import-policy>
                          <import-policy>ROUTEMAP0</import-policy>
                          <import-policy>ROUTEMAP2</import-policy>
                          <default-import-policy>REJECT_ROUTE</default-import-policy>
                        </config>
                      </table-connection>
                    </table-connections>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        delta_xml1 = """
            <xc:config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0"
                       xmlns:yang="urn:ietf:params:xml:ns:yang:1">
              <network-instances xmlns="http://openconfig.net/yang/network-instance">
                <network-instance>
                  <name>default</name>
                  <table-connections>
                    <table-connection>
                      <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                      <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                      <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                      <config>
                        <import-policy xc:operation="create"
                                       yang:insert="before"
                                       yang:value="ROUTEMAP2">ROUTEMAP0</import-policy>
                        <import-policy xc:operation="merge"
                                       yang:insert="after"
                                       yang:value="ROUTEMAP1">ROUTEMAP3</import-policy>
                      </config>
                    </table-connection>
                  </table-connections>
                </network-instance>
              </network-instances>
            </xc:config>
            """
        delta_xml2 = """
            <xc:config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0"
                       xmlns:yang="urn:ietf:params:xml:ns:yang:1">
              <network-instances xmlns="http://openconfig.net/yang/network-instance">
                <network-instance>
                  <name>default</name>
                  <table-connections>
                    <table-connection>
                      <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                      <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                      <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                      <config>
                        <import-policy xc:operation="delete">ROUTEMAP0</import-policy>
                        <import-policy xc:operation="delete">ROUTEMAP3</import-policy>
                      </config>
                    </table-connection>
                  </table-connections>
                </network-instance>
              </network-instances>
            </xc:config>
            """
        config1 = Config(self.d, config_xml1)
        config2 = Config(self.d, config_xml2)

        # modify schema node
        nodes = config1.xpath('.//oc-netinst:network-instance'
                              '/oc-netinst:table-connections'
                              '/oc-netinst:table-connection'
                              '/oc-netinst:config/oc-netinst:import-policy')
        node = nodes[0]
        schema_node = config1.get_schema_node(node)
        schema_node.set('ordered-by', 'user')

        delta = ConfigDelta(config1, delta=delta_xml1)
        config3 = config1 + delta
        self.assertEqual(config2, config3)
        config4 = config3 - delta
        self.assertEqual(config1, config4)

    def test_add_7(self):
        config_xml1 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <table-connections>
                      <table-connection>
                        <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                        <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                          <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                          <import-policy>ROUTEMAP1</import-policy>
                          <import-policy>ROUTEMAP2</import-policy>
                          <default-import-policy>REJECT_ROUTE</default-import-policy>
                        </config>
                      </table-connection>
                    </table-connections>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        config_xml2 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"
                       message-id="101">
              <data>
                <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
                  <router>
                    <bgp xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-bgp">
                      <id>10</id>
                      <bgp>
                        <router-id>10.8.55.30</router-id>
                        <log-neighbor-changes/>
                      </bgp>
                    </bgp>
                  </router>
                </native>
              </data>
            </rpc-reply>
            """
        config_xml3 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <table-connections>
                      <table-connection>
                        <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                        <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                          <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                          <import-policy>ROUTEMAP1</import-policy>
                          <import-policy>ROUTEMAP2</import-policy>
                          <default-import-policy>REJECT_ROUTE</default-import-policy>
                        </config>
                      </table-connection>
                    </table-connections>
                  </network-instance>
                </network-instances>
                <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
                  <router>
                    <bgp xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-bgp">
                      <id>10</id>
                      <bgp>
                        <router-id>10.8.55.30</router-id>
                        <log-neighbor-changes/>
                      </bgp>
                    </bgp>
                  </router>
                </native>
              </data>
            </rpc-reply>
            """
        config1 = Config(self.d, config_xml1)
        config2 = Config(self.d, config_xml2)
        config3 = Config(self.d, config_xml3)
        config4 = config1 + config2
        self.assertEqual(config4, config3)

    def test_add_8(self):
        config_xml1 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"
                       message-id="101">
              <data>
                <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
                  <router>
                    <bgp xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-bgp">
                      <id>10</id>
                      <bgp>
                        <router-id>10.8.55.30</router-id>
                      </bgp>
                    </bgp>
                  </router>
                </native>
              </data>
            </rpc-reply>
            """
        config_xml2 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"
                       message-id="101">
              <data>
                <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
                  <router>
                    <bgp xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-bgp">
                      <id>10</id>
                      <bgp>
                        <router-id>10.8.55.30</router-id>
                        <log-neighbor-changes/>
                      </bgp>
                      <address-family>
                        <no-vrf>
                          <ipv4>
                            <af-name>unicast</af-name>
                          </ipv4>
                        </no-vrf>
                      </address-family>
                    </bgp>
                  </router>
                </native>
              </data>
            </rpc-reply>
            """
        config1 = Config(self.d, config_xml1)
        config2 = Config(self.d, config_xml2)
        config3 = config1 + config2
        self.assertEqual(config2, config3)

    def test_add_9(self):
        config_xml1 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <table-connections>
                      <table-connection>
                        <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                        <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                          <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                          <import-policy>ROUTEMAP1</import-policy>
                          <import-policy>ROUTEMAP2</import-policy>
                          <default-import-policy>REJECT_ROUTE</default-import-policy>
                        </config>
                      </table-connection>
                    </table-connections>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        delta_xml = """
            <xc:config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0"
                       xmlns:yang="urn:ietf:params:xml:ns:yang:1">
              <network-instances xmlns="http://openconfig.net/yang/network-instance">
                <network-instance>
                  <name>default</name>
                  <table-connections>
                    <table-connection>
                      <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                      <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                      <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                      <config>
                        <import-policy xc:operation="create"
                                       yang:insert="before"
                                       yang:value="ROUTEMAP2">ROUTEMAP1</import-policy>
                      </config>
                    </table-connection>
                  </table-connections>
                </network-instance>
              </network-instances>
            </xc:config>
            """
        config1 = Config(self.d, config_xml1)

        # modify schema node
        nodes = config1.xpath('.//oc-netinst:network-instance'
                              '/oc-netinst:table-connections'
                              '/oc-netinst:table-connection'
                              '/oc-netinst:config/oc-netinst:import-policy')
        node = nodes[0]
        schema_node = config1.get_schema_node(node)
        schema_node.set('ordered-by', 'user')

        self.assertRaises(ConfigDeltaError,
                          ConfigDelta,
                          config1, delta=delta_xml)

    def test_add_10(self):
        config_xml1 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <table-connections>
                      <table-connection>
                        <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                        <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                          <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                          <import-policy>ROUTEMAP1</import-policy>
                          <import-policy>ROUTEMAP2</import-policy>
                          <default-import-policy>REJECT_ROUTE</default-import-policy>
                        </config>
                      </table-connection>
                    </table-connections>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        delta_xml = """
            <xc:config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0"
                       xmlns:yang="urn:ietf:params:xml:ns:yang:1">
              <network-instances xmlns="http://openconfig.net/yang/network-instance">
                <network-instance>
                  <name>default</name>
                  <table-connections>
                    <table-connection>
                      <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                      <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                      <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                      <config>
                        <import-policy yang:insert="before"
                                       yang:value="ROUTEMAP7">ROUTEMAP1</import-policy>
                      </config>
                    </table-connection>
                  </table-connections>
                </network-instance>
              </network-instances>
            </xc:config>
            """
        config1 = Config(self.d, config_xml1)

        # modify schema node
        nodes = config1.xpath('.//oc-netinst:network-instance'
                              '/oc-netinst:table-connections'
                              '/oc-netinst:table-connection'
                              '/oc-netinst:config/oc-netinst:import-policy')
        node = nodes[0]
        schema_node = config1.get_schema_node(node)
        schema_node.set('ordered-by', 'user')

        self.assertRaises(ConfigDeltaError,
                          ConfigDelta,
                          config1, delta=delta_xml)

    def test_add_11(self):
        config_xml1 = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101">
              <data>
                <network-instances xmlns="http://openconfig.net/yang/network-instance">
                  <network-instance>
                    <name>default</name>
                    <config>
                      <name>default</name>
                      <type xmlns:oc-ni-types="http://openconfig.net/yang/network-instance-types">oc-ni-types:DEFAULT_INSTANCE</type>
                      <description>default-vrf [read-only]</description>
                    </config>
                    <table-connections>
                      <table-connection>
                        <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                        <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                        <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                        <config>
                          <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                          <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                          <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                          <import-policy>ROUTEMAP1</import-policy>
                          <import-policy>ROUTEMAP2</import-policy>
                          <default-import-policy>REJECT_ROUTE</default-import-policy>
                        </config>
                      </table-connection>
                    </table-connections>
                  </network-instance>
                </network-instances>
              </data>
            </rpc-reply>
            """
        delta_xml = """
            <xc:config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0"
                       xmlns:yang="urn:ietf:params:xml:ns:yang:1">
              <network-instances xmlns="http://openconfig.net/yang/network-instance">
                <network-instance>
                  <name>default</name>
                  <table-connections>
                    <table-connection>
                      <src-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:DIRECTLY_CONNECTED</src-protocol>
                      <dst-protocol xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">oc-pol-types:BGP</dst-protocol>
                      <address-family xmlns:oc-types="http://openconfig.net/yang/openconfig-types">oc-types:IPV4</address-family>
                      <config>
                        <import-policy yang:insert="after">ROUTEMAP1</import-policy>
                      </config>
                    </table-connection>
                  </table-connections>
                </network-instance>
              </network-instances>
            </xc:config>
            """
        config1 = Config(self.d, config_xml1)

        # modify schema node
        nodes = config1.xpath('.//oc-netinst:network-instance'
                              '/oc-netinst:table-connections'
                              '/oc-netinst:table-connection'
                              '/oc-netinst:config/oc-netinst:import-policy')
        node = nodes[0]
        schema_node = config1.get_schema_node(node)
        schema_node.set('ordered-by', 'user')

        self.assertRaises(ConfigDeltaError,
                          ConfigDelta,
                          config1, delta=delta_xml)

    def test_get_schema_node_1(self):
        xml = """
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"
                       message-id="101">
              <data>
                <interfaces xmlns="http://openconfig.net/yang/interfaces">
                  <interface>
                    <name>GigabitEthernet1/0/1</name>
                    <config>
                      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:ethernetCsmacd</type>
                      <name>GigabitEthernet1/0/1</name>
                      <enabled>true</enabled>
                    </config>
                    <routed-vlan xmlns="http://openconfig.net/yang/vlan">
                      <ipv6 xmlns="http://openconfig.net/yang/interfaces/ip">
                        <config>
                          <enabled>false</enabled>
                        </config>
                      </ipv6>
                    </routed-vlan>
                  </interface>
                </interfaces>
              </data>
            </rpc-reply>
            """
        config = Config(self.d, xml)
        p = '/nc:config/oc-if:interfaces/oc-if:interface/oc-vlan:routed-vlan/oc-ip:ipv6'
        config_node = config.xpath(p)[0]
        schema_node = self.d.get_schema_node(config_node)
        assert schema_node is not None

#     def test_get_prefix_1(self):
#         prefix = self.d.get_prefix('urn:ietf:params:xml:ns:yang:iana-if-type')
#         self.assertEqual(prefix, 'ianaift')

    def test_get_config_1(self):
        expected_ns = {
            'nc': 'urn:ietf:params:xml:ns:netconf:base:1.0',
            'oc-netinst': 'http://openconfig.net/yang/network-instance',
            'oc-ni-types': 'http://openconfig.net/yang/network-instance-types',
            'oc-pol-types': 'http://openconfig.net/yang/policy-types',
            'oc-types': 'http://openconfig.net/yang/openconfig-types'}
        r = self.d.get_config(models='openconfig-network-instance')
        self.assertEqual(r.ns, expected_ns)

    def test_get_1(self):
        r = self.d.get(models='openconfig-network-instance')
        name = r.xpath('.//oc-netinst:network-instances/'
                       'oc-netinst:network-instance'
                       '[oc-netinst:name="Mgmt-intf"]'
                       '/oc-netinst:config/oc-netinst:name/text()')
        self.assertEqual(name, ['Mgmt-intf'])

