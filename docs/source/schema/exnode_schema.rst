.. _exnode_schema:

Exnode Representation
=======================

Extends None

An Exnode is metadata describing a file.  Chunks of a file are represented as
:ref:`Extents <extent_schema>`.


JSON Schema
-----------
See `<http://unis.crest.iu.edu/schema/exnode/6/exnode>`_.

Attributes
~~~~~~~~~~
The following table contains only the Exnode required attributes.

.. tabularcolumns:: |l|l|J|

+---------------+-----------+--------------------------------------------------+
| Name          | Value     | Description                                      |
+===============+===========+==================================================+
| id            | string    | The Exnode identifier.                           |
+---------------+-----------+--------------------------------------------------+
| selfRef       | string    | Self hyperlink reference for the Exnode.         |
+---------------+-----------+--------------------------------------------------+
| mode          | enum      | The Exnode type: "file" or "directory"           |
+---------------+-----------+--------------------------------------------------+
| parent        | string    | A hyperlink to the Exnode parent resource, or    |  
|               |           | null.                                            |
+---------------+-----------+--------------------------------------------------+
| created       | integer   | 64-bit Integer timestamp of the Exnode creation  |
|               |           | date.                                            |
+---------------+-----------+--------------------------------------------------+
| modified      | integer   | 64-bit Integer timestamp of the Exnode modified  |
|               |           | date.                                            |
+---------------+-----------+--------------------------------------------------+
| size          | integer   | Size of the file in bytes.                       |
+---------------+-----------+--------------------------------------------------+
| owner         | string    | User ID of file.                                 |
+---------------+-----------+--------------------------------------------------+
| group         | string    | Group ID of file.                                |
+---------------+-----------+--------------------------------------------------+
| permission    | string    | File permission in owner-group-other rwx format, |
|               |           | e.g 766 rwx-rw--rw-                              |
+---------------+-----------+--------------------------------------------------+


Example::
~~~~~~~~~~

The following is an Exnode resource example::

 {
   "status": "UNKNOWN", 
   "$schema": "http://unis.crest.iu.edu/schema/exnode/6/exnode#", 
   "extents": [], 
   "description": "", 
   "parent": null, 
   "permission": "644", 
   "urn": "", 
   "created": 1493065033787554, 
   "selfRef": "http://dev.crest.iu.edu:8888/exnodes/752df622-8401-4725-aa20-a09676365c37", 
   "modified": 0, 
   "id": "752df622-8401-4725-aa20-a09676365c37", 
   "ts": 1493065035968319, 
   "owner": "kissel", 
   "group": "kissel", 
   "mode": "file", 
   "size": 1048576000, 
   "properties": {}, 
   "name": "temp"
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
