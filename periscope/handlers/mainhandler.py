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
#!/usr/bin/env python

import tornado.web
import json

from periscope.settings import MIME

class MainHandler(tornado.web.RequestHandler):
    def initialize(self, base_url, resources):
        self._resources = resources
    
    def get(self):
        links = []
        for resource in self._resources:
            href = "%s://%s%s" % (self.request.protocol,
                self.request.host, self.reverse_url(resource))
            links.append({"href": href, "rel": "full"})
        self.set_header("Content-Type", MIME["JSON"])
        self.write(json.dumps(links, indent=4))
