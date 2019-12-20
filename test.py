import datetime
import time

from ncdiff import manager, ModelDevice, Model
from ncdiff import ConfigDelta

import os
from lxml import etree

def dump(name, content):
    with open(name, "w") as fh:
        fh.write(str(content))

def load(name):
    with open(name, "r") as fh:
        return fh.read()


start = datetime.datetime.now().timestamp()

m = manager.connect(
    host='192.168.2.102',
    port=830,
    username='admin',
    password='admin',
    hostkey_verify=False, look_for_keys=False, allow_agent=False)


m.scan_models()
#
# reply = m.get_config()

m.load_model('oneos-glob')
m.load_model('ietf-netconf-server')

print("load time", datetime.datetime.now().timestamp()-start)

config1 = m.extract_config(load("config1"))



configdelta_xml = """
<data xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
    <system xmlns="http://oneaccess-net.com/oneos/glob">
    <ip>
      <route xmlns="http://oneaccess-net.com/oneos/routing/route">
        <ip-route-list xmlns="http://oneaccess-net.com/oneos/routing/static" nc:operation="delete">
              <prefix>0.0.0.0</prefix>
              <mask>0.0.0.0</mask>
              <gateway>10.1.2.1</gateway>
        </ip-route-list>
      </route>
    </ip>
      <interface>
        <gigabitethernet xmlns="http://oneaccess-net.com/oneos/infrastructure/interface">
            <name>0/1</name>
            <description>To Traffic Generator -Priority</description>
            <ip xmlns="http://oneaccess-net.com/oneos/intfipglob">
                <address xmlns="http://oneaccess-net.com/oneos/infrastructure/ipmgmt">
                    <primary>
                        <address>192.168.2.1</address>
                        <mask>255.255.255.0</mask>
                    </primary>
                </address>
            </ip>
        </gigabitethernet>
      </interface>
    </system>
</data>
"""



delta = ConfigDelta(config1, delta=configdelta_xml)
# print(20*"--")
# print(config1)
# print(20*"--")
c2 = config1 + delta
dump("config2", c2)
#
# print(20*"--")
#
#
dump("c1-c2",config1-c2)
dump("c2-c1",c2-config1)

print(20*"--")
print(-delta)