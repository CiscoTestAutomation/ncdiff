.. _ncdiff:


Introduction
============

Configuration is a major goal of NetConf. RFC 6241 claims "NETCONF defined in
this document provides mechanisms to install, manipulate, and delete the
configuration of network devices."

Each YANG model tries to abstract one aspect of configuration by a hierarchical
schema. There might be a model to describe OSPF configuration, and another
model to describe BGP configuration, etc.

For one model, there are many different possible configurations. Each
configuration might be considered as a state, and it can be obtained by a
get-config request. Between two states, there are two directional transitions:
from state A to state B, and from state B to state A. Each transition
corresponds to an edit-config RPC.

Primarily, there are three classes defined in this module: ModelDevice, Config
and ConfigDelta.

* A modeled device supporting multiple models - ModelDevice
* A config state of multiple models - Config
* A config delta between two configs - ConfigDelta

Quick examples can be found in section Tutorial.

Features
--------

* Connect to a Netconf device by an instance of ModelDevice
* Download, compile and print model schemas
* Get config states
* Calculate diff of two instances of Config, so edit-config can be sent to the
  device to toggle between config state A and B
* Given a config state and an edit-config, calculate the new config state
* Support XPATH on Config and RPCReply
* Instantiate Config objects by Netconf rpc-reply
* Present ConfigDelta objects in the form of Netconf (a config content of
  edit-config).

Config Operations
-----------------

Summary of config operations:

=============   =========   =============   =========   =============   ==============================
operand         operator    operand         equality    result          note
=============   =========   =============   =========   =============   ==============================
Config          \+          Config          =           Config          Combine two config
Config          \+          ConfigDelta     =           Config          Apply edit-config to a config
ConfigDelta     \+          ConfigDelta     =           N/A             Not implemented
ConfigDelta     \+          Config          =           Config          Apply edit-config to a config
Config          \-          Config          =           ConfigDelta     Generate an edit-config
Config          \-          ConfigDelta     =           Config          Apply an opposite edit-config
ConfigDelta     \-          ConfigDelta     =           N/A             Not implemented
ConfigDelta     \-          Config          =           N/A             Not implemented
=============   =========   =============   =========   =============   ==============================


Support Mailers
===============
Users are encouraged to contribute to ncdiff module as expertise of data model
testing grows in Cisco. Any questions or requests may be sent to
yang-python@cisco.com.


Usage Examples
==============

.. toctree::

   usage_tutorial
   usage_config
   usage_configdelta
   usage_model
   usage_running
   usage_rpcreply


Installation
============

ncdiff module requires a few packages. Some of them are required implicitly:

* `lxml <http://lxml.de/index.html>`_ (required by ncclient)
* `paramiko <https://pypi.org/project/paramiko/>`_ (required by ncclient)

Others are required directly:

* `ncclient <http://ncclient.readthedocs.io/en/latest/>`_
* `pyang <https://pypi.org/project/pyang/>`_

Installation of these packages are normally smooth. Based on our support
experience, most issues are related to lxml and paramiko.

lxml Installation
-----------------

lxml package is available on Internet so your server may need proxy setup to
access external sites.

.. code-block:: text

    pip install lxml

.. note::

    Depending on your system of 32-bit or 64-bit python, some other packages
    need to be installed first. Please refer to some instructions in
    `YDK Installation <https://wiki.cisco.com/display/PYATS/YDK#YDK-Installation>`_
    as YDK has very similar dependencies. Another useful resource is
    `PieStack <http://piestack.cisco.com/>`_

Verify whether lxml installation is successful (you are on the good path if you
do not see any error):

.. code-block:: text

    bash$ python
    Python 3.4.1 (default, Jul 20 2016, 07:21:38)
    [GCC 4.4.7 20120313 (Red Hat 4.4.7-16)] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    >>> from lxml import etree
    >>>

paramiko Installation
---------------------

When you have a relatively new version of CEL on your server, paramiko
installation could be straight forward.

.. code-block:: text

    pip install paramiko

If there are errors during installation, try paramiko version 1.15.3:

.. code-block:: text

    pip install paramiko==1.15.3

ncdiff Installation
-------------------

This package can be installed from Cisco pypi server.

First-time installation steps:

.. code-block:: text

    pip install ncdiff


Steps to upgrade to latest:

.. code-block:: text

    pip install --upgrade ncdiff


.. sectionauthor:: Jonathan Yang <yuekyang@cisco.com>
