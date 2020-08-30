#!/usr/bin/env python
# =============================================================================
#  periscope-ps (unis)
#
#  Copyright (c) 2012-2016, Trustees of Indiana University,
#  All rights reserved.
#
#  This software may be modified and distributed under the terms of the BSD
#  license.  See the COPYING file for details.
#
#  This software was created at the Indiana University Center for Research in
#  Extreme Scale Technologies (CREST).
# =============================================================================

from periscope import settings

class SchemaHandler(object):
    def on_get(self, req, resp, res_id=None):
        """Handles HTTP GET"""
        args = self.req.params
        buf = []
        if 'name' in args.keys() and "node" in settings.SCHEMAS:
            """ Return schema json """  
            buf = schemaLoader.get(settings.SCHEMAS["node"])
        else:
            buf = settings.SCHEMAS
        resp.body = json.dumps(buf, indent=4)

