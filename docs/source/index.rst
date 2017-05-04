.. UNIS documentation

.. image:: _static/CREST.png
      :align: center

.. _BLiPP: http://github.com/periscope-ps/blipp
	      
Welcome to the UNIS documentation!
=====================================

The recent advancement in Software Defined Networks (SDNs) has increased the
need for a centric view of the network that reflects the actual topology of the
network and provide different real-time and historical data about network
resources.  A number of data models for networks have been proposed, e.g., NMWG,
NDL, and the developing NML. However, all these models focused in how to model a
network and left many open questions that make these models less optimal for use
in an SDN world. One of the biggest limitations of these models that they don't
define a well defined API, at best API guidelines are defined to interact with
these models.

Currently networks are viewed from different perspectives; design, configuration
and management, monitoring, and analysis. Each view of the network is using one
or more models to represent the network. For example, NETCONF uses YANG for
network configuration and management while perfSONAR uses NMWG for network
monitoring. Generally, network models are designed and optimized with unique
properties and level of abstraction to serve a certain view of the
network. However, using different inconsistent models for each views often leads
to inconsistent views of the same network.

The Unified Network Information Service (UNIS), with its eponymous schema, is an
effort to develop a unifying network data model along with a well-defined
RESTful API.  UNIS falls within the Periscope framework, which includes a
measurement store (MS) and the BLiPP_ measurement agent.

Contents:

.. toctree::
   :maxdepth: 2
   
   schema/unis_model
   rest/index

Indices and tables
==================
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

