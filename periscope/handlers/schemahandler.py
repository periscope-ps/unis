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

import periscope.settings as settings
import tornado.web

class SchemaHandler(tornado.web.RequestHandler):
    def initialize(self, base_url):
        None
    def get(self, res_id=None):
        """Handles HTTP GET"""
        args = self.request.arguments
        if 'name' in args.keys() and "node" in settings.SCHEMAS:
            """ Return schema json """  
            self.write(schemaLoader.get(settings.SCHEMAS["node"]))
        else:
            self.write(settings.SCHEMAS)                    
        self.finish()
