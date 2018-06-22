gNMI SetRequest
===============

ConfigDelta objects have an attribute 'gnmi', which is a gNMI SetRequest.
It can achieve the same transaction as a Netconf edit-config does.

gNMI specification can be found `here
<https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md>`_.


connect to gNMI
---------------

Build a basic gNMI connection class:

.. code-block:: text

    import time
    import grpc
    from ncdiff import gnmi_pb2
    from ncdiff import gnmi_pb2_grpc

    import logging
    logger = logging.getLogger(__name__)


    class gNMI(object):

        def __init__(self, ip=None, port=50052, timeout=30):
            self.ip = ip
            self.port = port
            self.timeout = timeout
            self.channel = None
            self.stub = None

        def connect(self):
            self.channel = grpc.insecure_channel('{}:{}'.format(self.ip,
                                                                self.port))
            channel_ready_future = grpc.channel_ready_future(self.channel)
            channel_ready_future.result(timeout=self.timeout)
            self.stub = gnmi_pb2_grpc.gNMIStub(self.channel)

        def disconnect(self, timeout=1):
            self.channel.__del__()
            deadline = time.time() + timeout
            while time.time() < deadline:
                if not self.connected:
                    return
                else:
                    time.sleep(0.001)
            raise Exception('disconnect() cannot be completed in {} sec' \
                            .format(timeout))

        @property
        def connected(self):
            return self.channel._connectivity_state.connectivity == \
                   grpc.ChannelConnectivity.READY

        @property
        def capabilities(self):
            return self.stub.Capabilities(gnmi_pb2.CapabilityRequest())

        def set(self, set_request):
            return self.stub.Set(set_request)

        def get(self, get_request):
            return self.stub.Get(get_request)

        def subscribe(self, subscribe_request):
            return self.stub.Subscribe(subscribe_request)

Connect to gNMI:

.. code-block:: text

    >>> gnmi = gNMI(ip='2.3.4.5', port=50052, timeout=10)
    >>> gnmi.connect()
    >>>

peek at SetRequest
------------------

Take a look at the gNMI SetRequest if there is an instance of ConfigDelta:

.. code-block:: text

    >>> print(delta.gnmi)
    update {
      path {
        elem {
          name: "oc-sys:system"
        }
        elem {
          name: "aaa"
        }
        elem {
          name: "server-groups"
        }
      }
      val {
        json_val: "{\"openconfig-system:server-group\": {\"name\": \"ISE1\", \"config\": {\"name\": \"ISE1\", \"type\": \"openconfig-aaa:RADIUS\"}}}"
      }
    }
    >>>

send SetRequest
---------------

All you have to do is sending the gNMI SetRequest:

.. code-block:: text

    >>> reply = gnmi.set(delta.gnmi)
    >>> print(reply)
    response {
      path {
        elem {
          name: "oc-sys:system"
        }
        elem {
          name: "aaa"
        }
        elem {
          name: "server-groups"
        }
      }
      op: UPDATE
    }
    timestamp: 1523462310023046066
    >>>

Check the device config by CLI, Netconf, Restconf or gNMI. It should be
changed!


.. sectionauthor:: Jonathan Yang <yuekyang@cisco.com>
