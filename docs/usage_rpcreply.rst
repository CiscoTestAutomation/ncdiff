RPCReply
========

RPCReply is originally a class in ncclient package, but it is enhanced by
ncdiff to support XPATH.

xpath
-----

RPCReply supports method xpath() but not filter().

.. code-block:: text

    >>> reply = m.get(models='openconfig-network-instance')

    >>> ret = reply.xpath('/nc:rpc-reply/nc:data/oc-netinst:network-instances'
                          '/oc-netinst:network-instance/oc-netinst:interfaces'
                          '/oc-netinst:interface/oc-netinst:id/text()')
    >>> assert(set(ret) == {'GigabitEthernet0/0'})
    >>>

.. note::

    In order to facilitate xpath(), users may call ns_help() to view the
    mapping between prefixes and URLs.

In some cases, especially when rpc-error is received, there might be some
namespaces that are not claimed in model schema. ns_help() still lists them and
make up some prefixes for you.

.. code-block:: text

    >>> reply = m.edit_config(delta, target='running')
    >>> reply.ok
    False
    >>> reply.ns_help()
    >>>

.. sectionauthor:: Jonathan Yang
