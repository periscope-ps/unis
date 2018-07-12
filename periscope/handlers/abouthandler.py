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

class AboutHandler(tornado.web.RequestHandler):
    def initialize(self, **kwargs):
        pass
        
    def get(self):
        about = {
            "uid": str(self.application.options["uuid"]),
            "haschild": self.application.options["lookup"],
            "depth": self.application._depth
        }
        self.set_header("Content-Type", MIME["JSON"])
        self.write(json.dumps(about, indent=4))
