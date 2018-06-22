Restconf Request of GET
=======================

Following the previous section, we assume the Restconf session is ready as 'rc'.

build Request of GET
--------------------

Write a URL and prepare the request:

.. code-block:: text

    >>> import requests
    >>> get_header_json = {'Accept-Encoding': 'gzip, deflate',
                           'Accept': 'application/yang-data+json, ' \
                                     'application/yang-data.errors+json'}
    >>> url = 'https://2.3.4.5:443/restconf/data/openconfig-interfaces:interfaces'
    >>> request = requests.Request('GET', url, headers=get_header_json)
    >>> prepped = rc.prepare_request(request)
    >>>

send Request of GET
-------------------

Get reply of Restconf Request of GET:

.. code-block:: text

    >>> reply = rc.send(prepped, verify=False, timeout=120)
    >>>

create an instance of Config
----------------------------

An object of Config can be instantiated. From the output, you may see the JSON
content in gNMI reply is converted to XML:

.. code-block:: text

    >>> from ncdiff import Config
    >>> state_rc = Config(device.nc, reply)
    >>>

compare states
--------------

Remember that the operational data can be retrieved from Netconf as well:

.. code-block:: text

    >>> reply = device.nc.get(models='openconfig-interfaces')
    INFO:ncclient.operations.rpc:Requesting 'Get'
    >>> state_nc = Config(device.nc, reply)
    >>>

Surprisingly, 'state_rc' and 'state_nc' are different:

.. code-block:: text

    >>> state_rc == state_nc
    False
    >>>

If you print them out, you will find that some interface statistics of
interfaces are different due to different fetch time, which makes sense.


.. sectionauthor:: Jonathan Yang <yuekyang@cisco.com>
