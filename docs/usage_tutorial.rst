Tutorial
========

Here are some basic usage examples of yang.ncdiff. They are organized in the
sequence of a typical use case - connect device, load models, get or get-config,
and edit-config.

connect to a Netconf device
---------------------------

Similar to ncclient, prepare Netconf connection and create an instance of
ModelDevice:

.. code-block:: text

    >>> from ncdiff import manager
    >>> m = manager.connect(host='2.3.4.5', port=830,
                            username='admin', password='admin',
                            hostkey_verify=False, look_for_keys=False)
    >>> m
    <ncdiff.manager.ModelDevice object at 0xf516316c>
    >>> m.raise_mode = 0
    >>>

.. note::

    raise_mode is an attribute of
    `ncclient Manager
    <http://ncclient.readthedocs.io/en/latest/manager.html#manager>`_
    that defines
    `exception raising mode
    <http://ncclient.readthedocs.io/en/latest/manager.html#ncclient.manager.Manager.raise_mode>`_.
    When raise_mode = 0,
    `RPCError
    <http://ncclient.readthedocs.io/en/latest/operations.html#ncclient.operations.RPCError>`_
    exceptions are not raised if there is an rpc-error in replies.

Set timeout if needed:

.. code-block:: text

    >>> m.timeout = 120
    >>> m.timeout
    120
    >>>

Download and scan models:

.. code-block:: text

    >>> m.scan_models()
    ...
    >>>

.. note::

    By default, a folder ./yang will be created to accommodate YANG files
    downloaded.


load models
-----------

Find what models are available:

.. code-block:: text

    >>> m.models_loadable
    ['BGP4-MIB', 'BRIDGE-MIB', ...]
    >>>

Load multiple models depending on your testing requirement:

.. code-block:: text

    >>> m1 = m.load_model('Cisco-IOS-XE-native')
    >>> m2 = m.load_model('openconfig-interfaces')
    >>> m3 = m.load_model('openconfig-network-instance')
    >>>

Print out model tree:

.. code-block:: text

    >>> print(m1)
    module: Cisco-IOS-XE-native
        +--rw native
           +--rw default
           |  +--rw crypto
           |     +--rw ikev2
           |        +--rw proposal?   empty
           |        +--rw policy?     empty
    ...
    >>>


If you forget what models are loaded, check attribute 'models_loaded':

.. code-block:: text

    >>> m.models_loaded
    ['Cisco-IOS-XE-native', 'cisco-ia', 'openconfig-interfaces', 'openconfig-network-instance']
    >>>

get
---

Since ModelDevice is a sub-class of
`ncclient Manager <http://ncclient.readthedocs.io/en/latest/manager.html#manager>`_,
it supports get, get-config, edit-config, and all other methods supported by
ncclient. On top of that, yang.ncdiff adds a new argument 'models' to method
get() and get_config():

.. code-block:: text

    >>> reply = m.get(models='openconfig-network-instance')
    >>> assert(reply.ok)
    >>> print(reply)
    ...
    >>>

You can even pull operational data or config from multiple models. For example:

.. code-block:: text

    >>> reply = m.get(models=['openconfig-interfaces',
                              'openconfig-network-instance'])
    >>> assert(reply.ok)
    >>> print(reply)
    ...
    >>>

get-config
----------

Config state can be captured by ModelDevice method extract_config():

.. code-block:: text

    >>> reply = m.get_config(models=['openconfig-interfaces',
                                     'openconfig-network-instance'])
    >>> assert(reply.ok)
    >>> config1 = m.extract_config(reply)
    >>> print(config1)
    <nc:config xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
      <interfaces xmlns="http://openconfig.net/yang/interfaces">
    ...
    >>>

edit-config
-----------

Assume there are two instances of Config: config1 and config2. Make sure they
are different:

.. code-block:: text

    >>> config1 == config2
    False
    >>> delta = config2 - config1
    >>> print(delta)
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
    >>>

If the current config state is config2, a Netconf transaction to config1 can be
achieved by an edit-config '-delta':

.. code-block:: text

    >>> reply = m.edit_config(target='running', config=(-delta).nc)
    INFO:ncclient.operations.rpc:Requesting 'EditConfig'
    >>> assert(reply.ok)
    >>>

Hey, check your device, its config should be config1 now!

.. code-block:: text

    >>> reply = m.get_config(models='openconfig-system')
    INFO:ncclient.operations.rpc:Requesting 'GetConfig'
    >>> config = m.extract_config(reply)
    >>> config == config1
    True
    >>>

Want to switch back to config2? No problem! Send 'delta':

.. code-block:: text

    >>> reply = m.edit_config(target='running', config=delta.nc)
    INFO:ncclient.operations.rpc:Requesting 'EditConfig'
    >>> assert(reply.ok)
    >>>
    >>> reply = m.get_config(models='openconfig-system')
    INFO:ncclient.operations.rpc:Requesting 'GetConfig'
    >>> config = m.extract_config(reply)
    >>> config == config2
    True
    >>>


.. sectionauthor:: Jonathan Yang <yuekyang@cisco.com>
