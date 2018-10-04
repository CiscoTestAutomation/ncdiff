API Reference
=============

ncdiff module
-------------

ncdiff module defines a set of classes that calculate diff of two configs,
and predict config when a diff is applied on a config. A config is the payload
of a Netconf get-config reply, and a diff is the payload of a edit-config
message.

classes
-------

ModelDevice is to abstract a device supporting Netconf and YANG models. Config
represents a config. ConfigDelta is the diff between two configs.

.. toctree::

   api_device
   api_config
   api_configdelta

other classes
-------------

Model represents a compiled YANG module. ModelDiff can be used to compare two
versions of the same model, while RunningConfigDiff is useful when comparing two
Cisco running-configs.

.. toctree::

   api_model
   api_modeldiff
   api_runningdiff
   api_modeldownloader
   api_modelcompiler

other sub-modules
-----------------

Other sub-modules are for internal consumption:

.. toctree::

   api_composer
   api_calculator
   api_netconf
