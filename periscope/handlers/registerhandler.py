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
import tornado.gen
import tornado.websocket

from tornado.httpclient import AsyncHTTPClient

from periscope import settings
from periscope.settings import MIME
from periscope.models import Manifest, ObjectDict
from networkresourcehandler import NetworkResourceHandler

class RegisterHandler(NetworkResourceHandler):
    @tornado.gen.coroutine
    def _insert(self, resources):
        accessPoint = resources[0]["accessPoint"]
        tmpExists = yield self.dblayer.find_one({ "accessPoint": accessPoint })
        self.application._depth = max(self.application._depth, resources[0]["properties"]["depth"] + 1)
        if tmpExists:
            yield self.dblayer.update({ "accessPoint": accessPoint }, resources[0], replace = True, multi=False)
        else:
            yield self.dblayer.insert(resources)
        
        for manifest in resources[0]["properties"]["summary"]:
            manifest = ObjectDict._from_mongo(manifest)
            manifest["href"] = accessPoint
            manifest["ttl"] = resources[0]["ttl"]
            manifest.pop(self.timestamp, 0)
            yield self._update_manifest(manifest, accessPoint)
        
    @tornado.gen.coroutine
    def _update_manifest(self, manifest, source):
        tmpDB = self.application.get_db_layer(manifest["$collection"], self.Id, self.timestamp, False, 0)
        tmpManifest = yield tmpDB.find_one({ "href": source })
        mongoManifest = dict(Manifest(manifest)._to_mongoiter())
        if tmpManifest:
            yield tmpDB.update({ "href": source }, mongoManifest, replace = True)
        else:
            yield tmpDB.insert(mongoManifest)
