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

import json
from periscope.settings import MIME, Resources

class MainHandler(object):
        
    def on_get(self, req, resp):

        links = []
        resources = ["links", "ports", "nodes", "services", "paths", "networks", "domains", "topologies", "events", "data", "metadata", "measurements", "exnodes", "extents"]
        
        for resource in resources:
            href = "%s://%s/%s" % (req.scheme, req.host, resource)
            
            links.append({ "href": href, 
                           "rel": "full",
                           "targetschema": { "type": "array", "items": { "rel": "full", "href": Resources[resource]["schema"][MIME["PSJSON"]] } } })
        
        resp.set_header("Content-Type", MIME["JSON"])
        resp.body = json.dumps(links, indent=4)
