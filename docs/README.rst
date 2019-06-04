[![published](https://static.production.devnetcloud.com/codeexchange/assets/images/devnet-published.svg)](https://developer.cisco.com/codeexchange/github/repo/CiscoTestAutomation/ncdiff)


.. _ncdiff:


Package ncdiff is a simplified version of yang.ncdiff. Both were initially
developed internally in Cisco and is now available to the general public through
open-source. yang.ncdiff is integrated into the modular architecture of pyATS
framework, while ncdiff is more lightweight and standalone.

Docs: `https://ncdiff.readthedocs.io/en/latest/ <https://ncdiff.readthedocs.io/en/latest/>`_

GitHub: `https://github.com/CiscoTestAutomation/ncdiff/ <https://github.com/CiscoTestAutomation/ncdiff/>`_


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

Quick examples can be found in section `Tutorial <https://ncdiff.readthedocs.io/en/latest/usage_tutorial.html>`_.

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
experience, most issues are related to lxml and paramiko installation.

ncdiff Installation
-------------------

This package can be installed from pypi server.

First-time installation steps:

.. code-block:: text

    pip install ncdiff


Steps to upgrade to latest:

.. code-block:: text

    pip install --upgrade ncdiff
