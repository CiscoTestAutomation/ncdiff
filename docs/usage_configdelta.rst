More on ConfigDelta
===================

Internally, a ConfigDelta object contains two Config objects: a source Config
instance and a destination Config instance. This allows us to calculate
equivalent diff as a Netconf edit-config, a list of Restconf Requests, or a gNMI
SetRequest. A ConfigDelta object is tightly coupled with a Config object.

create ConfigDelta objects
--------------------------

As we see in Tutorial section, a ConfigDelta object can be created by two
Config objects in a form of subtraction.

Another way, a ConfigDelta object can be instantiated from a Config object and
an edit-config.

In the following example, current device config is set to config1:

.. code-block:: text

    >>> m.load_model('openconfig-system')
    ...
    >>> reply = m.get_config(models='openconfig-system')
    INFO:ncclient.operations.rpc:Requesting 'GetConfig'
    >>> config1 = m.extract_config(reply)
    >>>

And we plan to send an edit-config as the XML string below:

.. code-block:: text

    >>> edit_config_xml = """
        <nc:config xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
          <system xmlns="http://openconfig.net/yang/system">
            <aaa>
              <server-groups>
                <server-group>
                  <name>ISE1</name>
                  <config>
                    <name>ISE1</name>
                    <type xmlns:oc-aaa="http://openconfig.net/yang/aaa">oc-aaa:RADIUS</type>
                  </config>
                </server-group>
              </server-groups>
            </aaa>
          </system>
        </nc:config>
        """
    >>> from ncdiff import ConfigDelta
    >>> delta = ConfigDelta(config1, delta=edit_config_xml)
    >>>

verify the result of a ConfigDelta object
-----------------------------------------

The result of the edit-config can be predicted as config2:

.. code-block:: text

    >>> config2 = config1 + delta
    >>>

Now send the edit-config to the device and capture the real result as config3:

.. code-block:: text

    >>> reply = m.edit_config(target='running', config=delta.nc)
    INFO:ncclient.operations.rpc:Requesting 'EditConfig'
    >>> reply.ok
    True
    >>> reply = m.get_config(models='openconfig-system')
    INFO:ncclient.operations.rpc:Requesting 'GetConfig'
    >>> config3 = m.extract_config(reply)
    >>>

Finally, ensure that config2 equals to config3 and claim the test is passed:

.. code-block:: text

    >>> config2 == config3
    True
    >>>

Additional confirmation might be achieved via CLI:

.. code-block:: text

    nyqT05#show running-config  | include aaa group server
    aaa group server radius ISE1
    nyqT05#

create ConfigDelta objects with special requirements
----------------------------------------------------

There are many different Netconf edit-config RPCs that can achieve the same
transition between two configuration states. By default, ConfigDelta.nc uses
'merge' and 'delete' operations as much as possible. But sometimes we would like to test
other Netconf operations such as 'create', 'replace' and 'remove'. The way
of doing that is creating ConfigDelta objects with arguments:

.. code-block:: text

    >>> delta = ConfigDelta(config_src=config1, config_dst=config2,
                            preferred_create='create',
                            preferred_replace='replace',
                            preferred_delete='remove')
    >>> print(delta)
    ...
    >>>

Netconf allows creating a new container, a new list instance, a new leaf or a
new leaf-list instance by operation 'create', 'replace' or 'merge', so the value
of 'preferred_create' can be any of these.

When the value of 'preferred_replace' is 'replace', a container, a list instance
or a leaf will be replaced by operation 'replace'. Using 'replace' operation to
replace an instance of leaf-list is illegal, as a result, 'replace' operation is
carried out at its parent level, which is either a container or a list instance.
If 'preferred_replace' is set to 'merge', we search deep and use either 'merge',
'delete' or 'remove' to modify end leaf or leaf-list.

Both 'delete' and 'remove' are valid options of 'preferred_delete'.


.. sectionauthor:: Jonathan Yang
