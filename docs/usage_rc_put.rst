Restconf Requests of DELETE, PUT and PATCH
==========================================

ConfigDelta objects have an attribute 'rc', which is a list of Restconf
Requests. In most cases, they should achieve the same transaction as a Netconf
edit-config does.

connect to Restconf
-------------------

Prepare Restconf session:

.. code-block:: text

    >>> import requests
    >>> rc = requests.Session()
    >>> rc.auth = ('admin', 'admin')
    >>> e = requests.packages.urllib3.exceptions.InsecureRequestWarning
    >>> requests.packages.urllib3.disable_warnings(e)
    >>>

peek at Requests
----------------

This step is not necessary, but it might help understanding:

.. code-block:: text

    >>> print(delta.rc)
    [<Request [PATCH]>]
    >>> print(delta.rc[0])
    PATCH https://2.3.4.5:443/restconf/data/openconfig-system%3Asystem/aaa/server-groups
    Content-Type: application/yang-data+json

    {
      "openconfig-system:server-groups": {
        "server-group": {
          "name": "ISE1",
          "config": {
            "name": "ISE1",
            "type": "oc-aaa:RADIUS"
          }
        }
      }
    }
    >>>

send Requests
-------------

It is a loop to send out Requests in sequence:

.. code-block:: text

    >>> rc = requests.Session()
    >>> rc.auth = ('admin', 'admin')
    >>> for request in delta.rc:
            prepped = rc.prepare_request(request)
            reply = rc.send(prepped, verify=False)
            assert(reply.ok)
    >>>


.. sectionauthor:: Jonathan Yang <yuekyang@cisco.com>
