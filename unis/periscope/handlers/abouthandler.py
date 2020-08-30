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
from pymongo import MongoClient
from uuid import uuid4
from periscope.settings import MIME, Resources

class AboutHandler(object):
        
    def on_get(self, req, resp):

        self._mongo = MongoClient('localhost', 27017)
    
        uuid = self._mongo.unis_db['about'].find()[0]['uuid']
        
        about = {
            "uid": str(uuid),
            "haschild": "false",
            "depth": 0
        }

        resp.set_header("Content-Type", MIME["JSON"])
        resp.body = json.dumps(about, indent=4)
