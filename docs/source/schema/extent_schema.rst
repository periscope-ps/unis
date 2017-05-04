.. _extent_schema:

Extent Representation
=======================

Extends  None

An Extent represents a part of a file with an offset and size, or potentially
the contents of a complete file, as referenced by an :ref:`Exnode
<exnode_schema>`.

JSON Schema
-----------
See `<http://unis.crest.iu.edu/schema/exnode/6/extent>`_.

Attributes
~~~~~~~~~~
The following table contains only the Extent required attributes.

.. tabularcolumns:: |l|l|J|

+---------------+-----------+--------------------------------------------------+
| Name          | Value     | Description                                      |
+===============+===========+==================================================+
| id            | string    | The Extent identifier.                           |
+---------------+-----------+--------------------------------------------------+
| selfRef       | string    | Self hyperlink reference for the Extent.         |
+---------------+-----------+--------------------------------------------------+
| location      | string    | The URI of a service maintaining the Extent data |
+---------------+-----------+--------------------------------------------------+
| size          | integer   | Size of the data in bytes.                       |
+---------------+-----------+--------------------------------------------------+
| offset        | integer   | Offset of this Extent in bytes relative to the   |
|               |           | complete file.                                   |
+---------------+-----------+--------------------------------------------------+
| parent        | string    | Pointer to the parent Exnode, null if adrift.    |
+---------------+-----------+--------------------------------------------------+
| index         | integer   | Relative index of an Extent                      |
+---------------+-----------+--------------------------------------------------+


Example::
~~~~~~~~~~

The following is an Extent resource example::

 {
   "index": 0,
   "selfRef": "http://dev.crest.iu.edu:8888/extents/0d3636f2-b899-467c-9e82-f71948f35ca9",
   "parent": {
   "href": "http://dev.crest.iu.edu:8888/exnodes/183f1037-7a92-4390-85c2-67834dda413c",
   "rel": "full"
 },
   "$schema": "http://unis.crest.iu.edu/schema/exnode/6/extent#",
   "ts": 1493065035129230,
   "location": "ftp:///10.10.1.1:8080/0d3636f2-b899-467c-9e82-f71948f35ca9",
   "offset": 377487360,
   "id": "0d3636f2-b899-467c-9e82-f71948f35ca9",
   "size": 20971520
 }
  
Actions
-------

TBD

.. comment
.. * :ref:`insert <exnode_insert>` Creates new Exnode.
.. * :ref:`list/query <exnode_list>` Return all Exnodes registered in the UNIS instance.
.. * :ref:`get <exnode_get>` Return Exnode representation.
.. * :ref:`update <exnode_update>` Update the specified Exnode.
.. * :ref:`delete <exnode_delete>` Delete a Exnode.
.. * :ref:`patch <exnode_patch>` patch the specified Exnode.

Extensions
----------

.. toctree::
   :maxdepth: 2

   ceph_extent.rst
   ibp_extent.rst
