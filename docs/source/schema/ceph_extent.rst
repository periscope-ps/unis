.. _ceph_extent_schema:

Ceph Extent Representation
=======================

Extends  :ref:`Extent <extent_schema>`


JSON Schema
-----------
See `<http://unis.crest.iu.edu/schema/exnode/ext/1/ceph>`_.

Attributes
~~~~~~~~~~
The following table contains only the Ceph required attributes and exludes
those inherited from :ref:`Extent <extent_schema>`.

.. tabularcolumns:: |l|l|J|

+---------------+-----------+--------------------------------------------------+
| Name          | Value     | Description                                      |
+===============+===========+==================================================+
| pool          | string    | The Ceph pool in which the object is stored.     |
+---------------+-----------+--------------------------------------------------+
  

Example::
~~~~~~~~~~

The following is a Ceph Extent resource example::
  
 {
   "index": 0,
   "selfRef": "http://dev.crest.iu.edu:8888/extents/b1f64a03-2c96-4787-bff7-8abfb73dd146",
   "parent": {
   "href": "http://dev.crest.iu.edu:8888/exnodes/752df622-8401-4725-aa20-a09676365c37",
   "rel": "full"
 },
   "$schema": "http://unis.crest.iu.edu/schema/exnode/ext/1/ceph#",
   "pool": "dlt",
   "ts": 1493065036129230,
   "location": "ceph://149.165.232.115/dlt/bc2e62a1-0347-4dea-bb06-f2aee348ebc0",
   "offset": 377487360,
   "id": "b1f64a03-2c96-4787-bff7-8abfb73dd146",
   "xattrs": [],
   "size": 20971520
 }
