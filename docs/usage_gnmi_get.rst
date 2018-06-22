gNMI GetRequest
===============

GetRequest allows gNMI client collect data from the device.

build GetRequest
----------------

A few steps to build a GetRequest:

.. code-block:: text

    >>> from yang.ncdiff import gnmi_pb2
    >>> ENCODING = {
            'JSON':0,
            'BYTES':1,
            'PROTO':2,
            'ASCII':3,
            'JSON_IETF':4}
    >>> GETREQUEST_DATATYPE = {
            'ALL':0,
            'CONFIG':1,
            'STATE':2,
            'OPERATIONAL':3}
    >>> my_path = [gnmi_pb2.Path(elem=[gnmi_pb2.PathElem(name='oc-sys:system')],
                                 origin=None)]
    >>> request = gnmi_pb2.GetRequest(prefix=None,
                                      path=my_path,
                                      type=GETREQUEST_DATATYPE['ALL'],
                                      encoding=ENCODING['JSON'])
    >>> print(request)
    path {
      elem {
        name: "oc-sys:system"
      }
    }

    >>>

send GetRequest
---------------

Send the GetRequest:

.. code-block:: text

    >>> reply = gnmi.get(request)
    >>> print(reply)
    notification {
      timestamp: 1523531026669412241
      update {
        path {
          elem {
            name: "oc-sys:system"
          }
        }
        val {
          json_val: "{\n\t\"openconfig-system:config\":\t\"nyqT05\", ...}"
        }
      }
    }

    >>>

create an instance of Config
----------------------------

An object of Config can be instantiated. From the output, you may see the JSON
content in gNMI reply is converted to XML:

.. code-block:: text

    >>> from ncdiff import Config
    >>> config = Config(device.nc, reply)
    >>> print(config)
    ...
    >>>


.. sectionauthor:: Jonathan Yang <yuekyang@cisco.com>
