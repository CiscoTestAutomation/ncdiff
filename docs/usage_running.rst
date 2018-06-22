RunningConfigDiff
=================

ncdiff module has a class to compute Cisco running-config diff.

create RunningConfigDiff objects
--------------------------------

Given two running-configs, an instance of RunningConfigDiff can be created:

.. code-block:: text

    >>> running1 = """
        Current configuration : 8732 bytes
        !
        ! Last configuration change at 10:21:24 UTC Wed Apr 18 2018 by NETCONF
        !
        version 16.9
        no service pad
        service timestamps debug datetime msec
        service timestamps log datetime msec
        no platform punt-keepalive disable-kernel-core
        platform shell
        !
        interface GigabitEthernet0/0
         vrf forwarding Mgmt-vrf
         ip address 5.34.27.59 255.255.0.0
         no negotiation auto
        !
        """
    >>> running2 = """
        Current configuration : 8732 bytes
        !
        ! Last configuration change at 10:21:24 UTC Wed Apr 18 2018 by NETCONF
        !
        version 16.9
        no service pad
        service timestamps debug datetime msec
        no platform punt-keepalive disable-kernel-core
        platform shell
        !
        interface GigabitEthernet0/0
         vrf forwarding Mgmt-vrf
         ip address 5.34.27.59 255.255.0.0
         speed 1000
         negotiation auto
        !
        """
    >>> from ncdiff import RunningConfigDiff
    >>> d = RunningConfigDiff(running1, running2)
    >>>

Simply print out the instance of RunningConfigDiff:

.. code-block:: text

    >>> print(d)
    -   service timestamps log datetime msec
    -   interface GigabitEthernet0/0
    -    no negotiation auto
    +   interface GigabitEthernet0/0
    +    speed 1000
    +    negotiation auto
    >>>


.. sectionauthor:: Jonathan Yang <yuekyang@cisco.com>
