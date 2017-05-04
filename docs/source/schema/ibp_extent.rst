.. _ibp_extent_schema:

IBP Representation
=======================

Extends :ref:`Extent <extent_schema>`

JSON Schema
-----------
See `<http://unis.crest.iu.edu/schema/exnode/ext/1/ibp>`_.

Attributes
~~~~~~~~~~
The following table contains only the IBP required attributes and exludes those
inherited from :ref:`Extent <extent_schema>`.

.. tabularcolumns:: |l|l|J|

+---------------+-----------+--------------------------------------------------+
| Name          | Value     | Description                                      |
+===============+===========+==================================================+
+---------------+-----------+--------------------------------------------------+
| mapping       | object    | The read/write/manage URI mappings for IBP.      |
+---------------+-----------+--------------------------------------------------+
| alloc_length  | integer   | Equivalent to the Extent size.                   |
+---------------+-----------+--------------------------------------------------+
| alloc_offset  | integer   | Equivalent to the Extent offset.                 |
+---------------+-----------+--------------------------------------------------+

Example::
~~~~~~~~~~

The following is an IBP Extent resource example::

  

