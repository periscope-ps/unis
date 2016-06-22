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

import json
import functools
from tornado.ioloop import IOLoop
import tornado.web


from periscope.settings import MIME
from networkresourcehandler import NetworkResourceHandler
from periscope.db import dumps_mongo


class ExtentHandler(NetworkResourceHandler):
    @tornado.gen.coroutine
    def _process_resource(self, resource, res_id = None, run_validate = True):
        if self.Id in resource:
            raise ValueError("Extent may not include id field in POST, use PUT for updates")
        
        tmpResource = self._model_class(resource)
        tmpResource = self._add_post_metadata(tmpResource)
        
        if run_validate == True:
            tmpResource._validate()
            
        ppi_classes = getattr(self.application, '_ppi_classes', [])
        for pp in ppi_classes:
            pp.pre_post(tmpResource, self.application, self.request, Handler = self)
            
        raise tornado.gen.Return(tmpResource)
