More on Config
==============

There are more usages of class Config.

create Config objects
---------------------

Config objects can be created by XML string:

.. code-block:: text

    >>> xml = """
        <nc:config xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
          <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
            <service>
              <timestamps>
                <debug>
                  <datetime>
                    <localtime>
                      <show-timezone>
                        <msec/>
                      </show-timezone>
                    </localtime>
                  </datetime>
                </debug>
              </timestamps>
            </service>
          </native>
        </nc:config>
        """
    >>> from ncdiff import Config
    >>> config = Config(device.nc, xml)
    >>> print(config)
    <nc:config xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
      <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
        <service>
          <timestamps>
            <debug>
              <datetime>
                <localtime>
                  <show-timezone>
                    <msec/>
                  </show-timezone>
                </localtime>
              </datetime>
            </debug>
          </timestamps>
        </service>
      </native>
    </nc:config>

    >>>

Config objects can store operational data as well:

.. code-block:: text

    >>> m.timeout = 120
    >>> m.load_model('openconfig-interfaces')
    ...
    >>> reply = m.get(models='openconfig-interfaces')
    INFO:ncclient.operations.rpc:Requesting 'Get'
    >>> state = Config(device.nc, reply)
    >>> print(state)
    <nc:config xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
      <interfaces xmlns="http://openconfig.net/yang/interfaces">
        <interface>
          <name>FortyGigabitEthernet1/1/1</name>
          <config>
            <name>FortyGigabitEthernet1/1/1</name>
            <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:ethernetCsmacd</type>
            <enabled>true</enabled>
          </config>
          <state>
          ...
          </state>
          ...
        </interface>
        ...
      </interfaces>
    </nc:config>

    >>>

xpath
-----

Instances of Config support XPATH. Say port speed config of GigabitEthernet1/0/1
is needed:

.. code-block:: text

    >>> ret = config.xpath('/nc:config/oc-if:interfaces/oc-if:interface'
                           '[oc-if:name="GigabitEthernet0/0"]/oc-eth:ethernet'
                           '/oc-eth:config/oc-eth:port-speed/text()')
    >>> assert(ret[0] == 'SPEED_1GB')
    >>>

Or the number of interfaces whose names start with "GigabitEthernet1/0/":

.. code-block:: text

    >>> ret = config.xpath('count(/nc:config/oc-if:interfaces/oc-if:interface'
                           '[starts-with(oc-if:name/text(), "GigabitEthernet1/0/")])')
    >>> assert(ret == 2.0)
    >>>

.. note::

    In order to facilitate xpath() and filter(), users may call ns_help() to
    view the mapping between prefixes and URLs.

filter
------

Class Config allows you to get a partial config. Traditional way is defining a
filter and calling get_config():

.. code-block:: text

    >>> from lxml import etree
    >>> f = etree.Element('{urn:ietf:params:xml:ns:netconf:base:1.0}filter',
                          type='xpath',
                          nsmap={'ios':
                                 'http://cisco.com/ns/yang/Cisco-IOS-XE-native'},
                          select=".//ios:native/ios:ntp")
    >>> reply = m.get_config(filter=f)
    >>> c1 = m.extract_config(reply)
    >>>

A better way is calling method filter() of Config instances:

.. code-block:: text

    >>> reply = m.get_config(models='Cisco-IOS-XE-native')
    >>> config = m.extract_config(reply)
    >>> c2 = config.filter('.//ios:native/ios:ntp')
    >>> print(c2)
    ...
    >>>

And `c1` equals to `c2`:

.. code-block:: text

    >>> c1 == c2
    True
    >>>

compare configs
---------------

The definition of 'less than or equal to' is: all nodes in one config exist in
the other config.

For instance, a native model config of all features is greater than a native
model config of loopback interfaces.

.. code-block:: text

    >>> reply = m.get_config(models='Cisco-IOS-XE-native')
    INFO:ncclient.operations.rpc:Requesting 'GetConfig'
    >>> c1 = m.extract_config(reply)
    >>> c2 = c1.filter('.//ios:native/ios:interface/ios:Loopback')
    >>> c1 > c2
    True
    >>>

.. sectionauthor:: Jonathan Yang
