.. _ofswitch_node_schema:

OFSwitch Node Representation
============================

Extends  :ref:`Node <node_schema>`

JSON Schema
-----------
See `<http://unis.crest.iu.edu/schema/ext/ofswitch/1/ofswitch>`_.

Attributes
~~~~~~~~~~
The following table contains only the OpenFlow Switch Node required attributes and exludes
those inherited from :ref:`Node <node_schema>`.

.. tabularcolumns:: |l|l|J|

+---------------+-----------+--------------------------------------------------+
| Name          | Value     | Description                                      |
+===============+===========+==================================================+
| mgmtaddress   | string    | Management IP Address of the OpenFlow switch     |
+---------------+-----------+--------------------------------------------------+
| datapathid    | string    | datapathid of the switch                         |
+---------------+-----------+--------------------------------------------------+
| mfrdesc       | string    | mfr_desc of the switch                           |
+---------------+-----------+--------------------------------------------------+
| hwdesc        | string    | hw_desc of the switch                            |
+---------------+-----------+--------------------------------------------------+
| swdesc        | string    | sw_desc of the switch                            |
+---------------+-----------+--------------------------------------------------+

Example::
~~~~~~~~~~

The following is a OF Switch Node resource example::

    {
      "status": "UNKNOWN",
      "$schema": "http://unis.crest.iu.edu/schema/ext/ofswitch/1/ofswitch#",
      "mfrdesc": "Dell",
      "name": "switch:365545302524608",
      "mgmtaddress": "156.56.64.39",
      "rules": [],
      "lifetimes": [],
      "urn": "",
      "description": "Dell,OpenFlow switch HW ver. 1.0,OpenFlow v1.3 SW Rel 9.11(0.0P2)",
      "selfRef": "http://dev.crest.iu.edu:8888/nodes/d15fab88-0a6d-4f01-a717-5611af7d4e20",
      "relations": {},
      "ports": [
        {
          "href": "http://dev.crest.iu.edu:8888/ports/87000b6e-5ed9-4acd-98c5-d2a7284d0d4e",
          "rel": "full"
        },
        {
          "href": "http://dev.crest.iu.edu:8888/ports/df7ec27b-48fe-422c-a8e4-6693b2f431ec",
          "rel": "full"
        }
      ],
      "ts": 1492621637361163,
      "location": {},
      "id": "d15fab88-0a6d-4f01-a717-5611af7d4e20",
      "datapathid": "365545302524608",
      "properties": {},
      "hwdesc": "OpenFlow switch HW ver. 1.0",
      "swdesc": "OpenFlow v1.3 SW Rel 9.11(0.0P2)"
    }